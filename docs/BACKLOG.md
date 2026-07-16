# Backlog — just-dna-format features to adopt

Tracks 0.4 (and forthcoming) library capabilities not yet wired into the authoring
layer. The library + compiler + MCP server are 0.4-aware; this list is about the
**agents, workflows, evals, and tooling** that still need to catch up.

Status legend: ✅ done · 🔜 next · ⏸ deferred · 💡 idea

## Deferred from the 0.4 advanced-adoption pass

- ⏸ **Binning kind** (`copynumbers.csv` / `repeat_alleles.csv` / `heteroplasmy.csv`).
  Needs a `binning-module-creator` agent + guidance covering: inclusive `[min,max]`
  ranges, the mandatory `unresolved` sentinel (measurement-absent ≠ reference bin),
  the no-overlap rule (`validate_bins`), and per-kind keys (`repeat_unit`;
  `reference_sequence` + `tissue`; `modifier_gene`/`modifier_cn`). Reject the legacy
  `NC_001807` mtDNA reference. Then a `create-binning-module` workflow + docs/guide
  rows (currently flagged "coming soon"). `paper-scout` already routes CNV/repeat/
  mtDNA papers to this kind.

- ⏸ **Eval coverage for composed / non-SNP modules** (all currently SNP-only):
  - `eval_scorer.py` is hard-gated on `weights.parquet` / `variants.csv`; a
    PGS/PGx module today loads as empty and **silently scores ~0** instead of
    erroring. Detect a composed/no-variants module and skip SNP dimensions
    explicitly. (Correctness bug, worth doing even before new dimensions.)
  - Per-kind scoring dimensions: PGS `PGSxxxxxx` id recall; PGx diplotype→phenotype
    accuracy, allele-function agreement, haplotype recall; binning bin-boundary
    correctness.
  - `modules.py` HF downloader/discovery: `MODULE_TABLES` is `[weights, annotations,
    studies]` and discovery is gated on `weights.parquet` — extend to the full 0.4
    table set (or drive from `manifest.json`) so 0.4-only modules are fetchable.
  - `tests/test_agent_evals.py` `_assert_output_files` requires `variants.csv` +
    `studies.csv`; relax to a composed module's table set.
  - New ground-truth fixtures (a PGx `cyp2d6`, a `pgs` fixture) + `EVALS.md` recipe
    + kind-aware `eval-module.js`.

## Other 0.4 columns/features not yet surfaced to agents

- 🔜 **Gene-panel modules** (`panel:` / `GenePanelSpec`). A declared gene-panel
  interface distinct from per-variant rows. No agent guidance yet.
- 🔜 **`icon_set`** on `module` — only the default Fomantic set is assumed. Document
  when a non-default set is in play.
- 🔜 **Richer SNP axes actually populated**, not just documented: `direction`,
  `stat_significance`, `effect_size` + `effect_measure` (OR/HR/beta/RR),
  `effect_allele`, `flags`, `trait_efo_id`. The researcher/module-creator prompts
  mention them; add worked examples so they get filled when evidence supports.
- 💡 **Authorship depth** (`Contribution`): the human ladder
  (`human`/`human_expert`/`human_certified`) and the `at` timestamp are unused —
  relevant once a human reviewer signs off, or for dated edit history.
- 💡 **Reserved namespace awareness** (`reference_db`, `callable_from`): reserved for
  RM6/typed-callability. Agents should never emit them (they hard-fail); note in
  the reviewer once those axes ship as real columns.

## Resolver / compiler behaviors agents should understand

- 🔜 **One-to-many rsid expansion**: a no-coord rsid mapping to several loci is
  expanded into N coord-keyed rows at compile time. The reviewer should treat a
  resulting count > 1 as a paralog/SV signal, not an error.
- 🔜 **Bidirectional rsid↔coord consistency warnings**: the resolver warns (never
  fails) when an authored rsid+coordinate pair disagrees with Ensembl. Surface such
  warnings in review rather than ignoring them.
- ⏸ **Other genome builds (RM15)**: the compiler is GRCh38-bound; GRCh37/T2T are
  recorded but not honored. Revisit if/when build-aware resolution lands.

## Tooling / DX ideas

- 💡 **Runtime schema preflight**: have the module-creator agents actually *call*
  `get_spec_format` at the start of a run (a preflight step), not just reference it,
  so a library bump is picked up automatically mid-task.
- 💡 **Signed modules** (`signing.py`) and **provenance aggregation**
  (`aggregate.py`): expose module signing / multi-manifest provenance summaries via
  the CLI/MCP once there's a consumer for them.
- 💡 **`derive.py` upgrade path**: legacy `state` → (`direction`, `stat_significance`)
  derivation exists in the library; consider a `just-dna-agents upgrade` command to
  migrate older specs to the orthogonal axes.

## Done (for reference)

- ✅ Bump to 0.4.0; live MCP reference tools (`get_spec_format` / `get_spec_schemas`
  / `list_icons` / `list_colors`); palettes from the library.
- ✅ Drift elimination across all prompt/doc surfaces; fixed `1-based`→`0-based`
  and removed invalid `module.version` (both now hard-fail under `extra="forbid"`).
- ✅ SNP-core 0.4 optional columns documented (`actionability`, `acmg_sf`,
  `requires_callable`, tri-state ClinVar flags; `doi` / `provenance_quote` /
  `provenance_regex`).
- ✅ Structured `authorship` emission + reviewer provenance grounding.
- ✅ `pgs-module-creator` + `pgx-module-creator` agents and workflows;
  `paper-scout` and the module-creation guide route papers to a module kind.
