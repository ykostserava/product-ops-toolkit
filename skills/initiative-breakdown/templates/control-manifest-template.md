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
**Quality Gate:** {PASSED/FAILED}

---

## Traceability Matrix

### Epic -> Initiative Mapping

| Epic Key | Epic Name | Parent Initiative | Link Type | Status |
|----------|-----------|-------------------|-----------|--------|
| {EPIC_KEY} | {EPIC_NAME} | {INITIATIVE_KEY} | Parent Link | pass |

### Story -> Epic Mapping

| Story Key | Story Summary | Parent Epic | Link Type | Platform | Component | Status |
|-----------|---------------|-------------|-----------|----------|-----------|--------|
| {STORY_KEY} | {STORY_SUMMARY} | {EPIC_KEY} | Epic Link | Android | {android_component} | pass |

### Task -> Epic Mapping

| Task Key | Task Summary | Parent Epic | Link Type | Platform | Component | Status |
|----------|--------------|-------------|-----------|----------|-----------|--------|
| {TASK_KEY} | {TASK_SUMMARY} | {EPIC_KEY} | Epic Link | Backend | {backend_component} | pass |

---

## Quality Metrics

### Template Compliance

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Stories with 15 sections | 100% | {PERCENTAGE}% | {pass/warn/fail} |
| Tasks with 4 sections | 100% | {PERCENTAGE}% | {pass/warn/fail} |
| Platform prefixes | 100% | {PERCENTAGE}% | {pass/warn/fail} |
| Components assigned | 100% | {PERCENTAGE}% | {pass/warn/fail} |
| Priorities assigned | 100% | {PERCENTAGE}% | {pass/warn/fail} |
| Story points empty | 100% | {PERCENTAGE}% | {pass/warn/fail} |

### INVEST Compliance

| Story Key | Independent | Negotiable | Valuable | Estimable | Small | Testable | Overall |
|-----------|-------------|------------|----------|-----------|-------|----------|---------|
| {STORY_KEY} | pass | pass | pass | pass | pass | pass | PASS |

**INVEST Summary:**
- Passed: {COUNT} stories ({PERCENTAGE}%)
- Issues: {COUNT} stories ({PERCENTAGE}%)
- Failed: {COUNT} stories ({PERCENTAGE}%)

### Confidence Scores

| Issue Key | Type | Confidence | Missing Sections | Status |
|-----------|------|------------|------------------|--------|
| {ISSUE_KEY} | Story | {PERCENTAGE}% | {LIST} | {pass/warn/fail} |

**Confidence Summary:**
- 90-100% (Ready): {COUNT} ({PERCENTAGE}%)
- 70-89% (Review): {COUNT} ({PERCENTAGE}%)
- <70% (Incomplete): {COUNT} ({PERCENTAGE}%)

**Average Confidence:** {AVERAGE}%

---

## AI Personas Review Results

### Overall Quality Gate

**Status:** {PASS / REVIEW / FAIL}

**Persona Results:**

| Persona | Result | Issues | Notes |
|---------|--------|--------|-------|
| Business Analyst | {pass/warn/fail} | {COUNT} critical, {COUNT} warnings | {SUMMARY} |
| Requirements Engineer | {pass/warn/fail} | {COUNT} critical, {COUNT} warnings | {SUMMARY} |
| Technical Architect | {pass/warn/fail} | {COUNT} critical, {COUNT} warnings | {SUMMARY} |
| QA Specialist | {pass/warn/fail} | {COUNT} critical, {COUNT} warnings | {SUMMARY} |
| Product Manager | {pass/warn/fail} | {COUNT} critical, {COUNT} warnings | {SUMMARY} |
| UX Researcher | {pass/warn/fail} | {COUNT} critical, {COUNT} warnings | {SUMMARY} |
| Compliance Officer | {pass/warn/fail} | {COUNT} critical, {COUNT} warnings | {SUMMARY} |
| DevOps Engineer | {pass/warn/fail} | {COUNT} critical, {COUNT} warnings | {SUMMARY} |

**Summary:**
- Passed: {COUNT}/8 personas
- Review: {COUNT}/8 personas
- Failed: {COUNT}/8 personas

---

### Critical Issues from AI Personas

{LIST_CRITICAL_ISSUES_FROM_ALL_PERSONAS}

**Example:**
1. **Product Manager:** Priorities not assigned (all "Unspecified")
   - **Fix:** Assign PROJ-7 -> P0, PROJ-3/PROJ-4/PROJ-6 -> P1
   - **Effort:** 5 minutes

2. **Compliance Officer:** Missing GDPR consent for analytics tracking
   - **Fix:** Add consent requirement to analytics task acceptance criteria
   - **Effort:** 15 minutes

3. **Requirements Engineer:** NFRs not quantified (PROJ-125: "fast" instead of "<2s")
   - **Fix:** Replace vague terms with specific metrics
   - **Effort:** 10 minutes

---

### Warnings from AI Personas

{LIST_WARNINGS_FROM_ALL_PERSONAS}

**Example:**
4. **UX Researcher:** Design not finalized (4 variants exist)
   - **Recommendation:** Complete PROJ-7 design review before starting implementation
   - **Impact:** Medium (blocks PROJ-3, PROJ-4)

5. **DevOps Engineer:** Rollout strategy not documented
   - **Recommendation:** Add gradual rollout plan (10% -> 50% -> 100%)
   - **Impact:** Low (can define during deployment)

6. **Technical Architect:** API response format example missing
   - **Recommendation:** Add example payload to "Endpoints & Contracts"
   - **Impact:** Low (nice-to-have for dev clarity)

---

### Strengths Identified by AI Personas

{LIST_STRENGTHS}

**Example:**
- **Business Analyst:** Clear business value articulated (reduces clicks by 50%)
- **Requirements Engineer:** Template compliance 100% (all 15 sections complete)
- **QA Specialist:** Comprehensive error handling (network, API, validation)
- **Technical Architect:** Uses existing API (low technical risk)
- **Product Manager:** T-shirt sizing appropriate (XS for 4 stories, 2 platforms)

---

### Recommendations from AI Personas

{LIST_RECOMMENDATIONS}

**Example:**
1. **Business Analyst:** Add quantitative success metrics ("4.5 -> 4.7 app rating" instead of just "improves ratings")
2. **UX Researcher:** Consider selection animation (instant vs fade transition)
3. **DevOps Engineer:** Add monitoring dashboard for account_selected conversion rate
4. **QA Specialist:** Add test data requirements ("Test with 0, 1, 5, 50, 100+ accounts")

---

## Platform Coverage

### Distribution by Platform

| Platform | Stories | Tasks | Total | Percentage |
|----------|---------|-------|-------|------------|
| Android | {COUNT} | {COUNT} | {COUNT} | {PERCENTAGE}% |
| iOS | {COUNT} | {COUNT} | {COUNT} | {PERCENTAGE}% |
| Web | {COUNT} | {COUNT} | {COUNT} | {PERCENTAGE}% |
| Backend | {COUNT} | {COUNT} | {COUNT} | {PERCENTAGE}% |

### Feature Parity Check

| Feature (Epic) | Android | iOS | Web | Backend | Status |
|----------------|---------|-----|-----|---------|--------|
| {EPIC_NAME} | yes | yes | yes | yes | Complete |
| {EPIC_NAME} | yes | yes | no | yes | Missing Web |

---

## Risk Assessment

### High-Risk Areas

| Risk ID | Category | Description | Impact | Likelihood | Mitigation | Owner |
|---------|----------|-------------|--------|------------|------------|-------|
| R-001 | Dependency | External API integration | High | Medium | Early POC | Backend Team |
| R-002 | Technical | Complex algorithm | High | Low | Spike story | Mobile Team |

### Dependencies

| Dependency ID | Type | Description | Dependent Issues | Status | Due Date |
|---------------|------|-------------|------------------|--------|----------|
| D-001 | External | Design approval | PROJ-100, PROJ-101 | Pending | {date} |
| D-002 | Internal | Backend API | PROJ-105, PROJ-106 | In Progress | {date} |

### Blockers

| Blocker ID | Description | Blocking Issues | Resolution Plan | ETA |
|------------|-------------|-----------------|-----------------|-----|
| B-001 | Design review pending | PROJ-100, PROJ-101, PROJ-102 | Schedule review with design stakeholder | {date} |

---

## Compliance Checks

### Mandatory Sections (Stories, adjust per story-template.md)

| Section | Required | Actual | Status |
|---------|----------|--------|--------|
| User Story | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| As-Is vs To-Be | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Acceptance Criteria | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Use Cases | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Error Handling | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Edge Cases | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| User Tier Applicability | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Client Type Applicability | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Feature Flags | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Non-Functional Requirements | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Localisation | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Endpoints & Contracts | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Analytics Events | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Design Links | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| Attachments | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |

### Mandatory Sections (Tasks)

| Section | Required | Actual | Status |
|---------|----------|--------|--------|
| [Why] Context | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| [What] Scope | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| [Where] Implementation | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |
| [Acceptance Criteria] | {COUNT}/{TOTAL} | {PERCENTAGE}% | {pass/fail} |

---

## Issues & Recommendations

### Critical Issues

{LIST_OF_CRITICAL_ISSUES}

**Example:**
- PROJ-123: Missing platform prefix in summary
- PROJ-125: Confidence score 65% (below 90% threshold)
- PROJ-128: INVEST validation failed (Not Small)

### Warnings

{LIST_OF_WARNINGS}

**Example:**
- PROJ-130: Missing design link (87% confidence)
- PROJ-132: No analytics events defined
- PROJ-135: Edge cases section sparse

### Recommendations

1. **Fix critical issues before Jira creation:**
   - Add platform prefixes to PROJ-123
   - Complete missing sections in PROJ-125 (User Tier Applicability, Analytics Events)
   - Split PROJ-128 into smaller stories

2. **Review warnings:**
   - Add design links or mark "Design TBD"
   - Define analytics events or mark "No tracking needed"

3. **Process improvements:**
   - {PROCESS_IMPROVEMENT_1}
   - {PROCESS_IMPROVEMENT_2}

---

## Approval & Sign-off

### Quality Gate

**Status:** {PASSED / FAILED}

**Criteria:**
- [ ] All epics have Parent Link to Initiative
- [ ] All stories/tasks have Epic Link (or Parent Link for XS)
- [ ] Platform prefixes on all summaries (100%)
- [ ] Template compliance >=90% for all stories
- [ ] Confidence score >=90% for all stories
- [ ] INVEST validation passed for all stories
- [ ] No critical blockers unresolved

### Readiness for Jira Creation

- [ ] Safe to proceed with --create-in-jira
- [ ] Review warnings before creating
- [ ] Fix critical issues before creating

### Sign-off

**Product Owner:** {NAME}
**Date:** {DATE}
**Status:** {APPROVED / PENDING FIXES}

**Notes:**
{NOTES}

---

## Appendix

### Legend

**Status Values:**
- pass - Passed / Complete
- warn - Warning / Review needed
- fail - Failed / Incomplete

**Confidence Thresholds:**
- 90-100%: Ready to create
- 70-89%: Review needed
- <70%: Incomplete

**INVEST Criteria:**
- **I**ndependent: Can be developed independently
- **N**egotiable: Flexible implementation approach
- **V**aluable: Delivers user value
- **E**stimable: Clear enough to estimate
- **S**mall: Can be completed in one iteration
- **T**estable: Has clear acceptance criteria

---

**Generated by:** /initiative-breakdown skill
**Skill Version:** 1.2.0
**Last Updated:** {TIMESTAMP}
