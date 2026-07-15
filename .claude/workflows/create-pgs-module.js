export const meta = {
  name: 'create-pgs-module',
  description: 'Create a polygenic-score (PGS) annotation module by curating PGS Catalog entries',
  whenToUse: 'When the source is a polygenic/PRS study or a set of PGS Catalog IDs (PGSxxxxxx)',
  phases: [
    { title: 'Create', detail: 'pgs-module-creator curates the pgs.csv manifest' },
    { title: 'Validate', detail: 'compile-validate the emitted spec' },
  ],
}

const task = args?.task || 'Create a PGS module based on the user request.'
const outputDir = args?.output_dir || 'module_output'

phase('Create')
log('Running pgs-module-creator...')

const createPrompt = `${task}

Write a PGS module spec directory under ${outputDir}/<module_name>/:
- module_spec.yaml (icon/color via list_icons/list_colors; top-level authorship block)
- pgs.csv (one row per curated PGSxxxxxx id; put the source citation in the note field)
- NO studies.csv (PGS rows have no variant identifier — citations go in note)

Call the MCP get_spec_format tool for the exact PgsRow columns. Then validate with
  uv run dna-agents validate ${outputDir}/<module_name>/
and fix any errors until it passes. Report the final spec directory path.`

const created = await agent(createPrompt, {
  label: 'pgs-module-creator',
  phase: 'Create',
  agentType: 'pgs-module-creator',
})

phase('Validate')
log('pgs-module-creator finished; see its report for the validated spec path.')

return { success: true, output: created }
