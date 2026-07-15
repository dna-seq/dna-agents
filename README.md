# dna-agents: Genetics Annotation Module Compiler

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Research use only](https://img.shields.io/badge/use-research%20only-orange.svg)](#research-use-only)
[![Not medical advice](https://img.shields.io/badge/medical-not%20advice-red.svg)](#research-use-only)
[![MCP ready](https://img.shields.io/badge/MCP-Claude%20%7C%20Cursor%20%7C%20Codex-blueviolet.svg)](#use-with-claude-cursor-codex-antigravity-or-other-agents)

`dna-agents` is a genetics annotation module compiler for the
[just-dna-lite](https://github.com/dna-seq/just-dna-lite) platform. It
validates and compiles curated SNP genotype annotations — packaged as
`module_spec.yaml` + `variants.csv` + `studies.csv` — into deployable parquet
files used by the just-dna-lite genome annotation pipeline.

The real power is that **AI agents can create these modules for you**. Give an
agent a research paper, a list of variants, or a freeform description like
"longevity-associated SNPs", and it will research the variants, collect study
references, write the spec files, validate them, and compile the output — all
in a single conversation. This works in **Claude Code, Claude Desktop, Cursor,
Codex, Antigravity**, and any other MCP-capable assistant, using your own
subscription with no extra API keys.

You can use it three ways:

- **With an AI agent** (Claude, Cursor, Codex, Antigravity) — connect the MCP
  server and ask the agent to create annotation modules from papers or variant
  lists. The agent handles research, spec writing, validation, and compilation.
- **From the CLI** — validate and compile module specs directly from the
  terminal.
- **As a Python library** — import `dna_agents` for programmatic validation,
  compilation, and Ensembl-based variant resolution.

## Contents

- [Creating modules (guide for non-biologists)](#creating-modules-guide-for-non-biologists)
- [Use with Claude, Cursor, Codex, Antigravity, or other agents](#use-with-claude-cursor-codex-antigravity-or-other-agents)
- [Claude Code agents and workflows](#claude-code-agents-and-workflows)
- [Evals (Quick Play)](#evals-quick-play)
- [Test genomes](#test-genomes)
- [CLI and Python](#cli-and-python)
- [Installation](#installation)
- [Project structure](#project-structure)
- [Module spec format](#module-spec-format)
- [Ensembl variant resolution](#ensembl-variant-resolution)
- [Testing](#testing)
- [Research use only](#research-use-only)

## Creating modules (guide for non-biologists)

You don't need a biology background to create annotation modules — but you do
need the right kind of source material. Not all genomics papers are suitable:

- **Reviews** summarize other work — they contain no original variant data.
  Trace back to the original studies they cite.
- **PRS / polygenic score studies** aggregate thousands of tiny-effect variants
  into a single score. Use [just-prs](https://github.com/dna-seq/just-prs)
  for these instead.
- **Gene expression / epigenetics papers** study RNA or methylation, not DNA
  variants. No SNPs to extract.
- **GWAS papers** are often suitable, but the individual SNP data is frequently
  in **supplementary tables**, not the main text. Always download and attach
  the supplements.

What works best: **candidate-gene studies**, **pharmacogenomics guidelines**
(CPIC/DPWG), and **GWAS papers where you also attach the supplementary tables**.

Use the `@paper-scout` agent in Claude Code to search for and classify papers
before creating a module. It will tell you which papers have extractable SNP
data and which don't.

For a full guide with paper taxonomy, search strategies, and step-by-step
workflow, see [docs/module-creation-guide.md](docs/module-creation-guide.md).

For a video walkthrough of the annotation principles (using the just-dna-lite
UI), see the [YouTube tutorial](https://www.youtube.com/watch?v=81ZKngPbBj0).

## Use with Claude, Cursor, Codex, Antigravity, or other agents

The MCP server exposes the module compiler as structured tools that any
MCP-capable assistant can call. No cloning needed — install from the package
directly.

### Claude Code

```bash
claude mcp add dna-agents-mcp -- uvx dna-agents-mcp serve --transport stdio
```

Or add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "dna-agents-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["dna-agents-mcp", "serve", "--transport", "stdio"]
    }
  }
}
```

### Claude Desktop

Open **Settings > Developer > Edit Config** and add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dna-agents-mcp": {
      "command": "uvx",
      "args": ["dna-agents-mcp", "serve", "--transport", "stdio"]
    }
  }
}
```

Restart Claude Desktop. The module compiler tools will appear in the tools menu
(hammer icon).

### Cursor

Add to `.cursor/mcp.json` in your project, or to your global Cursor MCP
configuration:

```json
{
  "mcpServers": {
    "dna-agents-mcp": {
      "command": "uvx",
      "args": ["dna-agents-mcp", "serve", "--transport", "stdio"]
    }
  }
}
```

### Codex

Add to your Codex MCP server configuration:

```toml
[mcp_servers.dna-agents-mcp]
command = "uvx"
args = ["dna-agents-mcp", "serve", "--transport", "stdio"]
```

### Antigravity / other MCP clients

Any MCP-capable assistant can connect using the server command:
`uvx dna-agents-mcp serve --transport stdio`.

### BioContext KB (recommended)

For variant research, add the [BioContext KB](https://biocontext-kb.fastmcp.app)
MCP server alongside `dna-agents-mcp`. It provides Ensembl, EuropePMC, UniProt,
Open Targets, Reactome, KEGG, ClinicalTrials, AlphaFold, InterPro, OLS, and
STRINGDb tools — everything an agent needs to research variants and find study
references:

```json
{
  "mcpServers": {
    "dna-agents-mcp": {
      "command": "uvx",
      "args": ["dna-agents-mcp", "serve", "--transport", "stdio"]
    },
    "biocontext-kb": {
      "type": "url",
      "url": "https://biocontext-kb.fastmcp.app/mcp"
    }
  }
}
```

### Available MCP tools

| Tool | Description |
|------|-------------|
| `validate_spec` | Validate a module spec directory (YAML structure, CSV validity, cross-row consistency) |
| `compile_module` | Compile a spec to parquet files (weights, annotations, studies) |
| `get_spec_format` | Return the full module spec format reference |
| `list_icons` | Valid Fomantic UI icon names and their semantic uses |
| `list_colors` | Valid hex colors and their semantic uses |

### Example conversation

Once connected, ask your agent something like:

> "Create an annotation module for MTHFR and NAD+ metabolism variants.
> Research each variant, collect PMIDs, and compile the module."

> "I have a paper about coronary artery disease SNPs — create an annotation
> module from it."

> "Build a pharmacogenomics module covering CYP2D6, CYP2C19, and CYP3A4
> variants."

The agent will use `get_spec_format` to learn the spec structure, research
variants using BioContext KB tools (Ensembl for coordinates, EuropePMC for
study references), write the spec files, validate with `validate_spec`, fix
any errors, and compile with `compile_module`.

### Environment variables

The MCP server reads configuration from environment variables with the
`DNA_AGENTS_MCP_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `DNA_AGENTS_MCP_OUTPUT_DIR` | `.` | Default output directory for compiled parquet files |
| `DNA_AGENTS_MCP_RESOLVE_WITH_ENSEMBL` | `true` | Resolve missing rsid/position via Ensembl DuckDB |

## Claude Code agents and workflows

When working in this repository with [Claude Code](https://docs.anthropic.com/en/docs/claude-code),
pre-built agent definitions and a multi-agent workflow are available:

### Agents

| Agent | Invoke with | Description |
|-------|-------------|-------------|
| Paper Scout | `@paper-scout` | Deep-research agent that finds and triages papers suitable for module creation. Classifies papers by type, filters out reviews/PRS/expression-only studies, flags supplementary data. |
| Module Creator | `@module-creator` | Solo agent that creates a complete module from a paper, variant list, or freeform description. Has access to BioContext KB tools. |
| Researcher | `@researcher` | Genetics researcher subagent — variant analysis, literature search, genotype assessment |
| Reviewer | `@reviewer` | Quality reviewer subagent — checks provenance, data integrity, scientific accuracy |

### Multi-agent workflow

The `create-module` workflow orchestrates a full research team:

1. **3 Researcher agents** run in parallel, each analyzing variants from
   different angles
2. **Reviewer agent** checks the researchers' findings for errors and gaps
3. **PI agent** synthesizes everything into the final module spec

Run it from Claude Code:

```
/workflow create-module
```

Or use `@module-creator` for a simpler single-agent flow.

### AGENTS.md (cross-tool instructions)

The `AGENTS.md` file at the repository root contains the complete module spec
format reference, critical rules, and workflow instructions. It is
automatically read by Codex, Antigravity, Cursor, Windsurf, and Aider — so
agents in those tools get the same context as Claude Code agents, even without
the MCP server.

## Evals (Quick Play)

Want to try the module creation workflow without waiting for an agent to do
research? The repo ships two ground-truth eval fixtures — complete module specs
that an agent should be able to reproduce from a freeform description:

| Eval | Topic | Variants | Studies | Freeform input |
|------|-------|----------|---------|----------------|
| `mthfr_nad` | MTHFR & NAD+ metabolism | 24 rows (8 rsids) | 12 PMIDs | Methylation cycle + NAD+ biosynthesis genetics |
| `cyp_panel` | CYP drug metabolism | 21 rows (7 rsids) | 12 PMIDs | Pharmacogenomics panel for CYP2C19, CYP2D6, CYP2C9, CYP3A4 |

Each fixture lives at `tests/fixtures/evals/<name>/` and contains:
- `freeform_input.md` — the natural-language prompt an agent receives
- `module_spec.yaml` — ground-truth YAML metadata
- `variants.csv` — ground-truth variant annotations
- `studies.csv` — ground-truth study references

### Run an eval manually

```bash
# Validate a ground-truth fixture
dna-agents validate tests/fixtures/evals/mthfr_nad/

# Compile it to parquet
dna-agents compile tests/fixtures/evals/cyp_panel/ -o /tmp/cyp_output/
```

### Run an eval with the agent workflow (Claude Code)

The `eval-module` workflow feeds the freeform input to the `@module-creator`
agent, then scores the agent's output against the ground truth:

```
/workflow eval-module {"eval": "mthfr_nad"}
/workflow eval-module {"eval": "cyp_panel"}
```

It runs three phases: **Create** (agent builds the module from `freeform_input.md`),
**Score** (compares against ground truth — variant recall, PMID precision, weight
accuracy), and **Report** (writes an evaluation report with pass/fail and
per-dimension breakdown).

## Test genomes

You can test compiled modules against real whole-genome VCFs without using your
own genome. Two public WGS datasets from the project authors are available on
Zenodo:

1. **Anton Kulaga's Genome** (CC0 / Public Domain)
   - **Zenodo Record**: [18370498](https://zenodo.org/records/18370498)
   - **VCF File**: `antonkulaga.vcf` (~482 MB)
   - **Direct URL**: `https://zenodo.org/api/records/18370498/files/antonkulaga.vcf/content`

2. **Livia Zaharia's Genome** (CC-BY-4.0)
   - **Zenodo Record**: [19487816](https://zenodo.org/records/19487816)
   - **VCF File**: `SIMHIFQTILQ.hard-filtered.vcf.gz` (~349 MB)
   - **Direct URL**: `https://zenodo.org/api/records/19487816/files/SIMHIFQTILQ.hard-filtered.vcf.gz/content`

Download a genome and use it with the just-dna-lite annotation pipeline to see
your compiled modules in action:

```bash
# Download Anton's genome
curl -L -o anton.vcf \
  "https://zenodo.org/api/records/18370498/files/antonkulaga.vcf/content"

# Download Livia's genome
curl -L -o livia.vcf.gz \
  "https://zenodo.org/api/records/19487816/files/SIMHIFQTILQ.hard-filtered.vcf.gz/content"
```

If you also have [just-prs](https://github.com/dna-seq/just-prs) installed,
these genomes are available as built-in aliases (`--vcf anton`, `--vcf livia`)
and auto-download on first use.

## CLI and Python

### CLI

```bash
# Validate a module spec directory
dna-agents validate /path/to/my_module/

# Compile to parquet (auto-resolves missing rsid/position via Ensembl)
dna-agents compile /path/to/my_module/

# Compile with explicit output directory
dna-agents compile /path/to/my_module/ --output /path/to/output/

# Compile without Ensembl resolution
dna-agents compile /path/to/my_module/ --no-resolve

# Run the MCP server directly
dna-agents-mcp serve                              # stdio (default)
dna-agents-mcp serve --transport http --port 8000  # HTTP
```

### Python

```python
from pathlib import Path
from dna_agents.compiler import validate_spec, compile_module

# Validate
result = validate_spec(Path("my_module/"))
print(result.valid, result.errors, result.warnings)

# Compile
result = compile_module(
    Path("my_module/"),
    Path("output/my_module/"),
    resolve_with_ensembl=True,
)
print(result.success, result.stats)
```

## Installation

Requires Python >= 3.14 and [uv](https://github.com/astral-sh/uv).

**As an MCP server (no clone needed):**

```bash
uvx dna-agents-mcp serve --transport stdio
```

**As a CLI tool:**

```bash
uv tool install dna-agents
dna-agents validate /path/to/spec/
```

**From source (development):**

```bash
git clone https://github.com/dna-seq/dna-agents.git
cd dna-agents
uv sync                     # installs both subprojects + dev deps
uv run pytest               # run tests
uv run dna-agents validate  # use the CLI
```

## Project structure

This is a **uv workspace** with two subprojects:

| Package | Directory | Description |
|---------|-----------|-------------|
| **dna-agents** | `dna-agents/` | Core library: module spec validation, compilation to parquet, Ensembl rsid/position resolver, reverse engineering from existing modules. CLI: `dna-agents`. |
| **dna-agents-mcp** | `dna-agents-mcp/` | FastMCP server exposing compiler tools over MCP (stdio and HTTP transports). CLI: `dna-agents-mcp`. |

```
dna-agents/
├── pyproject.toml                  # workspace root
├── AGENTS.md                       # cross-tool agent instructions
├── CLAUDE.md                       # Claude Code project instructions
├── .mcp.json                       # MCP server config for development
├── .env.template                   # env var template
│
├── dna-agents/                     # core library
│   ├── pyproject.toml
│   └── src/dna_agents/
│       ├── compiler.py             # validate, compile, reverse
│       ├── models.py               # pydantic models (VariantRow, ModuleSpec, ...)
│       ├── resolver.py             # Ensembl DuckDB rsid <-> position resolver
│       └── cli.py                  # Typer CLI
│
├── dna-agents-mcp/                 # MCP server
│   ├── pyproject.toml
│   └── src/dna_agents_mcp/
│       ├── server.py               # FastMCP server (create_server factory)
│       ├── config.py               # pydantic-settings config
│       └── cli.py                  # Typer CLI
│
├── .claude/
│   ├── agents/                     # Claude Code agent definitions
│   │   ├── module-creator.md
│   │   ├── researcher.md
│   │   └── reviewer.md
│   └── workflows/
│       └── create-module.js        # multi-agent orchestration
│
└── tests/
    ├── test_module_compiler.py     # 27 unit + 34 integration tests
    ├── test_module_roundtrip.py    # 52 round-trip tests (HF download → reverse → recompile)
    └── fixtures/evals/             # eval fixtures (mthfr_nad, cyp_panel)
```

## Module spec format

A module **composes** from optional table kinds (just-dna-format 0.4). The common
case is the SNP core below (`module_spec.yaml` + `variants.csv` + `studies.csv`);
a module may also/instead carry PGS (`pgs.csv`), PGx star-allele
(`haplotypes.csv`, `allele_function.csv`, `diplotypes.csv`, `activity_phenotype.csv`,
`pharm_variants.csv`), or binning (`copynumbers.csv`, `repeat_alleles.csv`,
`heteroplasmy.csv`) tables. The authoritative, always-current field reference is
served live by the MCP `get_spec_format` / `get_spec_schemas` tools — the tables
below are a quick reference for the SNP core.

### module_spec.yaml

```yaml
schema_version: "1.0"
module:
  name: my_module           # lowercase, underscores only
  title: "My Module"
  description: "One-line description"
  report_title: "Report Title"
  icon: heart-pulse         # see icon catalog below
  color: "#21ba45"          # see color palette below
defaults:
  curator: ai-module-creator
  method: literature-review  # literature-review | gwas | clinvar-review | expert-curation
  priority: medium           # low | medium | high
genome_build: GRCh38        # must be GRCh38
```

### variants.csv

One row per (rsid, genotype) combination:

| Column | Required | Description |
|--------|----------|-------------|
| rsid | yes* | dbSNP ID (rs...). Blank if chrom/start/ref/alts present |
| chrom | no | Chromosome without "chr" prefix |
| start | no | 0-based position (GRCh38) |
| ref | no | Reference allele |
| alts | no | Alt allele(s) |
| genotype | yes | Slash-separated sorted alleles (A/G not G/A) |
| weight | yes | positive = protective, negative = risk, 0 = neutral |
| state | yes | neutral, ref, risk, protective, significant, alt |
| conclusion | yes | Human-readable interpretation |
| gene | yes | HGNC gene symbol |
| phenotype | yes | Associated trait |
| category | yes | Grouping category |

### studies.csv (mandatory)

One row per (rsid, pmid):

| Column | Required | Description |
|--------|----------|-------------|
| rsid | yes | dbSNP ID matching variants.csv |
| pmid | yes | PubMed ID (real — never invented) |
| population | no | Study population |
| p_value | no | Statistical significance |
| conclusion | no | Study finding |
| study_design | no | Study methodology |

### Icon catalog

| Icon | Best for |
|------|----------|
| heart-pulse | longevity, cardiovascular |
| heart | coronary artery disease |
| droplets | lipids, metabolism, blood |
| activity | athletic performance, fitness |
| zap | elite / superhuman performance |
| pill | pharmacogenomics, drug metabolism |
| dna | methylation, epigenetics |
| database | generic / default |
| chart-bar | risk scores, polygenic traits |
| boxes | multi-trait panels |

### Color palette

| Color | Hex | Use |
|-------|-----|-----|
| Green | #21ba45 | longevity, protective, beneficial |
| Yellow | #fbbd08 | metabolism, neutral/mixed |
| Blue | #2185d0 | performance, athletic, cognitive |
| Teal | #00b5ad | elite performance, rare variants |
| Red | #db2828 | disease risk, pathogenic |
| Purple | #a333c8 | pharmacogenomics, drug response |
| Indigo | #6435c9 | default / other genetics |

## Ensembl variant resolution

The compiler resolves missing rsid or genomic position against a local Ensembl
reference cache (GRCh38) via `just-dna-compiler` (inject-only — it never
downloads). You only need to provide **one** of rsid or (chrom + start + ref)
per variant — resolution fills in the other.

The reference is located in this order (see `just_dna_compiler.cache`):

1. Explicit `--ensembl-cache` CLI flag
2. `JUST_DNA_ENSEMBL_CACHE` environment variable (a `.duckdb` file or a directory)
3. `<base>/ensembl_variations/` under `JUST_DNA_PIPELINES_CACHE_DIR`, else the
   platformdirs user cache — the same layout just-dna-lite uses
   (`~/.cache/just-dna-pipelines/ensembl_variations/`)

If none is present, `dna-agents compile --resolve` provisions the parquet cache
from HuggingFace Hub (`just-dna-seq/ensembl_variations`) into
`<base>/ensembl_variations/data/`. If the download can't run (no
`huggingface_hub`), resolution is skipped with a warning rather than failing.

## Testing

```bash
uv run pytest                        # all tests
uv run pytest -m "not integration"   # unit tests only
uv run pytest -m integration         # integration tests only
```

| Suite | Tests | What it validates |
|-------|-------|-------------------|
| `test_module_compiler.py` | 61 | Pydantic models, YAML/CSV parsing, validation rules, weight/state consistency, compilation, Ensembl resolution |
| `test_module_roundtrip.py` | 52 | Downloads modules from HuggingFace (`just-dna-seq/annotators`), reverse-engineers to spec DSL, recompiles, and compares schemas, row counts, rsid sets, genotypes, weights, states, and study PMIDs against originals |

Integration tests require:

- Network access (HuggingFace downloads)
- `HF_TOKEN` in `.env` for private repos
- Ensembl DuckDB cache at `~/.cache/just-dna-pipelines/ensembl_variations/` for resolver tests

Copy `.env.template` to `.env` and fill in your tokens:

```bash
cp .env.template .env
```

## Research use only

These annotation modules are for **research use only**. They summarize
published genetic association findings and are not clinical-grade evidence.

- Use "associated with", "may contribute to", "has been linked to"
- Never use "causes", "guarantees", "will result in"
- No individual-level predictions from population data
- All study references must be real PMIDs — never invented

## Data sources

- [Ensembl Variations](https://www.ensembl.org/) — rsid/position resolution (GRCh38)
- [EuropePMC](https://europepmc.org/) — study references and PMIDs
- [just-dna-seq/annotators](https://huggingface.co/datasets/just-dna-seq/annotators) — existing compiled modules on HuggingFace
- [BioContext KB](https://biocontext-kb.fastmcp.app) — multi-database MCP server for variant research
