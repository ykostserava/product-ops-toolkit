---
name: Full Story Template
description: Comprehensive 15-section story template with As-Is/To-Be, error handling, NFRs, analytics
type: template
---

# Full Story Template

Comprehensive story structure for features that need thorough specification -- cross-platform work, customer-facing changes, payment/financial features, or anything where missing an edge case is expensive.

For lighter stories, use `user-story-template.md` instead.

---

## Title Format

Use the platform prefix convention from `config.yml`:

`[Platform] Feature action`

Examples:
- `[Android] User creates savings goal`
- `[iOS] Transaction history filtering`
- `[Web] Account switching dropdown`
- `[BE] Savings interest calculation API`

---

## Story Description

**As a** [customer / end user / role]
**I want to** [perform an action]
**So that** [I achieve a goal or benefit]

---

## As-Is vs To-Be

| As-Is (Current State) | To-Be (Future State) | Value / Rationale |
|---|---|---|
| Describe current behaviour or gap | Describe the desired behaviour | Why are we doing this? What problem does it solve? |

---

## Acceptance Criteria

What conditions must be met for this story to be accepted?

- [ ] Criterion 1 (Given-When-Then)
- [ ] Criterion 2 (Given-When-Then)
- [ ] Criterion 3 (Given-When-Then)

---

## Use Cases

Describe the specific scenarios in which this feature is used.

| # | Actor | Action | Expected Outcome |
|---|---|---|---|
| 1 | [persona] | [action] | [outcome] |
| 2 | [persona] | [action] | [outcome] |
| 3 | [persona] | [action] | [outcome] |

---

## Error Handling

What errors can occur and how should the system respond?

| Error Scenario | Expected Behaviour | Error Message (if applicable) |
|---|---|---|
| Network timeout | Show retry button | "Connection failed. Please try again." |
| Invalid input | Highlight field, show inline error | "[specific message]" |
| Server 500 | Show generic error, log to monitoring | "Something went wrong. Please try again later." |

---

## Edge Cases

Scenarios outside the happy path that must be handled.

**Offline behaviour:**
- Show cached data if available
- Disable actions that require network
- Display offline indicator

**Poor connectivity:**
- Show loading state for >2 seconds
- Implement retry logic with exponential backoff
- Allow user to cancel long-running requests

**Other edge cases:**
- Empty state: [specific to this feature]
- Max limit reached: [specific to this feature]
- Zero / null values: [specific to this feature]

---

## User Segment Applicability

Customize segments per your product. Example segments (replace with yours):

| User Segment | Applicable? | Notes |
|---|---|---|
| Segment A | Yes / No | [notes] |
| Segment B | Yes / No | [notes] |
| Segment C | Yes / No | [notes] |

---

## Feature Flags & Remote Config

Are any feature flags or remote config parameters required?

| Flag / Config Key | Default Value | Purpose |
|---|---|---|
| `enable_feature_x` | `false` | Enable new feature behind flag |
| `config_param_y` | `N` | Configurable limit or threshold |

---

## Non-Functional Requirements

Performance, reliability, security, accessibility expectations.

| Category | Requirement | Example |
|---|---|---|
| Performance | Screen loads within Xs | Initial render <2s, API calls <500ms |
| Security | Data encrypted in transit | HTTPS, TLS 1.3 |
| Reliability | Handles N concurrent users | No degradation under normal load |
| Accessibility | [standard] compliant | Screen reader support, contrast ratios |

---

## Localisation & Supported Languages

Which languages must be supported? (Customize per your product markets.)

| Language | Supported? | Notes |
|---|---|---|
| English | Yes | Default language |
| [Market language] | Yes / No | [notes] |

---

## Endpoints & Contracts (Backend Dependencies)

List backend endpoints and any dependencies.

| Endpoint | Method | Description | Owner / Team |
|---|---|---|---|
| `/api/v1/resource` | POST | [description] | Backend Team |
| `/api/v1/resource/{id}` | GET | [description] | Backend Team |

**API Contract (example):**

```json
POST /api/v1/resource
Request:
{
  "field1": "value",
  "field2": 123
}

Response (201):
{
  "id": "resource_abc",
  "field1": "value",
  "field2": 123,
  "status": "created"
}
```

---

## Analytics / Tracking Events

| Event Name | Trigger | Parameters | Notes |
|---|---|---|---|
| `feature_action_completed` | User completes action | `[relevant properties]` | Conversion tracking |
| `feature_error_shown` | Error appears | `error_code`, `screen` | Quality tracking |

---

## Design Links

**Design tool links:**
- Design file: [Link]
- Prototype: [Link]
- Notes: Any clarifications or edge cases not covered in designs

---

## Attachments & Supporting Material

- Architecture diagram (if complex integration)
- Sequence diagram (for multi-step flows)
- Database schema changes (if applicable)
- Third-party integration docs (if using external APIs)
- Competitor references (for inspiration)

---

## Metadata

**Platform:** [from config.yml platforms]
**Component:** [from config.yml or Jira components]
**Priority:** [from config.yml priority_scheme]
**Estimate:** [to be set by team]
**Labels:** [tags relevant to team workflow]
