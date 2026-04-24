---
name: Task Template
description: Technical task template (backend, infrastructure, tech work) - Why / What / Where / AC structure
type: template
---

# Task Template

For technical work items that don't have direct end-user value but enable user-facing features (backend endpoints, migrations, infrastructure, integrations, tech tasks).

For user-facing work, use `story-template.md` or `user-story-template.md`.

---

## Title Format

`[Platform] Task name`

Examples:
- `[BE] Implement resource creation API endpoint`
- `[BE] Database migration for resources table`
- `[iOS] Add analytics SDK integration`
- `[Web] Configure analytics provider for events`

---

## [Why] Context & Impact

Give context to understand the impact on the user or our product.

**Business Context:**
- What problem are we solving?
- Who is affected?
- What's the impact if we don't do this?
- What does this task unlock (which user-facing stories)?

---

## [What] What Should Be Done

Specific, actionable description.

**Scope:**
- What exactly needs to be implemented or changed?
- What's included?
- What's explicitly excluded?

---

## [Where] Implementation Guidance

Files or links to guide implementation.

**Files to modify:**
- `path/to/file1`
- `path/to/file2`

**References:**
- API spec: [link]
- Database schema: [link]
- Similar implementation: [where in codebase]
- Technical design doc: [link]

**Dependencies:**
- Requires [other task] to run first
- Depends on [existing service]

---

## [Acceptance Criteria] Conditions for Acceptance

### Functional Criteria

- [ ] [Specific behaviour that must work]
- [ ] [Response shape / structure]
- [ ] [Validation / error cases]
- [ ] [Authorization checks]

### Non-Functional Criteria

- [ ] Response time target (e.g. <300ms P95)
- [ ] Idempotency handling (where relevant)
- [ ] Input validation (injection-safe)
- [ ] Errors logged to monitoring with context
- [ ] Analytics event fires on success (if applicable)

### Testing Criteria

- [ ] Unit tests written (team coverage target)
- [ ] Integration tests for happy path + error cases
- [ ] API collection updated with examples
- [ ] API documentation updated

### QA Validation

**How QA can verify:**
1. [Step to reproduce expected behaviour]
2. [How to verify in database / logs / API response]
3. [Error cases to test]

**Test Data:**
```
Valid request example:
{ ... }

Invalid request example:
{ ... }
```

---

## Technical Details (optional -- fill for complex tasks)

**API Endpoint (example):**
```
POST /api/v1/resource
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "field1": "string (required, 1-100 chars)",
  "field2": "number (required, >0)"
}
```

**Response (201 Created):**
```json
{
  "id": "resource_abc",
  "field1": "value",
  "status": "created",
  "created_at": "2026-04-13T10:00:00Z"
}
```

**Error Responses:**
- 400 Bad Request - Validation failed
- 401 Unauthorized - Invalid token
- 409 Conflict - Duplicate
- 429 Too Many Requests - Rate limit
- 500 Internal Server Error

---

## Database Changes (if applicable)

Include migration SQL or link to migration file.

---

## Security Considerations

- [ ] Input validation and sanitization
- [ ] Authorization checks (user owns resource)
- [ ] Rate limiting
- [ ] Audit logging
- [ ] Encryption at rest (where applicable)

---

## Performance Considerations

- [ ] Database query optimization
- [ ] Response caching (where applicable)
- [ ] Load testing

---

## Monitoring & Alerts

**Metrics to track:**
- Request count per endpoint
- Response time (P50, P95, P99)
- Error rate (4xx, 5xx)

**Alerts:**
- P95 latency above threshold -> team alerting channel
- Error rate above threshold -> on-call alert

---

## Rollout Plan (for risky changes)

**Phase 1: Dev / Staging**
- Deploy to non-prod environment
- Run integration tests
- QA validation

**Phase 2: Production (Beta)**
- Deploy behind feature flag
- Enable for X% of users
- Monitor metrics for Y hours

**Phase 3: Full Rollout**
- If no issues, enable for 100%
- Monitor for N days

**Rollback Plan:**
- Disable feature flag
- Revert migration (if needed)

---

## Metadata

**Platform:** [from config.yml platforms]
**Component:** [from config.yml or Jira components]
**Priority:** [from config.yml priority_scheme]
**Estimate:** [to be set by team]
**Labels:** [tags relevant to team workflow]
**Blocked By:** [list of blocking tasks]
**Blocks:** [list of stories this unblocks]
