export const meta = {
  name: 'create-module',
  description: 'Create a genetics annotation module using PI + Researchers + Reviewer team',
  whenToUse: 'When asked to create a genetics annotation module from a paper, variant list, or description',
  phases: [
    { title: 'Research', detail: 'Independent researchers analyze variants in parallel' },
    { title: 'Review', detail: 'Reviewer checks draft for errors and consistency' },
    { title: 'Compile', detail: 'PI synthesizes findings and writes final module' },
  ],
}

const RESEARCHER_PROMPT = `You are a genetics research assistant specializing in SNP variant analysis.
You work independently — other researchers are doing the same task in parallel.
Your output will be compared against theirs to establish consensus.

## Rules
- GRCh38 ONLY for all coordinates
- The compiler auto-resolves rsid <-> coordinates. You only need ONE.
- Use cautious language: "associated with", "may contribute to", "suggests"
- NEVER: "causes", "guarantees", "will result in"
- Never invent PMIDs

## Output format
One block per variant:
rsid: rs1234567
gene: GENE1 | ref: A > alt: G
genotypes:
  A/A: neutral, weight 0 — reference genotype observation
  A/G: risk, weight -0.6 — association description
  G/G: risk, weight -1.1 — association description
evidence:
  PMID:12345678 — study design, population, finding

RESEARCH TASK:
`

const REVIEWER_PROMPT = `You are a genetics module quality reviewer. Check the draft module for:
1. Research provenance — variants confirmed by multiple researchers = high confidence
2. Genome build — must be GRCh38 only
3. Variant integrity — real rsids, sorted alleles, all genotypes present, wild-type included
4. Weight/state consistency — negative=risk, positive=protective, magnitudes reasonable
5. Scientific accuracy — real PMIDs, correct gene symbols
6. Epistemic humility — no deterministic claims, no individual predictions

The compiler auto-resolves missing rsid/coordinates, so do NOT flag those as errors.

Return:
- ERRORS: must-fix issues
- WARNINGS: should-fix issues
- OK: what passed

DRAFT TO REVIEW:
`

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    variants: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rsid: { type: 'string' },
          gene: { type: 'string' },
          genotypes: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                genotype: { type: 'string' },
                state: { type: 'string' },
                weight: { type: 'number' },
                conclusion: { type: 'string' },
              },
              required: ['genotype', 'state', 'weight', 'conclusion'],
            },
          },
          evidence: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                pmid: { type: 'string' },
                summary: { type: 'string' },
              },
              required: ['pmid', 'summary'],
            },
          },
        },
        required: ['gene', 'genotypes'],
      },
    },
  },
  required: ['variants'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    errors: {
      type: 'array',
      items: { type: 'string' },
    },
    warnings: {
      type: 'array',
      items: { type: 'string' },
    },
    ok_summary: { type: 'string' },
  },
  required: ['errors', 'warnings', 'ok_summary'],
}

const task = args?.task || 'Create a genetics annotation module based on the user request.'
const numResearchers = args?.researchers || 3
const outputDir = args?.output_dir || 'module_output'

phase('Research')
log(`Spawning ${numResearchers} independent researchers...`)

const researchResults = await parallel(
  Array.from({ length: numResearchers }, (_, i) => () =>
    agent(RESEARCHER_PROMPT + task, {
      label: `researcher-${i + 1}`,
      phase: 'Research',
      schema: FINDINGS_SCHEMA,
    })
  )
)

const validResults = researchResults.filter(Boolean)
log(`${validResults.length}/${numResearchers} researchers returned results`)

if (validResults.length === 0) {
  return { success: false, error: 'All researchers failed to return results' }
}

const allVariants = validResults.flatMap(r => r.variants || [])
const variantsByRsid = {}
for (const v of allVariants) {
  const key = v.rsid || v.gene
  if (!variantsByRsid[key]) variantsByRsid[key] = []
  variantsByRsid[key].push(v)
}

const consensusVariants = []
for (const [key, copies] of Object.entries(variantsByRsid)) {
  const count = copies.length
  const best = copies[0]
  consensusVariants.push({
    ...best,
    confidence: count >= 2 ? 'high' : 'low',
    researcher_count: count,
  })
}

log(`Found ${consensusVariants.length} unique variants (${consensusVariants.filter(v => v.confidence === 'high').length} high-confidence)`)

const draftSummary = consensusVariants.map(v => {
  const genotypes = (v.genotypes || []).map(g =>
    `  ${g.genotype}: ${g.state}, weight ${g.weight} — ${g.conclusion}`
  ).join('\n')
  const evidence = (v.evidence || []).map(e =>
    `  PMID:${e.pmid} — ${e.summary}`
  ).join('\n')
  return `rsid: ${v.rsid || 'unknown'}\ngene: ${v.gene}\nconfidence: ${v.confidence} (${v.researcher_count} researchers)\ngenotypes:\n${genotypes}\nevidence:\n${evidence}`
}).join('\n\n')

phase('Review')
log('Sending draft to reviewer...')

const review = await agent(REVIEWER_PROMPT + draftSummary, {
  label: 'reviewer',
  phase: 'Review',
  schema: REVIEW_SCHEMA,
})

if (review) {
  log(`Review: ${review.errors.length} errors, ${review.warnings.length} warnings`)
}

phase('Compile')
log('PI synthesizing final module...')

const piPrompt = `You are the Principal Investigator synthesizing a genetics annotation module.

You have research results from ${validResults.length} independent researchers and a quality review.

## Consensus Variants
${draftSummary}

## Review Feedback
${review ? `ERRORS: ${JSON.stringify(review.errors)}\nWARNINGS: ${JSON.stringify(review.warnings)}\nOK: ${review.ok_summary}` : 'Reviewer did not return feedback.'}

## Your Task
1. Fix ALL errors identified by the reviewer
2. Address warnings (use conservative estimates for disagreements)
3. Include only high-confidence variants (confirmed by 2+ researchers) unless
   low-confidence ones have strong PMID support
4. Write the final module spec files to: ${outputDir}/

Write three files:
- module_spec.yaml (with proper icon, color, genome_build: GRCh38)
- variants.csv (all genotypes, sorted alleles, proper quoting)
- studies.csv (all PMIDs from researcher evidence)

Then validate the module with: uv run dna-agents validate ${outputDir}/<module_name>/

Use epistemic humility in all conclusions. This is Research Use Only.`

const finalResult = await agent(piPrompt, {
  label: 'pi-synthesizer',
  phase: 'Compile',
})

return {
  success: true,
  researchers: validResults.length,
  variants_found: consensusVariants.length,
  high_confidence: consensusVariants.filter(v => v.confidence === 'high').length,
  review_errors: review?.errors?.length || 0,
  review_warnings: review?.warnings?.length || 0,
  pi_output: finalResult,
}
