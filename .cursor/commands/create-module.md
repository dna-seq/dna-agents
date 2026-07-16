# Create genetics annotation module

Create a just-dna-lite SNP annotation module from the user's request (paper, variant list, or freeform topic).

## Orchestration (Cursor equivalent of Claude Code `/workflow create-module`)

1. Read `.claude/agents/researcher.md` and spawn **2–3** Task subagents with `subagent_type: researcher` in parallel on the same research task.
2. Merge consensus variants (prefer findings confirmed by 2+ researchers).
3. Task `reviewer` with the draft + researcher outputs (read `.claude/agents/reviewer.md`).
4. As PI: fix all ERRORS, address WARNINGS conservatively, write to an output directory:
   - `module_spec.yaml`
   - `variants.csv`
   - `studies.csv`
   - `MODULE.md`
5. Validate: `uv run just-dna-agents validate <output_dir>/<module_name>/`
6. Fix until valid. Optionally compile: `uv run just-dna-agents compile … -o …`

## Rules

Follow `AGENTS.md` and `.cursor/rules/just-dna-agents-critical.mdc`. GRCh38, forward-strand alleles, verified PMIDs, epistemic humility.

For a faster solo path, Task `module-creator` once instead of the full team.
