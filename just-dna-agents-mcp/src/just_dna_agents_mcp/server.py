"""
FastMCP server wrapping the just_dna_agents module compiler tools.

Exposes validation, compilation, spec format reference, and
icon/color listing as MCP tools.

The spec-format reference and the recommended icon/colour palettes are NOT hand-maintained here.
They are read live from ``just_dna_format`` — ``reference.authoring_reference()`` and
``manifest.RECOMMENDED_ICONS`` / ``RECOMMENDED_COLORS`` — so they cannot drift from the schema the
compiler actually enforces (the exact failure mode ``just_dna_format.reference`` was written to kill:
its docstring names this server's old ``get_spec_format`` as the drift it replaces).
"""

from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.utilities.tasks import TaskConfig

from just_dna_agents_mcp.config import Settings, get_settings

# Every tool may run synchronously or be promoted to a background task
# by the client (the MCP background-task protocol).
TASK = TaskConfig(mode="optional")


def create_server(settings: Settings | None = None) -> FastMCP:
    """Build and configure the DNA Agents MCP server."""
    settings = settings or get_settings()
    mcp: FastMCP = FastMCP(
        "just-dna-agents-mcp",
        instructions=(
            "DNA annotation module compiler tools. Validate and compile module "
            "spec directories into deployable parquet files. As of just-dna-format "
            "0.4 a module composes from optional table kinds: the SNP core "
            "(variants.csv + studies.csv) and/or 0.4 tables (pgs.csv, diplotypes.csv, "
            "pharm_variants.csv, the binning kinds, ...). Use get_spec_format for the "
            "live, drift-proof field/vocabulary reference (get_spec_schemas for full "
            "JSON Schema), and list_icons / list_colors for the recommended UI palette."
        ),
    )

    @mcp.tool(task=TASK)
    async def validate_spec(spec_dir: str) -> dict[str, Any]:
        """Validate a module spec directory.

        Checks YAML structure, CSV row validity, cross-row consistency,
        and weight/state directionality. Returns a validation result dict
        with 'valid', 'errors', 'warnings', and 'stats' keys.

        Args:
            spec_dir: Path to the module spec directory containing
                module_spec.yaml, variants.csv, and studies.csv.

        Example:
            validate_spec(spec_dir="/path/to/my_module/")
            -> {"valid": true, "errors": [], "warnings": [],
                "stats": {"variant_rows": 42, "unique_rsids": 15, ...}}
        """
        from just_dna_compiler.compiler import validate_spec as _validate_spec

        result = _validate_spec(Path(spec_dir))
        return result.model_dump(mode="json")

    @mcp.tool(task=TASK)
    async def compile_module(
        spec_dir: str,
        output_dir: str | None = None,
        compression: str = "zstd",
    ) -> dict[str, Any]:
        """Compile a module spec directory into deployable parquet files.

        Validates the spec, optionally resolves missing rsid/position via
        Ensembl DuckDB, and produces the composed parquet artifact in the
        output directory: the SNP core (weights/annotations/studies) when the
        module carries variants, plus one parquet per 0.4 table kind present
        (pgs, diplotypes, pharm_variants, the binning kinds, ...).

        Args:
            spec_dir: Path to the module spec directory.
            output_dir: Output directory for parquet files. If not provided,
                uses the configured default output directory.
            compression: Parquet compression codec (zstd, snappy, lz4, gzip).

        Example:
            compile_module(
                spec_dir="/path/to/my_module/",
                output_dir="/path/to/output/",
            )
            -> {"success": true, "output_dir": "/path/to/output/",
                "errors": [], "warnings": [],
                "stats": {"weights_rows": 42, "annotations_rows": 15, ...}}
        """
        from just_dna_compiler.compiler import compile_module as _compile_module

        out = Path(output_dir) if output_dir else Path(settings.output_dir)
        result = _compile_module(
            Path(spec_dir),
            out,
            compression=compression,
            resolve_with_ensembl=settings.resolve_with_ensembl,
        )
        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_spec_format() -> dict[str, Any]:
        """Return the module spec format reference, generated live from just-dna-format.

        Introspects the current Pydantic models and vocabularies (via
        ``just_dna_format.reference.authoring_reference``) so the field set,
        vocabularies, reserved names, and recommended display palette can never
        drift from what the compiler enforces. Covers the SNP core (VariantRow /
        StudyRow) and every 0.4 table kind (binning / PGx / PGS).

        Returns a dict with keys: schema_version, genome_build_default, models
        (per-model field lists: name/type/required/description), vocabularies,
        open_recommended, reserved_names, recommended_palette.

        Example:
            get_spec_format()
            -> {"schema_version": "1.0", "models": {"VariantRow": [...], ...}, ...}
        """
        from just_dna_format.reference import authoring_reference

        return authoring_reference()

    @mcp.tool()
    async def get_spec_schemas() -> dict[str, Any]:
        """Return the full JSON Schema for every authored model.

        The machine-validatable form of the spec (Pydantic ``model_json_schema``
        per model), for consumers that want to validate authored rows directly
        rather than read the compact ``get_spec_format`` summary.

        Example:
            get_spec_schemas()
            -> {"VariantRow": {"$defs": {...}, "properties": {...}, ...}, ...}
        """
        from just_dna_format.reference import json_schemas

        return json_schemas()

    @mcp.tool()
    async def list_icons() -> dict[str, str]:
        """Return the recommended Fomantic UI icons, keyed by semantic use.

        The curated authoring palette from just-dna-format
        (``manifest.RECOMMENDED_ICONS``) — pick the icon for the module's subject
        area when authoring module_spec.yaml. Recommendation only: ``icon`` is
        free-form within its ``icon_set``, so any Fomantic glyph is accepted.

        Example:
            list_icons()
            -> {"cardiometabolic": "heartbeat", "pharmacogenomic": "pills", ...}
        """
        from just_dna_format.manifest import RECOMMENDED_ICONS

        return dict(RECOMMENDED_ICONS)

    @mcp.tool()
    async def list_colors() -> dict[str, str]:
        """Return the recommended hex colours, keyed by semantic use.

        The curated authoring palette from just-dna-format
        (``manifest.RECOMMENDED_COLORS``) — pick the colour for the module's
        risk level or category when authoring module_spec.yaml. Recommendation
        only: ``color`` is validated by pattern, so any valid hex is accepted.

        Example:
            list_colors()
            -> {"risk": "#db2828", "protective": "#21ba45", ...}
        """
        from just_dna_format.manifest import RECOMMENDED_COLORS

        return dict(RECOMMENDED_COLORS)

    return mcp
