"""Tests for the paper downloader."""

import csv
from pathlib import Path

import pytest

from dna_agents.papers import extract_pmids


EVALS_DIR = Path(__file__).parent.parent / "data" / "evals"


class TestExtractPmids:
    """Test PMID extraction from studies.csv files."""

    def test_cyp_panel_pmids(self):
        pmids = extract_pmids(EVALS_DIR / "cyp_panel")
        assert len(pmids) >= 5
        assert "17622601" in pmids
        assert "21270786" in pmids
        assert "27441996" in pmids
        assert "22992668" in pmids
        assert "24458010" in pmids

    def test_sirtuin_pmids(self):
        pmids = extract_pmids(EVALS_DIR / "sirtuin_longevity")
        assert len(pmids) >= 7
        assert "22234866" in pmids
        assert "23839864" in pmids
        assert "20633545" in pmids

    def test_empty_dir(self, tmp_path):
        pmids = extract_pmids(tmp_path)
        assert pmids == []

    def test_pmids_sorted_and_unique(self):
        pmids = extract_pmids(EVALS_DIR / "cyp_panel")
        assert pmids == sorted(set(pmids))


@pytest.mark.integration
class TestPaperDownload:
    """Integration tests requiring network access to EuropePMC."""

    def test_fetch_single_metadata(self):
        from dna_agents.papers import fetch_paper_metadata

        meta = fetch_paper_metadata("17622601")
        assert meta.pmid == "17622601"
        assert meta.title  # should have a title
        assert meta.journal
        assert meta.authors

    def test_download_to_dir(self, tmp_path):
        from dna_agents.papers import download_papers

        results = download_papers(["17622601"], tmp_path)
        assert len(results) == 1
        assert results[0].success
        assert results[0].metadata_path.exists()
        assert (tmp_path / "index.json").exists()
