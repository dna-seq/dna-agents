# Evaluation Guide — DNA Agents

This document describes how to evaluate the quality of Claude Code agents
that create genetics annotation modules. It covers manual testing, the
automated eval CLI, and CI-friendly pytest integration.

## Overview

The eval system compares agent-produced modules against ground truth on
8 dimensions. Ground truth is loaded from HF parquet modules where
available, falling back to local spec directories for modules not on HF:

| Dimension              | Weight | What it measures                              |
|------------------------|--------|-----------------------------------------------|
| variant_recall         | 2.0x   | Fraction of expected rsids found              |
| variant_precision      | 1.0x   | Fraction of agent rsids that are expected      |
| genotype_completeness  | 1.5x   | All expected genotypes present per variant     |
| weight_accuracy        | 1.0x   | Mean absolute error of weights (0 = perfect)   |
| weight_direction       | 1.5x   | State agreement (risk/protective/neutral)      |
| pmid_recall            | 1.5x   | Fraction of expected PMIDs cited               |
| pmid_precision         | 0.5x   | Fraction of agent PMIDs that are expected       |
| gene_accuracy          | 1.0x   | Correct gene symbols per variant               |

Overall score is a weighted average, 0–100%. Pass threshold: **70%**.

## Ground-Truth Sources

Ground truth can be loaded from three sources:

1. **HF parquet modules** (preferred): `just-dna-agents eval output/ longevitymap --rsids rs3758391,rs107251`
   Loads weights.parquet + annotations.parquet + studies.parquet directly from
   `just-dna-seq/annotators`. Use `--rsids` to restrict to a subset.
2. **Local parquet**: `just-dna-agents eval output/ data/modules/longevitymap/`
3. **Spec directory**: `just-dna-agents eval output/ data/evals/cyp_panel/`
   for modules not on HF (e.g. pharmacogenomics).

### Eval cases

| Eval | Ground truth | Notes |
|------|-------------|-------|
| sirtuin_longevity | HF `longevitymap` (7 rsids) | Sirtuin pathway subset |
| cyp_panel | Local spec dir | Pharmacogenomics, no HF module yet |

### Local eval data

Eval datasets in `data/evals/` each contain:

```
data/evals/
├── cyp_panel/             # Pharmacogenomics (CYP2C19, CYP2D6, CYP2C9, CYP3A4)
│   ├── freeform_input.md  # Agent prompt — what the agent receives
│   ├── module_spec.yaml   # Expected module metadata
│   ├── variants.csv       # Expected variants (7 rsids, 21 genotype rows)
│   └── studies.csv        # Expected study citations (9 unique PMIDs)
└── sirtuin_longevity/     # Longevity (SIRT1, SIRT3, SIRT6)
    ├── freeform_input.md
    ├── module_spec.yaml
    ├── variants.csv       # 7 rsids, 27 genotype rows (from HF longevitymap)
    └── studies.csv        # 13 study rows from HF longevitymap
```

Additional test fixtures in `tests/fixtures/evals/` (mthfr_nad, cyp_panel).

### Regenerating ground truth from HF

```bash
# Download module and reverse-compile to spec format
uv run just-dna-agents download-modules -m longevitymap --reverse
```

## Paper Downloader

Download the actual papers referenced in eval data for context grounding:

```bash
# Download metadata + open-access full text for all PMIDs in studies.csv
uv run just-dna-agents download-papers data/evals/cyp_panel/

# Metadata only (faster)
uv run just-dna-agents download-papers data/evals/cyp_panel/ --no-fulltext

# Custom output directory
uv run just-dna-agents download-papers data/evals/sirtuin_longevity/ -o papers/sirtuin/
```

Output structure:
```
data/papers/cyp_panel/
├── metadata/
│   ├── 17622601.json    # Title, authors, journal, abstract, DOI
│   └── ...
├── fulltext/
│   └── 27441996.xml     # Open-access XML (when available)
└── index.json           # Summary of all downloads
```

Uses the EuropePMC REST API (free, no API key needed). Full text is only
available for open-access papers — typically 1-2 out of ~10 for these panels.

## Manual Evaluation

### Step 1: Run the agent

Use the `module-creator` agent or the `create-module` workflow:

```bash
# Single agent (faster, cheaper)
claude -p \
  --permission-mode bypassPermissions \
  --allowedTools "Bash Read Write Edit WebSearch mcp" \
  "Read data/evals/cyp_panel/freeform_input.md and create a module \
   spec in eval_output/cyp_panel/. Include module_spec.yaml, \
   variants.csv, and studies.csv. Then validate with: \
   uv run just-dna-agents validate eval_output/cyp_panel/"

# Multi-agent workflow (PI + researchers + reviewer)
claude -p \
  --permission-mode bypassPermissions \
  "Run the create-module workflow with args: \
   {task: 'Read data/evals/cyp_panel/freeform_input.md and create a module from it', \
    output_dir: 'eval_output/cyp_panel'}"
```

### Step 2: Score the output

```bash
# Score against local spec ground truth
uv run just-dna-agents eval eval_output/cyp_panel/ data/evals/cyp_panel/

# Score against HF module (preferred for modules on HF)
uv run just-dna-agents eval eval_output/sirtuin/ longevitymap \
  --rsids rs3758391,rs12778366,rs7896005,rs4746720,rs11555236,rs4980329,rs107251
```

Example output:
```
                 Evaluation Score
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
│ Dimension             │        Score │ Details                      │
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ variant_recall        │   100% (7/7) │                              │
│ variant_precision     │   100% (7/7) │                              │
│ genotype_completeness │ 100% (21/21) │                              │
│ weight_accuracy       │   100% (1/1) │                              │
│ weight_direction      │ 100% (21/21) │                              │
│ pmid_recall           │   100% (9/9) │                              │
│ pmid_precision        │   100% (9/9) │                              │
│ gene_accuracy         │   100% (7/7) │                              │
└───────────────────────┴──────────────┴──────────────────────────────┘

Overall: 100.0%
```

### Step 3: Iterate on agent prompts

If scores are low, the most impactful changes:
- **Low variant recall** → improve the agent prompt in `.claude/agents/researcher.md`
  to emphasize extracting ALL variants from the input
- **Low PMID recall** → ensure the freeform input lists PMIDs clearly;
  adjust researcher instructions to preserve cited PMIDs
- **Wrong weight direction** → clarify state/weight rules in the agent prompt
- **Low genotype completeness** → emphasize "include ref/ref, ref/alt, alt/alt
  for every variant" in agent instructions

## Semi-Automated Evaluation (pytest)

Integration tests in `tests/test_agent_evals.py` run the `claude` CLI
in print mode, parse the output, and score it. These tests use your
Claude Code subscription — no separate API key needed.

### Running agent evals

```bash
# Run all agent evals (slow — each spawns a claude session)
uv run pytest tests/test_agent_evals.py -v -m agent_eval

# Run a specific eval
uv run pytest tests/test_agent_evals.py -v -m agent_eval -k cyp_panel

# With a specific model
CLAUDE_MODEL=sonnet uv run pytest tests/test_agent_evals.py -v -m agent_eval
```

### What the tests do

1. Read `freeform_input.md` from the eval directory
2. Run `claude -p` with the module-creator agent and the freeform input as prompt
3. The agent writes `module_spec.yaml`, `variants.csv`, `studies.csv` to a temp dir
4. Score the output against ground truth using `score_module()`
5. Assert minimum thresholds (default: 70% overall, 60% variant recall)

### Configuration

Tests respect environment variables:

| Variable             | Default      | Description                              |
|----------------------|--------------|------------------------------------------|
| `CLAUDE_MODEL`       | (default)    | Model override (e.g. `sonnet`, `opus`)   |
| `EVAL_MIN_OVERALL`   | `0.70`       | Minimum overall score to pass            |
| `EVAL_MIN_RECALL`    | `0.60`       | Minimum variant recall to pass           |
| `EVAL_TIMEOUT`       | `600`        | Seconds before the claude process times out |

### Interpreting failures

A failing eval test prints the full score breakdown and details about
what was missing. Common failure modes:

- **Timeout**: agent took too long (MCP server latency, too many tool calls).
  Increase `EVAL_TIMEOUT` or simplify the agent prompt.
- **Low recall**: agent missed variants mentioned in the input. Check if the
  freeform input is ambiguous or if the agent stopped early.
- **Wrong weights**: agent used different magnitude conventions. The eval
  scorer uses MAE — small deviations (<0.3) are tolerated.
- **Missing PMIDs**: agent didn't preserve PMIDs from the input. Most common
  when the agent uses MCP tools instead of reading the attached text.

## Eval Workflow (multi-agent)

For evaluating the full `create-module` workflow (PI + researchers + reviewer):

```bash
claude -p \
  --permission-mode bypassPermissions \
  "Run the eval-module workflow with args: {eval: 'cyp_panel'}"
```

This runs create-module → scores → generates a report in `data/eval_output/`.

## Adding New Evals

1. Create a new directory under `data/evals/<name>/`
2. Write `freeform_input.md` — the prompt the agent will receive
3. Create ground-truth `module_spec.yaml`, `variants.csv`, `studies.csv`
4. Download papers: `uv run just-dna-agents download-papers data/evals/<name>/`
5. Self-test: `uv run just-dna-agents eval data/evals/<name>/ data/evals/<name>/`
   (should score 100%)
6. Add the eval name to the `EVAL_CASES` list in `tests/test_agent_evals.py`

## Testing Claude Code Agents — General Approach

There is no built-in `claude eval` command. The standard approach for
testing Claude Code agents is:

1. **Deterministic tests** (pytest, no LLM) — test the compiler, resolver,
   and scorer independently. These are fast and cheap. Already in
   `test_module_compiler.py`.

2. **Agent integration tests** (pytest + `claude -p`) — run the agent in
   non-interactive mode, score output against ground truth. Uses your
   Claude Code subscription. Semi-automated: runs in CI if `claude` is
   authenticated.

3. **Workflow evals** (`eval-module.js`) — the full multi-agent workflow
   with built-in scoring and reporting. Most comprehensive but most expensive.

4. **Round-trip tests** (`test_module_roundtrip.py`) — download production
   modules from HuggingFace, reverse-engineer to spec, recompile, compare.
   Tests compiler fidelity, not agent quality.

The eval loop: run agent → score → identify weakest dimension → tune agent
prompts in `.claude/agents/*.md` → re-run → compare scores.
