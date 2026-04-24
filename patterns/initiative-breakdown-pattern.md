---
name: Initiative Breakdown Pattern
description: Three-level task hierarchy pattern for breaking down initiatives into epics and stories
type: pattern
---

# Initiative Breakdown Pattern

## Hierarchy

```
Initiative - Strategic goal, 3-6 months
+-- Epic 1 - Feature set, 2-4 sprints or 4-8 weeks
|   +-- Story - User-facing feature, 1-5 days
|   +-- Task - Backend / infra work, 1-3 days
|   \-- Tech Task - Architecture / POC, 1-2 days
\-- Epic 2
    \-- ...
```

## Issue Types

| Type | Purpose | Typical Size | Example |
|------|---------|--------------|---------|
| **Initiative** | Strategic theme | Multi-month | "Launch Savings Product" |
| **Epic** | Feature group | 2-4 sprints | "Core Savings Features" |
| **Story** | User functionality | 1-8 story points | "User creates savings goal" |
| **Task** | Technical work | 1-5 story points | "Implement savings API" |
| **Tech Task** | Architecture / POC | 1-3 story points | "Design database schema" |

## Breakdown Rules

### Initiative -> Epics (3-7 epics)

**Break by FEATURES, not platforms.**

Wrong (platform-based):
- Epic 1: Android Implementation
- Epic 2: iOS Implementation
- Epic 3: Web Implementation
- Epic 4: Backend Implementation

Right (feature-based):
- Epic 1: User Account Management
- Epic 2: Transaction History & Filtering
- Epic 3: Multi-Currency Support
- Epic 4: Analytics & Tracking

**Why feature-based?**
- Each epic delivers **business value** independently
- Platform implementation is split at **story** level
- Easier to prioritize by user impact
- Natural alignment with product roadmap

**Consider these dimensions for epics:**
- **User Capability:** What can users do after this epic?
- **System Function:** What system capability is enabled?
- **Value Stream:** What business value is delivered?

**Good epic names:**
- "Savings Goal Management" (user capability)
- "Transaction History & Filtering" (system function)
- "Push Notification System" (system function)
- "Compliance & Audit Logging" (system function)

**Bad epic names:**
- "Android Development" (platform-based)
- "Backend Work" (not outcome-focused)
- "Mobile Features" (too vague)

### Epic -> Stories / Tasks (Platform-Specific)

For each feature epic, create stories and tasks per delivery track. Group cross-platform mobile work in one story when behaviour is identical; keep web and backend separate.

**Example: Epic "Savings Goal Management"**

```
Epic: Savings Goal Management
+-- [Mobile] User creates savings goal (Story)
|   +-- [iOS] Implement savings goal UI (Sub-task)
|   +-- [iOS] Add feature flag (Sub-task)
|   +-- [iOS] Add analytics events (Sub-task)
|   +-- [Android] Implement savings goal UI (Sub-task)
|   +-- [Android] Add feature flag (Sub-task)
|   \-- [Android] Add analytics events (Sub-task)
+-- [Web] User creates savings goal (Story)
+-- [BE] Savings CRUD API endpoints (Task)
+-- [BE] Database schema for savings (Tech Task)
\-- [Analytics] Goal creation tracking (Task)
```

**Platform prefix rules (adjust to your `config.yml`):**
- Mobile stories: single story with iOS and Android sub-tasks when behaviour is identical across platforms
- Web stories: separate per web bundle
- Backend tasks: separate per service
- Avoid creating parallel platform-only stories -- causes duplicated descriptions, divergent design links, and double maintenance

**Balance:**
- 50-60% Stories (user-facing)
- 30-40% Tasks (backend / infra / analytics)
- 10% Tech Tasks (architecture / design)

**Story size guidance (no estimation in breakdown):**

Developers estimate during sprint / refinement. Breakdown's job is to identify size signals, not pin numbers.

**Complexity indicators (for guidance):**
- **Simple:** Single screen, no backend changes, standard UI patterns
- **Medium:** Multiple screens, API integration, some complexity
- **Complex:** Multi-step flow, complex logic, multiple integrations
- **Very Complex:** Consider splitting into smaller stories

**If story seems too large -> split by:**
- Create vs Edit vs Delete vs View
- Different user types (personal vs business)
- Different screens or sub-features
- Happy path vs edge cases

## Acceptance Criteria Pattern

Format: Given-When-Then.

Minimum per story:
- 1 happy path scenario
- 1 edge case (empty state, error)
- 1 validation or security check

**Example:**

```
Given user is logged in
When user taps "Create Savings Goal"
Then savings goal creation screen appears

Given user enters goal name and target amount
When user taps "Save"
Then goal is created and appears in goals list
And user sees success message
And analytics event "savings_goal_created" is fired

Given user enters invalid amount (negative)
When user taps "Save"
Then validation error appears: "Amount must be positive"
And goal is not created
```

## Priority Assignment (P0 / P1 / P2)

**P0 (Critical) - Must Have:**
- Blocks MVP launch
- Legal / compliance requirement
- Critical bug fix
- Dependency for other P0 work

**P1 (High) - Should Have:**
- Important for user experience
- Planned for current release
- High user value
- Not a blocker but painful without

**P2 (Medium) - Nice to Have:**
- Can be deferred to next release
- Low user impact
- Optimization / polish
- Future-proofing

## Dependencies

**Types:**
- **Technical:** API must exist before UI can call it
- **Sequential:** Feature A must work before Feature B
- **External:** Design, legal, third-party integration

**Mark in Jira:**
- "Blocks" / "Blocked by" links
- Mention in epic / story description
- Track in breakdown document

## Quality Checklist

**Initiative level:**
- [ ] Clear business goal and success metrics
- [ ] Scope is well-defined
- [ ] Stakeholders identified
- [ ] Timeline is realistic

**Epic level:**
- [ ] 3-7 epics (not too many, not too few)
- [ ] Each epic is independently valuable
- [ ] Epic names are clear and action-oriented
- [ ] Dependencies between epics identified

**Story / Task level:**
- [ ] Each story follows "As a / I want / So that" format
- [ ] Acceptance criteria use Given-When-Then
- [ ] Stories are right-sized (no XL)
- [ ] Priority assigned
- [ ] Platform specified
- [ ] All stories are testable

**Overall balance:**
- [ ] ~60% user stories, ~40% tasks and tech
- [ ] P0 items front-loaded
- [ ] Backend work precedes frontend
- [ ] Analytics and docs included

## Anti-Patterns

- **Too many epics (10+)** -> make epics larger, group related work
- **Too few epics (1-2)** -> initiative is too small, or needs breakdown
- **Stories > 8 SP** -> split into smaller stories
- **No acceptance criteria** -> stories are not testable
- **All P0 priority** -> prioritization has no meaning
- **No tech tasks** -> architecture / design work ignored
- **No dependencies marked** -> team will be blocked
- **Generic story titles** -> "Fix bugs", "Improve UX" are not actionable

## How to Apply

1. Start with initiative description or PRD
2. Identify 3-7 major themes -> Epics
3. Break each epic into 3-8 stories / tasks
4. Write acceptance criteria for each (Given-When-Then)
5. Assign priorities (P0 / P1 / P2)
6. Allocate to sprints / weeks based on dependencies
7. Create in Jira with proper linking
8. Review with team and adjust

## Related

- `user-story-format.md` - how to write a single story
- `tshirt-sizing-guide.md` - sizing the initiative before breakdown
- `jira-api-best-practices.md` - safe encoding and priority rules
