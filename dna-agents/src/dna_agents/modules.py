"""
HuggingFace module downloader for just-dna-seq annotator modules.

Downloads parquet files (weights, annotations, studies) from the
just-dna-seq/annotators HuggingFace dataset and optionally reverse-compiles
them to the module spec DSL format (module_spec.yaml + variants.csv + studies.csv).

Uses Polars' native hf:// protocol for parquet access, matching the pattern
used in just-dna-lite's hf_modules.py.

Public API:
    list_available_modules() -> list[str]
    discover_modules() -> list[str]
    download_module(name, output_dir) -> ModuleDownloadResult
    download_all_modules(output_dir) -> list[ModuleDownloadResult]
    scan_module_table(name, table) -> pl.LazyFrame
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

HF_DATASET = "just-dna-seq/annotators"
HF_PREFIX = f"hf://datasets/{HF_DATASET}/data"

KNOWN_MODULES = [
    "coronary",
    "drugs",
    "lipidmetabolism",
    "longevitymap",
    "superhuman",
    "vo2max",
]

MODULE_TABLES = ["weights", "annotations", "studies"]


@dataclass
class ModuleDownloadResult:
    name: str
    success: bool
    parquet_dir: Path | None = None
    spec_dir: Path | None = None
    files_downloaded: list[str] = field(default_factory=list)
    error: str = ""


def list_available_modules() -> list[str]:
    """Return known module names from the just-dna-seq/annotators dataset."""
    return list(KNOWN_MODULES)


def discover_modules() -> list[str]:
    """
    Discover modules dynamically by scanning the HuggingFace repo.

    Falls back to KNOWN_MODULES if huggingface_hub is not available.
    """
    try:
        from huggingface_hub import HfFileSystem, get_token

        fs = HfFileSystem(token=get_token())
        base_path = f"datasets/{HF_DATASET}/data"
        entries = fs.ls(base_path, detail=True)
        modules = []
        for entry in entries:
            if entry["type"] == "directory":
                folder = entry["name"].split("/")[-1]
                weights_path = f"{entry['name']}/weights.parquet"
                if fs.exists(weights_path):
                    modules.append(folder)
        return sorted(modules)
    except ImportError:
        logger.debug("huggingface_hub not installed, using known modules list")
        return list(KNOWN_MODULES)


def scan_module_table(name: str, table: str) -> pl.LazyFrame:
    """
    Lazily scan a module table directly from HuggingFace.

    Uses Polars' native hf:// protocol — no local download needed.

    Args:
        name: Module name (e.g. "longevitymap").
        table: Table name: "weights", "annotations", or "studies".

    Returns:
        LazyFrame for memory-efficient processing.
    """
    url = f"{HF_PREFIX}/{name}/{table}.parquet"
    return pl.scan_parquet(url)


def download_module(
    name: str,
    output_dir: Path,
    reverse: bool = False,
    spec_output_dir: Path | None = None,
) -> ModuleDownloadResult:
    """
    Download a single module's parquet files from HuggingFace.

    Args:
        name: Module name (e.g. "longevitymap", "drugs").
        output_dir: Base directory. Files go to output_dir/<name>/*.parquet
        reverse: If True, also reverse-compile to module spec format.
        spec_output_dir: Where to write reversed spec files.
            Default: output_dir/<name>_spec/

    Returns:
        ModuleDownloadResult with download status.
    """
    result = ModuleDownloadResult(name=name, success=False)
    parquet_out = Path(output_dir) / name
    parquet_out.mkdir(parents=True, exist_ok=True)

    try:
        for table in MODULE_TABLES:
            filename = f"{table}.parquet"
            hf_path = f"{HF_PREFIX}/{name}/{filename}"
            try:
                df = pl.read_parquet(hf_path)
                local_path = parquet_out / filename
                df.write_parquet(local_path)
                result.files_downloaded.append(filename)
                logger.info("Downloaded %s/%s (%d rows)", name, filename, df.height)
            except Exception:
                if table == "weights":
                    raise
                logger.debug("Optional table %s/%s not available", name, filename)

        result.parquet_dir = parquet_out
        result.success = True

        if reverse:
            from dna_agents.compiler import reverse_module

            if spec_output_dir is None:
                spec_output_dir = Path(output_dir) / f"{name}_spec"
            reverse_module(parquet_out, spec_output_dir, module_name=name)
            result.spec_dir = spec_output_dir
            logger.info("Reversed %s to spec at %s", name, spec_output_dir)

    except Exception as e:
        result.error = str(e)
        logger.error("Failed to download module %s: %s", name, e)

    return result


def download_all_modules(
    output_dir: Path,
    reverse: bool = False,
    spec_output_dir: Path | None = None,
) -> list[ModuleDownloadResult]:
    """
    Download all known modules from HuggingFace.

    Args:
        output_dir: Base directory for parquet files.
        reverse: If True, also reverse-compile each module to spec format.
        spec_output_dir: Base dir for reversed specs. Default: output_dir/<name>_spec/

    Returns:
        List of ModuleDownloadResult for each module.
    """
    results: list[ModuleDownloadResult] = []
    for name in KNOWN_MODULES:
        per_spec = None
        if spec_output_dir is not None:
            per_spec = Path(spec_output_dir) / name
        result = download_module(name, output_dir, reverse=reverse, spec_output_dir=per_spec)
        results.append(result)
    return results
