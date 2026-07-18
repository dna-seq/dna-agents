---
description: Create a research-use SNP annotation module from evidence.
---

For a high-confidence SNP module, delegate the request to two or three
`researcher` agents in parallel, then delegate the combined evidence to
`reviewer`. Synthesize only grounded findings into a spec with
`module_spec.yaml`, `variants.csv`, and `studies.csv`.

Call `get_spec_format`, then validate with `validate_spec`. Fix validation
errors before returning the compiled module location.
