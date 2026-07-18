---
description: Create a pharmacogenomics module from CPIC, PharmVar, or PharmGKB evidence.
---

Delegate this request to `pgx-module-creator`. Preserve star-allele strings
verbatim, verify defining variants against Ensembl GRCh38 forward-strand
alleles, and include an unresolved sentinel in any activity-phenotype table.
Validate the composed module with `validate_spec`.
