---
name: dna-agents
description: DNA annotation module compiler. Use when creating, validating, or compiling genetics annotation modules (module_spec.yaml + variants.csv + studies.csv). Ensures correct spec format, GRCh38 coordinates, epistemic humility in conclusions, and proper weight conventions.
---

# dna-agents — Module Compiler

Genetics annotation module compiler for the just-dna-lite platform. Validates
and compiles module spec directories into deployable parquet files.

## Quick start

```python
from dna_agents import validate_spec, compile_module

result = validate_spec(Path("my_module/"))
if result.valid:
    compile_module(Path("my_module/"), Path("output/"))
```

CLI:

```bash
# Validate a spec directory
uv run dna-agents validate path/to/spec/

# Compile to parquet
uv run dna-agents compile path/to/spec/ --output path/to/output/
```

## Module spec directory format

A module spec directory contains three files:

### 1. module_spec.yaml

```yaml
schema_version: "1.0"
module:
  name: my_module           # lowercase, underscores only
  version: 1                # integer, auto-bumped on edits
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

### 2. variants.csv

One row per (rsid, genotype) combination:

| Column     | Required | Type   | Description |
|------------|----------|--------|-------------|
| rsid       | yes*     | string | dbSNP ID (rs...). Blank OK if chrom/start/ref/alts present |
| chrom      | no       | string | Chromosome without "chr" prefix (1-22, X, Y, MT) |
| start      | no       | int    | 1-based position (GRCh38) |
| ref        | no       | string | Reference allele |
| alts       | no       | string | Alt allele(s) |
| genotype   | yes      | string | Slash-separated SORTED alleles (A/G not G/A) |
| weight     | yes      | float  | positive=protective, negative=risk, 0=neutral |
| state      | yes      | string | neutral, ref, risk, protective, significant, alt |
| conclusion | yes      | string | Human-readable interpretation |
| gene       | yes      | string | HGNC gene symbol (e.g. MTHFR, APOE) |
| phenotype  | yes      | string | Associated trait/phenotype |
| category   | yes      | string | Grouping category within the module |

### 3. studies.csv (mandatory)

One row per (rsid, pmid):

```
rsid,pmid,population,p_value,conclusion,study_design
```

Every module must have study references. Never invent PMIDs.

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
  version: 1
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
from dna_agents import validate_spec, ValidationResult

result: ValidationResult = validate_spec(Path("my_module/"))
# result.valid: bool
# result.errors: list[str]    — must-fix issues
# result.warnings: list[str]  — should-fix issues
# result.stats: dict          — variant_rows, unique_rsids, unique_genes, etc.
```

## Compilation API

```python
from dna_agents import compile_module, CompilationResult

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
# Produces: weights.parquet, annotations.parquet, studies.parquet
```
