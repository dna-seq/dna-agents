"""Tests for the eval scorer: comparing candidate modules against ground truth."""

import csv
from pathlib import Path

import pytest

from dna_agents.eval_scorer import score_module


EVALS_DIR = Path(__file__).parent.parent / "data" / "evals"


class TestEvalScorerPerfectMatch:
    """Scoring a directory against itself should yield 100%."""

    def test_cyp_panel_self_score(self):
        ref = EVALS_DIR / "cyp_panel"
        result = score_module(ref, ref)
        assert result.variant_recall.normalized == 1.0
        assert result.variant_precision.normalized == 1.0
        assert result.genotype_completeness.normalized == 1.0
        assert result.weight_direction.normalized == 1.0
        assert result.pmid_recall.normalized == 1.0
        assert result.pmid_precision.normalized == 1.0
        assert result.gene_accuracy.normalized == 1.0
        assert result.overall == pytest.approx(1.0, abs=0.01)

    def test_sirtuin_self_score(self):
        ref = EVALS_DIR / "sirtuin_longevity"
        result = score_module(ref, ref)
        assert result.overall == pytest.approx(1.0, abs=0.01)


class TestEvalScorerPartialMatch:
    """Test scoring with a deliberately degraded candidate."""

    @pytest.fixture
    def partial_candidate(self, tmp_path):
        """Create a candidate with only 3 of 7 CYP variants, one wrong weight."""
        ref = EVALS_DIR / "cyp_panel"

        cand_dir = tmp_path / "candidate"
        cand_dir.mkdir()

        # Copy only first 3 variants (rs4244285 has 3 genotype rows)
        with open(ref / "variants.csv", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        # Keep only rs4244285 and rs4986893 (6 rows), skip the rest
        kept_rsids = {"rs4244285", "rs4986893"}
        kept_rows = [r for r in rows if r["rsid"] in kept_rsids]

        # Flip one weight to test weight accuracy
        for r in kept_rows:
            if r["rsid"] == "rs4244285" and r["genotype"] == "A/A":
                r["weight"] = "-1.0"  # was -1.5

        with open(cand_dir / "variants.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(kept_rows)

        # Copy only some studies
        with open(ref / "studies.csv", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            study_fields = reader.fieldnames
            study_rows = [r for r in reader if r["rsid"] in kept_rsids]

        with open(cand_dir / "studies.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=study_fields)
            writer.writeheader()
            writer.writerows(study_rows)

        return cand_dir

    def test_partial_variant_recall(self, partial_candidate):
        ref = EVALS_DIR / "cyp_panel"
        result = score_module(partial_candidate, ref)
        # 2 of 7 rsids found
        assert result.variant_recall.score == 2.0
        assert result.variant_recall.max_score == 7.0
        assert result.variant_recall.normalized == pytest.approx(2 / 7, abs=0.01)

    def test_partial_precision_is_perfect(self, partial_candidate):
        ref = EVALS_DIR / "cyp_panel"
        result = score_module(partial_candidate, ref)
        # All candidate rsids are in reference
        assert result.variant_precision.normalized == 1.0

    def test_partial_weight_accuracy(self, partial_candidate):
        ref = EVALS_DIR / "cyp_panel"
        result = score_module(partial_candidate, ref)
        # Weight accuracy should be less than perfect (one weight is off by 0.5)
        assert result.weight_accuracy.normalized < 1.0
        assert result.weight_accuracy.normalized > 0.5

    def test_partial_overall_below_100(self, partial_candidate):
        ref = EVALS_DIR / "cyp_panel"
        result = score_module(partial_candidate, ref)
        assert result.overall < 0.9
        assert result.overall > 0.1

    def test_summary_string(self, partial_candidate):
        ref = EVALS_DIR / "cyp_panel"
        result = score_module(partial_candidate, ref)
        s = result.summary()
        assert "Overall score:" in s
        assert "variant_recall" in s

    def test_to_dict(self, partial_candidate):
        ref = EVALS_DIR / "cyp_panel"
        result = score_module(partial_candidate, ref)
        d = result.to_dict()
        assert "overall" in d
        assert "dimensions" in d
        assert "variant_recall" in d["dimensions"]


class TestEvalScorerEmptyCandidate:
    """Edge case: empty or minimal candidate."""

    def test_empty_candidate(self, tmp_path):
        cand = tmp_path / "empty"
        cand.mkdir()
        (cand / "variants.csv").write_text("rsid,genotype,weight,state,conclusion\n")
        (cand / "studies.csv").write_text("rsid,pmid\n")

        ref = EVALS_DIR / "cyp_panel"
        result = score_module(cand, ref)
        assert result.variant_recall.normalized == 0.0
        assert result.overall < 0.1


class TestEvalScorerExtraVariants:
    """Candidate has extra variants not in reference."""

    def test_extra_rsids_reduce_precision(self, tmp_path):
        ref = EVALS_DIR / "cyp_panel"

        cand = tmp_path / "extra"
        cand.mkdir()

        # Copy all reference variants plus add a fake one
        with open(ref / "variants.csv", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        fake_row = dict(rows[0])
        fake_row["rsid"] = "rs999999"
        fake_row["genotype"] = "A/G"
        rows.append(fake_row)

        with open(cand / "variants.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        result = score_module(cand, ref)
        assert result.variant_recall.normalized == 1.0
        assert result.variant_precision.normalized < 1.0
        assert "rs999999" in result.variant_precision.details[0]
