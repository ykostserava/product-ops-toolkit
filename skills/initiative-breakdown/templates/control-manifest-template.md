# Control Manifest: {INITIATIVE_KEY} - {INITIATIVE_NAME}

**Generated:** {DATE}
**T-Shirt Size:** {SIZE}
**Status:** {STATUS}

---

## Executive Summary

**Initiative:** {INITIATIVE_KEY}
**Epics:** {EPIC_COUNT}
**Stories:** {STORY_COUNT}
**Tasks:** {TASK_COUNT}
**Total Issues:** {TOTAL_COUNT}

**Timeline:** {ESTIMATED_TIMELINE}
**Quality Gate:** {PASSED / FAILED}

---

## Traceability Matrix

### Epic -> Initiative Mapping

| Epic Key | Epic Name | Parent Initiative | Link Type | Status |
|----------|-----------|-------------------|-----------|--------|
| {EPIC_KEY} | {EPIC_NAME} | {INITIATIVE_KEY} | Relates To | {status} |

### Story -> Epic Mapping

| Story Key | Story Summary | Parent Epic | Link Type | Platform | Component | Status |
|-----------|---------------|-------------|-----------|----------|-----------|--------|
| {STORY_KEY} | {SUMMARY} | {EPIC_KEY} | Epic Link | {platform} | {component} | {status} |

### Task -> Epic Mapping

| Task Key | Task Summary | Parent Epic | Link Type | Platform | Component | Status |
|----------|--------------|-------------|-----------|----------|-----------|--------|
| {TASK_KEY} | {SUMMARY} | {EPIC_KEY} | Epic Link | {platform} | {component} | {status} |

---

## Quality Metrics

### Template Compliance

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Stories with all sections | 100% | {%} | {status} |
| Tasks with all sections | 100% | {%} | {status} |
| Platform prefixes | 100% | {%} | {status} |
| Components assigned | 100% | {%} | {status} |
| Priorities assigned | 100% | {%} | {status} |
| Story points empty | 100% | {%} | {status} |

### INVEST Compliance

| Story Key | Independent | Negotiable | Valuable | Estimable | Small | Testable | Overall |
|-----------|-------------|------------|----------|-----------|-------|----------|---------|
| {KEY} | pass / fail | pass / fail | pass / fail | pass / fail | pass / fail | pass / fail | PASS / FAIL |

**INVEST Summary:**
- Passed: {N} stories ({%})
- Issues: {N} stories ({%})
- Failed: {N} stories ({%})

### Confidence Scores

| Issue Key | Type | Confidence | Missing Sections | Status |
|-----------|------|------------|------------------|--------|
| {KEY} | Story / Task | {%} | {list} | {status} |

**Confidence Summary:**
- 90-100% (Ready): {N} ({%})
- 70-89% (Review): {N} ({%})
- <70% (Incomplete): {N} ({%})

**Average Confidence:** {%}

---

## AI Personas Review

### Overall Quality Gate

**Status:** {PASS / REVIEW / FAIL}

| Persona | Result | Critical | Warnings | Notes |
|---------|--------|----------|----------|-------|
| Business Analyst | {status} | {N} | {N} | {summary} |
| Requirements Engineer | {status} | {N} | {N} | {summary} |
| Technical Architect | {status} | {N} | {N} | {summary} |
| QA Specialist | {status} | {N} | {N} | {summary} |
| Product Manager | {status} | {N} | {N} | {summary} |
| UX Researcher | {status} | {N} | {N} | {summary} |
| Compliance Officer | {status} | {N} | {N} | {summary} |
| DevOps Engineer | {status} | {N} | {N} | {summary} |

**Summary:**
- Passed: {N}/8 personas
- Review: {N}/8 personas
- Failed: {N}/8 personas

### Critical Issues

{LIST_CRITICAL_ISSUES}

### Warnings

{LIST_WARNINGS}

### Strengths

{LIST_STRENGTHS}

### Recommendations

{LIST_RECOMMENDATIONS}

---

## Platform Coverage

### Distribution

| Platform | Stories | Tasks | Total | % |
|----------|---------|-------|-------|---|
| {platform1} | {N} | {N} | {N} | {%} |
| {platform2} | {N} | {N} | {N} | {%} |
| Backend | {N} | {N} | {N} | {%} |

### Feature Parity

| Feature (Epic) | {platform1} | {platform2} | Web | Backend | Status |
|----------------|-------------|-------------|-----|---------|--------|
| {EPIC_NAME} | yes/no | yes/no | yes/no | yes/no | Complete / Missing |

---

## Risk Assessment

### High-Risk Areas

| Risk ID | Category | Description | Impact | Likelihood | Mitigation | Owner |
|---------|----------|-------------|--------|------------|------------|-------|
| R-001 | Dependency | External API integration | High | Medium | Early POC | Backend Team |
| R-002 | Technical | Complex algorithm | High | Low | Spike story | Mobile Team |

### Dependencies

| ID | Type | Description | Dependent Issues | Status | Due Date |
|----|------|-------------|------------------|--------|----------|
| D-001 | External | Design approval | {keys} | Pending | {date} |
| D-002 | Internal | Backend API | {keys} | In Progress | {date} |

### Blockers

| ID | Description | Blocking Issues | Resolution Plan | ETA |
|----|-------------|-----------------|-----------------|-----|
| B-001 | {blocker} | {keys} | {plan} | {date} |

---

## Compliance Checks

### Mandatory Sections (adjust per story-template.md)

| Section | Required | Actual | Status |
|---------|----------|--------|--------|
| User Story | {N/M} | {%} | {status} |
| As-Is vs To-Be | {N/M} | {%} | {status} |
| Acceptance Criteria | {N/M} | {%} | {status} |
| Use Cases | {N/M} | {%} | {status} |
| Error Handling | {N/M} | {%} | {status} |
| Edge Cases | {N/M} | {%} | {status} |
| Feature Flags | {N/M} | {%} | {status} |
| NFRs | {N/M} | {%} | {status} |
| Endpoints & Contracts | {N/M} | {%} | {status} |
| Analytics Events | {N/M} | {%} | {status} |
| Design Links | {N/M} | {%} | {status} |

### Mandatory Sections (Tasks)

| Section | Required | Actual | Status |
|---------|----------|--------|--------|
| [Why] Context | {N/M} | {%} | {status} |
| [What] Scope | {N/M} | {%} | {status} |
| [Where] Implementation | {N/M} | {%} | {status} |
| [Acceptance Criteria] | {N/M} | {%} | {status} |

---

## Issues & Recommendations

### Critical Issues

{LIST_OF_CRITICAL_ISSUES}

### Warnings

{LIST_OF_WARNINGS}

### Recommendations

1. Fix critical issues before Jira creation
2. Review warnings and address before development starts
3. Process improvements for future breakdowns

---

## Approval & Sign-off

### Quality Gate Criteria

- [ ] All epics have Relates To link to Initiative
- [ ] All stories / tasks have Epic Link (or Relates To for XS)
- [ ] Platform prefixes on all summaries (100%)
- [ ] Template compliance >=90% for all stories
- [ ] Confidence score >=90% for all stories
- [ ] INVEST validation passed for all stories
- [ ] No critical blockers unresolved

### Readiness for Jira Creation

- [ ] Safe to proceed with `--create-in-jira`
- [ ] Review warnings before creating
- [ ] Fix critical issues before creating

### Sign-off

**Product Owner:** {NAME}
**Date:** {DATE}
**Status:** {APPROVED / PENDING FIXES}

**Notes:** {NOTES}

---

## Appendix

### Legend

- pass / Passed / Complete
- review / Warning / Review needed
- fail / Failed / Incomplete

### Confidence Thresholds

- 90-100%: Ready to create
- 70-89%: Review needed
- <70%: Incomplete

### INVEST Criteria

- **I**ndependent
- **N**egotiable
- **V**aluable
- **E**stimable
- **S**mall
- **T**estable

---

**Generated by:** /initiative-breakdown skill
**Last Updated:** {TIMESTAMP}
