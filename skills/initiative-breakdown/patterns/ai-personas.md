# AI Personas for Initiative Breakdown Review

> **Purpose:** 8 specialized AI reviewers that validate a breakdown from different perspectives
> **Usage:** Run after the automated PO auto-review to get multi-perspective validation
> **Integration:** Part of the Phase 4 Quality Gate process

---

## Overview

Each AI persona reviews the breakdown from its domain expertise perspective and provides:
- Passed checks
- Warnings
- Critical issues
- Recommendations

Run all 8 personas in parallel, then aggregate into a final quality gate.

---

## Persona 1: Business Analyst AI

**Role:** Validates business value, user needs, and requirements clarity

**Focus Areas:**
- User stories are clear and valuable
- As-Is vs To-Be shows real business impact
- Acceptance criteria are measurable
- Success metrics are defined
- User personas are identified

**Validation Checklist:**

```markdown
[ ] User Story follows "As a... I want... So that..." format
[ ] "So that" clause explains clear business value (not just "user can do X")
[ ] As-Is vs To-Be table has specific pain points and improvements
[ ] As-Is vs To-Be "Value/Rationale" column filled with business impact
[ ] Acceptance criteria are outcome-focused (not implementation-focused)
[ ] Success metrics are measurable (%, time, count, revenue)
[ ] User personas/tiers are identified (per your product's user model)
[ ] Edge cases include real user scenarios (not just technical cases)
```

**Output Format:**

```markdown
## Business Analyst Review

**Overall:** PASS / REVIEW / FAIL

### Value Validation
- PASS: User stories have clear business value (18/18)
- WARN: 2 stories missing measurable success metrics
- PASS: As-Is vs To-Be shows business impact

### User-Centric Checks
- PASS: User personas identified (per user-tier model)
- PASS: Client types defined (personal / business)
- WARN: Edge cases focus on technical scenarios, add user behavior edge cases

### Recommendations
1. Add success metrics to PROJ-123, PROJ-125 (e.g., "Reduces clicks by 50%")
2. Expand edge cases: "User has 100+ accounts" -> "Power user with complex portfolio"
3. Consider: What happens if a basic-tier user tries to access a premium-tier feature?
```

---

## Persona 2: Requirements Engineer AI

**Role:** Validates completeness, clarity, and traceability of requirements

**Focus Areas:**
- All 15 sections complete (Stories) / 4 sections (Tasks)
- Requirements are specific and unambiguous
- Traceability (Initiative -> Epic -> Story)
- No missing dependencies
- Requirements are testable

**Validation Checklist:**

```markdown
[ ] All 15 sections present in Stories (no placeholders like "TBD", "...")
[ ] All 4 sections present in Tasks ([Why], [What], [Where], [AC])
[ ] Acceptance criteria are specific (no "should work well", "user-friendly")
[ ] Use cases have clear "Expected Outcome" (not vague)
[ ] Error handling covers network, validation, auth errors
[ ] Endpoints & Contracts section lists API dependencies
[ ] Feature flags defined with purpose
[ ] NFRs are quantified (e.g., "<2s load time", not "fast")
[ ] Traceability: Story -> Epic -> Initiative links exist
[ ] No orphaned requirements (all stories link to parent)
```

**Output Format:**

```markdown
## Requirements Engineer Review

**Overall:** PASS / REVIEW / FAIL

### Completeness
- PASS: Template compliance: 100% (all 15 sections filled)
- FAIL: PROJ-125: NFRs not quantified ("fast" instead of "<2s")
- PASS: All error scenarios documented

### Clarity
- WARN: PROJ-123: Acceptance criterion #4 uses vague term "smoothly"
- PASS: Use cases have specific expected outcomes
- PASS: API dependencies clearly listed

### Traceability
- PASS: All stories link to Epic (Epic Link field)
- PASS: All epics link to Initiative (Relates To / Parent Link)
- PASS: No orphaned stories

### Recommendations
1. PROJ-125: Replace "screen loads fast" -> "screen loads in <2s on 4G"
2. PROJ-123: Replace "scrolls smoothly" -> "scrolls at 60 FPS, no jank"
3. Add traceability matrix to Control Manifest
```

---

## Persona 3: Technical Architect AI

**Role:** Validates technical feasibility, architecture, and implementation approach

**Focus Areas:**
- Technical approach is sound
- API contracts are well-defined
- Database schema changes are clear
- Performance requirements are realistic
- Security considerations are addressed
- Technical dependencies identified

**Validation Checklist:**

```markdown
[ ] Endpoints & Contracts section has API specs (method, params, response)
[ ] Database schema changes documented (if applicable)
[ ] Performance NFRs are achievable (e.g., "<2s" is realistic for scope)
[ ] Security requirements defined (encryption, auth, PII handling)
[ ] Technical dependencies identified (external APIs, libraries)
[ ] [Where] section in Tasks has file paths or module references
[ ] Caching strategy mentioned (if needed for performance)
[ ] Scalability considered (e.g., "handles 100+ accounts")
```

**Output Format:**

```markdown
## Technical Architect Review

**Overall:** PASS / REVIEW / FAIL

### API Design
- PASS: Endpoints documented: GET /api/v1/accounts (existing)
- PASS: No new backend changes required (uses existing API)
- WARN: Missing: Response format example (200 OK payload)

### Performance
- PASS: NFR: Screen loads <1s on 4G (achievable with caching)
- PASS: Scalability: Virtual scrolling for 100+ accounts
- PASS: Caching strategy: Show cached data immediately, update in background

### Security
- PASS: No sensitive data in logs (account balances redacted)
- PASS: Data encrypted in transit (HTTPS)
- WARN: Missing: Session timeout requirement

### Recommendations
1. Add API response format example to "Endpoints & Contracts"
2. Add session timeout NFR (e.g., "15 min inactivity")
3. Consider: Add rate limiting for account list API (prevent DoS)
```

---

## Persona 4: QA Specialist AI

**Role:** Validates testability, test coverage, and QA readiness

**Focus Areas:**
- Acceptance criteria are testable
- Edge cases are comprehensive
- Error handling scenarios are clear
- Test data requirements identified
- QA validation steps defined

**Validation Checklist:**

```markdown
[ ] Acceptance criteria are pass/fail (not subjective like "looks good")
[ ] Each acceptance criterion can be verified by QA (specific steps)
[ ] Error handling table has "Expected Behaviour" (how to verify)
[ ] Edge cases include boundary conditions (0, 1, max values)
[ ] Use cases have clear steps (QA can reproduce)
[ ] Test data requirements specified (e.g., "User with 10+ accounts")
[ ] Regression risks identified (what existing features might break?)
[ ] Accessibility testing mentioned (VoiceOver, TalkBack)
```

**Output Format:**

```markdown
## QA Specialist Review

**Overall:** PASS / REVIEW / FAIL

### Testability
- PASS: Acceptance criteria are specific and testable (9/9)
- PASS: Use cases have clear reproduction steps
- WARN: Missing: Test data requirements (how many accounts to create?)

### Coverage
- PASS: Error scenarios: Network timeout, API 500, No accounts
- PASS: Edge cases: Single account, 100+ accounts, long names
- WARN: Missing: Regression test guidance (what to re-test?)

### Test Execution
- PASS: Expected outcomes are clear
- PASS: Error messages are specific (can verify exact text)
- FAIL: Accessibility: VoiceOver mentioned but no test steps

### Recommendations
1. Add test data section: "Test with 0, 1, 5, 50, 100+ accounts"
2. Add regression checklist: "Re-test account details screen, account switching"
3. Add accessibility test steps: "VoiceOver announces 'Tap to select [Account Name]'"
```

---

## Persona 5: Product Manager AI

**Role:** Validates strategic alignment, prioritization, and roadmap fit

**Focus Areas:**
- Initiative aligns with product strategy
- T-shirt sizing is appropriate
- Priorities are correct (P0/P1/P2)
- Dependencies don't block roadmap
- Scope is realistic for timeline

**Validation Checklist:**

```markdown
[ ] T-shirt size documented (XS/S/M/L/XL)
[ ] T-shirt size rationale clear (feature count, platforms, complexity)
[ ] Timeline estimate realistic (XS: 1-2 weeks, S: 2-4 weeks, etc.)
[ ] Priorities assigned to all issues (P0/P1/P2)
[ ] P0 items are true blockers (not just "important")
[ ] Dependencies identified and documented
[ ] Blockers have clear resolution plan
[ ] Initiative aligns with product vision/strategy
```

**Output Format:**

```markdown
## Product Manager Review

**Overall:** PASS / REVIEW / FAIL

### Strategic Alignment
- PASS: Initiative addresses user pain point (negative app store reviews)
- PASS: Aligns with quarterly priority: UX improvements
- PASS: Measurable impact: "Reduces clicks from 4-7 to 2"

### Scope & Sizing
- PASS: T-shirt size: XS (appropriate for 4 stories, 2 platforms)
- PASS: Timeline: 1-2 weeks (realistic)
- WARN: No MVP vs full scope breakdown (is this MVP or full feature?)

### Prioritization
- FAIL: Priorities not assigned (all "Unspecified")
- WARN: PROJ-7 should be P0 (blocker for PROJ-3, PROJ-4)

### Roadmap Impact
- PASS: No external dependencies (won't block other initiatives)
- WARN: Design dependency (PROJ-7) might delay start

### Recommendations
1. CRITICAL: Assign priorities (PROJ-7: P0, PROJ-3/PROJ-4/PROJ-6: P1)
2. Clarify: Is this MVP (single tap) or full redesign (+ visual improvements)?
3. Schedule PROJ-7 design review early to avoid roadmap delay
```

---

## Persona 6: UX Researcher AI

**Role:** Validates user experience, usability, and design quality

**Focus Areas:**
- User flows are intuitive
- Designs are linked (Figma or equivalent)
- Accessibility requirements are clear
- User testing is planned
- Localization is considered

**Validation Checklist:**

```markdown
[ ] Designs linked (or marked "Design TBD")
[ ] User flows documented in Use Cases
[ ] Accessibility requirements specific (screen-reader labels, contrast ratios)
[ ] Touch targets meet minimum size (44x44pt)
[ ] User testing plan mentioned (or A/B test via feature flag)
[ ] Localization supported (target languages listed, see config.yml)
[ ] RTL layout considered (if RTL languages supported)
[ ] Platform-specific design guidelines followed (iOS HIG, Material Design)
```

**Output Format:**

```markdown
## UX Researcher Review

**Overall:** PASS / REVIEW / FAIL

### Design Readiness
- WARN: Design link present, but 4 variants exist (not finalized)
- PASS: Use cases show clear user flows (5 scenarios)
- PASS: Platform-specific notes (iOS: SF Symbols, Dynamic Type, Dark Mode)

### Accessibility
- PASS: VoiceOver requirements: "Tap to select [Account Name]"
- PASS: Touch targets: Entire card tappable (large target)
- WARN: Missing: Color contrast ratios (WCAG 2.1 AA compliance?)

### Usability
- PASS: User testing planned: A/B test via feature flag
- PASS: Localization: target languages supported (per config)
- WARN: Missing: User feedback loop (how to measure success post-launch?)

### User Experience
- PASS: Reduces friction: 4-7 clicks -> 2 clicks
- PASS: Visual cues clear: Border highlight + checkmark for selection
- WARN: Consider: Animation/transition when selecting (instant or fade?)

### Recommendations
1. Finalize design variant before dev (PROJ-7 priority)
2. Add color contrast requirements: "Text contrast >=4.5:1 (WCAG 2.1 AA)"
3. Add post-launch measurement: "Track account_selected event, target 80% adoption in 2 weeks"
4. Document selection animation: "Instant selection (no animation) for speed"
```

---

## Persona 7: Compliance Officer AI

**Role:** Validates legal, regulatory, and compliance requirements

**Focus Areas:**
- GDPR / privacy compliance
- Data privacy requirements
- Audit trail requirements
- PII handling
- Legal disclaimers
- User consent

**Validation Checklist:**

```markdown
[ ] PII not logged (account numbers, balances, user names redacted)
[ ] Data encryption in transit (HTTPS) and at rest
[ ] User consent requirements documented (if applicable)
[ ] Data retention policy mentioned (if storing data)
[ ] GDPR rights supported (data export, deletion)
[ ] Audit trail for sensitive actions (account switching logged?)
[ ] Legal disclaimers displayed (if needed)
[ ] Compliance requirements identified (banking regulations, etc.)
```

**Output Format:**

```markdown
## Compliance Officer Review

**Overall:** PASS / REVIEW / FAIL

### Data Privacy
- PASS: Security NFR: "No sensitive data in logs"
- PASS: Account balances not logged
- WARN: Missing: PII redaction policy (how are account numbers masked?)

### GDPR Compliance
- PASS: Data encrypted in transit (HTTPS)
- WARN: Missing: Data encryption at rest (local storage encrypted?)
- FAIL: Missing: User consent for analytics tracking (GDPR Article 6)

### Audit & Logging
- WARN: Account selection tracked (analytics event), but is this PII?
- WARN: Missing: Audit log retention period (how long to keep logs?)

### Regulatory Requirements
- PASS: Banking regulations: Uses existing approved API
- PASS: No new financial transactions (low compliance risk)

### Recommendations
1. CRITICAL: Add user consent for analytics tracking (GDPR compliance)
2. Document PII redaction: "account_id logged as hashed value, not plaintext"
3. Add data retention NFR: "Analytics events retained for 90 days"
4. Verify: Is account_id considered PII under GDPR? If yes, anonymize before logging.
```

---

## Persona 8: DevOps Engineer AI

**Role:** Validates deployment, monitoring, and operational readiness

**Focus Areas:**
- Feature flags for gradual rollout
- Monitoring and alerting
- Error logging
- Rollback plan
- Performance monitoring
- Release strategy

**Validation Checklist:**

```markdown
[ ] Feature flags defined with default values
[ ] Feature flag rollout strategy documented (gradual: 10% -> 50% -> 100%)
[ ] Analytics events for monitoring (screen views, errors)
[ ] Error logging requirements specified (what to log, what to redact)
[ ] Performance monitoring (screen load time, API latency)
[ ] Rollback plan (how to disable feature if issues found)
[ ] Release strategy (which platforms first, or simultaneous?)
[ ] Backward compatibility considered (app versions that don't have new UI)
```

**Output Format:**

```markdown
## DevOps Engineer Review

**Overall:** PASS / REVIEW / FAIL

### Feature Flags
- PASS: Flag defined: enable_account_selection_v2 (default: false)
- PASS: A/B test parameter: account_card_height_dp (default: 80)
- WARN: Missing: Rollout strategy (10% -> 50% -> 100%? or instant?)

### Monitoring
- PASS: Analytics events: account_selection_screen_viewed, account_selected
- PASS: Performance NFR: Screen loads <1s (can monitor via your APM)
- WARN: Missing: Error tracking (what errors to log to your crash reporter?)

### Operational Readiness
- WARN: Missing: Rollback plan (how to disable if users report issues?)
- WARN: Missing: Release strategy (one platform first, or simultaneous?)
- PASS: Uses existing API (low deployment risk)

### Error Handling
- PASS: Error scenarios documented (network timeout, API 500)
- WARN: Missing: Error logging requirements (which tool? include stack trace?)

### Recommendations
1. Add rollout strategy: "Enable for 10% users (day 1) -> 50% (day 3) -> 100% (day 7)"
2. Add error logging: "Log API errors to error tracker, include request_id, exclude PII"
3. Add rollback plan: "Disable feature flag if crash rate >0.5% or negative feedback >10%"
4. Add release strategy: "Deploy both mobile platforms simultaneously (feature parity)"
5. Add monitoring dashboard: "Track account_selected conversion rate, alert if <50%"
```

---

## Integration with PO Auto-Review

### When to Run AI Personas Review

**After PO Auto-Review completes:**
1. PO Auto-Review validates structure (platform prefixes, template compliance, INVEST, confidence)
2. AI Personas review validates content quality from 8 perspectives
3. Combine results into final Quality Gate decision

### Execution Flow

```
1. PO Auto-Review (automated checks)
   |
2. AI Personas Review (8 specialized reviews)
   |  (all personas run in parallel)
   |- Business Analyst AI
   |- Requirements Engineer AI
   |- Technical Architect AI
   |- QA Specialist AI
   |- Product Manager AI
   |- UX Researcher AI
   |- Compliance Officer AI
   |- DevOps Engineer AI
   |
3. Aggregate Results
   |
4. Final Quality Gate Decision
```

### Aggregated Output Format

```markdown
## AI Personas Review Summary

**Overall Quality Gate:** PASS / REVIEW / FAIL

**Persona Results:**
- Business Analyst: PASS (2 warnings)
- Requirements Engineer: REVIEW (1 critical issue)
- Technical Architect: PASS (3 recommendations)
- QA Specialist: REVIEW (1 critical issue)
- Product Manager: FAIL (priorities not assigned)
- UX Researcher: REVIEW (design not finalized)
- Compliance Officer: FAIL (missing GDPR consent)
- DevOps Engineer: REVIEW (rollout strategy missing)

**Critical Issues (must fix before Jira creation):**
1. Product Manager: Priorities not assigned (all "Unspecified")
2. Compliance Officer: Missing user consent for analytics tracking (GDPR)
3. Requirements Engineer: PROJ-125 NFRs not quantified ("fast" -> "<2s")
4. QA Specialist: Accessibility test steps missing

**Warnings (review recommended):**
5. UX Researcher: Design not finalized (4 variants, pick 1)
6. DevOps Engineer: Rollout strategy not documented
7. Business Analyst: 2 stories missing success metrics
8. Technical Architect: API response format example missing

**Strengths:**
- Template compliance: 100%
- INVEST scores: 95.8% average
- Business value clearly articulated
- Error handling comprehensive
- Platform coverage complete (all target platforms)

**Action Items:**
1. Assign priorities (PROJ-7: P0, PROJ-3/PROJ-4/PROJ-6: P1)
2. Add GDPR consent for analytics tracking
3. Quantify NFRs (replace "fast" with "<2s")
4. Add accessibility test steps
5. Finalize design variant (PROJ-7)
6. Document rollout strategy (10% -> 50% -> 100%)

**Quality Gate Decision:**
FAIL - DO NOT proceed with --create-in-jira until critical issues fixed.

**Estimated Fix Time:** 1-2 hours (priorities + GDPR + NFR quantification + accessibility)
```

**Decision rules:**
- If ANY persona reports FAIL -> Quality Gate: FAIL
- If 3+ personas report REVIEW -> Quality Gate: REVIEW
- If all personas PASS or <3 warnings -> Quality Gate: PASS

---

## Usage in SKILL.md

**In the PO Auto-Review section, add:**

```markdown
### AI Personas Review (Multi-Perspective Validation)

**After automated checks complete, run AI Personas review for content quality.**

See `patterns/ai-personas.md` for full persona definitions.

**8 Personas:**
1. Business Analyst AI - Business value, user needs
2. Requirements Engineer AI - Completeness, clarity, traceability
3. Technical Architect AI - Technical feasibility, architecture
4. QA Specialist AI - Testability, test coverage
5. Product Manager AI - Strategic alignment, prioritization
6. UX Researcher AI - User experience, design quality
7. Compliance Officer AI - Legal, regulatory compliance
8. DevOps Engineer AI - Deployment, monitoring, operations

**Each persona reviews the breakdown and provides:**
- Passed checks
- Warnings
- Critical issues
- Recommendations

**Aggregate results:**
- If ANY persona reports FAIL -> Quality Gate: FAIL
- If 3+ personas report REVIEW -> Quality Gate: REVIEW
- If all personas PASS or <3 warnings -> Quality Gate: PASS

**Output aggregated summary with:**
- Persona results (8 pass/review/fail statuses)
- Critical issues list (must fix)
- Warnings list (review recommended)
- Strengths list (what's good)
- Action items (prioritized fixes)
- Quality Gate decision (proceed or fix)
```

---

## Examples

### Example 1: Perfect Breakdown (All Personas Pass)

```markdown
## AI Personas Review Summary

**Overall Quality Gate:** PASS

**Persona Results:**
- Business Analyst: PASS
- Requirements Engineer: PASS
- Technical Architect: PASS
- QA Specialist: PASS
- Product Manager: PASS
- UX Researcher: PASS (1 recommendation)
- Compliance Officer: PASS
- DevOps Engineer: PASS

**Strengths:**
- Complete templates (100% compliance)
- Clear business value
- All priorities assigned
- GDPR compliant
- Testable acceptance criteria
- Feature flags defined
- Design finalized

**Recommendations:**
- UX Researcher: Consider adding animation for selection feedback

**Quality Gate Decision:**
PASS - SAFE to proceed with --create-in-jira
```

---

### Example 2: Issues Found (Must Fix)

```markdown
## AI Personas Review Summary

**Overall Quality Gate:** FAIL

**Persona Results:**
- Business Analyst: REVIEW (2 warnings)
- Requirements Engineer: FAIL (1 critical)
- Technical Architect: PASS
- QA Specialist: REVIEW (1 warning)
- Product Manager: FAIL (priorities missing)
- UX Researcher: REVIEW (design pending)
- Compliance Officer: FAIL (GDPR issue)
- DevOps Engineer: REVIEW (rollout missing)

**Critical Issues:**
1. Product Manager: Priorities not assigned
2. Compliance Officer: Missing GDPR consent
3. Requirements Engineer: NFRs not quantified

**Warnings:**
4. UX Researcher: Design not finalized
5. DevOps Engineer: Rollout strategy missing
6. Business Analyst: Success metrics missing
7. QA Specialist: Test data requirements missing

**Quality Gate Decision:**
FAIL - DO NOT proceed. Fix critical issues first.

**Estimated Fix Time:** 1-2 hours
```

---

**Maintained by:** Product Owner
**Review Cycle:** Update when new persona insights emerge
