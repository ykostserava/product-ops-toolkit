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

// refuted = the file was read and the claim is contradicted (audit-quality problem).
// unverifiable = the check itself could not run (unreadable file, ambiguous path,
// repo state) — a legal outcome that must NOT count against the audit's verdict.
// `checked` and `verdict` are deliberately NOT in this schema: both are computed
// deterministically in the workflow (see verdictFor), never taken from the model.
const VERIFY_SCHEMA = {
  type: 'object',
  required: ['confirmed', 'refuted', 'unverifiable'],
  properties: {
    confirmed: { type: 'array', items: { type: 'string' } },
    refuted: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'reason'],
        properties: { claim: { type: 'string' }, reason: { type: 'string' } },
      },
    },
    unverifiable: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'reason'],
        properties: { claim: { type: 'string' }, reason: { type: 'string' } },
      },
    },
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
    verification_summary: {
      type: 'array',
      items: {
        type: 'object',
        required: ['platform', 'verdict'],
        properties: {
          platform: { type: 'string' },
          verdict: { type: 'string' },
          checked: { type: 'number' },
          confirmed: { type: 'number' },
          refuted: { type: 'number' },
          unverifiable: { type: 'number' },
          unevidenced: { type: 'number' },
          demoted: { type: 'number' },
        },
      },
    },
    _coverage_matrix_md: { type: 'string' },
  },
  additionalProperties: true,
}

// Agent role specs are read from disk by each (read-only) Explore agent at start —
// NOT resolved via the agent registry. Rationale: the registry is session-cached and
// can silently drop agents whose .md was momentarily malformed (e.g. a stray BOM);
// reading the file keeps a single source of truth and never goes stale. Workflow
// scripts have no Node API access (the same restriction that forces `date` to arrive
// as an arg), so the environment cannot be probed here — `args.agentsDir` is THE
// override when the agents live elsewhere (a plugin install, or a repo-local copy).
const AGENTS_DIR = (input && input.agentsDir) || '.claude/agents'

// Deterministic evidence gate (no LLM, VVAH-s5-style): a claim is spot-checkable only
// when its citation contains something that looks like a source file (optionally :line).
// FAIL-CLOSED: a citation whose extension is missing from this list is dropped as
// `unevidenced` and never reaches the verify agent — when adding a stack, extend the
// list, or valid citations get discarded. Extensions are word-bounded so `.jsonx`
// does not pass as `.json`.
const FILE_REF_RX = /[\w<>./\\-]+\.(swift|h|hh|hpp|m|mm|c|cc|cpp|kt|kts|java|gradle|ts|tsx|js|jsx|vue|php|py|rb|go|cs|graphql|raml|ya?ml|json|xml|html|twig|scss|css|sql)\b(:\d+)?/i
const hasFileRef = s => typeof s === 'string' && FILE_REF_RX.test(s)

// Deterministic verdict — computed HERE, not by the model, so verdicts are comparable
// across platforms and runs. Driven by refuted (the audit was wrong); unverifiable
// (the check could not run) can only degrade to minor-issues, never to unreliable.
// Rules: (a) if EVERYTHING checked was wrong, that is unreliable at any sample size;
// (b) otherwise the ratio rule needs refuted >= 2, so one wrong citation is never
// 'unreliable' regardless of how few claims a small platform produced.
const verdictFor = (refuted, unverifiable, total) => {
  const allRefuted = refuted >= 1 && refuted === total
  if (allRefuted || (refuted >= 2 && refuted / total >= 0.2)) return 'unreliable'
  if (refuted >= 1 || unverifiable / total > 0.5) return 'minor-issues'
  return 'trustworthy'
}

// Claims are matched between what we supplied and what the verifier echoed back.
// The verifier is a model: whitespace/case wobble must not break the accounting,
// so both sides are compared via this normalisation (semantic edits still miss —
// that lands in `unverifiable` by name, which only ever degrades the verdict).
const norm = s => String(s).replace(/\s+/g, ' ').trim().toLowerCase()
const dedupeBy = (arr, key) => {
  const seen = new Set()
  return arr.filter(x => { const k = key(x); if (seen.has(k)) return false; seen.add(k); return true })
}

phase('Audit')
log(`Auditing feature='${feature}' across ${PLATFORMS.length} platforms: ${PLATFORMS.join(', ')}`)

// Each platform flows audit -> verify independently (no barrier): iOS findings get
// verified while Android is still scanning.
const results = await pipeline(
  PLATFORMS,

  p => agent(
    `First Read your role definition at ${AGENTS_DIR}/${p}-auditor.md (expand a leading '~' ` +
    `to the user home directory) and adopt it EXACTLY ` +
    `(workflow steps, output contract, hard rules). Then perform the task: ` +
    `Audit feature='${feature}' for repo_path='${repos[p]}'. audit_date='${auditDate}'. ` +
    `You are read-only: do not modify any file. ` +
    `Return the full findings object via structured output (including _markdown_report).`,
    { agentType: 'Explore', model: 'sonnet', label: `audit:${p}`, phase: 'Audit', schema: AUDIT_SCHEMA }
  ),

  (audit, p) => {
    if (!audit) return null
    // Evidence gate: entries citing no file never reach the verify agent (nothing to
    // open = nothing to check). The dropped claims are KEPT (not just counted) so the
    // coordinator can attribute them to matrix rows and a human can eyeball them.
    const evidencedEndpoints = (audit.endpoints || []).filter(e => hasFileRef(e.callsite))
    const evidencedEvents = (audit.analytics_events || []).filter(a => hasFileRef(a.trigger))
    // Endpoints the auditor self-demoted to notes ("uncited endpoint: ...") are claims
    // that carry no evidence — kept SEPARATE from `unevidenced` (a demotion is honest
    // self-reporting, not a junk citation, and the coordinator already handles the
    // note via its backend_uncited rule), but they must still reach the verdict:
    // otherwise an audit that demotes everything arrives with endpoints: [] and
    // sails through the zero-claims branch as 'trustworthy'.
    const demoted = (Array.isArray(audit.notes) ? audit.notes : []).filter(n => /^\s*uncited endpoint:/i.test(n))
      .map(n => String(n).trim())
    const unevidenced = (audit.endpoints || []).filter(e => !hasFileRef(e.callsite))
      .map(e => `endpoint ${e.method} ${e.path} (callsite: ${JSON.stringify(e.callsite || '')})`)
      .concat((audit.analytics_events || []).filter(a => !hasFileRef(a.trigger))
        .map(a => `analytics event '${a.event}' (trigger: ${JSON.stringify(a.trigger || '')})`))
    if (unevidenced.length) {
      log(`[prefilter] ${p}: ${unevidenced.length} claim(s) cite no parseable file reference — never verified, reported as unevidenced`)
    }
    // Sample up to 8 endpoint callsites + 8 analytics triggers for the spot-check.
    // Citations are whitespace-collapsed (a callsite with a newline would break the
    // bullet list below AND make a verbatim echo impossible) and deduped, so
    // `checked` counts unique claims.
    const claims = [...new Set([]
      .concat(evidencedEndpoints.slice(0, 8).map(e => `endpoint ${e.method} ${e.path} at ${String(e.callsite).replace(/\s+/g, ' ')}`))
      .concat(evidencedEvents.slice(0, 8).map(a => `analytics event '${a.event}' fired at ${String(a.trigger).replace(/\s+/g, ' ')}`)))]
    if (!claims.length) {
      // Nothing survived the evidence gate. If the audit DID make claims but none carried
      // evidence — whether as junk citations (unevidenced) or as self-demoted notes
      // (demoted) — that is the worst possible signal — the old behaviour (default to
      // trustworthy) inverted the verdict for exactly the audits this gate exists to catch.
      const verdict = (unevidenced.length || demoted.length) ? 'unreliable' : 'trustworthy'
      if (unevidenced.length) {
        log(`[warn] ${p}: every claim lacked a file reference — verdict forced to 'unreliable'`)
      } else if (demoted.length) {
        log(`[warn] ${p}: auditor self-demoted all ${demoted.length} endpoint(s) to notes (no citable evidence) — verdict forced to 'unreliable'`)
      }
      return { platform: p, audit, verification: { checked: 0, confirmed: [], refuted: [], unverifiable: [], unevidenced, demoted, verdict } }
    }
    return agent(
      `Adversarially verify audit claims against the repo at '${repos[p]}'. You are read-only — ` +
      `use only Read/Glob/Grep, never modify files. For each claim below, open the cited file ` +
      `and confirm the referenced call/event actually exists at (or near) the cited line. ` +
      `If a claim cites a file WITHOUT a line number, the check is whether the call/event ` +
      `exists anywhere in that file — such a claim is confirmed or refuted, never unverifiable. ` +
      `Citation shapes that are VALID and must not be refuted for their shape alone: ` +
      `(1) indirect analytics dispatch — the cited location (with OR without a line number) may ` +
      `read e.g. analytics.log(it.analyticsEvent) with the event name declared in a separate file. ` +
      `This rule takes precedence over the whole-file check above. A trace means you located the ` +
      `declaration file:line whose value flows into the dispatch expression; confirm only with such ` +
      `a trace. If you found a dispatch site but cannot pin the declaration, the claim is ` +
      `unverifiable with reason 'dispatch site found, event name not traced' — not confirmed, not ` +
      `refuted. Refute only when the cited file contains no plausible dispatch at all.` +
      (p === 'backend'
        ? ` (2) endpoint claims citing an API spec (.raml/.yaml/openapi) — the check is whether the ` +
          `endpoint DECLARATION sits at (or near) the cited line; account for nested resource syntax ` +
          `(path segments split across nesting levels, lowercase method keywords), and do not refute ` +
          `a spec citation for not being a call site. `
        : ` A spec file (.raml/.yaml/openapi) is NOT a call site for this platform's consumption ` +
          `claims — treat such citations per the normal rules. `) +
      `Sort every claim into exactly one bucket: confirmed (you read the file and the claim ` +
      `holds); refuted (the file does not exist where cited, or you read it and it contains ` +
      `nothing matching the claim); unverifiable (the check itself could not run — unreadable ` +
      `file, ambiguous path, repo state issue — record the concrete reason). Never guess: an ` +
      `unchecked claim is unverifiable, not confirmed. Every claim must appear VERBATIM in ` +
      `exactly one bucket — confirmed is the array of confirmed claim strings.` +
      `\n\nClaims:\n- ${claims.join('\n- ')}`,
      { agentType: 'Explore', label: `verify:${p}`, phase: 'Verify', schema: VERIFY_SCHEMA }
    ).then(v => {
      if (!v) {
        // The VERIFIER died or was skipped — that says nothing about the audit itself.
        // Keep the platform: every sampled claim becomes a NAMED unverifiable entry
        // (verdict degrades to minor-issues via the >50% rule, never to unreliable).
        log(`[warn] verify:${p} agent returned no result — audit kept, sampled claims marked unverifiable`)
        const unverifiable = claims.map(c => ({ claim: c, reason: 'verify agent did not run' }))
        const verdict = verdictFor(0, unverifiable.length, claims.length)
        return { platform: p, audit, verification: { checked: claims.length, confirmed: [], refuted: [], unverifiable, verdict, unevidenced, demoted } }
      }
      // Deterministic accounting guard. Invariant after this block: the three buckets
      // are disjoint, contain only supplied claims, and their sizes sum to `checked`.
      const supplied = new Set(claims.map(norm))
      const extra = v.refuted.length + v.unverifiable.length + v.confirmed.length
      v.refuted = dedupeBy(v.refuted.filter(r => supplied.has(norm(r.claim))), r => norm(r.claim))
      const refutedKeys = new Set(v.refuted.map(r => norm(r.claim)))
      v.unverifiable = dedupeBy(
        v.unverifiable.filter(u => supplied.has(norm(u.claim)) && !refutedKeys.has(norm(u.claim))),
        u => norm(u.claim))
      const flagged = new Set([...refutedKeys, ...v.unverifiable.map(u => norm(u.claim))])
      v.confirmed = claims.filter(c => !flagged.has(norm(c))
        && v.confirmed.some(rc => norm(rc) === norm(c)))
      const dropped = extra - (v.refuted.length + v.unverifiable.length + v.confirmed.length)
      if (dropped > 0) {
        log(`[warn] verify:${p} reported ${dropped} entr(y/ies) outside the supplied claim list or in two buckets — dropped`)
      }
      const reported = new Set([...v.confirmed, ...v.refuted.map(r => r.claim), ...v.unverifiable.map(u => u.claim)].map(norm))
      const missing = claims.filter(c => !reported.has(norm(c)))
      if (missing.length) {
        log(`[warn] verify:${p} did not report ${missing.length}/${claims.length} claim(s) — marked unverifiable by name`)
        missing.forEach(c => v.unverifiable.push({ claim: c, reason: 'verifier did not report this claim' }))
      }
      // 'dispatch site found, event name not traced' caps at minor-issues via verdictFor,
      // so a verifier that never traces can hide behind it — make the reason countable
      // in the run log (a run where it dominates is a lazy verifier, not a clean audit).
      const untraced = v.unverifiable.filter(u => /event name not traced/i.test(u.reason || ''))
      if (untraced.length) {
        log(`[verify] ${p}: ${untraced.length}/${claims.length} claim(s) unverifiable as 'dispatch site found, event name not traced' — such claims can never become 'refuted'`)
      }
      const verdict = verdictFor(v.refuted.length, v.unverifiable.length, claims.length)
      return { platform: p, audit, verification: Object.assign({}, v, { checked: claims.length, verdict, unevidenced, demoted }) }
    })
  }
)

const findings = results.filter(Boolean)
if (!findings.length) {
  throw new Error('No platform produced findings — check repo paths in args.repos')
}

for (const f of findings) {
  const v = f.verification
  if (!v) continue
  if (v.verdict === 'unreliable') {
    log(`[warn] ${f.platform} audit flagged unreliable: ${v.refuted.length} refuted, ${(v.unevidenced || []).length} unevidenced, ${(v.demoted || []).length} demoted — coordinator will be told`)
  }
  if (v.unverifiable && v.unverifiable.length) {
    log(`[note] ${f.platform}: ${v.unverifiable.length} claim(s) unverifiable (check could not run — not counted against the audit)`)
  }
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
  `First Read your role definition at ${AGENTS_DIR}/audit-coordinator.md (expand a leading '~' ` +
  `to the user home directory) and adopt it EXACTLY ` +
  `(workflow steps, output contract, hard rules). Then perform the task: ` +
  `Merge the platform audit findings below into a cross-platform coverage matrix for ` +
  `feature='${feature}', audit_date='${auditDate}'. The findings are provided INLINE as JSON ` +
  `(do not look for a findings_dir on disk). Each entry includes an independent 'verification' ` +
  `spot-check result: treat platforms with verdict 'unreliable' with caution and say so in the ` +
  `report. 'verification.unevidenced' LISTS the claims that cited no parseable file reference ` +
  `and therefore never reached the spot-check — fill 'verification_summary' with one entry per ` +
  `platform ({platform, verdict, checked, confirmed, refuted, unverifiable, unevidenced, demoted} — ` +
  `numbers are COUNTS; confirmed/refuted/unverifiable/unevidenced/demoted arrive as lists, use lengths) and ` +
  `list the unevidenced claims themselves under the affected matrix rows (they are candidate ` +
  `hallucinations, distinct from unverifiable). 'verification.demoted' LISTS the auditor's own ` +
  `"uncited endpoint:" demotion notes — those are honest self-reports of real-but-uncitable ` +
  `endpoints, never candidate hallucinations. For the backend platform handle them via your ` +
  `backend_uncited rule; for consumer platforms list them under the platform's demoted count ` +
  `in the verdicts section (no backend flag - the backend_uncited rule is backend-only). ` +
  `Report 'refuted' and 'unverifiable' separately: ` +
  `refuted means the audit was wrong, unverifiable means the spot-check could not run — never ` +
  `conflate the two. ` +
  `Return the full coverage object via structured output (including _coverage_matrix_md).\n\n` +
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
