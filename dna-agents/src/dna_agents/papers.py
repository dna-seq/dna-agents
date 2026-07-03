"""
Paper downloader using the EuropePMC REST API.

Downloads metadata and open-access full text for PMIDs referenced in
module spec studies.csv files. Useful for grounding agent evals with
the actual papers the agents should be citing.

Public API:
    fetch_paper_metadata(pmid) -> PaperMetadata
    fetch_full_text(pmid)      -> str | None
    download_papers(pmids, output_dir) -> list[DownloadResult]
    extract_pmids(spec_dir)    -> list[str]
"""

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx

EUROPEPMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest"
PMID_RE = re.compile(r"\d+")


@dataclass
class PaperMetadata:
    pmid: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    year: str = ""
    doi: str = ""
    abstract: str = ""
    is_open_access: bool = False
    pmc_id: str = ""

    def to_dict(self) -> dict:
        return {
            "pmid": self.pmid,
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "year": self.year,
            "doi": self.doi,
            "abstract": self.abstract,
            "is_open_access": self.is_open_access,
            "pmc_id": self.pmc_id,
        }


@dataclass
class DownloadResult:
    pmid: str
    success: bool
    metadata_path: Path | None = None
    fulltext_path: Path | None = None
    error: str = ""


def extract_pmids(spec_dir: Path) -> list[str]:
    """Extract unique PMIDs from a module spec's studies.csv."""
    studies_path = Path(spec_dir) / "studies.csv"
    if not studies_path.exists():
        return []

    pmids: set[str] = set()
    with open(studies_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            raw = (row.get("pmid") or "").strip()
            match = PMID_RE.search(raw)
            if match:
                pmids.add(match.group())

    return sorted(pmids)


def fetch_paper_metadata(pmid: str, client: httpx.Client | None = None) -> PaperMetadata:
    """Fetch paper metadata from EuropePMC by PMID."""
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=30)
    try:
        url = f"{EUROPEPMC_API}/search"
        params = {
            "query": f"EXT_ID:{pmid} AND SRC:MED",
            "format": "json",
            "resultType": "core",
            "pageSize": 1,
        }
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("resultList", {}).get("result", [])
        if not results:
            return PaperMetadata(pmid=pmid)

        paper = results[0]
        authors_raw = paper.get("authorList", {}).get("author", [])
        authors = [
            a.get("fullName", a.get("lastName", ""))
            for a in authors_raw
            if isinstance(a, dict)
        ]

        journal_info = paper.get("journalInfo", {})
        journal_obj = journal_info.get("journal", {})
        journal_title = (
            journal_obj.get("title", "")
            or paper.get("journalTitle", "")
        )

        return PaperMetadata(
            pmid=pmid,
            title=paper.get("title", ""),
            authors=authors,
            journal=journal_title,
            year=str(paper.get("pubYear", "")),
            doi=paper.get("doi", "") or "",
            abstract=paper.get("abstractText", ""),
            is_open_access=paper.get("isOpenAccess", "N") == "Y",
            pmc_id=paper.get("pmcid", "") or "",
        )
    finally:
        if own_client:
            client.close()


def fetch_full_text(pmid: str, client: httpx.Client | None = None) -> str | None:
    """
    Fetch full text XML from EuropePMC for open-access papers.

    Returns the XML string if available, None otherwise.
    First resolves the PMC ID, then fetches from the full text endpoint.
    """
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=60)
    try:
        meta = fetch_paper_metadata(pmid, client)
        if not meta.pmc_id:
            return None

        url = f"{EUROPEPMC_API}/{meta.pmc_id}/fullTextXML"
        resp = client.get(url)
        if resp.status_code == 200 and resp.text.strip():
            return resp.text
        return None
    finally:
        if own_client:
            client.close()


def download_papers(
    pmids: list[str],
    output_dir: Path,
    include_fulltext: bool = True,
) -> list[DownloadResult]:
    """
    Download metadata and optionally full text for a list of PMIDs.

    Creates output_dir with:
      - metadata/<pmid>.json   (always)
      - fulltext/<pmid>.xml    (if open-access and available)
      - index.json             (summary of all downloads)
    """
    output_dir = Path(output_dir)
    meta_dir = output_dir / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    if include_fulltext:
        text_dir = output_dir / "fulltext"
        text_dir.mkdir(parents=True, exist_ok=True)

    results: list[DownloadResult] = []

    with httpx.Client(timeout=30) as client:
        for pmid in pmids:
            result = DownloadResult(pmid=pmid, success=False)
            try:
                meta = fetch_paper_metadata(pmid, client)
                meta_path = meta_dir / f"{pmid}.json"
                meta_path.write_text(
                    json.dumps(meta.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                result.metadata_path = meta_path
                result.success = True

                if include_fulltext and meta.pmc_id:
                    xml = fetch_full_text(pmid, client)
                    if xml:
                        ft_path = text_dir / f"{pmid}.xml"
                        ft_path.write_text(xml, encoding="utf-8")
                        result.fulltext_path = ft_path

            except Exception as e:
                result.error = str(e)

            results.append(result)

    index = {
        "total": len(results),
        "success": sum(1 for r in results if r.success),
        "with_fulltext": sum(1 for r in results if r.fulltext_path),
        "papers": [
            {
                "pmid": r.pmid,
                "success": r.success,
                "has_metadata": r.metadata_path is not None,
                "has_fulltext": r.fulltext_path is not None,
                "error": r.error or None,
            }
            for r in results
        ],
    }
    (output_dir / "index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )

    return results
