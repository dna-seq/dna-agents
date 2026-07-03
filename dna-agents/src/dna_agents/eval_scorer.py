"""
Evaluation scorer for comparing agent-produced modules against ground truth.

Ground truth can be:
    - A module spec directory (variants.csv + studies.csv)
    - A compiled parquet directory (weights.parquet + studies.parquet)
    - An HF module name (loaded directly from just-dna-seq/annotators)

Scores agent output on multiple dimensions:
    - Variant recall / precision (rsid coverage)
    - Genotype completeness (all expected genotypes present)
    - Weight accuracy (MAE of weights for matched genotypes)
    - Weight direction (risk/protective state agreement)
    - PMID recall / precision (study citation coverage)
    - Gene assignment accuracy

Public API:
    score_module(candidate_dir, reference, rsid_filter=None) -> EvalScore
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DimensionScore:
    name: str
    score: float
    max_score: float
    details: list[str] = field(default_factory=list)

    @property
    def normalized(self) -> float:
        return self.score / self.max_score if self.max_score > 0 else 0.0


@dataclass
class EvalScore:
    """Aggregated evaluation score across all dimensions."""

    variant_recall: DimensionScore
    variant_precision: DimensionScore
    genotype_completeness: DimensionScore
    weight_accuracy: DimensionScore
    weight_direction: DimensionScore
    pmid_recall: DimensionScore
    pmid_precision: DimensionScore
    gene_accuracy: DimensionScore

    @property
    def dimensions(self) -> list[DimensionScore]:
        return [
            self.variant_recall,
            self.variant_precision,
            self.genotype_completeness,
            self.weight_accuracy,
            self.weight_direction,
            self.pmid_recall,
            self.pmid_precision,
            self.gene_accuracy,
        ]

    @property
    def overall(self) -> float:
        """Weighted overall score [0, 1]."""
        weights = {
            "variant_recall": 2.0,
            "variant_precision": 1.0,
            "genotype_completeness": 1.5,
            "weight_accuracy": 1.0,
            "weight_direction": 1.5,
            "pmid_recall": 1.5,
            "pmid_precision": 0.5,
            "gene_accuracy": 1.0,
        }
        total_w = sum(weights.values())
        weighted_sum = sum(
            getattr(self, name).normalized * w
            for name, w in weights.items()
        )
        return weighted_sum / total_w

    def summary(self) -> str:
        lines = [f"Overall score: {self.overall:.2%}", ""]
        for d in self.dimensions:
            lines.append(f"  {d.name}: {d.normalized:.2%} ({d.score:.1f}/{d.max_score:.1f})")
            for detail in d.details[:3]:
                lines.append(f"    - {detail}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "overall": round(self.overall, 4),
            "dimensions": {
                d.name: {
                    "normalized": round(d.normalized, 4),
                    "score": round(d.score, 2),
                    "max_score": round(d.max_score, 2),
                    "details": d.details,
                }
                for d in self.dimensions
            },
        }


def _load_variants_csv(spec_dir: Path) -> dict[str, list[dict]]:
    """Load variants.csv, grouped by rsid."""
    path = spec_dir / "variants.csv"
    if not path.exists():
        return {}

    by_rsid: dict[str, list[dict]] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rsid = (row.get("rsid") or "").strip()
            if rsid:
                by_rsid.setdefault(rsid, []).append(row)
    return by_rsid


def _load_studies_csv(spec_dir: Path) -> dict[str, set[str]]:
    """Load studies.csv, returning {rsid: set of pmids}."""
    path = spec_dir / "studies.csv"
    if not path.exists():
        return {}

    by_rsid: dict[str, set[str]] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rsid = (row.get("rsid") or "").strip()
            pmid = (row.get("pmid") or "").strip()
            if rsid and pmid:
                by_rsid.setdefault(rsid, set()).add(pmid)
    return by_rsid


def _load_variants_parquet(
    parquet_dir: Path,
    rsid_filter: Optional[set[str]] = None,
) -> dict[str, list[dict]]:
    """Load variants from parquet (weights + annotations), grouped by rsid."""
    import polars as pl

    weights_path = parquet_dir / "weights.parquet"
    if not weights_path.exists():
        return {}

    wdf = pl.read_parquet(weights_path)
    if rsid_filter:
        wdf = wdf.filter(pl.col("rsid").is_in(list(rsid_filter)))

    ann_lookup: dict[str, dict] = {}
    ann_path = parquet_dir / "annotations.parquet"
    if ann_path.exists():
        adf = pl.read_parquet(ann_path)
        if rsid_filter:
            adf = adf.filter(pl.col("rsid").is_in(list(rsid_filter)))
        for row in adf.iter_rows(named=True):
            ann_lookup[row["rsid"]] = {
                "gene": row.get("gene", ""),
                "phenotype": row.get("phenotype", ""),
                "category": row.get("category", ""),
            }

    by_rsid: dict[str, list[dict]] = {}
    for row in wdf.iter_rows(named=True):
        rsid = row.get("rsid", "")
        if not rsid:
            continue
        genotype_raw = row.get("genotype")
        if isinstance(genotype_raw, list):
            genotype = "/".join(sorted(genotype_raw))
        else:
            genotype = str(genotype_raw) if genotype_raw else ""

        ann = ann_lookup.get(rsid, {})
        entry = {
            "rsid": rsid,
            "genotype": genotype,
            "weight": str(row.get("weight", 0)),
            "state": row.get("state", ""),
            "conclusion": row.get("conclusion", ""),
            "gene": ann.get("gene", row.get("gene", "")),
            "phenotype": ann.get("phenotype", row.get("phenotype", "")),
            "category": ann.get("category", row.get("category", "")),
        }
        by_rsid.setdefault(rsid, []).append(entry)

    return by_rsid


def _load_studies_parquet(
    parquet_dir: Path,
    rsid_filter: Optional[set[str]] = None,
) -> dict[str, set[str]]:
    """Load studies from parquet, returning {rsid: set of pmids}."""
    import polars as pl

    path = parquet_dir / "studies.parquet"
    if not path.exists():
        return {}

    sdf = pl.read_parquet(path)
    if rsid_filter:
        sdf = sdf.filter(pl.col("rsid").is_in(list(rsid_filter)))

    by_rsid: dict[str, set[str]] = {}
    for row in sdf.iter_rows(named=True):
        rsid = (row.get("rsid") or "").strip()
        pmid = str(row.get("pmid", "")).strip()
        if rsid and pmid:
            by_rsid.setdefault(rsid, set()).add(pmid)
    return by_rsid


def _load_from_hf(
    module_name: str,
    rsid_filter: Optional[set[str]] = None,
) -> tuple[dict[str, list[dict]], dict[str, set[str]]]:
    """Load variants and studies directly from HF parquet."""
    import polars as pl

    hf_prefix = f"hf://datasets/just-dna-seq/annotators/data/{module_name}"

    wdf = pl.read_parquet(f"{hf_prefix}/weights.parquet")
    if rsid_filter:
        wdf = wdf.filter(pl.col("rsid").is_in(list(rsid_filter)))

    ann_lookup: dict[str, dict] = {}
    try:
        adf = pl.read_parquet(f"{hf_prefix}/annotations.parquet")
        if rsid_filter:
            adf = adf.filter(pl.col("rsid").is_in(list(rsid_filter)))
        for row in adf.iter_rows(named=True):
            ann_lookup[row["rsid"]] = {
                "gene": row.get("gene", ""),
                "phenotype": row.get("phenotype", ""),
                "category": row.get("category", ""),
            }
    except Exception:
        pass

    by_rsid: dict[str, list[dict]] = {}
    for row in wdf.iter_rows(named=True):
        rsid = row.get("rsid", "")
        if not rsid:
            continue
        genotype_raw = row.get("genotype")
        if isinstance(genotype_raw, list):
            genotype = "/".join(sorted(genotype_raw))
        else:
            genotype = str(genotype_raw) if genotype_raw else ""

        ann = ann_lookup.get(rsid, {})
        entry = {
            "rsid": rsid,
            "genotype": genotype,
            "weight": str(row.get("weight", 0)),
            "state": row.get("state", ""),
            "conclusion": row.get("conclusion", ""),
            "gene": ann.get("gene", row.get("gene", "")),
            "phenotype": ann.get("phenotype", row.get("phenotype", "")),
            "category": ann.get("category", row.get("category", "")),
        }
        by_rsid.setdefault(rsid, []).append(entry)

    studies: dict[str, set[str]] = {}
    try:
        sdf = pl.read_parquet(f"{hf_prefix}/studies.parquet")
        if rsid_filter:
            sdf = sdf.filter(pl.col("rsid").is_in(list(rsid_filter)))
        for row in sdf.iter_rows(named=True):
            rsid = (row.get("rsid") or "").strip()
            pmid = str(row.get("pmid", "")).strip()
            if rsid and pmid:
                studies.setdefault(rsid, set()).add(pmid)
    except Exception:
        pass

    return by_rsid, studies


def _load_reference(
    reference: Path | str,
    rsid_filter: Optional[set[str]] = None,
) -> tuple[dict[str, list[dict]], dict[str, set[str]]]:
    """
    Load reference data from any supported source.

    Args:
        reference: One of:
            - Path to a spec dir (variants.csv)
            - Path to a parquet dir (weights.parquet)
            - HF module name string (e.g. "longevitymap")
        rsid_filter: Optional set of rsids to restrict to.
    """
    ref = str(reference)

    # HF module name (no slashes, no file extension)
    if "/" not in ref and "." not in ref and not Path(ref).exists():
        return _load_from_hf(ref, rsid_filter)

    ref_path = Path(ref)

    # Parquet directory
    if (ref_path / "weights.parquet").exists():
        variants = _load_variants_parquet(ref_path, rsid_filter)
        studies = _load_studies_parquet(ref_path, rsid_filter)
        if rsid_filter:
            variants = {k: v for k, v in variants.items() if k in rsid_filter}
            studies = {k: v for k, v in studies.items() if k in rsid_filter}
        return variants, studies

    # CSV spec directory
    variants = _load_variants_csv(ref_path)
    studies = _load_studies_csv(ref_path)
    if rsid_filter:
        variants = {k: v for k, v in variants.items() if k in rsid_filter}
        studies = {k: v for k, v in studies.items() if k in rsid_filter}
    return variants, studies


def _all_pmids(studies: dict[str, set[str]]) -> set[str]:
    return {pmid for pmids in studies.values() for pmid in pmids}


def score_module(
    candidate_dir: Path,
    reference: Path | str,
    rsid_filter: Optional[set[str]] = None,
) -> EvalScore:
    """
    Score a candidate module spec directory against a reference (ground truth).

    Args:
        candidate_dir: Path to candidate spec dir (variants.csv + studies.csv).
        reference: Ground truth source — spec dir, parquet dir, or HF module name.
        rsid_filter: Optional set of rsids to restrict scoring to.
    """
    candidate_dir = Path(candidate_dir)

    ref_variants, ref_studies = _load_reference(reference, rsid_filter)
    cand_variants = _load_variants_csv(candidate_dir)
    cand_studies = _load_studies_csv(candidate_dir)

    if rsid_filter:
        cand_variants = {k: v for k, v in cand_variants.items() if k in rsid_filter}
        cand_studies = {k: v for k, v in cand_studies.items() if k in rsid_filter}

    ref_rsids = set(ref_variants.keys())
    cand_rsids = set(cand_variants.keys())

    # -- Variant recall --
    found = ref_rsids & cand_rsids
    missing = ref_rsids - cand_rsids
    recall_details = []
    if missing:
        recall_details.append(f"Missing: {', '.join(sorted(missing))}")
    variant_recall = DimensionScore(
        name="variant_recall",
        score=float(len(found)),
        max_score=float(len(ref_rsids)),
        details=recall_details,
    )

    # -- Variant precision --
    extra = cand_rsids - ref_rsids
    precision_details = []
    if extra:
        precision_details.append(f"Extra: {', '.join(sorted(extra))}")
    variant_precision = DimensionScore(
        name="variant_precision",
        score=float(len(found)),
        max_score=float(len(cand_rsids)) if cand_rsids else 1.0,
        details=precision_details,
    )

    # -- Genotype completeness --
    total_expected = 0
    total_found = 0
    geno_details = []
    for rsid in found:
        ref_genos = {r["genotype"] for r in ref_variants[rsid]}
        cand_genos = {r["genotype"] for r in cand_variants[rsid]}
        total_expected += len(ref_genos)
        matched = ref_genos & cand_genos
        total_found += len(matched)
        missing_g = ref_genos - cand_genos
        if missing_g:
            geno_details.append(f"{rsid} missing genotypes: {', '.join(sorted(missing_g))}")

    genotype_completeness = DimensionScore(
        name="genotype_completeness",
        score=float(total_found),
        max_score=float(total_expected) if total_expected else 1.0,
        details=geno_details,
    )

    # -- Weight accuracy (MAE for matched genotypes) --
    weight_errors: list[float] = []
    weight_details: list[str] = []
    for rsid in found:
        ref_by_geno = {r["genotype"]: r for r in ref_variants[rsid]}
        cand_by_geno = {r["genotype"]: r for r in cand_variants[rsid]}
        for geno in ref_by_geno.keys() & cand_by_geno.keys():
            ref_w = _parse_weight(ref_by_geno[geno].get("weight"))
            cand_w = _parse_weight(cand_by_geno[geno].get("weight"))
            if ref_w is not None and cand_w is not None:
                err = abs(ref_w - cand_w)
                weight_errors.append(err)
                if err > 0.3:
                    weight_details.append(
                        f"{rsid} {geno}: expected {ref_w}, got {cand_w} (err={err:.2f})"
                    )

    if weight_errors:
        mae = sum(weight_errors) / len(weight_errors)
        weight_score = max(0.0, 1.0 - mae)
    else:
        weight_score = 0.0

    weight_accuracy = DimensionScore(
        name="weight_accuracy",
        score=weight_score,
        max_score=1.0,
        details=weight_details,
    )

    # -- Weight direction (state agreement) --
    total_state_checks = 0
    state_matches = 0
    direction_details: list[str] = []
    for rsid in found:
        ref_by_geno = {r["genotype"]: r for r in ref_variants[rsid]}
        cand_by_geno = {r["genotype"]: r for r in cand_variants[rsid]}
        for geno in ref_by_geno.keys() & cand_by_geno.keys():
            ref_state = (ref_by_geno[geno].get("state") or "").strip()
            cand_state = (cand_by_geno[geno].get("state") or "").strip()
            if ref_state:
                total_state_checks += 1
                if ref_state == cand_state:
                    state_matches += 1
                else:
                    direction_details.append(
                        f"{rsid} {geno}: expected '{ref_state}', got '{cand_state}'"
                    )

    weight_direction = DimensionScore(
        name="weight_direction",
        score=float(state_matches),
        max_score=float(total_state_checks) if total_state_checks else 1.0,
        details=direction_details,
    )

    # -- PMID recall --
    ref_pmids = _all_pmids(ref_studies)
    cand_pmids = _all_pmids(cand_studies)
    found_pmids = ref_pmids & cand_pmids
    missing_pmids = ref_pmids - cand_pmids
    pmid_recall_details = []
    if missing_pmids:
        pmid_recall_details.append(f"Missing PMIDs: {', '.join(sorted(missing_pmids))}")

    pmid_recall = DimensionScore(
        name="pmid_recall",
        score=float(len(found_pmids)),
        max_score=float(len(ref_pmids)) if ref_pmids else 1.0,
        details=pmid_recall_details,
    )

    # -- PMID precision --
    extra_pmids = cand_pmids - ref_pmids
    pmid_prec_details = []
    if extra_pmids:
        pmid_prec_details.append(f"Extra PMIDs: {', '.join(sorted(extra_pmids))}")

    pmid_precision = DimensionScore(
        name="pmid_precision",
        score=float(len(found_pmids)),
        max_score=float(len(cand_pmids)) if cand_pmids else 1.0,
        details=pmid_prec_details,
    )

    # -- Gene accuracy --
    total_gene_checks = 0
    gene_matches = 0
    gene_details: list[str] = []
    for rsid in found:
        ref_genes = {(r.get("gene") or "").strip().upper() for r in ref_variants[rsid]} - {""}
        cand_genes = {(r.get("gene") or "").strip().upper() for r in cand_variants[rsid]} - {""}
        if ref_genes:
            total_gene_checks += 1
            if ref_genes & cand_genes:
                gene_matches += 1
            else:
                gene_details.append(
                    f"{rsid}: expected {ref_genes}, got {cand_genes or '(none)'}"
                )

    gene_accuracy = DimensionScore(
        name="gene_accuracy",
        score=float(gene_matches),
        max_score=float(total_gene_checks) if total_gene_checks else 1.0,
        details=gene_details,
    )

    return EvalScore(
        variant_recall=variant_recall,
        variant_precision=variant_precision,
        genotype_completeness=genotype_completeness,
        weight_accuracy=weight_accuracy,
        weight_direction=weight_direction,
        pmid_recall=pmid_recall,
        pmid_precision=pmid_precision,
        gene_accuracy=gene_accuracy,
    )


def _parse_weight(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    val = str(val).strip()
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None
