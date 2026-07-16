---
name: just-dna-agents
description: DNA annotation module compiler. Use when creating, validating, or compiling genetics annotation modules (SNP core module_spec.yaml + variants.csv + studies.csv, and/or the 0.4 table kinds). Ensures correct spec format, GRCh38 coordinates, epistemic humility in conclusions, and proper weight conventions.
---

# just-dna-agents — Module Compiler

Genetics annotation module compiler for the just-dna-lite platform. Validates
and compiles module spec directories into deployable parquet files.

> **Authoritative field reference — always prefer this over the tables below.**
> The spec is defined by the `just-dna-format` library, and the exact current
> field/vocabulary set is served live (it cannot drift from what the compiler
> enforces). When the `just-dna-agents-mcp` server is connected, call:
> - **`get_spec_format`** — compact reference: every model's fields
>   (name/type/required/description), vocabularies, reserved names, recommended
>   palette. Covers the SNP core **and** all 0.4 table kinds.
> - **`get_spec_schemas`** — full JSON Schema per model (machine-validatable).
> - **`list_icons` / `list_colors`** — the recommended UI palette, keyed by use.
>
> The tables in this file are a *quick reference for the SNP core only*. If they
> ever disagree with `get_spec_format`, `get_spec_format` wins.

## Module composition (0.4)

A module **composes** from optional table kinds. The SNP core is the common case
(`variants.csv` + `studies.csv`), but a module may instead — or additionally —
carry 0.4 tables: PGS (`pgs.csv`), PGx star-alleles (`haplotypes.csv`,
`allele_function.csv`, `diplotypes.csv`, `activity_phenotype.csv`,
`pharm_variants.csv`), or binning (`copynumbers.csv`, `repeat_alleles.csv`,
`heteroplasmy.csv`). Include only the CSVs a module actually uses; the compiler
emits one parquet per present kind. Every unknown/misspelled column is a **hard
error** (`extra="forbid"`), so match column names exactly (via `get_spec_format`).

## Quick start

```python
from just_dna_agents import validate_spec, compile_module

result = validate_spec(Path("my_module/"))
if result.valid:
    compile_module(Path("my_module/"), Path("output/"))
```

CLI:

```bash
# Validate a spec directory
uv run just-dna-agents validate path/to/spec/

# Compile to parquet
uv run just-dna-agents compile path/to/spec/ --output path/to/output/
```

## Module spec directory format (SNP core)

A SNP-core module spec directory contains these files:

### 1. module_spec.yaml

```yaml
schema_version: "1.0"
module:
  name: my_module           # lowercase, underscores only
  title: "My Module"        # human-readable title
  description: "..."        # one-liner for module cards
  report_title: "..."       # section title in reports
  icon: heart-pulse         # see Icon Catalog below
  color: "#21ba45"          # hex color, see Color Palette below
defaults:
  curator: ai-module-creator
  method: literature-review  # literature-review | gwas | clinvar-review | expert-curation
  priority: medium           # low | medium | high
genome_build: GRCh38        # MUST always be GRCh38
```

A top-level `authorship:` list (0.4, sibling of `module`/`defaults`) records
contributors — see "Authorship" below.

### Icons & colors

Pick `icon` / `color` from the recommended palette — call the MCP `list_icons` /
`list_colors` tools for the current keyed-by-use set (e.g. `pharmacogenomic → pills`,
`protective → #21ba45`, `cancer → #f2711c`). `icon` is free-form within its icon set
and `color` is any valid hex, so the palette is a recommendation, not a hard limit.

### Authorship (0.4, optional)

`authorship` is a **top-level** key (sibling of `module` / `defaults` /
`genome_build`, **not** nested under `module:`) recording who contributed to *this
version* — so a downstream consumer can route scrutiny by author-kind. One entry
per contributor; a joint human+AI contribution is two entries.

```yaml
schema_version: "1.0"
module:
  name: my_module
  # ...
defaults:
  # ...
genome_build: GRCh38
authorship:                            # top-level, not under module:
  - who: pgx-module-creator            # a name, handle, or model id
    role: created                      # created | edited | audited | reviewed
    kind: [ai, agent]                  # human ladder {human, human_expert, human_certified}
                                       # or {ai} + scale {agent, team, swarm}
  - who: reviewer
    role: reviewed
    kind: [ai, agent]
```

`role` is a closed vocabulary; `kind` is an open tag set (recommended seed above,
new tags allowed). It is module metadata (out of the content digest), so it never
changes a module's content identity. (Reverse-compiling a parquet artifact does not
restore `authorship` to `module_spec.yaml` — it lives only in the manifest.)

### 2. variants.csv

One row per (rsid, genotype) combination. Core columns:

| Column     | Required | Type   | Description |
|------------|----------|--------|-------------|
| rsid       | yes*     | string | dbSNP ID (rs...). Blank OK if chrom/start/ref/alts present |
| chrom      | no       | string | Chromosome without "chr" prefix (1-22, X, Y, MT) |
| start      | no       | int    | **0-based** position (GRCh38) |
| ref        | no       | string | Reference allele |
| alts       | no       | string | Alt allele(s) |
| genotype   | yes      | string | Slash-separated SORTED alleles (A/G not G/A) |
| weight     | yes      | float  | positive=protective, negative=risk, 0=neutral |
| state      | yes      | string | neutral, ref, risk, protective, significant, alt |
| conclusion | yes      | string | Human-readable interpretation |
| gene       | yes      | string | HGNC gene symbol (e.g. MTHFR, APOE) |
| phenotype  | yes      | string | Associated trait/phenotype |
| category   | yes      | string | Grouping category within the module |

Optional 0.4 columns (leave blank when not stated — do **not** invent values):

| Column            | Type   | Description |
|-------------------|--------|-------------|
| actionability     | string | ACTIONABILITY_SEED: actionable, preventable, pharmacogenomic, incurable, reproductive, descriptive, modifiable |
| acmg_sf           | bool   | `true` when the gene is on the ACMG secondary-findings list |
| requires_callable | bool   | `true` when the *absence* of the variant is the informative call (recessive carrier / "pathogenic variant absent" reassurance) |
| clin_sig          | string | ClinVar/ACMG tier (VEP CLIN_SIG vocab, e.g. pathogenic) |

`clinvar` / `pathogenic` / `benign` are **tri-state** booleans: `true`, `false`,
or blank (unstated). Leave blank when you have no ClinVar assertion — do not write
`false`, which means "curator states not-pathogenic" and is preserved distinctly.

(Other optional axes exist — `direction`, `stat_significance`, `effect_size`,
`effect_measure`, `effect_allele`, `flags`, `trait_efo_id`. Call `get_spec_format`
for the full current list.)

### 3. studies.csv (mandatory for variant modules)

One row per (rsid, pmid):

```
rsid,pmid,population,p_value,conclusion,study_design
```

Optional 0.4 provenance columns — recommended when you have the source in hand:

| Column           | Type   | Description |
|------------------|--------|-------------|
| doi              | string | DOI (bare `10.x/...` or a doi.org URL); wider than pmid — covers preprints/books/datasets |
| provenance_quote | string | A literal passage from the cited article's fulltext that grounds the claim |
| provenance_regex | string | A regex locating the claim in fulltext (must compile) |

Every variant module must have study references. Never invent PMIDs. When the
paper fulltext is available (e.g. downloaded under `data/papers/`), quote the
grounding sentence in `provenance_quote`.

## Critical rules

### GRCh38 only

All genomic coordinates must be GRCh38 (hg38). Never use GRCh37/hg19.
Always set `genome_build: GRCh38` in module_spec.yaml.

### Compiler auto-resolution

The compiler resolves missing identifiers at build time:
- rsid present → chrom/start/ref/alts auto-resolved from Ensembl GRCh38
- GRCh38 coordinates present → rsid auto-resolved

You only need ONE of {rsid} or {GRCh38 coordinates} per variant. Do not
look up coordinates for a known rsid or vice versa — the compiler handles it.

### Genotype rules

- Alleles MUST be alphabetically sorted: A/G not G/A, C/T not T/C
- Each rsid typically needs 3 rows: ref/ref, ref/alt, alt/alt
- Always include the wild-type genotype with weight 0 and state "neutral"

### Weight conventions

- Negative = risk / harmful (e.g. -1.2 for strong disease association)
- Positive = protective / beneficial (e.g. +1.0 for confirmed longevity allele)
- Zero = neutral / no known effect
- Magnitude: 0.1–0.3 weak, 0.4–0.8 moderate, 0.9–1.2 strong, 1.3–1.5 very strong
- Reserve extremes (>1.3) for well-established, replicated findings

### State values

| State       | When to use                                    |
|-------------|------------------------------------------------|
| neutral     | Wild-type / reference — weight ~ 0             |
| ref         | Explicit reference allele homozygote           |
| risk        | Increased disease risk — weight < 0            |
| protective  | Reduced disease risk — weight > 0              |
| significant | Clinically actionable — use sparingly          |
| alt         | Alt homozygote with uncertain/mixed effect     |

### Epistemic humility (mandatory)

This is a Research Use Only platform. All conclusions must use cautious language:

**Use**: "associated with", "may contribute to", "has been linked to",
"suggests", "in population studies", "evidence indicates"

**Never use**: "causes", "guarantees", "will result in", "ensures",
"the effect is colossal", "onset will shift by X years"

Never make individual-level predictions from population-level data.
Conclusions should read as research observations, not clinical diagnoses.

## Example module

```yaml
# module_spec.yaml
schema_version: "1.0"
module:
  name: methylation
  title: "Methylation & Folate"
  description: "MTHFR and MTRR variants affecting folate metabolism"
  report_title: "Methylation & Folate Cycle"
  icon: dna
  color: "#6435c9"
defaults:
  curator: ai-module-creator
  method: literature-review
  priority: medium
genome_build: GRCh38
```

```csv
# variants.csv
rsid,genotype,weight,state,conclusion,gene,phenotype,category
rs1801133,C/C,0,neutral,"Reference genotype; associated with typical MTHFR enzyme activity.",MTHFR,Folate metabolism,Methylation cycle
rs1801133,C/T,-0.5,risk,"Associated with moderately reduced MTHFR activity (~65% of normal in vitro).",MTHFR,Folate metabolism,Methylation cycle
rs1801133,T/T,-1.2,significant,"Associated with substantially reduced MTHFR activity (~30% of normal in vitro).",MTHFR,Folate metabolism,Methylation cycle
```

```csv
# studies.csv
rsid,pmid,population,p_value,conclusion,study_design
rs1801133,9215008,European,1e-10,"C677T homozygosity associated with elevated plasma homocysteine.",Case-control
```

## Validation API

```python
from just_dna_agents import validate_spec, ValidationResult

result: ValidationResult = validate_spec(Path("my_module/"))
# result.valid: bool
# result.errors: list[str]    — must-fix issues
# result.warnings: list[str]  — should-fix issues
# result.stats: dict          — variant_rows, unique_rsids, unique_genes, etc.
```

## Compilation API

```python
from just_dna_agents import compile_module, CompilationResult

result: CompilationResult = compile_module(
    spec_dir=Path("my_module/"),
    output_dir=Path("output/"),
    compression="zstd",          # zstd | snappy | lz4 | gzip
    resolve_with_ensembl=True,   # auto-resolve rsid <-> coordinates
)
# result.success: bool
# result.output_dir: Path
# result.errors: list[str]
# result.warnings: list[str]
# Produces the composed artifact: the SNP core (weights.parquet, annotations.parquet,
# studies.parquet) when the module has variants, plus one parquet per 0.4 table kind
# present (pgs.parquet, diplotypes.parquet, ...), all with a manifest.json.
```
