# DNA Agents

Genetics annotation module builder for the just-dna-lite platform.

## Project layout

uv workspace with two members:

- `just-dna-agents/` — module compiler library (`just_dna_agents` package)
- `just-dna-agents-mcp/` — FastMCP server (`just_dna_agents_mcp` package)

## Commands

```bash
# Install all workspace dependencies
uv sync

# Run tests
uv run pytest

# Run only unit tests (no network/Ensembl)
uv run pytest -m "not integration"

# Validate a module spec
uv run just-dna-agents validate /path/to/spec/

# Compile a module (auto-resolves rsid <-> GRCh38 coordinates via Ensembl DuckDB)
uv run just-dna-agents compile /path/to/spec/ -o /path/to/output/

# Download papers from EuropePMC for a module's studies.csv
uv run just-dna-agents download-papers data/evals/cyp_panel/

# Download HF annotator modules (parquet files)
uv run just-dna-agents download-modules

# Download a single module with reverse-compile to spec format
uv run just-dna-agents download-modules -m longevitymap --reverse

# List available HF modules
uv run just-dna-agents download-modules --list

# Score agent output against local ground truth
uv run just-dna-agents eval candidate_output/ data/evals/cyp_panel/

# Score against HF module directly (preferred for modules on HF)
uv run just-dna-agents eval agent_output/ longevitymap --rsids rs3758391,rs107251

# Run agent evals (requires claude CLI)
uv run pytest tests/test_agent_evals.py -v -m agent_eval

# Start MCP server (stdio)
uv run just-dna-agents-mcp serve

# Start MCP server (HTTP)
uv run just-dna-agents-mcp serve --transport http --port 8000
```

## Critical rules

1. **GRCh38 ONLY** — all coordinates must be GRCh38. Never use GRCh37/hg19.
2. **Forward-strand alleles ONLY** — ref and alt alleles must match Ensembl's
   forward-strand convention. Never use reverse-strand complement alleles.
3. **Verify ref/alt via Ensembl** — for every rsid, confirm that the ref allele
   matches the GRCh38 reference genome and the alt is a known alternate.
   Genotype alleles must be a subset of {ref, alt}.
4. **Compiler auto-resolution** — the compiler resolves rsid -> coordinates and
   coordinates -> rsid automatically. You only need ONE of them per variant.
5. **Epistemic humility** — Research Use Only. Use "associated with",
   "may contribute to", "has been linked to". NEVER "causes", "guarantees".
6. **Alleles sorted alphabetically** — A/G not G/A, C/T not T/C.
7. **Include wild-type** — every variant needs ref/ref genotype with weight 0.
8. **Weight range** — -1.5 to +1.5.
9. **Verify every PMID** — search EuropePMC for each PMID. Confirm it exists AND
   check that the title, authors, and topic match the variant/gene being cited.
   Never invent PMIDs. A missing citation is better than a wrong one.
10. **studies.csv is mandatory** — modules without study references are not useful.

## MCP servers

This project uses BioContext KB for variant research. Configure in `.mcp.json`.

## Agent definitions

Shared prompts (Claude Code + Cursor — do not fork under `.cursor/`):

- `.claude/agents/paper-scout.md` — deep-research agent: finds and triages papers, routing each to a module kind (SNP / PGS / PGx)
- `.claude/agents/module-creator.md` — solo SNP module creator (single agent, full workflow)
- `.claude/agents/pgs-module-creator.md` — polygenic-score module creator (curates PGS Catalog ids into pgs.csv)
- `.claude/agents/pgx-module-creator.md` — star-allele PGx module creator (haplotypes/allele_function/diplotypes/activity_phenotype/pharm_variants)
- `.claude/agents/researcher.md` — genetics researcher subagent (variant analysis)
- `.claude/agents/reviewer.md` — quality reviewer subagent (error checking)
- `.claude/workflows/create-module.js` — multi-agent SNP orchestration (PI + researchers + reviewer)
- `.claude/workflows/create-pgs-module.js` — single-agent PGS module orchestration
- `.claude/workflows/create-pgx-module.js` — single-agent PGx module orchestration
- `.claude/workflows/eval-module.js` — evaluate create-module against ground truth evals

Cursor-only portable wrappers (rules + slash commands; machine state gitignored):

- `.cursor/rules/` — always-on critical rules + module-creation workflow
- `.cursor/commands/create-module.md` — Cursor equivalent of `/workflow create-module`
- `.cursor/commands/paper-scout.md` — paper triage slash command

## Ground truth & evals

- Deployed HF modules at `just-dna-seq/annotators` are the source of truth for alleles
- Use `download-modules --reverse` to generate eval ground truth from deployed parquet
- Ensembl DuckDB cache at `~/.cache/just-dna-pipelines/ensembl_variations/` for rsid verification
- Downloaded papers go to `data/papers/` (gitignored)
- Downloaded module parquet files go to `data/modules/` (gitignored)

## Module creation

Use `@paper-scout` first to find suitable papers and route each to a module **kind**
(especially useful for non-biologists who may not know which paper types contain
extractable data). A module composes from optional table kinds (just-dna-format 0.4):

- **SNP** — `@module-creator`, or the `create-module` workflow for the full PI +
  researcher + reviewer team.
- **PGS** (polygenic-score manifest) — `@pgs-module-creator`, or `create-pgs-module`.
- **PGx** (star-allele pharmacogenomics) — `@pgx-module-creator`, or `create-pgx-module`.
- **Binning** (copy number / repeat expansion / mtDNA heteroplasmy) — not yet supported.

The authoritative field reference for any kind is the MCP `get_spec_format` /
`get_spec_schemas` tool (drift-proof, generated from the just-dna-format models).

See `AGENTS.md` for the complete module spec format reference.
See `docs/module-creation-guide.md` for a human-facing guide on paper selection.
See `docs/BACKLOG.md` for just-dna-format features not yet adopted (binning kind,
per-kind evals, gene panels, resolver-behavior awareness, ...).
