export const meta = {
  name: 'eval-module',
  description: 'Evaluate the create-module workflow against ground-truth eval data',
  whenToUse: 'When asked to evaluate agent quality, run evals, or test the module creation workflow',
  phases: [
    { title: 'Create', detail: 'Run create-module workflow against eval input' },
    { title: 'Score', detail: 'Score agent output against ground truth' },
    { title: 'Report', detail: 'Summarize evaluation results' },
  ],
}

const SCORE_SCHEMA = {
  type: 'object',
  properties: {
    eval_name: { type: 'string' },
    overall_score: { type: 'number' },
    variant_recall: { type: 'number' },
    variant_precision: { type: 'number' },
    genotype_completeness: { type: 'number' },
    weight_accuracy: { type: 'number' },
    weight_direction: { type: 'number' },
    pmid_recall: { type: 'number' },
    pmid_precision: { type: 'number' },
    gene_accuracy: { type: 'number' },
    missing_variants: { type: 'array', items: { type: 'string' } },
    extra_variants: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['eval_name', 'overall_score', 'variant_recall', 'pmid_recall'],
}

const evalName = args?.eval || 'cyp_panel'
const evalsDir = args?.evals_dir || 'data/evals'
const outputBase = args?.output_dir || 'data/eval_output'
const numResearchers = args?.researchers || 3

const evalDir = `${evalsDir}/${evalName}`
const outputDir = `${outputBase}/${evalName}`

phase('Create')
log(`Running create-module against ${evalDir}/freeform_input.md...`)

const createResult = await agent(
  `Read the file ${evalDir}/freeform_input.md and use its contents as the research task.

Create a genetics annotation module based on the freeform description in that file.
Write the output files (module_spec.yaml, variants.csv, studies.csv) to: ${outputDir}/

IMPORTANT:
- Read the freeform_input.md file FIRST to understand what module to create
- Include ALL variants mentioned in the input
- Include ALL PMIDs mentioned in the input
- Write proper CSV files with headers matching the spec format
- Validate the output with: uv run just-dna-agents validate ${outputDir}/

The variants.csv core columns: rsid,genotype,weight,state,conclusion,gene,phenotype,category
The studies.csv core columns: rsid,pmid,population,p_value,conclusion,study_design
Optional columns (e.g. chrom/start/ref/alts, priority, clin_sig, actionability) may be
added — call the MCP get_spec_format tool for the authoritative column set. Unknown or
misspelled columns are a hard compile error, so match names exactly.`,
  {
    label: `create-${evalName}`,
    phase: 'Create',
    agentType: 'module-creator',
  }
)

phase('Score')
log(`Scoring agent output against ground truth...`)

const scoreResult = await agent(
  `Score the agent-produced module at ${outputDir}/ against the ground truth at ${evalDir}/.

Run this command:
uv run just-dna-agents eval ${outputDir}/ ${evalDir}/

Then also manually compare:
1. Read ${outputDir}/variants.csv and ${evalDir}/variants.csv
2. Read ${outputDir}/studies.csv and ${evalDir}/studies.csv
3. Count how many expected rsids are present vs missing
4. Check if PMIDs match
5. Check if weights and states are reasonable

Return structured scores.`,
  {
    label: `score-${evalName}`,
    phase: 'Score',
    schema: SCORE_SCHEMA,
  }
)

phase('Report')
log('Generating evaluation report...')

const report = await agent(
  `Write a concise evaluation report for the ${evalName} module creation eval.

Agent output directory: ${outputDir}/
Ground truth directory: ${evalDir}/

Scores: ${JSON.stringify(scoreResult, null, 2)}

Create output: ${typeof createResult === 'string' ? createResult.slice(0, 2000) : JSON.stringify(createResult).slice(0, 2000)}

Write the report to ${outputBase}/${evalName}_report.md with:
- Overall score and pass/fail (>70% = pass)
- Per-dimension breakdown
- Specific errors (missing variants, wrong weights, missing PMIDs)
- Recommendations for improving agent prompts

Keep the report under 100 lines.`,
  {
    label: `report-${evalName}`,
    phase: 'Report',
  }
)

return {
  eval_name: evalName,
  scores: scoreResult,
  output_dir: outputDir,
  report: typeof report === 'string' ? report.slice(0, 1000) : report,
}
