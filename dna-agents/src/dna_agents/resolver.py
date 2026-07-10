"""
App-side Ensembl reference provisioning for the dna-agents compiler.

The actual rsid <-> position resolution lives in ``just_dna_compiler.resolver`` (inject-only:
it never downloads). This module is the *provisioning* layer the library intentionally omits —
it locates a usable Ensembl reference and, if none is present, downloads the parquet cache from
HuggingFace Hub.

On-disk layout mirrors just-dna-lite / just-dna-pipelines exactly (so an existing deployment's
cache is reused without re-downloading)::

    <base>/ensembl_variations/data/*.parquet
    <base>/ensembl_variations/ensembl_variations.duckdb   # optional prebuilt view

where ``<base>`` is ``$JUST_DNA_PIPELINES_CACHE_DIR`` (or the platformdirs user cache), resolved by
``just_dna_compiler.cache``. ``$JUST_DNA_ENSEMBL_CACHE`` (a ``.duckdb`` file or a directory)
overrides everything.
"""

import logging
from pathlib import Path
from typing import Optional

from just_dna_compiler.cache import default_ensembl_cache_dir, resolve_ensembl_reference

logger = logging.getLogger(__name__)

# Same dataset just-dna-lite pulls the Ensembl variations parquet from.
HF_ENSEMBL_DATASET = "just-dna-seq/ensembl_variations"
_HF_REMOTE_PREFIX = f"datasets/{HF_ENSEMBL_DATASET}/data"


def ensure_resolver_reference(ensembl_cache: Optional[Path] = None) -> Optional[Path]:
    """Locate a usable Ensembl reference, downloading the parquet cache if needed.

    Returns a path suitable to pass as ``compile_module(ensembl_cache=...)`` — either a prebuilt
    ``ensembl_variations.duckdb`` file or the cache directory holding ``data/*.parquet`` (the
    library resolver queries the parquet directly via an in-memory view). Returns ``None`` if the
    reference is absent and the download cannot be performed, so the caller (and the library
    resolver) skips resolution with a warning rather than failing.

    Args:
        ensembl_cache: Explicit cache path override. When ``None``, honours
            ``$JUST_DNA_ENSEMBL_CACHE`` / ``$JUST_DNA_PIPELINES_CACHE_DIR`` via the library cache.
    """
    reference = resolve_ensembl_reference(ensembl_cache)
    if reference is not None:
        logger.info("Using Ensembl reference at %s", reference)
        return reference

    # Nothing on disk: provision the parquet cache from HuggingFace, matching just-dna-lite's layout
    # (<base>/ensembl_variations/data/*.parquet).
    cache_dir = Path(ensembl_cache) if ensembl_cache else default_ensembl_cache_dir()
    data_dir = cache_dir / "data"
    try:
        from huggingface_hub import HfFileSystem, get_token
    except ImportError:
        logger.warning(
            "Ensembl reference not found and huggingface_hub is unavailable; "
            "resolution will be skipped. Provision %s or set JUST_DNA_ENSEMBL_CACHE.",
            data_dir,
        )
        return None

    logger.info("Ensembl parquet cache not found -- downloading from HuggingFace Hub ...")
    data_dir.mkdir(parents=True, exist_ok=True)
    fs = HfFileSystem(token=get_token())
    remote_files = [f for f in fs.ls(_HF_REMOTE_PREFIX, detail=False) if f.endswith(".parquet")]
    logger.info("Found %d remote parquet files", len(remote_files))
    for remote_path in remote_files:
        filename = remote_path.rsplit("/", 1)[-1]
        local_path = data_dir / filename
        if local_path.exists():
            continue
        logger.info("  Downloading %s ...", filename)
        fs.get(remote_path, str(local_path))
    logger.info("Download complete: %s", cache_dir)

    # Best-effort prebuilt DuckDB for parity with just-dna-lite (optional — the library resolver
    # falls back to a parquet view when no .duckdb is present).
    try:
        from just_dna_pipelines.annotation.duckdb_assets import ensure_ensembl_duckdb_exists

        ensure_ensembl_duckdb_exists(logger=logger)
    except ImportError:
        pass

    return resolve_ensembl_reference(ensembl_cache)
