export const meta = {
  name: 'create-pgx-module',
  description: 'Create a star-allele pharmacogenomics (PGx) annotation module from CPIC/PharmVar/PharmGKB',
  whenToUse: 'When the source is gene-drug pharmacogenomics: star-alleles, allele functions, diplotype→phenotype tables',
  phases: [
    { title: 'Create', detail: 'pgx-module-creator builds the star-allele tables' },
    { title: 'Validate', detail: 'compile-validate the emitted spec' },
  ],
}

const task = args?.task || 'Create a PGx module based on the user request.'
const outputDir = args?.output_dir || 'module_output'

phase('Create')
log('Running pgx-module-creator...')

const createPrompt = `${task}

Write a PGx module spec directory under ${outputDir}/<module_name>/, composing from
the tables the evidence supports (include only what you have):
- module_spec.yaml (icon/color via list_icons/list_colors; top-level authorship block)
- haplotypes.csv, allele_function.csv, diplotypes.csv, activity_phenotype.csv,
  and/or pharm_variants.csv

Rules: star-allele strings are verbatim truth; activity_phenotype bins must not overlap
and must include one unresolved=true sentinel; verify defining-variant rsids/alleles on
the GRCh38 forward strand. Call the MCP get_spec_format tool for the exact columns of
each row model. Then validate with
  uv run dna-agents validate ${outputDir}/<module_name>/
and fix any errors until it passes. Report the final spec directory path.`

const created = await agent(createPrompt, {
  label: 'pgx-module-creator',
  phase: 'Create',
  agentType: 'pgx-module-creator',
})

phase('Validate')
log('pgx-module-creator finished; see its report for the validated spec path.')

return { success: true, output: created }
