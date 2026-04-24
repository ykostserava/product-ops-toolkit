# User Story Format

## Standard Format

```
As a [persona / user type]
I want [goal / capability]
So that [benefit / value]
```

## Acceptance Criteria Format

Use **Given-When-Then** format for clear, testable criteria:

```
Given [initial context / state]
When [action is performed]
Then [expected outcome / result]
```

## Template Structure

### Story Header
- **Title:** action-oriented, describes what user does (e.g. "Submit expense report")
- **Priority:** High / Medium / Low (or your team's scheme)
- **Estimate:** story points or time estimate
- **Jira ID:** link to ticket

### Story Body

**As a** [specific user type or persona]
**I want** [specific functionality or capability]
**So that** [clear business value or user benefit]

### Acceptance Criteria

Checklist of measurable, testable criteria:

- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]

## Quality Checklist: INVEST

A good user story is **INVEST**:

- **I**ndependent: can be developed independently
- **N**egotiable: details can be discussed and refined
- **V**aluable: delivers value to users or business
- **E**stimable: team can estimate effort
- **S**mall: can be completed in one iteration
- **T**estable: clear acceptance criteria

## Examples

### E-commerce

**As a** returning customer
**I want** to see my order history on my profile page
**So that** I can track my purchases and reorder items easily

**Acceptance Criteria:**
- [ ] Given I am logged in, when I navigate to My Profile, then I see "Order History" section
- [ ] Given I have 5+ orders, when viewing order history, then orders are sorted by date (newest first)
- [ ] Given I click on an order, when the details page loads, then I see order number, date, items, total, and delivery status
- [ ] Given I click "Reorder" on a past order, when the action completes, then all items are added to my cart

**Priority:** High
**Estimate:** 5 story points

### Mobile App

**As a** mobile app user
**I want** to receive push notifications for important updates
**So that** I stay informed without opening the app constantly

**Acceptance Criteria:**
- [ ] Given notifications are enabled, when a payment is processed, then I receive a push notification within 30 seconds
- [ ] Given notifications are disabled in settings, when events occur, then no push notifications are sent
- [ ] Given I tap on a notification, when the app opens, then I am directed to the relevant screen
- [ ] Given I have multiple unread notifications, when I view notification center, then they are grouped by type

**Priority:** Medium
**Estimate:** 8 story points

## Anti-Patterns

**Too technical:**
- Bad: "As a developer, I want to implement REST API endpoints"
- Good: "As a mobile user, I want to sync my data across devices"

**Too vague:**
- Bad: "As a user, I want a better experience"
- Good: "As a user, I want to filter search results by price range"

**No clear value:**
- Bad: "As a user, I want a settings page"
- Good: "As a user, I want to customize my notification preferences so that I only receive alerts that matter to me"

**Too large:**
- Bad: Epic-sized story that takes months
- Good: Story completable in one iteration

## Definition of Done (template)

Every story should meet these criteria before being marked Done (customize per team):

- [ ] Code reviewed and approved
- [ ] All acceptance criteria met
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] UX / UI matches design specs
- [ ] Deployed to staging environment
- [ ] Product Owner acceptance
- [ ] No critical bugs
- [ ] Performance requirements met
