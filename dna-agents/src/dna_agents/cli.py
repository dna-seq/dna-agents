"""
CLI for the dna-agents module compiler.

Provides Typer commands for validating, compiling, and serving
module specs via MCP.
"""

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="dna-agents",
    help="DNA annotation module compiler: validate, compile, and serve module specs.",
    no_args_is_help=True,
)

console = Console()


class Transport(str, Enum):
    stdio = "stdio"
    http = "http"


@app.command("validate")
def validate(
    spec_dir: Path = typer.Argument(
        ...,
        help="Path to module spec directory (contains module_spec.yaml + variants.csv).",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """
    Validate a module spec without producing output.

    Checks YAML structure, CSV row validity, cross-row consistency,
    and weight/state directionality.

    Examples:

        dna-agents validate data/module_specs/evals/mthfr_nad/
    """
    from dna_agents.compiler import validate_spec

    console.print(f"\n[bold]Validating:[/bold] {spec_dir}\n")
    result = validate_spec(spec_dir)

    if result.errors:
        console.print("[bold red]Errors:[/bold red]")
        for err in result.errors:
            console.print(f"  [red]x[/red] {err}")
        console.print()

    if result.warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warn in result.warnings:
            console.print(f"  [yellow]![/yellow] {warn}")
        console.print()

    if result.stats:
        table = Table(title="Spec Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        for key, val in result.stats.items():
            table.add_row(key, str(val))
        console.print(table)

    if result.valid:
        console.print("[bold green]Spec is valid[/bold green]\n")
    else:
        console.print(f"[bold red]Validation failed with {len(result.errors)} error(s)[/bold red]\n")
        raise typer.Exit(1)


@app.command("compile")
def compile_cmd(
    spec_dir: Path = typer.Argument(
        ...,
        help="Path to module spec directory (contains module_spec.yaml + variants.csv).",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory. Default: data/output/modules/<module_name>/",
    ),
    compression: str = typer.Option(
        "zstd",
        "--compression", "-c",
        help="Parquet compression: zstd, snappy, lz4, gzip.",
    ),
    resolve: bool = typer.Option(
        True,
        "--resolve/--no-resolve",
        help="Resolve missing rsid/position via Ensembl DuckDB (auto-downloads if needed).",
    ),
    ensembl_cache: Optional[Path] = typer.Option(
        None,
        "--ensembl-cache",
        help="Explicit Ensembl parquet cache path. Default: auto-detect from platform cache.",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """
    Compile a module spec into deployable parquet files.

    Produces weights.parquet, annotations.parquet, and (if studies.csv exists)
    studies.parquet in the output directory.

    By default, resolves missing rsid/position fields via the local Ensembl
    DuckDB (GRCh38). The DuckDB is auto-built from the Ensembl parquet cache;
    if the cache is missing it is downloaded from HuggingFace Hub.

    Examples:

        dna-agents compile data/module_specs/evals/mthfr_nad/

        dna-agents compile data/module_specs/evals/cyp_panel/ \\
            --output data/output/modules/cyp_panel/

        dna-agents compile data/module_specs/evals/cyp_panel/ --no-resolve
    """
    from dna_agents.compiler import compile_module

    # Determine output dir: load module name from YAML for default path
    if output is None:
        import yaml as _yaml

        yaml_path = spec_dir / "module_spec.yaml"
        if yaml_path.exists():
            raw = _yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            module_name = raw.get("module", {}).get("name", spec_dir.name)
        else:
            module_name = spec_dir.name
        output = Path("data/output/modules") / module_name

    console.print(f"\n[bold]Compiling:[/bold] {spec_dir}")
    console.print(f"[bold]Output:   [/bold] {output}")
    console.print(f"[bold]Resolve:  [/bold] {'yes' if resolve else 'no'}\n")

    result = compile_module(
        spec_dir,
        output,
        compression=compression,
        resolve_with_ensembl=resolve,
        ensembl_cache=ensembl_cache,
    )

    if result.errors:
        console.print("[bold red]Errors:[/bold red]")
        for err in result.errors:
            console.print(f"  [red]x[/red] {err}")
        console.print()

    if result.warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warn in result.warnings:
            console.print(f"  [yellow]![/yellow] {warn}")
        console.print()

    if result.success:
        table = Table(title="Compilation Result")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        for key, val in result.stats.items():
            table.add_row(key, str(val))
        console.print(table)
        console.print(f"\n[bold green]Module compiled successfully to {output}[/bold green]\n")
    else:
        console.print(
            f"[bold red]Compilation failed with {len(result.errors)} error(s)[/bold red]\n"
        )
        raise typer.Exit(1)


@app.command("download-papers")
def download_papers_cmd(
    spec_dir: Path = typer.Argument(
        ...,
        help="Path to module spec directory containing studies.csv.",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory for downloaded papers. Default: data/papers/<spec_name>/",
    ),
    no_fulltext: bool = typer.Option(
        False,
        "--no-fulltext",
        help="Skip downloading full text XML, only fetch metadata.",
    ),
) -> None:
    """
    Download papers referenced in a module spec's studies.csv.

    Fetches metadata and open-access full text from EuropePMC for all
    PMIDs found in studies.csv. Papers are saved as JSON (metadata)
    and XML (full text, when available).

    Examples:

        dna-agents download-papers data/evals/cyp_panel/

        dna-agents download-papers data/evals/sirtuin_longevity/ -o papers/sirtuin/
    """
    from dna_agents.papers import download_papers, extract_pmids

    pmids = extract_pmids(spec_dir)
    if not pmids:
        console.print("[yellow]No PMIDs found in studies.csv[/yellow]")
        raise typer.Exit(0)

    if output is None:
        output = Path("data/papers") / spec_dir.name

    console.print(f"\n[bold]Downloading papers for:[/bold] {spec_dir}")
    console.print(f"[bold]PMIDs found:[/bold] {len(pmids)}")
    console.print(f"[bold]Output:[/bold] {output}\n")

    results = download_papers(pmids, output, include_fulltext=not no_fulltext)

    table = Table(title="Download Results")
    table.add_column("PMID", style="cyan")
    table.add_column("Metadata", style="green")
    table.add_column("Full Text", style="green")
    table.add_column("Status", style="bold")

    for r in results:
        status = "[green]OK" if r.success else f"[red]{r.error}"
        meta = "[green]yes" if r.metadata_path else "[red]no"
        ft = "[green]yes" if r.fulltext_path else "[dim]no"
        table.add_row(r.pmid, meta, ft, status)

    console.print(table)
    success = sum(1 for r in results if r.success)
    fulltext = sum(1 for r in results if r.fulltext_path)
    console.print(f"\n[bold]{success}/{len(results)}[/bold] metadata, [bold]{fulltext}[/bold] full text\n")


@app.command("eval")
def eval_cmd(
    candidate_dir: Path = typer.Argument(
        ...,
        help="Path to candidate (agent-produced) module spec directory.",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    reference_dir: Path = typer.Argument(
        ...,
        help="Path to reference (ground truth) module spec directory.",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """
    Score a candidate module spec against a reference ground truth.

    Compares variants.csv and studies.csv on multiple dimensions:
    variant recall/precision, genotype completeness, weight accuracy,
    weight direction, PMID recall/precision, gene accuracy.

    Examples:

        dna-agents eval module_output/cyp_drug_metabolism/ data/evals/cyp_panel/

        dna-agents eval agent_output/ tests/fixtures/evals/cyp_panel/
    """
    from dna_agents.eval_scorer import score_module

    console.print(f"\n[bold]Candidate:[/bold] {candidate_dir}")
    console.print(f"[bold]Reference:[/bold] {reference_dir}\n")

    result = score_module(candidate_dir, reference_dir)

    table = Table(title="Evaluation Score")
    table.add_column("Dimension", style="cyan")
    table.add_column("Score", style="green", justify="right")
    table.add_column("Details")

    for d in result.dimensions:
        pct = f"{d.normalized:.0%}"
        raw = f"({d.score:.0f}/{d.max_score:.0f})"
        detail = d.details[0] if d.details else ""
        if len(detail) > 70:
            detail = detail[:67] + "..."
        table.add_row(d.name, f"{pct} {raw}", detail)

    console.print(table)
    console.print(f"\n[bold]Overall: {result.overall:.1%}[/bold]\n")


@app.command("serve")
def serve(
    transport: Transport = typer.Option(
        Transport.stdio, help="Transport to serve on."
    ),
    host: str = typer.Option("127.0.0.1", help="Host for the HTTP transport."),
    port: int = typer.Option(8000, help="Port for the HTTP transport."),
) -> None:
    """Run the MCP server over stdio or streamable HTTP."""
    from dna_agents_mcp.server import create_server

    mcp = create_server()
    if transport is Transport.stdio:
        mcp.run()
    else:
        mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    app()
