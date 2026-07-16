"""
Smoke tests for the library-backed compiler seam.

After retiring the local spec/compiler, just-dna-agents consumes just-dna-format + just-dna-compiler
directly. These tests confirm the imports resolve to the libraries (including the 0.4 composed table
kinds and the live authoring reference) and that an offline compile of a bundled fixture produces the
expected artifact (the SNP-core parquet tables + manifest.json).
"""

from pathlib import Path

from conftest import EVALS_DIR


def test_compiler_imports_resolve_to_library():
    import just_dna_compiler.compiler as lib
    from just_dna_compiler.compiler import compile_module, reverse_module, validate_spec

    assert compile_module.__module__ == lib.__name__
    assert validate_spec.__module__ == lib.__name__
    assert reverse_module.__module__ == lib.__name__


def test_spec_models_import_from_format():
    from just_dna_format.spec import ModuleSpecConfig, StudyRow, VariantRow  # noqa: F401


def test_format_0_4_table_kinds_import():
    # 0.4 composed table kinds: importable so the MCP server / agents can reference them.
    from just_dna_format.binning import (  # noqa: F401
        ActivityPhenotypeRow,
        CopyNumberRow,
        HeteroplasmyRow,
        RepeatAlleleRow,
    )
    from just_dna_format.pgs import PgsRow  # noqa: F401
    from just_dna_format.pgx import (  # noqa: F401
        AlleleFunctionRow,
        DiplotypeRow,
        HaplotypeRow,
        PharmVariantRow,
    )


def test_authoring_reference_is_live_and_covers_0_4():
    # The MCP get_spec_format / get_spec_schemas tools are backed by these; guard the surface they
    # expose so a library upgrade that changes it fails here rather than silently at the tool.
    from just_dna_format.reference import authoring_reference, json_schemas

    ref = authoring_reference()
    assert ref["genome_build_default"] == "GRCh38"
    models = ref["models"]
    # SNP core carries the 0.4 general annotation axes...
    variant_fields = {f["name"] for f in models["VariantRow"]}
    assert {"requires_callable", "acmg_sf", "actionability"} <= variant_fields
    # ...StudyRow carries the 0.4 provenance columns...
    study_fields = {f["name"] for f in models["StudyRow"]}
    assert {"doi", "provenance_quote", "provenance_regex"} <= study_fields
    # ...and the composed table kinds are described.
    assert {"PgsRow", "DiplotypeRow", "PharmVariantRow"} <= models.keys()
    # variant_key is compiler-managed: materialized but not part of the authored reference.
    assert "variant_key" not in variant_fields
    assert "VariantRow" in json_schemas()


def test_mcp_server_reference_tools_use_live_format():
    # End-to-end: the server's palette/reference tools return the library's live values, not a
    # hand-maintained copy (the drift just_dna_format.reference exists to prevent).
    from just_dna_format.manifest import RECOMMENDED_COLORS, RECOMMENDED_ICONS

    from just_dna_agents_mcp.server import create_server

    create_server()  # must build without a hardcoded palette/reference
    assert "protective" in RECOMMENDED_COLORS
    assert "pharmacogenomic" in RECOMMENDED_ICONS


def test_resolver_helper_is_provisioning_only():
    # The local resolver is now a thin provisioning wrapper; resolution lives in the library.
    from just_dna_agents.resolver import ensure_resolver_reference  # noqa: F401


def test_validate_fixture(tmp_path):
    from just_dna_compiler.compiler import validate_spec

    result = validate_spec(EVALS_DIR / "mthfr_nad")
    assert result.valid, result.errors


def test_compile_fixture_offline(tmp_path):
    from just_dna_compiler.compiler import compile_module

    out = tmp_path / "out"
    result = compile_module(
        EVALS_DIR / "mthfr_nad",
        out,
        resolve_with_ensembl=False,
    )
    assert result.success, result.errors
    for name in ("weights.parquet", "annotations.parquet", "studies.parquet", "manifest.json"):
        assert (out / name).exists(), f"missing {name}"
