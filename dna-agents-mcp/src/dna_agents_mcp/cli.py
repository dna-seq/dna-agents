"""
CLI for the dna-agents-mcp server.

Provides Typer commands for serving, validating, and compiling
module specs.
"""

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    help="DNA Agents MCP server and module compiler tools.",
    no_args_is_help=True,
)

console = Console()


class Transport(str, Enum):
    stdio = "stdio"
    http = "http"


@app.command()
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
        help="Output directory for parquet files.",
    ),
    compression: str = typer.Option(
        "zstd",
        "--compression", "-c",
        help="Parquet compression: zstd, snappy, lz4, gzip.",
    ),
    resolve: bool = typer.Option(
        True,
        "--resolve/--no-resolve",
        help="Resolve missing rsid/position via Ensembl DuckDB.",
    ),
    ensembl_cache: Optional[Path] = typer.Option(
        None,
        "--ensembl-cache",
        help="Explicit Ensembl parquet cache path.",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """
    Compile a module spec into deployable parquet files.

    Produces weights.parquet, annotations.parquet, and studies.parquet
    in the output directory.
    """
    from dna_agents.compiler import compile_module

    from dna_agents_mcp.config import get_settings

    settings = get_settings()

    if output is None:
        import yaml as _yaml

        yaml_path = spec_dir / "module_spec.yaml"
        if yaml_path.exists():
            raw = _yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            module_name = raw.get("module", {}).get("name", spec_dir.name)
        else:
            module_name = spec_dir.name
        output = Path(settings.output_dir) / module_name

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


if __name__ == "__main__":
    app()
