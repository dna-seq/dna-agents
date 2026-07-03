# DNA Agents

Genetics annotation module builder for the just-dna-lite platform.

## Project layout

uv workspace with two members:

- `dna-agents/` — module compiler library (`dna_agents` package)
- `dna-agents-mcp/` — FastMCP server (`dna_agents_mcp` package)

## Commands

```bash
# Install all workspace dependencies
uv sync

# Run tests
uv run pytest

# Run only unit tests (no network/Ensembl)
uv run pytest -m "not integration"

# Validate a module spec
uv run dna-agents validate /path/to/spec/

# Compile a module
uv run dna-agents compile /path/to/spec/ -o /path/to/output/

# Download papers from EuropePMC for a module's studies.csv
uv run dna-agents download-papers data/evals/cyp_panel/

# Score agent output against ground truth
uv run dna-agents eval candidate_output/ data/evals/cyp_panel/

# Start MCP server (stdio)
uv run dna-agents-mcp serve

# Start MCP server (HTTP)
uv run dna-agents-mcp serve --transport http --port 8000
```

## MCP servers

This project uses BioContext KB for variant research. Configure in `.mcp.json`.

## Agent definitions

- `.claude/agents/module-creator.md` — solo module creator (single agent, full workflow)
- `.claude/agents/researcher.md` — genetics researcher subagent (variant analysis)
- `.claude/agents/reviewer.md` — quality reviewer subagent (error checking)
- `.claude/workflows/create-module.js` — multi-agent orchestration (PI + researchers + reviewer)
- `.claude/workflows/eval-module.js` — evaluate create-module against ground truth evals

## Module creation

Use `@module-creator` for single-agent module creation, or run the
`create-module` workflow for the full PI + researcher team setup.

See `AGENTS.md` for the complete module spec format reference.
