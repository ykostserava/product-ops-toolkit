// Cross-platform parallel codebase audit — Claude Code Workflow script.
//
// Invoke:  Workflow({scriptPath: "<this file>", args: {
//            feature: "savings",
//            date: "2026-01-15",
//            repos: { ios: "/path/to/ios-repo", android: "/path/to/android-repo",
//                     web: "/path/to/web-repo", backend: "/path/to/backend-repo" },
//            agentsDir: ".claude/agents",
//          }})
//
// args:
//   feature   (required)  short scope name: 'savings', 'home', 'statements', '*'
//   date      (required)  audit date YYYY-MM-DD (workflow scripts cannot call Date.now())
//   repos     (required)  map of platform -> absolute repo path;
//                         omit a platform (or set it to null/'') to skip it
//   agentsDir (optional)  directory holding the *-auditor.md role definitions
//                         (default '.claude/agents'; point it at this toolkit's agents/
//                         directory if you installed the plugin elsewhere)
//   dryRun    (optional)  true = show the launch plan, spawn no agents
//
// Design notes:
//   - No disk persistence inside the workflow (scripts have no filesystem access).
//     The caller writes audits/<date>-<feature>/findings/*.{json,md} + coverage-matrix.*
//     from the returned object (each payload carries its target path in `persist`).
//   - Verify phase: each platform audit gets an adversarial spot-check of its
//     cited file:line references before the coordinator trusts it.
//   - Read-only is enforced by `tools: Read, Glob, Grep` in the agents' frontmatter.

export const meta = {
  name: 'cross-platform-audit',
  description: 'Parallel iOS/Android/Web/Backend feature audit with adversarial verify and merged coverage matrix',
  whenToUse: 'Cross-platform feature audit for product teams: endpoint coverage, UI pattern parity, analytics events and tracking gaps across all four platforms.',
  phases: [
    { title: 'Audit', detail: 'one read-only auditor agent per platform, in parallel' },
    { title: 'Verify', detail: 'adversarial spot-check of cited file:line references' },
    { title: 'Coordinate', detail: 'merge verified findings into coverage matrix' },
  ],
}

// Tolerate args arriving as a JSON-encoded string (happens with some invocation paths).
let input = args
if (typeof input === 'string') {
  try { input = JSON.parse(input) } catch (e) { throw new Error(`args is a non-JSON string: ${input}`) }
}

const feature = input && input.feature
const auditDate = input && input.date
const repos = (input && input.repos) || {}
const PLATFORMS = ['ios', 'android', 'web', 'backend'].filter(p => repos[p])
if (!feature || !auditDate || !PLATFORMS.length) {
  throw new Error(
    `Required args missing (got: ${JSON.stringify(input)}). ` +
    `Example: {feature: 'savings', date: '2026-01-15', repos: {ios: '/path/to/ios-repo'}}`
  )
}
const outDir = `audits/${auditDate}-${feature}`

if (input && input.dryRun) {
  const plan = PLATFORMS.map(p => `${p}-auditor -> ${repos[p]}`)
  log(`[dry-run] would launch ${PLATFORMS.length} auditors, verify each, then coordinate into ${outDir}/coverage-matrix.md`)
  return { dryRun: true, feature, auditDate, plan, outDir }
}

const AUDIT_SCHEMA = {
  type: 'object',
  required: ['platform', 'feature', 'endpoints', 'ui_patterns', 'analytics_events', 'tracking_gaps', '_markdown_report'],
  properties: {
    platform: { type: 'string' },
    feature: { type: 'string' },
    audit_date: { type: 'string' },
    stack: { type: 'object' },
    endpoints: { type: 'array', items: { type: 'object' } },
    ui_patterns: { type: 'array', items: { type: 'object' } },
    analytics_events: { type: 'array', items: { type: 'object' } },
    tracking_gaps: { type: 'array', items: { type: 'object' } },
    notes: { type: 'array', items: { type: 'string' } },
    _markdown_report: { type: 'string' },
  },
  additionalProperties: true,
}

const VERIFY_SCHEMA = {
  type: 'object',
  required: ['checked', 'confirmed', 'refuted', 'verdict'],
  properties: {
    checked: { type: 'number' },
    confirmed: { type: 'number' },
    refuted: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'reason'],
        properties: { claim: { type: 'string' }, reason: { type: 'string' } },
      },
    },
    verdict: { type: 'string', enum: ['trustworthy', 'minor-issues', 'unreliable'] },
  },
  additionalProperties: false,
}

const COVERAGE_SCHEMA = {
  type: 'object',
  required: ['feature', 'platforms_covered', 'endpoint_matrix', 'po_summary', '_coverage_matrix_md'],
  properties: {
    feature: { type: 'string' },
    audit_date: { type: 'string' },
    platforms_covered: { type: 'array', items: { type: 'string' } },
    platforms_missing: { type: 'array', items: { type: 'string' } },
    endpoint_matrix: { type: 'array', items: { type: 'object' } },
    endpoint_gaps: { type: 'object' },
    ui_pattern_equivalents: { type: 'array', items: { type: 'object' } },
    analytics_coverage: { type: 'array', items: { type: 'object' } },
    tracking_gaps: { type: 'array' },
    event_name_drift: { type: 'array' },
    backend_drift: { type: 'array' },
    po_summary: { type: 'object' },
    _coverage_matrix_md: { type: 'string' },
  },
  additionalProperties: true,
}

// Agent role specs are read from disk by each (read-only) Explore agent at start —
// NOT resolved via the agent registry. Rationale: the registry is session-cached and
// can silently drop agents whose .md was momentarily malformed (e.g. a stray BOM);
// reading the file keeps a single source of truth and never goes stale.
const AGENTS_DIR = (input && input.agentsDir) || '.claude/agents'

phase('Audit')
log(`Auditing feature='${feature}' across ${PLATFORMS.length} platforms: ${PLATFORMS.join(', ')}`)

// Each platform flows audit -> verify independently (no barrier): iOS findings get
// verified while Android is still scanning.
const results = await pipeline(
  PLATFORMS,

  p => agent(
    `First Read your role definition at ${AGENTS_DIR}/${p}-auditor.md and adopt it EXACTLY ` +
    `(workflow steps, output contract, hard rules). Then perform the task: ` +
    `Audit feature='${feature}' for repo_path='${repos[p]}'. audit_date='${auditDate}'. ` +
    `You are read-only: do not modify any file. ` +
    `Return the full findings object via structured output (including _markdown_report).`,
    { agentType: 'Explore', model: 'sonnet', label: `audit:${p}`, phase: 'Audit', schema: AUDIT_SCHEMA }
  ),

  (audit, p) => {
    if (!audit) return null
    // Sample up to 8 endpoint callsites + 8 analytics triggers for the spot-check.
    const claims = []
      .concat((audit.endpoints || []).slice(0, 8).map(e => `endpoint ${e.method} ${e.path} at ${e.callsite}`))
      .concat((audit.analytics_events || []).slice(0, 8).map(a => `analytics event '${a.event}' fired at ${a.trigger}`))
    if (!claims.length) {
      return { platform: p, audit, verification: { checked: 0, confirmed: 0, refuted: [], verdict: 'trustworthy' } }
    }
    return agent(
      `Adversarially verify audit claims against the repo at '${repos[p]}'. You are read-only — ` +
      `use only Read/Glob/Grep, never modify files. For each claim below, open the cited file ` +
      `and confirm the referenced call/event actually exists at (or near) the cited location. ` +
      `A claim is refuted if the file does not exist or contains nothing matching the claim. ` +
      `Default to refuted when you cannot confirm.\n\nClaims:\n- ${claims.join('\n- ')}`,
      { agentType: 'Explore', label: `verify:${p}`, phase: 'Verify', schema: VERIFY_SCHEMA }
    ).then(v => ({ platform: p, audit, verification: v }))
  }
)

const findings = results.filter(Boolean)
if (!findings.length) {
  throw new Error('No platform produced findings — check repo paths in args.repos')
}

const unreliable = findings.filter(f => f.verification && f.verification.verdict === 'unreliable')
for (const f of unreliable) {
  log(`[warn] ${f.platform} audit flagged unreliable: ${f.verification.refuted.length} refuted claims — coordinator will be told`)
}

phase('Coordinate')
log(`Merging ${findings.length} verified platform findings`)

// Coordinator gets findings inline (no disk round-trip); _markdown_report stripped to save tokens.
const coordinatorInput = findings.map(f => {
  const slim = Object.assign({}, f.audit)
  delete slim._markdown_report
  return { platform: f.platform, verification: f.verification, audit: slim }
})

const coverage = await agent(
  `First Read your role definition at ${AGENTS_DIR}/audit-coordinator.md and adopt it EXACTLY ` +
  `(workflow steps, output contract, hard rules). Then perform the task: ` +
  `Merge the platform audit findings below into a cross-platform coverage matrix for ` +
  `feature='${feature}', audit_date='${auditDate}'. The findings are provided INLINE as JSON ` +
  `(do not look for a findings_dir on disk). Each entry includes an independent 'verification' ` +
  `spot-check result: treat platforms with verdict 'unreliable' with caution and say so in the ` +
  `report. Return the full coverage object via structured output (including _coverage_matrix_md).\n\n` +
  JSON.stringify(coordinatorInput),
  { agentType: 'Explore', model: 'sonnet', label: 'coordinator', phase: 'Coordinate', schema: COVERAGE_SCHEMA }
)

if (!coverage) throw new Error('Coordinator produced no output')

// Caller persists these (workflow scripts cannot write files):
return {
  feature,
  auditDate,
  outDir,
  persist: findings
    .map(f => ({
      json: `${outDir}/findings/${f.platform}.json`,
      md: `${outDir}/findings/${f.platform}.md`,
      verification: f.verification,
      data: f.audit,
    }))
    .concat([{ json: `${outDir}/coverage-matrix.md.json`, md: `${outDir}/coverage-matrix.md`, data: coverage }]),
  po_summary: coverage.po_summary,
}
