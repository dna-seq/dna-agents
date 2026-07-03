"""
FastMCP server wrapping the dna_agents module compiler tools.

Exposes validation, compilation, spec format reference, and
icon/color listing as MCP tools.
"""

from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.utilities.tasks import TaskConfig

from dna_agents_mcp.config import Settings, get_settings

# Every tool may run synchronously or be promoted to a background task
# by the client (the MCP background-task protocol).
TASK = TaskConfig(mode="optional")

# ── Spec format reference (hardcoded summary) ────────────────────────────────

SPEC_FORMAT_REFERENCE = """\
Module Spec Directory Format
=============================

A module spec directory contains three files:

1. module_spec.yaml
   ─────────────────
   schema_version: "1.0"
   module:
     name: <lowercase_underscored>     # Machine name
     title: <string>                    # Human-readable title
     description: <string>             # One-liner
     report_title: <string>            # Title for reports
     icon: <fomantic_ui_icon>          # e.g. "dna", "heartbeat", "pills"
     color: <hex_color>                # e.g. "#21ba45"
   defaults:
     curator: <string>                 # Default curator identifier
     method: <string>                  # Default annotation method
     priority: <low|medium|high>       # Optional default priority
   genome_build: "GRCh38"

2. variants.csv
   ─────────────
   Required columns: rsid OR (chrom + start), genotype, state, conclusion
   Optional columns: ref, alts, weight, priority, gene, phenotype, category,
                     clinvar, pathogenic, benign, curator, method

   - rsid: dbSNP identifier (e.g. rs1801133)
   - chrom: Chromosome without 'chr' prefix (1-22, X, Y, MT)
   - start: 0-based genomic position (GRCh38)
   - genotype: Slash-separated sorted alleles (e.g. A/G)
   - state: One of: risk, protective, neutral, significant, alt, ref
   - weight: Float score (positive=protective, negative=risk)
   - conclusion: Human-readable interpretation

3. studies.csv (mandatory)
   ────────────
   Required columns: rsid OR (chrom + start), pmid
   Optional columns: population, p_value, conclusion, study_design

   Every variant must have at least one study reference (PMID).
"""

# ── Valid icons and colors ────────────────────────────────────────────────────

VALID_ICONS = {
    "dna": "Genetic/DNA-related modules",
    "heartbeat": "Cardiovascular health",
    "pills": "Pharmacogenomics / drug metabolism",
    "brain": "Neurological / cognitive traits",
    "shield": "Immune system / defense",
    "eye": "Vision / ophthalmology",
    "bone": "Skeletal / bone health",
    "leaf": "Nutrition / metabolism",
    "running": "Athletic / fitness traits",
    "tint": "Blood / hematology",
    "sun": "Dermatology / skin traits",
    "database": "General / uncategorized (default)",
    "flask": "Biochemistry / lab markers",
    "user md": "Clinical / medical genetics",
    "chart line": "Quantitative traits / biomarkers",
    "weight": "Body composition / anthropometrics",
    "clock": "Circadian / chronobiology",
    "fire": "Inflammation / autoimmune",
    "puzzle piece": "Complex / multi-gene traits",
    "star": "Notable / highlighted modules",
}

VALID_COLORS = {
    "#db2828": "Red - high risk / critical findings",
    "#f2711c": "Orange - moderate risk / caution",
    "#fbbd08": "Yellow - low risk / attention",
    "#21ba45": "Green - protective / positive",
    "#2185d0": "Blue - informational / neutral",
    "#6435c9": "Violet - default / general (default)",
    "#a5673f": "Brown - metabolic / nutrition",
    "#e03997": "Pink - hormonal / reproductive",
    "#00b5ad": "Teal - immune / defense",
    "#767676": "Grey - uncertain / VUS",
    "#1b1c1d": "Black - strong evidence / confirmed",
}


def create_server(settings: Settings | None = None) -> FastMCP:
    """Build and configure the DNA Agents MCP server."""
    settings = settings or get_settings()
    mcp: FastMCP = FastMCP(
        "dna-agents-mcp",
        instructions=(
            "DNA annotation module compiler tools. Validate and compile module "
            "spec directories (module_spec.yaml + variants.csv + studies.csv) "
            "into deployable parquet files. Use get_spec_format to learn the "
            "spec directory structure, list_icons / list_colors for valid UI "
            "metadata values."
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
        from dna_agents.compiler import validate_spec as _validate_spec

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
        Ensembl DuckDB, and produces weights.parquet, annotations.parquet,
        and studies.parquet in the output directory.

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
        from dna_agents.compiler import compile_module as _compile_module

        out = Path(output_dir) if output_dir else Path(settings.output_dir)
        result = _compile_module(
            Path(spec_dir),
            out,
            compression=compression,
            resolve_with_ensembl=settings.resolve_with_ensembl,
        )
        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_spec_format() -> str:
        """Return the module spec format reference.

        Describes the expected directory structure, file formats, and
        field definitions for module spec directories.

        Example:
            get_spec_format()
            -> "Module Spec Directory Format\\n===...\\n"
        """
        return SPEC_FORMAT_REFERENCE

    @mcp.tool()
    async def list_icons() -> dict[str, str]:
        """Return valid Fomantic UI icon names and their semantic uses.

        Use these when creating module_spec.yaml to pick an appropriate
        icon for the module's subject area.

        Example:
            list_icons()
            -> {"dna": "Genetic/DNA-related modules",
                "heartbeat": "Cardiovascular health", ...}
        """
        return VALID_ICONS

    @mcp.tool()
    async def list_colors() -> dict[str, str]:
        """Return valid hex colors and their semantic uses.

        Use these when creating module_spec.yaml to pick an appropriate
        color for the module's risk level or category.

        Example:
            list_colors()
            -> {"#db2828": "Red - high risk / critical findings",
                "#21ba45": "Green - protective / positive", ...}
        """
        return VALID_COLORS

    return mcp
