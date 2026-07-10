"""
Smoke tests for the library-backed compiler seam.

After retiring the local spec/compiler, dna-agents consumes just-dna-format + just-dna-compiler
directly. These tests confirm the imports resolve to the libraries and that an offline compile of a
bundled fixture produces the expected artifact (three parquet tables + manifest.json).
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


def test_resolver_helper_is_provisioning_only():
    # The local resolver is now a thin provisioning wrapper; resolution lives in the library.
    from dna_agents.resolver import ensure_resolver_reference  # noqa: F401


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
