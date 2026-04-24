---
name: User Story Template
description: Minimal user story format - title, user story, AC, DoD, dependencies
type: template
---

# User Story Template

## Title: [Feature Name] ([Platform/Component])

**Epic:** [Epic Name]
**Priority:** [from config.yml priority_scheme]
**Estimate:** [Story Points or T-shirt size - to be estimated by team]

---

## User Story

**As a** [type of user]
**I want** [an action/feature]
**So that** [benefit/value]

---

## Acceptance Criteria

Use **Given-When-Then** format:

**Given** [initial context / state]
**When** [action / event occurs]
**Then** [expected outcome]

**And** [additional outcome if needed]

### Example

```
Given user is logged in
When user taps on account name at top of screen
Then dropdown menu appears showing all accounts
And user can select any account from the list
And selected account becomes active immediately
```

---

## Technical Details

**Implementation Notes:**
- [Key technical considerations]
- [API endpoints to use / create]
- [Third-party integrations]
- [Performance requirements]

**Platform-Specific (customize per platforms in config.yml):**
- Platform A: [notes]
- Platform B: [notes]
- Backend: [changes needed]

---

## Definition of Done

**Code:**
- [ ] Implementation complete
- [ ] Unit tests written (team's coverage target)
- [ ] Code reviewed
- [ ] Static analysis clean
- [ ] Merged to main branch

**Testing:**
- [ ] QA tested on all target platforms
- [ ] Edge cases tested (offline, errors, etc.)
- [ ] Performance acceptable (no regressions)
- [ ] Analytics events verified (if applicable)

**Deployment:**
- [ ] Deployed to staging environment
- [ ] Smoke tests passed
- [ ] Deployed to production (or beta)
- [ ] Rollout monitoring (no critical errors)

**Documentation:**
- [ ] API documentation updated (if applicable)
- [ ] README updated (if needed)
- [ ] Release notes written

---

## Dependencies

**Blocked by:**
- [Other stories that must complete first]
- [External dependencies - Legal, Design, etc.]

**Blocks:**
- [Stories that depend on this one]

---

## Design / Mockups

**Design links:**
- [Link to designs if applicable]

**Screenshots:**
- [Attach screenshots or describe UI changes]

---

## Test Scenarios

### Happy Path

1. [Step 1]
2. [Step 2]
3. [Expected result]

### Edge Cases

1. **Offline mode:** [what happens?]
2. **Error handling:** [what if API fails?]
3. **Empty state:** [what if no data?]
4. **Loading state:** [what does user see?]

---

## Analytics Events (if applicable)

**Events to track:**
- `event_name` - When: [trigger], Properties: [list]
- `another_event` - When: [trigger], Properties: [list]

---

## Notes

- [Any additional context]
- [Links to related tickets]
- [Decisions made during planning]
- [Known limitations or future work]

---

## Checklist before handoff to team

- [ ] User story is clear and testable
- [ ] Acceptance criteria use Given-When-Then format
- [ ] Definition of Done is complete
- [ ] Dependencies identified
- [ ] Priority assigned
- [ ] Epic linked
- [ ] Technical details reviewed with team
- [ ] Designs attached (if UI changes)
- [ ] Story is small enough (1-2 devs, 2-5 days max)
