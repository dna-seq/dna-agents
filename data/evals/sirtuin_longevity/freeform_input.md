# Sirtuin Longevity Panel — Agent Input (Freeform)

Build an annotation module for sirtuin pathway variants associated with human longevity.
Sirtuins (SIRT1–7) are NAD+-dependent deacetylases that regulate aging, metabolism,
DNA repair, and inflammation. Genetic variation in sirtuin genes has been studied in
multiple longevity cohorts across European and Asian populations.

## SIRT1 — Sirtuin 1

Master regulator of aging. Deacetylates p53, NF-κB, PGC-1α, and FOXO transcription
factors. Activated by caloric restriction and NAD+ availability.

- **rs3758391** (T/C): Promoter region variant. The C allele was more common in
  Chinese Han centenarians vs controls (PMID 20633545). A European multi-cohort study
  (Danish, German, Dutch — PMID 22234866) did not replicate the association after
  multiple testing correction, but the gene-level signal was suggestive.

- **rs12778366** (G/C): Intronic variant. The minor C allele was associated with better
  glucose tolerance and lower HbA1c in the Leiden Longevity Study (PMID 23505545).
  Not replicated in the Danish–German–Dutch study (PMID 22234866) or the Ashkenazi
  Jewish LonGenity cohort (PMID 25305471).

- **rs7896005** (A/G): Intronic variant. The G allele showed significant effects on
  telomere length in a US Caucasian cohort (PMID 21972126). No association with longevity
  in the Ashkenazi Jewish cohort (PMID 25305471).

- **rs4746720** (G/C): 3'UTR variant. The C allele was more common in the Chinese Han
  longevity group along with rs3758391/C (PMID 20633545). Genotype distribution did not
  differ significantly between cases and controls when analyzed independently.

## SIRT3 — Sirtuin 3

Mitochondrial matrix deacetylase. Regulates mitochondrial metabolism, ROS detoxification,
and the electron transport chain. Expressed mainly in metabolically active tissues.

- **rs11555236** (A/T): Intronic variant in SIRT3. An Italian Northern cohort longitudinal
  study (PMID 23839864) found an association for rs11555236 in whole-cohort survival
  analysis, though the cross-sectional centenarian vs control comparison was negative.
  A European multi-center study (PMID 19367319) found no significant results.

- **rs4980329** (A/T): Intronic variant. The same Italian Northern cohort (PMID 23839864)
  found an association for rs4980329 in longitudinal survival analysis. Cross-sectional
  analysis was not significant.

## SIRT6 — Sirtuin 6

Nuclear sirtuin involved in DNA double-strand break repair, telomere maintenance, and
glucose homeostasis. SIRT6 knockout mice show accelerated aging.

- **rs107251** (C/T): Intronic variant. A gene-based analysis across Danish, German,
  and Dutch longevity cohorts (PMID 22234866) showed a significant association of SIRT6
  variations with longevity. This was the strongest sirtuin signal in the study.

## Weighting Guidelines

Sirtuin–longevity associations are generally modest in effect size and inconsistently
replicated across populations. Weights should reflect this:

- Variants with replication across populations: weight 0.3–0.7 for protective alleles
- Variants with single-study support: weight 0.1–0.3
- Include neutral/reference genotype at weight 0.0 for all variants
- Use state "protective" for longevity-associated alleles, "neutral" for reference

## Key Studies

- PMID 22234866 — Danish, German, Dutch multi-cohort sirtuin longevity study
- PMID 23839864 — Italian Northern cohort SIRT3 longitudinal survival
- PMID 23505545 — Leiden Longevity Study SIRT1 and glucose metabolism
- PMID 20633545 — Chinese Han centenarian SIRT1 study
- PMID 21972126 — US Caucasian SIRT1 and telomere length
- PMID 25305471 — Ashkenazi Jewish LonGenity SIRT1 replication
- PMID 19367319 — European longevity candidate gene study
