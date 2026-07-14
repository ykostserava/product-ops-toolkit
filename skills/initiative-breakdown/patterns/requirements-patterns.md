# Requirements Patterns

> **Purpose:** Common patterns and reusable requirements the breakdown skill can auto-apply when sections are missing
> **Usage:** The `breakdown-generator` and `quality-reviewer` agents use these to auto-fill missing sections in stories

Customize this file for your product domain -- these are generic patterns that cover common fintech / consumer app needs. Add or remove patterns based on what your product deals with.

---

## Common User Story Patterns

### Pattern: Account Management
```
As a user
I want to [view/select/switch] my account
So that I can manage my finances across multiple accounts
```

**Common variations:**
- View account details
- Select active account
- Switch between accounts
- Add new account
- Close/deactivate account

### Pattern: Transaction Handling
```
As a user
I want to [view/filter/search/export] my transactions
So that I can track my spending effectively
```

**Common variations:**
- View transaction history
- Filter by date/amount/category
- Search transactions
- Export to CSV/PDF
- Categorize transactions

### Pattern: Payments & Transfers
```
As a user
I want to [send/receive/request] money
So that I can make payments conveniently
```

**Common variations:**
- Send money to contact
- Request payment
- Receive money (QR code)
- Schedule recurring payment
- Split bill with friends

### Pattern: Savings & Goals
```
As a user
I want to [create/track/manage] savings goals
So that I can save toward my financial objectives
```

**Common variations:**
- Create savings goal
- Track progress toward goal
- Deposit to savings
- Withdraw from savings
- Delete completed goal

### Pattern: Security & Authentication
```
As a user
I want to [authenticate/verify/secure] my account
So that my financial data remains secure
```

**Common variations:**
- Biometric login
- 2FA verification
- Session timeout
- Device authorization
- Security alerts

---

## Common Acceptance Criteria

### UI/UX Criteria

**Screen Loading:**
- [ ] Screen loads within 2 seconds on 4G connection
- [ ] Loading indicator displayed while fetching data
- [ ] Cached data shown immediately, updated in background

**Form Validation:**
- [ ] All required fields marked with asterisk (*)
- [ ] Inline validation shows errors immediately
- [ ] Error messages are specific and actionable
- [ ] Submit button disabled until form is valid

**Navigation:**
- [ ] Back button returns to previous screen
- [ ] Navigation preserves scroll position
- [ ] Deep links work correctly
- [ ] Tab bar highlights active section

**Empty States:**
- [ ] Empty state shown when no data exists
- [ ] CTA button visible in empty state
- [ ] Helpful text explains next steps

### Data Criteria

**Data Display:**
- [ ] Currency formatted correctly (EUR, USD, etc.)
- [ ] Dates formatted in user's locale (DD/MM/YYYY or MM/DD/YYYY)
- [ ] Large numbers use thousand separators (1,000.00)
- [ ] Negative amounts shown in red (optional: with minus sign)

**Data Persistence:**
- [ ] Changes saved immediately (no manual save)
- [ ] Optimistic UI updates shown before API confirmation
- [ ] Data synced across devices
- [ ] Conflict resolution handles concurrent edits

### Security Criteria

**Authentication:**
- [ ] Session expires after 15 minutes of inactivity
- [ ] Biometric authentication available (if device supports)
- [ ] Sensitive screens require re-authentication
- [ ] Session invalidated on logout

**Data Protection:**
- [ ] Passwords never logged or stored in plaintext
- [ ] Sensitive data encrypted in transit (HTTPS)
- [ ] Sensitive data encrypted at rest
- [ ] PII redacted in error logs

### Accessibility Criteria

**Screen Reader:**
- [ ] All elements have accessibility labels
- [ ] Images have alt text
- [ ] Forms announce errors to screen reader
- [ ] Focus order is logical

**Visual:**
- [ ] Text contrast meets WCAG 2.1 AA (4.5:1)
- [ ] Font size minimum 16px (body text)
- [ ] Touch targets minimum 44x44pt
- [ ] Color not the only indicator (use icons/text too)

---

## Common Error Scenarios

### Network Errors

| Error Scenario | Expected Behaviour | Error Message |
|----------------|-------------------|---------------|
| No internet connection | Show offline indicator, use cached data | "No internet connection. Showing cached data." |
| API timeout (>10s) | Show retry button, preserve user input | "Request timed out. Tap to retry." |
| Server error (500) | Show error state with retry option | "Something went wrong. Please try again." |
| Bad gateway (502/503) | Show maintenance message | "Service temporarily unavailable. Please try again later." |

### Authentication Errors

| Error Scenario | Expected Behaviour | Error Message |
|----------------|-------------------|---------------|
| Session expired | Redirect to login, preserve navigation state | "Your session has expired. Please log in again." |
| Invalid credentials | Highlight field, show error inline | "Incorrect email or password." |
| Account locked | Show contact support message | "Account locked. Contact support for assistance." |
| 2FA code invalid | Allow retry (3 attempts), show countdown | "Invalid verification code. 2 attempts remaining." |

### Validation Errors

| Error Scenario | Expected Behaviour | Error Message |
|----------------|-------------------|---------------|
| Required field empty | Highlight field, show error below | "This field is required." |
| Invalid email format | Show error on blur | "Please enter a valid email address." |
| Amount exceeds balance | Disable submit, show error | "Insufficient balance. Maximum: 1,234.56 EUR" |
| Amount below minimum | Show error inline | "Minimum amount: 0.01 EUR" |

### Transaction Errors

| Error Scenario | Expected Behaviour | Error Message |
|----------------|-------------------|---------------|
| Insufficient balance | Prevent transaction, show balance | "Insufficient balance. Available: 123.45 EUR" |
| Daily limit exceeded | Prevent transaction, show limit | "Daily limit exceeded. Limit: 5,000.00 EUR" |
| Recipient not found | Show error, allow retry | "Recipient not found. Please check the details." |
| Transaction declined | Show decline reason, offer alternatives | "Transaction declined. [Reason from bank]" |

---

## Common Edge Cases

### Offline Behaviour
- **Scenario:** User loses internet connection mid-flow
- **Expected:**
  - Show offline indicator at top of screen
  - Queue actions (like "favorite transaction") for later sync
  - Allow viewing cached data
  - Prevent actions that require network (like payments)
  - Auto-retry when connection restored

### Low Connectivity (2G/slow 3G)
- **Scenario:** User on slow connection
- **Expected:**
  - Show cached data immediately
  - Update in background when data arrives
  - Compress images/assets
  - Reduce API payload size
  - Show "slow connection" indicator if >5s

### Data Boundary Cases

**Empty Data:**
- 0 transactions -> Show empty state with CTA
- 0 accounts -> Show onboarding flow
- 0 contacts -> Suggest adding first contact

**Large Data:**
- 10,000+ transactions -> Paginate (load 50 at a time)
- Very long account name (>50 chars) -> Truncate with ellipsis
- Large transaction amount (>1M) -> Format with abbreviation (1.2M)

**Multi-Currency:**
- User has accounts in EUR, USD, GBP -> Show currency symbol
- Transaction in different currency than account -> Show exchange rate
- Mixed currency portfolio -> Show total in primary currency

### Concurrent Actions

**Scenario:** User edits data on 2 devices simultaneously
- **Expected:**
  - Last write wins (timestamp-based)
  - Sync conflict notification shown
  - Option to view both versions and choose

### System Boundaries

**Very old devices / OS versions:**
- Graceful degradation (disable advanced features)
- Show "update required" message if critical features unavailable

**App in background >1 hour:**
- Require biometric/PIN re-authentication
- Refresh data on foreground
- Resume user's navigation state

---

## Common Analytics Events

### Screen View Events

| Event Name | Trigger | Parameters | Notes |
|------------|---------|------------|-------|
| `screen_viewed` | User navigates to screen | `screen_name`, `previous_screen` | Track navigation flow |
| `dashboard_viewed` | User opens app | `account_count`, `has_pending_transactions` | Entry point tracking |
| `transaction_list_viewed` | User views transactions | `filter_applied`, `sort_by` | Feature usage |

### User Action Events

| Event Name | Trigger | Parameters | Notes |
|------------|---------|------------|-------|
| `account_selected` | User selects account | `account_id`, `account_type`, `from_screen` | Conversion tracking |
| `transaction_filtered` | User applies filter | `filter_type`, `date_range`, `amount_range` | Feature engagement |
| `payment_initiated` | User starts payment | `amount`, `currency`, `recipient_type` | Funnel start |
| `payment_completed` | Payment succeeds | `amount`, `currency`, `payment_method`, `duration_ms` | Conversion |
| `payment_failed` | Payment fails | `error_code`, `error_message`, `amount` | Error tracking |

### Feature Engagement Events

| Event Name | Trigger | Parameters | Notes |
|------------|---------|------------|-------|
| `savings_goal_created` | User creates goal | `goal_amount`, `target_date`, `category` | Feature adoption |
| `savings_goal_completed` | User reaches goal | `goal_id`, `days_to_complete`, `amount` | Success metric |
| `export_transaction_csv` | User exports data | `date_range`, `transaction_count` | Power user feature |
| `biometric_enabled` | User enables biometrics | `biometric_type` (face/fingerprint) | Security adoption |

### Performance Events

| Event Name | Trigger | Parameters | Notes |
|------------|---------|------------|-------|
| `api_call_duration` | API call completes | `endpoint`, `duration_ms`, `status_code` | Performance monitoring |
| `screen_load_time` | Screen finishes loading | `screen_name`, `load_time_ms`, `cache_hit` | UX metric |

Customize event naming to match your team's convention (e.g. `screen_action_object` vs flat snake_case).

---

## Common Non-Functional Requirements

### Performance

| Category | Requirement | Example | Measurement |
|----------|-------------|---------|-------------|
| **Response Time** | API calls <500ms (p95) | Transaction list loads in 300ms | Analytics / APM tool |
| **Screen Load** | Screens load <2s on 4G | Dashboard loads in 1.5s | Performance monitoring |
| **App Launch** | Cold start <3s | App opens in 2.8s | Performance monitoring |
| **Animation** | 60 FPS (smooth scrolling) | Transaction list scrolls at 60 FPS | On-device profiler |

### Security

| Category | Requirement | Example | Validation |
|----------|-------------|---------|------------|
| **Data Encryption** | All data encrypted in transit and at rest | HTTPS + AES-256 for local storage | Security audit |
| **Authentication** | Session timeout after 15min inactivity | User re-authenticates after timeout | Manual test |
| **Secrets** | No secrets in logs, source code, or error messages | API keys never logged | Code review |
| **PII Protection** | Personally identifiable info redacted in logs | Email shown as e***@example.com | Log review |

### Reliability

| Category | Requirement | Example | Measurement |
|----------|-------------|---------|-------------|
| **Uptime** | 99.9% API uptime | Max 43min downtime/month | Uptime monitor |
| **Crash Rate** | <0.1% sessions | <1 crash per 1000 sessions | Crash reporter |
| **Error Handling** | Graceful degradation on API errors | Show cached data if API fails | Manual test |
| **Data Integrity** | No data loss on crashes | Pending actions saved, synced on restart | QA validation |

### Accessibility

| Category | Requirement | Example | Validation |
|----------|-------------|---------|------------|
| **Screen Reader** | Full VoiceOver/TalkBack support | All elements have labels | Accessibility audit |
| **Contrast** | WCAG 2.1 AA (4.5:1 for text) | Text readable on background | Color contrast tool |
| **Touch Targets** | Minimum 44x44pt | Buttons meet minimum size | Design review |
| **Font Scaling** | Supports system font sizes (up to 200%) | Text readable at 200% scale | Manual test |

---

## Common API Endpoint Patterns

### RESTful Patterns

**Account Endpoints:**
```
GET    /api/v1/accounts              # List all accounts
GET    /api/v1/accounts/{id}         # Get account details
POST   /api/v1/accounts              # Create account
PUT    /api/v1/accounts/{id}         # Update account
DELETE /api/v1/accounts/{id}         # Close account
```

**Transaction Endpoints:**
```
GET    /api/v1/transactions          # List transactions (paginated)
GET    /api/v1/transactions/{id}     # Get transaction details
POST   /api/v1/transactions          # Create transaction (payment)
GET    /api/v1/transactions/export   # Export transactions (CSV)
```

**Query Parameters:**
- `?page=1&limit=50` - Pagination
- `?sort=date:desc` - Sorting
- `?filter[date]=2024-01-01:2024-01-31` - Filtering
- `?filter[amount_min]=100&filter[amount_max]=500` - Range filtering

### Response Format

**Success Response:**
```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-04-14T10:30:00Z",
    "request_id": "abc123"
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Insufficient balance for this transaction",
    "details": {
      "available": 123.45,
      "required": 200.00
    }
  },
  "meta": {
    "timestamp": "2026-04-14T10:30:00Z",
    "request_id": "abc123"
  }
}
```

### Common Headers

**Request:**
- `Authorization: Bearer {token}`
- `Content-Type: application/json`
- `X-Client-Version: 1.2.3`
- `X-Platform: ios` (or `android`, `web`)

**Response:**
- `X-Request-ID: abc123` (for debugging)
- `X-RateLimit-Remaining: 95` (rate limiting)
- `Cache-Control: max-age=60` (caching)

---

## Common Feature Flags

### Pattern: Gradual Rollout

```
enable_new_dashboard_ui = false   # Default off, gradual rollout
account_card_height_dp  = 80      # A/B testing different heights
enable_savings_goals    = true    # Feature complete, on for all
```

**Naming convention:**
- `enable_{feature_name}` - Boolean flags for features
- `{feature}_{parameter}` - Configuration parameters
- Use snake_case for consistency

### Pattern: Kill Switch

```
enable_payment_processing = true  # Can disable quickly if issues
enable_biometric_auth = true      # Can revert to password-only
```

**Purpose:** Quickly disable feature in production if critical bug found

---

## Common Localisation Requirements

### Supported Languages (define yours in config.yml)

| Language | Code | Market | Status |
|----------|------|--------|--------|
| English | en | International | Default |
| {Primary market language} | {xx} | Primary market | Required |
| {Secondary market language} | {xx} | Secondary market | Required |
| {Expansion market language} | {xx} | Expansion market | Optional |

### Localisation Checklist

- [ ] All user-facing text extracted to strings file
- [ ] Date/time formatted per locale (DD/MM vs MM/DD)
- [ ] Currency formatted per locale (1.234,56 vs 1,234.56)
- [ ] Number formatting matches locale (decimal separator)
- [ ] Plurals handled correctly (1 item, 2 items, 5 items)
- [ ] RTL layout tested (if RTL language support added)

---

## Common User Tier Applicability

Replace this example with your product's actual user / verification model (define it in config.yml).

### Example User Tiers

| Tier | Description | Applicability |
|------|-------------|---------------|
| **Tier 1** | Basic user (email verified) | All basic features |
| **Tier 2** | Verified user (ID submitted) | Enhanced limits |
| **Tier 3** | Business accounts | Business-specific features |
| **Tier 4** | Enterprise/VIP | Premium features |

### Pattern: Feature Gating by Tier

**Example: Savings Goals**
- Tier 1: Can create up to 3 goals
- Tier 2: Can create up to 10 goals, multi-currency goals
- Tier 3: Business savings goals (separate from personal)
- Tier 4: Unlimited goals, premium rates

---

## Usage Instructions for the Breakdown Agents

**When generating story descriptions:**

1. **Auto-fill missing sections** using patterns above:
   - If "Error Handling" is empty -> use common error scenarios
   - If "Edge Cases" is empty -> use common edge cases (offline, low connectivity)
   - If "NFRs" is empty -> use performance, security, reliability standards
   - If "Analytics Events" is empty -> generate based on screen/action type

2. **Context-aware pattern matching:**
   - If story mentions "account" -> use Account Management pattern
   - If story mentions "transaction" -> use Transaction Handling pattern
   - If story mentions "payment" -> use Payments & Transfers pattern

3. **Maintain consistency:**
   - Use same error messages across similar features
   - Use same NFR thresholds (2s load time, 99.9% uptime)
   - Use same analytics event naming (snake_case)

4. **Adapt, don't copy blindly:**
   - Customize patterns to specific feature context
   - Add feature-specific edge cases
   - Include domain-specific validation rules

---

**Maintained by:** Product Owner
**Review Cycle:** Monthly (or when new patterns emerge)
