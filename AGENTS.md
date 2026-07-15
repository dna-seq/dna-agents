# DNA Agents — Genetics Annotation Module Builder

This repository provides tools and agent instructions for creating genetics
annotation modules for the just-dna-lite platform. Modules are curated sets of
SNP genotype annotations packaged as `module_spec.yaml` + `variants.csv` +
`studies.csv`.

## Project Structure

This is a **uv workspace** with two subprojects:

- `dna-agents/` — core module compiler library (validate, compile, reverse)
- `dna-agents-mcp/` — FastMCP server exposing compiler tools over MCP

## Available MCP Tools

When connected to the `dna-agents-mcp` server (or via the BioContext KB MCP),
these tools are available:

- **validate_spec** — validate a module spec directory
- **compile_module** — compile a spec to parquet files
- **get_spec_format** — the full spec format reference, generated **live** from
  just-dna-format (models, fields, vocabularies, reserved names, palette). This
  is the authoritative, always-current field list — it cannot drift from what the
  compiler enforces, so prefer it over the static tables below.
- **get_spec_schemas** — full JSON Schema per authored model (machine-validatable)
- **list_icons** — recommended icons, keyed by semantic use
- **list_colors** — recommended hex colors, keyed by semantic use

> **just-dna-format 0.4:** a module now *composes* from optional table kinds — the
> SNP core (`variants.csv` + `studies.csv`) and/or 0.4 tables (`pgs.csv`,
> `diplotypes.csv`, `pharm_variants.csv`, `haplotypes.csv`, `allele_function.csv`,
> and the binning kinds: `copynumbers.csv`, `repeat_alleles.csv`,
> `heteroplasmy.csv`, `activity_phenotype.csv`). VariantRow gains
> `requires_callable` / `acmg_sf` / `actionability`; StudyRow gains `doi` /
> `provenance_quote` / `provenance_regex`; module metadata gains structured
> `authorship`. Unknown/misspelled columns are now a hard error (`extra="forbid"`).
> Call `get_spec_format` / `get_spec_schemas` for the exact current fields.

Additionally, BioContext KB (`https://biocontext-kb.fastmcp.app/mcp`) provides
Ensembl, EuropePMC, UniProt, Open Targets, Reactome, KEGG, ClinicalTrials,
AlphaFold, InterPro, OLS, and STRINGDb tools for variant research.

## Module Spec Format

### module_spec.yaml

```yaml
schema_version: "1.0"
module:
  name: my_module           # lowercase, underscores only
  title: "My Module"
  description: "..."
  report_title: "..."
  icon: heart-pulse         # see Icon Catalog
  color: "#21ba45"          # see Color Palette
defaults:
  curator: ai-module-creator
  method: literature-review  # literature-review | gwas | clinvar-review | expert-curation
  priority: medium           # low | medium | high
genome_build: GRCh38        # MUST be GRCh38
```

### Icon Catalog

| Icon name   | Best for                         |
|-------------|----------------------------------|
| heart-pulse | longevity, cardiovascular        |
| heart       | coronary artery disease          |
| droplets    | lipids, metabolism, blood        |
| activity    | athletic performance, fitness    |
| zap         | elite / superhuman performance   |
| pill        | pharmacogenomics, drug metabolism|
| dna         | methylation, epigenetics         |
| database    | generic / default                |
| chart-bar   | risk scores, polygenic traits    |
| boxes       | multi-trait panels               |

### Color Palette

| Color  | Hex     | Use                                      |
|--------|---------|------------------------------------------|
| Green  | #21ba45 | longevity, protective, beneficial        |
| Yellow | #fbbd08 | metabolism, neutral/mixed                |
| Blue   | #2185d0 | performance, athletic, cognitive         |
| Teal   | #00b5ad | elite performance, rare variants         |
| Red    | #db2828 | disease risk, pathogenic                 |
| Purple | #a333c8 | pharmacogenomics, drug response          |
| Indigo | #6435c9 | default / other genetics                 |

### variants.csv

One row per (rsid, genotype) combination:

| Column     | Required | Description |
|------------|----------|-------------|
| rsid       | yes*     | dbSNP ID (rs...). Blank OK if chrom/start/ref/alts present |
| chrom      | no       | Chromosome without "chr" prefix |
| start      | no       | **0-based** position (GRCh38) |
| ref        | no       | Reference allele |
| alts       | no       | Alt allele(s) |
| genotype   | yes      | Slash-separated SORTED alleles (A/G not G/A) |
| weight     | yes      | positive=protective, negative=risk, 0=neutral |
| state      | yes      | neutral, ref, risk, protective, significant, alt |
| conclusion | yes      | Human-readable interpretation |
| gene       | yes      | HGNC gene symbol |
| phenotype  | yes      | Associated trait |
| category   | yes      | Grouping category |

Optional 0.4 columns (blank when unstated): `actionability`, `acmg_sf`,
`requires_callable`, `clin_sig`, plus `direction` / `stat_significance` /
`effect_size` / `effect_measure` / `effect_allele` / `flags` / `trait_efo_id`.
`clinvar` / `pathogenic` / `benign` are tri-state (true/false/blank) — leave blank
when you have no assertion. Call `get_spec_format` for the authoritative list.

### studies.csv (mandatory)

One row per (rsid, pmid):

```
rsid,pmid,population,p_value,conclusion,study_design
```

Optional 0.4 provenance columns: `doi`, `provenance_quote` (a literal grounding
passage from the cited fulltext), `provenance_regex`. Populate them when the source
is in hand.

## Critical Rules

1. **GRCh38 ONLY** — all coordinates must be GRCh38. Never use GRCh37/hg19.
2. **Forward-strand alleles ONLY** — ref and alt alleles must be on the
   forward (plus) strand as reported by Ensembl. Never use reverse-strand
   complement alleles. If a paper reports C/T but Ensembl shows G/A for
   that rsid, use G/A.
3. **Verify ref/alt via Ensembl** — for every rsid, confirm that the ref allele
   matches the GRCh38 reference genome and that the alt is a known alternate.
   Genotype alleles must be a subset of {ref, alt}.
4. **Compiler auto-resolution** — the compiler resolves rsid -> coordinates and
   coordinates -> rsid automatically. You only need ONE of them per variant.
5. **Epistemic humility** — this is Research Use Only. Use "associated with",
   "may contribute to", "has been linked to". NEVER use "causes", "guarantees",
   "will result in". No individual-level predictions from population data.
6. **Alleles sorted alphabetically** — A/G not G/A, C/T not T/C.
7. **Include wild-type** — every variant needs ref/ref genotype with weight 0
   and state "neutral".
8. **Weight range** — -1.5 to +1.5. Reserve extremes for well-established findings.
9. **Verify every PMID** — search EuropePMC for each PMID and confirm it exists.
   Check that the title, authors, and topic match what you expect. You do NOT need
   the exact rsid in the abstract — just confirm the paper is about the right
   gene/phenotype. Prefer DOIs when available (resolve via `DOI:<doi>` query).
   Never invent PMIDs. A missing citation is better than a wrong one.
10. **studies.csv is mandatory** — modules without study references are not useful.

## Workflow: Creating a Module

1. Analyze input (paper, variant list, or freeform text)
2. Research variants using BioContext KB tools (Ensembl, EuropePMC, Open Targets)
3. For each variant: confirm rsid/coordinates, gene, all genotypes, weights, states
4. Collect PMIDs from attached material first, EuropePMC otherwise
5. Write spec files (module_spec.yaml, variants.csv, studies.csv)
6. Validate with `validate_spec`
7. Fix any errors and re-validate
8. Document with MODULE.md

## CLI Commands

```bash
# Validate a spec directory
uv run dna-agents validate /path/to/spec/

# Compile to parquet
uv run dna-agents compile /path/to/spec/ --output /path/to/output/

# Download papers from EuropePMC for a module's studies.csv
uv run dna-agents download-papers data/evals/cyp_panel/

# Download HF annotator modules (parquet files)
uv run dna-agents download-modules

# Download a single module with reverse-compile to spec format
uv run dna-agents download-modules -m longevitymap --reverse

# List available HF modules
uv run dna-agents download-modules --list

# Score agent output against local ground truth
uv run dna-agents eval candidate_output/ data/evals/cyp_panel/

# Score agent output against HF module directly (best for modules on HF)
uv run dna-agents eval agent_output/ longevitymap --rsids rs3758391,rs107251

# Score against downloaded parquet
uv run dna-agents eval agent_output/ data/modules/longevitymap/

# Run agent evals (requires claude CLI)
uv run pytest tests/test_agent_evals.py -v -m agent_eval

# Run MCP server (stdio for Claude Code / Cursor)
uv run dna-agents-mcp serve --transport stdio

# Run MCP server (HTTP for remote access)
uv run dna-agents-mcp serve --transport http --port 8000
```

## Evaluation System

Agent output is scored against ground truth on 8 weighted dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| variant_recall | 2.0 | Fraction of reference rsids found in candidate |
| variant_precision | 1.0 | Fraction of candidate rsids that are in reference |
| genotype_completeness | 1.5 | Fraction of expected genotypes present |
| weight_accuracy | 1.0 | 1 - MAE of weights for matched genotypes |
| weight_direction | 1.5 | State (risk/protective/neutral) agreement |
| pmid_recall | 1.5 | Fraction of reference PMIDs found |
| pmid_precision | 0.5 | Fraction of candidate PMIDs that are valid |
| gene_accuracy | 1.0 | Correct gene symbol assignment |

### Ground truth sources

- **HF parquet modules** (preferred): `dna-agents eval output/ longevitymap`
  loads weights.parquet + annotations.parquet + studies.parquet directly from
  `just-dna-seq/annotators`. Use `--rsids` to restrict to a subset.
- **Local parquet**: `dna-agents eval output/ data/modules/longevitymap/`
- **Spec directory**: `dna-agents eval output/ data/evals/cyp_panel/`
  for modules not on HF (e.g. pharmacogenomics).

### Eval cases

| Eval | Ground truth | Notes |
|------|-------------|-------|
| sirtuin_longevity | HF `longevitymap` (7 rsids) | Sirtuin pathway subset |
| cyp_panel | Local spec dir | Pharmacogenomics, no HF module yet |
