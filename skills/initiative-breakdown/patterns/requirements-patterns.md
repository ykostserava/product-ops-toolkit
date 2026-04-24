# Requirements Patterns

> Reusable patterns and common requirements that the breakdown skill can auto-apply when sections are missing.

Customize this file for your product domain -- these are generic patterns that cover common fintech / consumer app needs. Add or remove patterns based on what your product deals with.

---

## Common User Story Patterns

### Pattern: Account Management

```
As a user
I want to [view / select / switch / add / close] my account
So that I can manage my resources across multiple accounts
```

### Pattern: Transaction / Record Handling

```
As a user
I want to [view / filter / search / export] my transactions
So that I can track and manage them effectively
```

### Pattern: Payments & Transfers

```
As a user
I want to [send / receive / request] [resource]
So that I can complete transactions conveniently
```

### Pattern: Goal / Target Management

```
As a user
I want to [create / track / manage] [goals / targets]
So that I can make progress toward objectives
```

### Pattern: Security & Authentication

```
As a user
I want to [authenticate / verify / secure] my account
So that my data remains secure
```

---

## Common Acceptance Criteria

### UI / UX Criteria

**Screen loading:**
- [ ] Screen loads within 2 seconds on typical network
- [ ] Loading indicator displayed while fetching
- [ ] Cached data shown immediately, updated in background

**Form validation:**
- [ ] Required fields marked clearly
- [ ] Inline validation shows errors immediately
- [ ] Error messages are specific and actionable
- [ ] Submit button disabled until form is valid

**Navigation:**
- [ ] Back button returns to previous screen
- [ ] Navigation preserves scroll position
- [ ] Deep links work correctly

**Empty states:**
- [ ] Empty state shown when no data exists
- [ ] CTA button visible in empty state
- [ ] Helpful text explains next steps

### Data Criteria

**Display:**
- [ ] Currency formatted correctly per locale
- [ ] Dates formatted per locale
- [ ] Large numbers use thousand separators
- [ ] Negative amounts distinguished visually

**Persistence:**
- [ ] Changes saved immediately (no manual save where possible)
- [ ] Optimistic UI updates shown before confirmation
- [ ] Data synced across devices
- [ ] Conflict resolution handles concurrent edits

### Security Criteria

**Authentication:**
- [ ] Session expires after configurable inactivity period
- [ ] Biometric authentication available where supported
- [ ] Sensitive screens require re-authentication
- [ ] Session invalidated on logout

**Data protection:**
- [ ] Passwords never logged or stored in plaintext
- [ ] Sensitive data encrypted in transit (HTTPS / TLS)
- [ ] Sensitive data encrypted at rest
- [ ] PII redacted in error logs

### Accessibility Criteria

**Screen reader:**
- [ ] All elements have accessibility labels
- [ ] Images have alt text
- [ ] Forms announce errors to screen reader
- [ ] Focus order is logical

**Visual:**
- [ ] Text contrast meets WCAG 2.1 AA (4.5:1)
- [ ] Body font size minimum 16px
- [ ] Touch targets minimum 44x44pt
- [ ] Color is not the only indicator

---

## Common Error Scenarios

### Network Errors

| Scenario | Expected behaviour | Error message |
|----------|-------------------|---------------|
| No internet connection | Show offline indicator, cached data | "No internet connection. Showing cached data." |
| API timeout (>10s) | Show retry, preserve input | "Request timed out. Tap to retry." |
| Server error 500 | Show error state with retry | "Something went wrong. Please try again." |
| Bad gateway 502/503 | Show maintenance message | "Service temporarily unavailable." |

### Authentication Errors

| Scenario | Expected behaviour | Error message |
|----------|-------------------|---------------|
| Session expired | Redirect to login, preserve state | "Your session has expired. Please log in again." |
| Invalid credentials | Highlight field, inline error | "Incorrect email or password." |
| Account locked | Show support contact | "Account locked. Contact support." |
| 2FA invalid | Allow retry (limited), countdown | "Invalid code. N attempts remaining." |

### Validation Errors

| Scenario | Expected behaviour | Error message |
|----------|-------------------|---------------|
| Required empty | Highlight, error below | "This field is required." |
| Invalid format | Show error on blur | "Please enter a valid [format]." |
| Amount over limit | Disable submit, show limit | "Maximum: [amount]" |
| Amount below minimum | Inline error | "Minimum: [amount]" |

### Transaction / Action Errors

| Scenario | Expected behaviour | Error message |
|----------|-------------------|---------------|
| Insufficient resources | Prevent, show available | "Insufficient. Available: [amount]" |
| Daily limit exceeded | Prevent, show limit | "Daily limit exceeded. Limit: [amount]" |
| Target not found | Show error, allow retry | "Not found. Please check details." |
| Action declined | Show reason, offer alternatives | "Declined. [Reason]" |

---

## Common Edge Cases

**Offline:** user loses connection mid-flow.
- Show offline indicator
- Queue actions for later sync
- Allow viewing cached data
- Prevent actions that need network
- Auto-retry when connection restored

**Low connectivity:** user on slow connection.
- Show cached data immediately
- Update in background
- Compress payloads / assets
- Show "slow connection" indicator if >Ns

**Data boundaries:**
- **Empty:** 0 items -> empty state with CTA
- **Large:** 10k+ items -> paginate (load N at a time)
- **Long strings:** truncate with ellipsis, show full on tap
- **Large numbers:** format with abbreviation (1.2M)

**Concurrent actions:**
- User edits same data on 2 devices
- Last write wins (timestamp-based)
- Sync conflict notification
- Option to view both and choose

**System boundaries:**
- Very old device / browser -> graceful degradation
- App in background >Nh -> re-authenticate, refresh data

---

## Common Analytics Events

### Screen View

| Event | Trigger | Parameters |
|-------|---------|------------|
| `screen_viewed` | Navigation | `screen_name`, `previous_screen` |
| `dashboard_viewed` | App open | `session_count`, `state_summary` |

### User Actions

| Event | Trigger | Parameters |
|-------|---------|------------|
| `action_completed` | User completes action | `action_type`, `duration_ms`, `from_screen` |
| `action_failed` | Action fails | `action_type`, `error_code`, `error_message` |
| `filter_applied` | User applies filter | `filter_type`, `filter_value` |

### Engagement

| Event | Trigger | Parameters |
|-------|---------|------------|
| `feature_used` | User uses feature | `feature_name`, `duration_ms` |
| `settings_changed` | User changes setting | `setting_name`, `old_value`, `new_value` |

### Performance

| Event | Trigger | Parameters |
|-------|---------|------------|
| `api_call_duration` | API call completes | `endpoint`, `duration_ms`, `status_code` |
| `screen_load_time` | Screen finishes loading | `screen_name`, `load_time_ms`, `cache_hit` |

Customize event naming to match your team's convention (e.g. `screen_action_object` vs `snake_case_flat`).

---

## Common Non-Functional Requirements

### Performance

| Category | Requirement | Measurement |
|----------|-------------|-------------|
| API calls | <500ms (p95) | Monitoring / APM |
| Screen load | <2s on typical network | Performance monitoring |
| App launch | <3s cold start | Performance monitoring |
| Animation | 60 FPS | On-device profiler |

### Security

| Category | Requirement | Validation |
|----------|-------------|------------|
| Data encryption | In transit + at rest | Security audit |
| Authentication | Session timeout | Manual test |
| Secrets | Never in logs / source | Code review |
| PII protection | Redacted in logs | Log review |

### Reliability

| Category | Requirement | Measurement |
|----------|-------------|-------------|
| Uptime | 99.9% API uptime | Uptime monitor |
| Crash rate | <0.1% sessions | Crash reporter |
| Error handling | Graceful degradation | Manual test |
| Data integrity | No loss on crashes | QA validation |

### Accessibility

| Category | Requirement | Validation |
|----------|-------------|------------|
| Screen reader | Full support | Accessibility audit |
| Contrast | WCAG 2.1 AA | Contrast tool |
| Touch targets | Minimum 44x44pt | Design review |
| Font scaling | Up to 200% | Manual test |

---

## Common API Endpoint Patterns

### RESTful resource endpoints

```
GET    /api/v1/{resource}              # List
GET    /api/v1/{resource}/{id}         # Detail
POST   /api/v1/{resource}              # Create
PUT    /api/v1/{resource}/{id}         # Update
DELETE /api/v1/{resource}/{id}         # Delete
```

### Common query parameters

- `?page=1&limit=50` - pagination
- `?sort=field:desc` - sorting
- `?filter[field]=value` - filtering
- `?filter[field_min]=N&filter[field_max]=M` - range

### Response envelope (example)

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-04-14T10:30:00Z",
    "request_id": "abc123"
  }
}
```

### Error envelope (example)

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { ... }
  },
  "meta": { ... }
}
```

### Common headers

**Request:**
- `Authorization: Bearer {token}`
- `Content-Type: application/json`
- `X-Client-Version: 1.2.3`

**Response:**
- `X-Request-ID: abc123`
- `X-RateLimit-Remaining: 95`
- `Cache-Control: max-age=60`

---

## Common Feature Flags

### Pattern: Gradual rollout

```
enable_{feature_name}  = false  # default off
{feature}_{parameter}  = N      # A/B testing
```

### Pattern: Kill switch

```
enable_critical_flow = true  # can disable quickly
```

---

## How to Use This File

The `breakdown-generator` and `quality-reviewer` agents read this file to auto-fill missing sections in stories. When a section is empty:

- **Error Handling empty** -> pick relevant error scenarios from this file
- **Edge Cases empty** -> pick offline / low-connectivity / data-boundary patterns
- **NFRs empty** -> apply performance / security / reliability standards
- **Analytics empty** -> generate events based on screen / action type

**Context-aware pattern matching:**
- Story mentions "account" -> Account Management pattern
- Story mentions "transaction" -> Transaction pattern
- Story mentions "payment" -> Payments pattern

**Adapt, don't copy blindly:**
- Customize patterns to specific feature context
- Add feature-specific edge cases
- Include domain-specific validation rules
