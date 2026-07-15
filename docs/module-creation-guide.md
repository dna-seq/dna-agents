# Creating Annotation Modules: A Guide for Non-Biologists

You don't need a biology degree to create annotation modules — you need the
right kind of source material and an AI agent to do the heavy lifting. This
guide explains what makes a paper useful for module creation, what doesn't work,
and how to find good sources.

For a video walkthrough of the annotation principles (using the just-dna-lite
UI), see the [YouTube tutorial](https://www.youtube.com/watch?v=81ZKngPbBj0).
The concepts are the same — here you'll use Claude Code or another AI agent
instead of the web interface.

## What is an annotation module?

An annotation module maps genetic findings to their effects, with a
human-readable conclusion and (for variant claims) published references (PMIDs).
The most common kind maps specific DNA variants (SNPs) — each with an rsid (like
`rs1801133`) and genotypes (like `C/C`, `C/T`, `T/T`) — to what each genotype is
associated with.

As of just-dna-format 0.4 a module **composes from several kinds**, so more source
material is now usable:

| Module kind | Source material | Creator agent |
|-------------|-----------------|---------------|
| **SNP** | Individual rsid→trait associations (the classic case) | `module-creator` |
| **PGS** | A published PGS Catalog polygenic score (`PGSxxxxxx`) | `pgs-module-creator` |
| **PGx** | Star-allele pharmacogenomics (CPIC/PharmVar/PharmGKB gene-drug) | `pgx-module-creator` |
| **Binning** | Copy number, repeat expansion, mtDNA heteroplasmy | *coming soon* |

For an SNP module, the source must contain **specific SNP-level associations**.
For PGS it must name a **PGS Catalog id**. For PGx it must give **star-allele /
diplotype** definitions. When unsure which kind fits, ask `@paper-scout` — it
classifies each paper and names the kind + agent to run.

## The paper taxonomy: what works and what doesn't

### Papers that work well

| Paper type | Why it works | What to look for |
|------------|-------------|-----------------|
| **Candidate-gene study** | Tests specific variants for association with a trait. Contains rsids, effect sizes, p-values. | Tables with rsid columns, odds ratios, p-values → **SNP** (`module-creator`) |
| **Pharmacogenomics guideline** (CPIC, PharmVar, PharmGKB) | Curated star-allele → drug-response tables. | Haplotype/diplotype→phenotype tables, allele functions, dosing per genotype → **PGx** (`pgx-module-creator`) |
| **PRS / polygenic score study** | Reports a published polygenic score. | A `PGSxxxxxx` PGS Catalog id → **PGS** (`pgs-module-creator`) |
| **GWAS with individual SNPs listed** | Genome-wide study that reports its top hits as individual variants. | Supplementary tables listing significant SNPs with rsids → **SNP** |
| **Functional study of specific variants** | Deep investigation of what a particular variant does. | Named rsids with functional characterization → **SNP** |
| **ClinVar/OMIM-referenced studies** | Studies about clinically annotated variants. | References to known pathogenic or protective variants → **SNP** |

### Papers that DON'T work (and what to do instead)

| Paper type | Why it doesn't work | What to do instead |
|------------|--------------------|--------------------|
| **Review / meta-review** | Summarizes other papers — no original variant data. May mention variants in passing but doesn't contain the evidence tables you need. | Find the **original studies** the review cites. Use the review's reference list as a starting point. |
| **Gene expression / transcriptomics** | Studies gene activity levels (RNA), not DNA variants. No SNP associations. | Only useful if the paper *also* identifies eQTLs (expression quantitative trait loci) — specific SNPs that affect gene expression. |
| **Epigenetics-only** | Studies methylation, histone modification, or chromatin state. No SNP-level data. | Only useful if the paper links specific SNPs to epigenetic changes (e.g. a variant that affects a CpG site). |
| **Population genetics / ancestry** | Studies population structure, migration, or selection — not disease/trait associations. | These papers rarely contain actionable genotype-phenotype links. |
| **Animal model only** | Findings in mice/flies/worms don't have human rsids. | Only useful if the paper validates findings in human cohorts with specific rsids. |

> **Now usable (0.4):** PRS studies with a `PGSxxxxxx` id → build a **PGS module**
> (`pgs-module-creator`), no longer redirected away. CNV / repeat-expansion / mtDNA
> heteroplasmy papers map to the **binning** kind — support is coming; flag them for
> later rather than discarding.

### The supplementary table trap

Many GWAS and association studies hide their most useful data in
**supplementary materials**, not the main text. The main paper might show:
- Manhattan plots (a chart of genome-wide significance — not extractable)
- A few top hits discussed in the text
- QQ plots, LD plots, and other summary visualizations

But the **supplementary tables** often contain:
- Complete lists of significant SNPs with rsids, p-values, effect sizes
- Genotype frequency tables across populations
- Per-variant functional annotation

**Always check for supplementary materials.** When giving a paper to the agent,
attach the supplementary tables too — they're often more useful than the paper
itself.

## How to find good papers

### Option 1: Use the @paper-scout agent

If you're working in Claude Code in this repository, use the `@paper-scout`
agent. Give it a topic (e.g. "variants associated with longevity" or "CYP2D6
pharmacogenomics") and it will:

1. Search EuropePMC and bioRxiv for relevant papers
2. Classify each paper by type (candidate-gene, GWAS, review, PRS, PGx, etc.)
3. Rate suitability and name the **module kind** + creator agent (SNP / PGS / PGx)
4. Flag papers that likely have useful supplementary data
5. Route PRS papers with a PGS Catalog id to a PGS module

### Option 2: Search EuropePMC yourself

Go to [europepmc.org](https://europepmc.org) and search with terms that
suggest individual variant data:

**Good search patterns:**
- `"rs1801133" AND "genotype"` — find papers about a specific variant
- `"CYP2D6" AND "polymorphism" AND "genotype"` — gene + variant language
- `"SNP" AND "association" AND "longevity"` — trait + variant study design
- `"pharmacogenomics" AND "genotype-phenotype"` — drug-gene relationships

**Less useful search patterns:**
- `"gene expression" AND "RNA-seq"` — will find transcriptomics (no SNPs)
- `"review" AND "genetics of"` — will find reviews (no original data)

**For non-SNP kinds:**
- `"PGS Catalog" AND "<trait>"` or a `PGSxxxxxx` id → PGS module (`pgs-module-creator`)
- `"CPIC" OR "PharmVar" AND "<gene>"` → PGx star-allele module (`pgx-module-creator`)

### Option 3: Start from a known variant

If you know specific rsids (e.g. from ClinVar, SNPedia, or a colleague),
skip the paper search entirely. Give the agent a variant list:

```
Create a module for these variants:
- rs1801133 (MTHFR C677T)
- rs1801131 (MTHFR A1298C)
- rs1805087 (MTR A2756G)
```

The agent will research each variant using BioContext KB tools and find
supporting PMIDs automatically.

## What to give the agent

The agent works best when you provide:

1. **A specific paper with supplementary tables** — attach the PDF and any
   supplementary CSV/Excel files. The agent will extract variants from them.

2. **A variant list** — if you already know which rsids you want, just list
   them. The agent handles the rest.

3. **A freeform description** — describe the topic ("pharmacogenomics variants
   for statin metabolism") and the agent will research it from scratch using
   BioContext KB.

### What to tell the agent about the paper

When handing a paper to the agent, it helps to say:
- "The significant SNPs are in Supplementary Table 3"
- "This is a GWAS — the top hits are in Table 2"
- "Focus on the variants in the Results section, not the ones mentioned in the Introduction from other studies"

This saves the agent from extracting variants that are just citations from
other work rather than original findings.

## Choosing a module kind: when to use which

| Scenario | Use |
|----------|-----|
| Paper lists individual SNPs with effect sizes | **SNP module** (`module-creator`) |
| Paper reports a polygenic score with a `PGSxxxxxx` id | **PGS module** (`pgs-module-creator`) — curates the score as a manifest |
| Star-allele pharmacogenomics (CPIC/PharmVar/PharmGKB) | **PGx module** (`pgx-module-creator`) |
| Paper does both (GWAS top hits + PRS) | An SNP module for the top individual SNPs **and** a PGS module for the score |
| Copy number / repeat expansion / mtDNA heteroplasmy | **Binning** kind — coming soon; flag for later |

`just-prs` (github.com/dna-seq/just-prs) is the runtime that *computes* a PGS from
its scoring file; a PGS module here *curates which scores to use* and how to caveat
them. They are complementary.

## Quality checklist

After the agent creates a module, verify:

- [ ] **Identifiers are real** — rsids exist in dbSNP / `PGSxxxxxx` ids exist in the PGS Catalog / star-alleles come from PharmVar (never invented)
- [ ] **PMIDs are real** — study references exist in PubMed (never invented)
- [ ] **Language is cautious** — "associated with", not "causes"
- [ ] **Validation passes** — run `dna-agents validate <module_dir>/`

SNP modules additionally:

- [ ] **Weights make sense** — risk variants are negative, protective are positive
- [ ] **All genotypes present** — each rsid has 3 rows (ref/ref, ref/alt, alt/alt)

## Example workflow

```
# 1. Ask the paper-scout to find suitable papers
@paper-scout Find papers with individual SNP associations for cardiac arrhythmia risk

# 2. Pick a promising paper and create a module (SNP kind)
@module-creator Create an annotation module from this paper: [attach PDF + supplements]

# 2b. Or, by kind:
@pgs-module-creator Curate a PGS module for CAD from PGS Catalog id PGS000135
@pgx-module-creator Create a CYP2D6 star-allele module from the CPIC guideline

# 3. Or use the multi-agent workflow for higher quality (SNP)
/workflow create-module {"task": "Create a cardiac arrhythmia module from these variants: rs1805124, rs12143842, rs10428132"}

# 4. Validate the output
dna-agents validate module_output/cardiac_arrhythmia/
```
