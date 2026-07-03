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
- **get_spec_format** — get the full module spec format reference
- **list_icons** — valid icon names and semantic uses
- **list_colors** — valid hex colors and semantic uses

Additionally, BioContext KB (`https://biocontext-kb.fastmcp.app/mcp`) provides
Ensembl, EuropePMC, UniProt, Open Targets, Reactome, KEGG, ClinicalTrials,
AlphaFold, InterPro, OLS, and STRINGDb tools for variant research.

## Module Spec Format

### module_spec.yaml

```yaml
schema_version: "1.0"
module:
  name: my_module           # lowercase, underscores only
  version: 1
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
| start      | no       | 1-based position (GRCh38) |
| ref        | no       | Reference allele |
| alts       | no       | Alt allele(s) |
| genotype   | yes      | Slash-separated SORTED alleles (A/G not G/A) |
| weight     | yes      | positive=protective, negative=risk, 0=neutral |
| state      | yes      | neutral, ref, risk, protective, significant, alt |
| conclusion | yes      | Human-readable interpretation |
| gene       | yes      | HGNC gene symbol |
| phenotype  | yes      | Associated trait |
| category   | yes      | Grouping category |

### studies.csv (mandatory)

One row per (rsid, pmid):

```
rsid,pmid,population,p_value,conclusion,study_design
```

## Critical Rules

1. **GRCh38 ONLY** — all coordinates must be GRCh38. Never use GRCh37/hg19.
2. **Compiler auto-resolution** — the compiler resolves rsid -> coordinates and
   coordinates -> rsid automatically. You only need ONE of them per variant.
3. **Epistemic humility** — this is Research Use Only. Use "associated with",
   "may contribute to", "has been linked to". NEVER use "causes", "guarantees",
   "will result in". No individual-level predictions from population data.
4. **Alleles sorted alphabetically** — A/G not G/A, C/T not T/C.
5. **Include wild-type** — every variant needs ref/ref genotype with weight 0
   and state "neutral".
6. **Weight range** — -1.5 to +1.5. Reserve extremes for well-established findings.
7. **Real PMIDs only** — never invent PMIDs. Use EuropePMC to find them.
8. **studies.csv is mandatory** — modules without study references are not useful.

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

# Run MCP server (stdio for Claude Code / Cursor)
uv run dna-agents-mcp serve --transport stdio

# Run MCP server (HTTP for remote access)
uv run dna-agents-mcp serve --transport http --port 8000
```
