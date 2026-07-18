---
name: genetics-module-authoring
description: Create or assess research-use genetic annotation modules from papers, variant lists, or genomics topics. Use for SNP associations, PGS manifests, and pharmacogenomics star-allele evidence.
---

# Genetics module authoring

Use the `just-dna-agents-mcp` tools to validate and compile module specs. Use
BioContext KB to research evidence, confirm Ensembl forward-strand GRCh38
alleles, and verify every PMID through EuropePMC.

## Route the request

- Unclear paper or topic: delegate to `paper-scout`.
- Individual variant associations: delegate to `module-creator`.
- PGS Catalog score selection: delegate to `pgs-module-creator`.
- Star-allele pharmacogenomics: delegate to `pgx-module-creator`.
- High-stakes SNP requests: delegate parallel `researcher` agents, then
  `reviewer` before authoring.

## Non-negotiable constraints

- Research use only; never provide clinical advice or deterministic predictions.
- Use GRCh38 coordinates only.
- Verify each ref/alt allele against Ensembl on the forward strand.
- Include a neutral reference genotype for SNP module variants.
- Use real, topic-matched PMIDs only.
- Call `get_spec_format` before authoring and `validate_spec` before completion.

The specialized agents contain the authoritative detailed workflows. Keep
runtime schema validation as the final source of truth.
