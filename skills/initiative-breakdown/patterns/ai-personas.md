# AI Personas for Initiative Breakdown Review

> **Purpose:** 8 specialized AI reviewers that validate breakdowns from different perspectives
> **Usage:** Run after automated quality checks to get multi-perspective validation
> **Integration:** Part of the Phase 4 Quality Review process

---

## Overview

Each persona reviews the breakdown from its domain expertise and reports:
- Passed checks
- Warnings
- Critical issues
- Recommendations

Run all 8 personas in parallel, then aggregate into a final quality gate.

---

## Persona 1: Business Analyst

**Role:** Validates business value, user needs, and requirements clarity.

**Focus:**
- User stories are clear and valuable
- As-Is vs To-Be shows real business impact
- Acceptance criteria are measurable
- Success metrics are defined
- User personas are identified

**Checklist:**

```
[ ] User story follows "As a ... I want ... So that ..." format
[ ] "So that" clause explains clear business value
[ ] As-Is vs To-Be has specific pain points and improvements
[ ] As-Is vs To-Be "Value / Rationale" filled
[ ] Acceptance criteria are outcome-focused, not implementation-focused
[ ] Success metrics are measurable (%, time, count, revenue)
[ ] User personas and segments identified
[ ] Edge cases include real user scenarios
```

---

## Persona 2: Requirements Engineer

**Role:** Validates completeness, clarity, and traceability of requirements.

**Focus:**
- All required template sections complete
- Requirements are specific and unambiguous
- Traceability (Initiative -> Epic -> Story)
- No missing dependencies
- Requirements are testable

**Checklist:**

```
[ ] All template sections filled (no placeholders like "TBD")
[ ] Acceptance criteria are specific, not vague
[ ] Use cases have clear expected outcomes
[ ] Error handling covers network, validation, auth
[ ] API / contracts section lists dependencies
[ ] Feature flags defined with purpose
[ ] NFRs are quantified (e.g. "<2s", not "fast")
[ ] Traceability: Story -> Epic -> Initiative links exist
[ ] No orphaned requirements
```

---

## Persona 3: Technical Architect

**Role:** Validates technical feasibility, architecture, and implementation approach.

**Focus:**
- Technical approach is sound
- API contracts are well-defined
- Database schema changes are clear
- Performance requirements are realistic
- Security considerations are addressed
- Technical dependencies identified

**Checklist:**

```
[ ] Endpoints & Contracts section has specs (method, params, response)
[ ] Database schema changes documented if applicable
[ ] Performance NFRs are achievable for scope
[ ] Security requirements defined (encryption, auth, PII)
[ ] Technical dependencies identified (APIs, libraries)
[ ] [Where] section in Tasks has file paths or module references
[ ] Caching strategy mentioned if needed
[ ] Scalability considered
```

---

## Persona 4: QA Specialist

**Role:** Validates testability, test coverage, and QA readiness.

**Focus:**
- Acceptance criteria are testable
- Edge cases are comprehensive
- Error handling scenarios are clear
- Test data requirements identified
- QA validation steps defined

**Checklist:**

```
[ ] Acceptance criteria are pass/fail, not subjective
[ ] Each AC can be verified by QA (specific steps)
[ ] Error handling table has "Expected Behaviour"
[ ] Edge cases include boundary conditions (0, 1, max)
[ ] Use cases have clear reproduction steps
[ ] Test data requirements specified
[ ] Regression risks identified
[ ] Accessibility testing mentioned
```

---

## Persona 5: Product Manager

**Role:** Validates strategic alignment, prioritization, and roadmap fit.

**Focus:**
- Initiative aligns with product strategy
- T-shirt sizing is appropriate
- Priorities are correct
- Dependencies don't block roadmap
- Scope is realistic for timeline

**Checklist:**

```
[ ] T-shirt size documented (XS/S/M/L/XL)
[ ] T-shirt size rationale clear
[ ] Timeline estimate realistic
[ ] Priorities assigned to all issues
[ ] Top-priority items are true blockers
[ ] Dependencies identified and documented
[ ] Blockers have clear resolution plan
[ ] Initiative aligns with product vision
```

---

## Persona 6: UX Researcher

**Role:** Validates user experience, usability, and design quality.

**Focus:**
- User flows are intuitive
- Designs are linked
- Accessibility requirements are clear
- User testing is planned
- Localization is considered

**Checklist:**

```
[ ] Design links present (or "Design TBD" marked)
[ ] User flows documented in Use Cases
[ ] Accessibility requirements specific (labels, contrast)
[ ] Touch targets meet minimum size
[ ] User testing plan mentioned (or A/B test via flag)
[ ] Localization supported
[ ] RTL layout considered where applicable
[ ] Platform-specific design guidelines followed
```

---

## Persona 7: Compliance Officer

**Role:** Validates legal, regulatory, and compliance requirements.

**Focus:**
- Privacy / GDPR compliance
- Audit trail requirements
- PII handling
- Legal disclaimers
- User consent

**Checklist:**

```
[ ] PII not logged in plaintext
[ ] Data encryption in transit and at rest
[ ] User consent requirements documented
[ ] Data retention policy mentioned
[ ] Rights supported (data export, deletion)
[ ] Audit trail for sensitive actions
[ ] Legal disclaimers displayed where needed
[ ] Compliance requirements identified
```

---

## Persona 8: DevOps Engineer

**Role:** Validates deployment, monitoring, and operational readiness.

**Focus:**
- Feature flags for gradual rollout
- Monitoring and alerting
- Error logging
- Rollback plan
- Performance monitoring
- Release strategy

**Checklist:**

```
[ ] Feature flags defined with default values
[ ] Rollout strategy documented (gradual %)
[ ] Analytics events for monitoring
[ ] Error logging requirements specified
[ ] Performance monitoring (latency, throughput)
[ ] Rollback plan documented
[ ] Release strategy (platforms first, simultaneous)
[ ] Backward compatibility considered
```

---

## Aggregated Output

After all personas complete, aggregate:

```markdown
## AI Personas Review Summary

Overall Quality Gate: [PASS / REVIEW / FAIL]

Persona Results:
- Business Analyst: [PASS / REVIEW / FAIL] - [N] critical, [N] warnings
- Requirements Engineer: [PASS / REVIEW / FAIL] - [N] critical, [N] warnings
- Technical Architect: [PASS / REVIEW / FAIL] - [N] critical, [N] warnings
- QA Specialist: [PASS / REVIEW / FAIL] - [N] critical, [N] warnings
- Product Manager: [PASS / REVIEW / FAIL] - [N] critical, [N] warnings
- UX Researcher: [PASS / REVIEW / FAIL] - [N] critical, [N] warnings
- Compliance Officer: [PASS / REVIEW / FAIL] - [N] critical, [N] warnings
- DevOps Engineer: [PASS / REVIEW / FAIL] - [N] critical, [N] warnings

Critical Issues (MUST fix before Jira creation):
[Aggregate from all personas]

Warnings (review recommended):
[Aggregate from all personas]

Strengths:
[Aggregate from all personas]

Decision:
- If ANY persona reports FAIL -> Quality Gate: FAIL
- If 3+ personas report REVIEW -> Quality Gate: REVIEW
- Else -> Quality Gate: PASS
```

---

## Integration

Run this review after the automated INVEST + auto-review checks in Phase 4. The result feeds into the final GO / NO-GO decision emitted by `quality-reviewer`.
