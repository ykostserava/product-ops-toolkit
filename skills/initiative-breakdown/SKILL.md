---
description: Multi-agent initiative breakdown - orchestrates 4 specialized agents across explicit phases with approval gates
---

# Initiative Breakdown

**Multi-Agent Orchestration for Product Planning**

> **Path resolution.** This skill is bundled with templates, patterns, and agent definitions in the plugin root. Whenever a path below references `${CLAUDE_PLUGIN_ROOT}`, run `echo "$CLAUDE_PLUGIN_ROOT"` in Bash first to get the absolute prefix, then call Read with the fully-resolved path.

Breaks an initiative down into **feature-based epics**, then into **platform-specific stories and tasks**, using **4 specialized Claude Code agents** coordinated through **approval gates** at each phase.

Designed for product owners and delivery managers who want AI-assisted breakdown that stays aligned with their team's conventions (templates, platform tagging, Jira project structure) without hand-crafting each story.

---

## Usage

```bash
# Generate markdown breakdown from a Jira issue
/initiative-breakdown PROJ-10

# Generate and create issues directly in Jira
/initiative-breakdown PROJ-10 --create-in-jira

# From a PRD file instead of a Jira issue
/initiative-breakdown "High-Yield Savings" --prd="docs/specs/savings-prd.md" --create-in-jira

# Dry run: preview without creating anything
/initiative-breakdown PROJ-10 --dry-run
```

---

## Setup

Before first use, configure the skill for your team. Create `config.yml` next to this `SKILL.md`:

```yaml
# config.yml
product:
  name: "Your Product Name"
  definition: "One-sentence product definition - what it is and is not"
  context_files:
    - memory/product/context.md
    - memory/product/requirements-patterns.md
    - memory/product/product-definition.md
  # Optional: canonical reference docs the sizing-validator checks scope
  # against (e.g. a service-by-market availability matrix, or customer
  # segment visibility rules). Leave empty to skip capability validation.
  availability_docs: []
  #  - docs/research/service-availability-matrix.md
  #  - docs/specs/segment-visibility-rules.md

process:
  workflow: "kanban"          # or "scrum"
  priority_scheme: "P0/P1/P2" # or "High/Medium/Low"
  estimation: "none"          # or "story-points" or "t-shirt"

jira:
  base_url: "https://your-jira.example.com"
  initiative_project: "PLAN"   # where initiatives live
  delivery_project: "PROJ"     # where stories/tasks live
  epic_link_field: "customfield_10091"  # varies by Jira instance
  default_priority: "High"
  unicode_allowed: false       # if false, enforce ASCII

platforms:
  # Platform prefixes for story titles. Customize per team.
  - key: "android"
    prefix: "[Android]"
    component: "mobile_android"
  - key: "ios"
    prefix: "[iOS]"
    component: "mobile_ios"
  - key: "web"
    prefix: "[Web]"
    component: "web"
  - key: "backend"
    prefix: "[BE]"
    component: "backend"

templates:
  story: templates/story-template.md
  task: templates/task-template.md
  epic: templates/epic-template.md

output:
  breakdown_dir: "docs/breakdowns"

constraints:
  # Team guardrails the breakdown must respect. Hard rules, not suggestions.
  # Examples:
  - "No dedicated designers - don't assume design resources exist"
  - "Describe any other hard rules here"
```

The skill reads this config at every invocation and applies it to agent prompts.

---

## CRITICAL RULES (Apply to ALL Breakdowns)

### 1. Product Context

The one-sentence `product.definition` from `config.yml` is the framing every epic and story must use.

- Load the files listed under `product.context_files` FIRST, before any breakdown work
- Never invent scope that contradicts the definition
- Example: if your product is "the home/dashboard screen inside an existing app - NOT a standalone application", stories must be framed as "the home screen shows..." and must never describe a new standalone app

### 2. Workflow & Process

Read `process.workflow` from config:

- **If `kanban`:** NEVER mention sprints, sprint planning, velocity, or sprint-based elements. Skip "Sprint Allocation" entirely. Focus on priority (per `process.priority_scheme`) and dependencies, NOT sprint numbers.
- **If `scrum`:** sprint allocation is allowed (see the Workflow Allocation section below).

### 3. Jira API Rules

- **If `jira.unicode_allowed` is `false`: ASCII ONLY** - no Unicode characters in summaries, descriptions, or any Jira fields
  - Don't use: arrow characters, currency symbols, non-Latin alphabets, special symbols
  - Use instead: `->` (dash-greater), currency codes like `EUR`/`USD`, Latin alphabet only
- **Default priority:** use `jira.default_priority` - never invent priority values outside `process.priority_scheme`
- **Confirm scope before creating** - list all stories to be created, get user approval first

### 4. Organizational Constraints

- Every entry under `constraints` in `config.yml` is a hard rule - enforce it in every phase
- Always ask before assuming organizational resources exist (designers, QA, second teams)
- Don't invent dependencies (e.g. a sibling project that "probably exists") - verify they exist first

---

## Core Principles

### 1. Feature-Based Epic Breakdown, Not Platform-Based

Don't break by platform (Android Epic, iOS Epic, Web Epic).
Break by **feature** (e.g. "User Account Management", "Savings Goals", "Transaction History").

**Why:** Each epic delivers business value independently. Platform implementation is split at **story** level, not epic level.

### 2. Platform Prefixes in Story Titles

All stories and tasks carry their platform in the title, using prefixes from `config.yml`:

| Platform | Prefix | Example |
|----------|--------|---------|
| Android | `[Android]` | `[Android] User creates savings goal` |
| iOS | `[iOS]` | `[iOS] User creates savings goal` |
| Web | `[Web]` | `[Web] Savings dashboard screen` |
| Backend | `[BE]` | `[BE] Savings deposit API endpoint` |

### 3. Two-Project Jira Structure

- **Initiative** lives in the planning/request project (`jira.initiative_project` in config)
- **Stories and Tasks** live in the delivery project (`jira.delivery_project` in config)

Linking:
- Epic -> Initiative: **Relates To**
- Story/Task -> Epic: **Epic Link** (customfield varies per instance; see `jira.epic_link_field`)
- Story/Task -> Initiative (only for XS initiatives with no Epic): **Relates To**

### 4. Config-Driven Constraints

All team-specific rules (ASCII-only, no sprint references, resource assumptions, etc.) live in `config.yml` under `constraints`. Agents read them and enforce them automatically.

### 5. No Story Point Estimation

**DO NOT** estimate story points (unless `process.estimation` says otherwise). Developers estimate manually during refinement. Remove all SP estimates from output.

### 6. Full Templates, No Shortcuts

Use the templates configured in `config.yml`:

- **Stories:** the full story template (`templates.story`) - include ALL sections (the bundled example template has 15)
- **Tasks:** the task template (`templates.task`) - Why / What / Where / Acceptance Criteria

Never write "Same as the Android story" - every story is a standalone document.

---

## Orchestration Workflow

The skill coordinates **4 specialized agents** across **4 explicit phases with approval gates**.

### Architecture

```
+------------------------------------------------------------+
|  /initiative-breakdown (Main Orchestrator)                 |
|  Coordinates agents, manages approval gates, emits output  |
+------------------------------------------------------------+
         |              |              |              |
         v              v              v              v
   +----------+   +----------+   +----------+   +----------+
   | Phase 1  |   | Phase 2  |   | Phase 3  |   | Phase 4  |
   | Context  |   | Sizing & |   | Break    |   | Quality  |
   | Loading  |   | Validate |   | down     |   | Review   |
   +----------+   +----------+   +----------+   +----------+
        |              |              |              |
        v              v              v              v
   product-      sizing-       breakdown-      quality-
   brain-        validator     generator       reviewer
   loader

   [Gate 1] --> [Gate 2] --> [Gate 3] --> [Output]
```

### Phase Flow

**Phase 1: Context Loading** -> **Approval Gate** -> **Phase 2: Sizing & Validation** -> **Approval Gate** -> **Phase 3: Breakdown** -> **Approval Gate** -> **Phase 4: Quality Review** -> **Output**

Each phase is handled by a specialized agent (see the plugin's `agents/` directory). Between phases, a human approves or redirects.

---

## Phase 1: Load Product Brain Context

**Agent:** `product-brain-loader`
**Duration:** 1-2 minutes
**Purpose:** Load product context, initiative details, and applicable patterns before breakdown begins.

### Process

1. Spawn `product-brain-loader` agent:
   ```
   Agent tool:
     description: "Load product context for initiative breakdown"
     prompt: "Follow instructions in ${CLAUDE_PLUGIN_ROOT}/agents/product-brain-loader.md to:
       1. Load files listed in config.yml under product.context_files
       2. Load templates from config.yml under templates.*
       3. Load initiative details from [Jira key or PRD file path]
       4. Validate for conflicts with product constraints
       5. Output structured context summary

     Initiative: [key or name from user input]
     PRD file: [if --prd flag provided]"
   ```

2. Agent outputs:
   - Product context summary
   - Initiative details extracted
   - Applicable patterns identified
   - Warnings or conflicts flagged

### Approval Gate 1

```
Product Brain Context Loaded

- Product Context: [Summary]
- Initiative: [Name and scope]
- Applicable Patterns: [List]
- Warnings: [Any conflicts or assumptions]

Proceed to Phase 2: Sizing & Validation? [Y/n]
```

If "No": ask what's wrong, adjust context, re-run Phase 1.
If "Yes": proceed to Phase 2.

---

## Phase 2: T-Shirt Sizing & Scope Validation

**Agent:** `sizing-validator`
**Duration:** 2-3 minutes
**Purpose:** Assess initiative size (XS/S/M/L/XL) and validate scope appropriateness.

### Process

1. Spawn `sizing-validator` agent:
   ```
   Agent tool:
     description: "Assess initiative size and validate scope"
     prompt: "Follow instructions in ${CLAUDE_PLUGIN_ROOT}/agents/sizing-validator.md to:
       1. Assess T-shirt size (XS/S/M/L/XL) based on:
          - Feature complexity
          - Platform coverage
          - Integrations and dependencies
          - Technical risk
       2. Validate scope:
          - XS: recommend skipping Epic layer
          - XL: STOP and recommend decomposition
          - S/M/L: proceed to breakdown
       3. If config.yml lists product.availability_docs, validate the scoped
          markets / customer segments / capabilities against those docs
       4. Identify high-risk areas
       5. Output sizing decision

     Context from Phase 1: [pass initiative details]"
   ```

2. Agent outputs:
   - T-shirt size (XS/S/M/L/XL)
   - Reasoning (feature complexity, platform coverage, etc.)
   - Estimated timeline
   - Epic and story count estimates
   - Recommendation: GO / NO-GO / NEEDS DECOMPOSITION / CAPABILITY-FIX
   - Risk areas flagged

### Approval Gate 2

```
T-Shirt Size Assessment

Size: [S/M/L/XL]
Timeline: [weeks]
Epic Count: [N]
Story Count: [N]

Recommendation: [GO / NO-GO / NEEDS DECOMPOSITION / CAPABILITY-FIX]

Reasoning: [Summary from agent]
High-Risk Areas: [Flagged risks]

Capability & Visibility Validation: [PASS / WARNINGS / FAIL / SKIPPED]
- Market gate: [scoped services x markets verified against availability docs]
- Segment gate: [customer-segment boundaries respected (e.g. personal vs business)]
- Terminology: [domain terms used consistently, no ambiguous entity naming]
- Visibility rules: [unavailable capabilities handled per your visibility spec]
- Unverified claims: [none cited]
[List any violations with severity]

Proceed to Phase 3: Breakdown? [Y/n/adjust]
```

**If CAPABILITY-FIX detected (any capability gate FAIL):**

```
Capability Conflict

The initiative scope conflicts with the canonical availability / visibility
docs listed in config.yml (product.availability_docs):

[Specific violations, e.g. "Feature X scoped for market Y - but the underlying
service is only available in market Z per the availability matrix"]

Recommendation: Rewrite the market / segment scope before proceeding.
Reference docs: [list from config.yml product.availability_docs]

Cannot proceed with breakdown until scope is corrected.
```

**If XL detected:**

```
Initiative Too Large (XL)

This initiative is estimated at [N] epics and [M] stories (>10 weeks).

Recommendation: Decompose into 2-4 smaller initiatives first.

Suggested decomposition:
[Vertical slices from agent]

Cannot proceed with breakdown until scope is reduced.
```

**If XS detected:**

```
Initiative Very Small (XS)

This initiative is only [N] stories (<2 weeks).

Recommendation: Skip Epic layer, link stories directly to Initiative.

Proceed with XS breakdown (no Epics)? [Y/n]
```

If "No": ask what to adjust (scope, assumptions), re-run Phase 2.
If "adjust": ask for specific changes, re-run Phase 2 with new constraints.
If "Yes": proceed to Phase 3.

---

## Phase 3: Epic & Story Breakdown

**Agent:** `breakdown-generator`
**Duration:** 5-15 minutes (depending on size)
**Purpose:** Generate feature-based epics and platform-specific stories and tasks.

### Process

1. Spawn `breakdown-generator` agent:
   ```
   Agent tool:
     description: "Generate epic and story breakdown"
     prompt: "Follow instructions in ${CLAUDE_PLUGIN_ROOT}/agents/breakdown-generator.md to:
       1. Determine epic structure based on size from Phase 2
       2. Generate [N] feature-based epics with:
          description, user value, scope, dependencies, success criteria
       3. For each epic, generate platform-specific stories and tasks:
          - Use the FULL story template (templates.story) for Stories
          - Use the FULL task template (templates.task) for Tasks
          - Apply platform prefixes from config.yml
          - Assign components and priorities
       4. Apply Product Brain patterns loaded in Phase 1 (errors, analytics, NFRs)
       5. Respect all constraints from config.yml (workflow language,
          ASCII if required, product framing per product.definition)

     Size: [from Phase 2]
     Epics needed: [from Phase 2]
     Stories needed: [from Phase 2]

     Use context from Phase 1 and sizing from Phase 2.

     Output: full markdown breakdown with all epics and stories."
   ```

2. Agent outputs:
   - [N] epics with complete descriptions
   - [M] stories using the full configured story template
   - [K] tasks using the full configured task template
   - Platform distribution
   - High-risk stories flagged
   - Missing information noted (design TBD, API spec needed, etc.)

### Approval Gate 3

```
Breakdown Generated

Structure:
- [N] Epics (feature-based)
- [M] Stories (platform-specific)
- [K] Tasks

Platform Distribution:
- Android: [N] stories
- iOS: [N] stories
- Web: [N] stories
- Backend: [K] tasks

High-Risk Stories: [List]
Missing Information: [Design TBD, API docs needed, etc.]

Preview: [Show first 2 epics with their stories]

Proceed to Phase 4: Quality Review? [Y/n/revise]
```

If "revise": ask what to change (epic structure, story scope, priorities), re-run Phase 3 with adjustments.
If "Yes": proceed to Phase 4.

---

## Phase 4: Quality Review & Control Manifest

**Agent:** `quality-reviewer`
**Duration:** 3-5 minutes
**Purpose:** Validate quality, run INVEST checks, generate control manifest.

### Process

1. Spawn `quality-reviewer` agent:
   ```
   Agent tool:
     description: "Quality review and control manifest"
     prompt: "Follow instructions in ${CLAUDE_PLUGIN_ROOT}/agents/quality-reviewer.md to:
       1. Run INVEST validation on ALL stories:
          Independent, Negotiable, Valuable, Estimable, Small, Testable
          Score each criterion (pass 1.0, warning 0.5, fail 0.0)
          Overall INVEST score must be >= 5.0
       2. Run PO auto-review:
          - Template completeness
          - Consistency (naming, priorities, platforms)
          - Constraint compliance (workflow language, ASCII if required,
            product framing - all from config.yml)
          - Scope validation
          - Dependencies
       3. Assign story quality scores (0-10)
       4. Check platform coverage (feature parity)
       5. Generate control manifest with:
          - Traceability matrix
          - Quality metrics
          - INVEST results
          - Confidence scores
          - Platform coverage
          - Risk assessment
          - Dependencies and blockers
          - Final GO / NO-GO recommendation

     Breakdown from Phase 3: [pass full breakdown]

     Output: Quality review report + control manifest"
   ```

2. Agent outputs:
   - INVEST validation results per story
   - PO auto-review checklist results
   - Story quality scores (0-10)
   - Platform coverage analysis
   - Control manifest (comprehensive quality audit)
   - Final recommendation: GO / GO WITH REVISIONS / NO-GO

### Approval Gate 4 (Final Quality Gate)

```
Quality Review Complete

Overall Quality Score: [7.8/10]

INVEST Compliance:
- Passed (>=5.0): [N] stories ([%])
- Issues: [M] stories ([%])
- Failed (<5.0): [K] stories ([%])

Template Compliance:
- Stories with all sections: [N/M] ([%])
- Tasks with all sections: [K/L] ([%])

Critical Issues: [List of MUST-FIX]
Warnings: [List of should-review]

Control Manifest: docs/breakdowns/[key]-control-manifest.md

Final Recommendation: [GO / GO WITH REVISIONS / NO-GO]

Proceed with Jira creation? [Y/n/fix-issues]
```

**If GO:**
- User approves -> create issues in Jira (if `--create-in-jira`)
- Save breakdown markdown to `[output.breakdown_dir]/[key]-breakdown.md`
- Save control manifest to `[output.breakdown_dir]/[key]-control-manifest.md`
- Output summary

**If GO WITH REVISIONS:**
- Show specific issues to fix
- Ask "fix now" or "proceed anyway"
- "fix now" -> revise specific stories, re-run Phase 4
- "proceed anyway" -> warn, allow creation

**If NO-GO:**
- Show critical blockers
- Offer automatic fixes or manual revision
- Re-run Phase 3 or Phase 4 after fixes

---

## Legacy Process Documentation

**NOTE:** The sections below are preserved for reference but are now **delegated to specialized agents**. The orchestrator (this skill) coordinates agents; agents execute the detailed steps.

### 1. Load Context & Input (Product Brain Integration)

**CRITICAL: Always read Product Brain files FIRST before any breakdown work.**

Product Brain = the knowledge base (files under `product.context_files`) that informs all requirements generation.

#### Step 1.1: Load Product Context

**Read in this order (paths are the defaults from `config.yml` - adjust to yours):**

1. **`memory/product/context.md`** (MANDATORY)
   - Product vision, mission, target users
   - Strategic priorities (current quarter, roadmap themes)
   - Success metrics (North Star, KPIs)
   - Constraints (business, technical)
   - Stakeholders and communication styles
   - Decision-making framework

2. **`memory/product/requirements-patterns.md`** (MANDATORY)
   - Common user story patterns (Account Management, Transactions, Payments, Savings, Security)
   - Reusable acceptance criteria (UI/UX, Data, Security, Accessibility)
   - Common error scenarios (Network, Auth, Validation, Transaction errors)
   - Common edge cases (Offline, Low connectivity, Data boundaries)
   - Common analytics events (Screen views, User actions, Performance)
   - Common NFRs (Performance, Security, Reliability, Accessibility)
   - API endpoint patterns (RESTful conventions, response formats)
   - Feature flag patterns
   - Localisation requirements (supported languages)
   - User segment applicability (verification tiers, personal/business)

**Why read Product Brain?**
- **Consistency:** Use same error messages, NFR thresholds, analytics naming across all stories
- **Completeness:** Auto-fill missing sections using patterns (e.g., if story has no Error Handling, use common errors)
- **Context:** Align breakdown with product vision, priorities, and constraints
- **Quality:** Reduce PO review time by pre-populating with correct patterns

#### Step 1.2: Load Templates & Guides

3. **`${CLAUDE_PLUGIN_ROOT}/patterns/tshirt-sizing-guide.md`** (if exists)
   - T-shirt sizing framework (XS/S/M/L/XL)
   - Sizing factors and thresholds

4. **Story template** from `config.yml` `templates.story` (MANDATORY)
   - Full multi-section story format (the bundled example has 15 sections)

5. **Task template** from `config.yml` `templates.task` (MANDATORY)
   - 4-section task format (Why/What/Where/AC)

6. **`${CLAUDE_PLUGIN_ROOT}/patterns/initiative-breakdown-pattern.md`** (if exists)
   - Feature-based epic breakdown rules

#### Step 1.3: Load Initiative Details

7. **Initiative data:**
   - From Jira (if issue key provided): fetch via your Jira skill/plugin
   - OR from PRD file (if `--prd` flag): read file at specified path

**Parse initiative:**
- Problem statement
- Target users (map to personas in context.md)
- Success metrics (align with KPIs in context.md)
- Scope and constraints
- Dependencies (external APIs, design, compliance)

#### Step 1.4: Contextualize with Product Brain

**Before proceeding to breakdown:**

1. **Map initiative to strategic priorities:**
   - Which current-quarter priority does this support?
   - Which roadmap theme does this align with?
   - How does this impact the North Star Metric?

2. **Identify applicable patterns:**
   - If initiative mentions "account" -> flag Account Management pattern
   - If initiative mentions "transaction" -> flag Transaction Handling pattern
   - If initiative mentions "payment" -> flag Payments & Transfers pattern
   - If initiative mentions "savings" -> flag Savings & Goals pattern

3. **Check constraints:**
   - Are there business constraints (budget, timeline, compliance)?
   - Are there technical constraints (legacy systems, performance SLAs)?
   - Are assumptions documented that need validation?

4. **Stakeholder context:**
   - Who are the key stakeholders for this initiative?
   - What communication style is needed?

**Output to user (optional, for transparency):**
```
Product Brain Loaded

- Product Context: [Your Product Name]
- Strategic Alignment: Current-quarter priority #2 (Transaction improvements)
- Requirements Patterns: 45+ reusable patterns loaded
- Applicable Patterns: Account Management, Transaction Handling
- Constraints: GDPR compliance required, 99.9% uptime SLA
- Stakeholders: [Names] (communication: data-driven, weekly sync)

Proceeding with breakdown...
```

---

### 2. Determine T-Shirt Size & Validate Scope

**BEFORE breaking down into epics, assess initiative size using T-shirt sizing.**

#### T-Shirt Size Scale

| Size | Duration | Description | Typical Scope | Action |
|------|----------|-------------|---------------|--------|
| **XS** | <2 weeks | Minor improvements, bug fixes, research tasks | <10 stories, 1-2 platforms, NO Epic | Skip Epic layer, link stories to Initiative via Relates To |
| **S** | 2-4 weeks | Small, well-defined feature | 2-3 epics, 10-20 stories, 2-3 platforms | Standard breakdown, single initiative |
| **M** | 4-6 weeks | Standard initiative, median complexity | 3-5 epics, 20-40 stories, all platforms | Standard breakdown |
| **L** | 6-10 weeks | Complex initiative, cross-team dependencies | 5-7 epics, 40-60 stories, external deps | Requires de-risking, risk assessment |
| **XL** | >10 weeks | Major strategic "Big Rock" | 7+ epics, 60+ stories, strategic scope | **MUST decompose** into vertical slices |

#### Sizing Factors

**Evaluate these factors:**

1. **Feature Complexity:**
   - How many distinct features/capabilities?
   - Single domain (e.g., just savings) or multiple domains?
   - New functionality or enhancement to existing?

2. **Platform Coverage:**
   - How many platforms? (from `config.yml` `platforms`, e.g. Android, iOS, Web, Backend)
   - All platforms required or subset?
   - Native implementations or shared logic?

3. **Integrations & Dependencies:**
   - External APIs or third-party services?
   - Cross-team dependencies?
   - Legal/compliance requirements?
   - Design dependencies (new patterns vs existing)?

4. **Technical Risk:**
   - New technology stack?
   - Performance challenges?
   - Security/compliance complexity?
   - Database migrations?

5. **Team Capacity:**
   - Available team size?
   - Single team or multiple teams?
   - Existing team throughput?

#### Sizing Logic

**XS (Extra Small) - <2 weeks:**
```
Indicators:
- 2-10 total stories/tasks (typically 3-5)
- Single feature, simple scope
- 1-2 platforms OR simple backend change
- No external dependencies
- Low technical risk
- Examples: "Fix transaction sorting bug", "Add CSV export button", "Update privacy policy text"

Recommendation:
-> Initiative EXISTS in Jira (already created)
-> DON'T create Epic layer
-> Create Stories DIRECTLY, link to Initiative
-> Output: "XS size - Skip Epic layer, create stories directly under Initiative."

Example Output:
```
XS Size - Skip Epic Layer

Initiative: PLAN-42 "Fix Transaction Sorting" (exists)

Create these stories directly under Initiative:

1. [Android] Fix transaction sorting (Story, P1)
   - Project: PROJ
   - Relates To: PLAN-42 (Initiative in planning project)
   - Component: mobile_android
   - Fix sort order on transaction list screen

2. [iOS] Fix transaction sorting (Story, P1)
   - Project: PROJ
   - Relates To: PLAN-42 (Initiative in planning project)
   - Component: mobile_ios
   - Fix sort order on transaction list screen

3. [BE] Add sort parameter to API (Task, P0)
   - Project: PROJ
   - Relates To: PLAN-42 (Initiative in planning project)
   - Component: backend
   - Add ?sort= query parameter to /api/v1/transactions

Structure:
PLAN-42 (Initiative)
+-- PROJ-11 (Story) [Android]
+-- PROJ-12 (Story) [iOS]
\-- PROJ-13 (Task) [BE]

Total: 3 stories linked to Initiative
Timeline: 1-2 weeks
Epic layer: Skipped (unnecessary overhead)
```
```

**S (Small) - 2-4 weeks:**
```
Indicators:
- 2-3 feature-based epics
- 10-20 stories/tasks total
- 2-3 platforms (e.g., Android + iOS, or Web + Backend)
- Minimal external dependencies
- Low-medium technical risk
- Examples: "Add filtering to transaction history", "Simple goal creation feature"

Recommendation:
-> Standard breakdown
-> Single initiative
-> Timeline: 2-4 weeks
```

**M (Medium) - 4-6 weeks:**
```
Indicators:
- 3-5 feature-based epics
- 20-40 stories/tasks total
- All platforms (Android, iOS, Web, Backend)
- Some external dependencies (analytics, compliance)
- Medium technical risk
- Examples: "Savings product MVP", "Multi-currency account switching"

Recommendation:
-> Standard breakdown
-> Timeline: 4-6 weeks
-> Include risk mitigation in breakdown
```

**L (Large) - 6-10 weeks:**
```
Indicators:
- 5-7 feature-based epics
- 40-60 stories/tasks total
- All platforms + complex integrations
- Cross-team dependencies
- High technical risk or new tech stack
- Examples: "Full savings product with interest calculation", "Payment gateway v2"

Recommendation:
-> Detailed breakdown required
-> Risk assessment needed BEFORE breakdown
-> Timeline: 6-10 weeks
-> De-risking activities early (POCs, spikes, prototypes)
-> Consider phased rollout (MVP -> V1.1 -> V1.2)
-> Flag high-risk areas
```

**XL (Extra Large) - >10 weeks:**
```
Indicators:
- 7+ epics
- 60+ stories/tasks
- Strategic scope (multi-product, platform-wide changes)
- Multiple team dependencies
- Very high technical/business risk
- Examples: "Launch a complete investments platform", "Migrate to new architecture"

Recommendation:
-> STOP breakdown process
-> Initiative is TOO LARGE
-> MUST decompose into vertical slices first
-> Output: "This initiative is XL size. Recommend decomposing into 2-4 smaller initiatives (vertical slices) before breakdown."
-> Suggest decomposition strategy (by phase, by product area, by platform)
```

#### Sizing Process

**Step 1: Quick Assessment**

Based on initiative description, identify:
- How many major features/capabilities?
- How many platforms involved?
- Any major integrations or dependencies mentioned?

**Step 2: Estimate Epic Count**

Mentally break down into feature-based epics. How many logical groups?
- 1-2 epics -> Likely XS
- 2-3 epics -> Likely S
- 3-5 epics -> Likely M
- 5-7 epics -> Likely L
- 7+ epics -> Likely XL

**Step 3: Check Complexity Multipliers**

Adjust size estimate based on:
- **+1 size** if high technical risk (new tech, complex migrations)
- **+1 size** if cross-team dependencies (multiple teams involved)
- **+1 size** if compliance/legal critical (financial regulations, GDPR)
- **-1 size** if mostly UI work with existing APIs
- **-1 size** if single platform only

**Step 4: Determine Final Size**

Pick the size that best matches indicators.

**Step 5: Output Size Assessment**

```markdown
## T-Shirt Size Assessment

**Estimated Size:** M (Medium)

**Reasoning:**
- Feature Complexity: 4 major features (goal creation, deposits, withdrawals, analytics)
- Platform Coverage: All platforms (Android, iOS, Web, Backend)
- Integrations: analytics platform, identity verification (existing)
- Technical Risk: Medium (new database tables, interest calculation logic)
- Dependencies: Minimal (internal only)

**Estimated Timeline:** 4-6 weeks

**Recommendation:** Proceed with standard breakdown. This is an appropriate scope for a single initiative.
```

#### Action Based on Size

**If XS:**
```
This scope is XS - Initiative exists, but skip Epic layer.

Recommendation: Create Stories directly, link to Initiative (no Epic).

Initiative: PLAN-42 "Fix Transaction Sorting"
  +-- [Android] Fix sort order (Story, P1) -> Linked to PLAN-42
  +-- [iOS] Fix sort order (Story, P1) -> Linked to PLAN-42
  \-- [BE] Add sort parameter (Task, P0) -> Linked to PLAN-42

Structure:
- Initiative: Exists in Jira
- Epic: Skip (no Epic layer for XS)
- Stories: Create directly, link to parent Initiative

Total: 3 stories, ~1-2 weeks
```

**If XL:**
```
This initiative is TOO LARGE for a single initiative.

Recommendation: Decompose into vertical slices first.

Suggested Slices:
1. Initiative 1: "Savings MVP" (M size)
   - Core goal CRUD
   - Basic deposits/withdrawals
   - Web + Mobile

2. Initiative 2: "Savings Advanced" (M size)
   - Interest calculation
   - Automated accrual
   - Analytics & reporting

3. Initiative 3: "Savings Optimization" (S size)
   - Performance improvements
   - Advanced features
   - Edge case handling

Proceed with breakdown ONLY after decomposition is approved.
```

**If S, M, or L:**
```
Size is appropriate. Proceed with breakdown.

[Continue to next step: Identify Feature-Based Epics]
```

---

### 3. Identify Feature-Based Epics (3-7 epics)

**Break by FEATURES, not platforms.**

**Good epic structure:**
```
Initiative: "Launch Savings Product"
+-- Epic 1: Savings Goal Management (CRUD for goals)
+-- Epic 2: Deposits & Withdrawals (Money movement)
+-- Epic 3: Interest Calculation (Automated accrual)
+-- Epic 4: Analytics & Tracking (Events, dashboards)
\-- Epic 5: Compliance & Security (Verification, audit logs)
```

**Bad epic structure (don't do this):**
```
Epic 1: Android Implementation     <- WRONG
Epic 2: iOS Implementation         <- WRONG
Epic 3: Web Implementation         <- WRONG
Epic 4: Backend Implementation     <- WRONG
```

**Epic naming rules:**
- Focus on **user capability** or **system function**
- Examples:
  - GOOD: "Transaction History & Filtering"
  - GOOD: "Multi-Currency Account Switching"
  - GOOD: "Push Notifications System"
  - BAD: "Mobile Development"
  - BAD: "Frontend Work"

**For each epic, define:**
- Title (action-oriented)
- Description (what user capability this enables)
- Business value (why it matters)
- Dependencies (if any)

---

### 4. Break Down Each Epic into Platform-Specific Stories/Tasks

For each epic, create stories/tasks for **each platform** that implements the feature.

**IMPORTANT:** Each story must have the FULL template description, even if multiple stories are similar (e.g., Android + iOS + Web versions of same feature). NEVER use shortcuts like "Same as Android story" - generate complete description for each.

**Example: Epic "Savings Goal Management"**

```
Epic: Savings Goal Management
+-- [Android] User creates savings goal (Story)
+-- [iOS] User creates savings goal (Story)
+-- [Web] User creates savings goal (Story)
+-- [BE] Savings goal CRUD API endpoints (Task)
+-- [BE] Database schema for savings_goals (Tech Task)
\-- [Analytics] Savings goal creation events (Task)
```

**Distribution guideline:**
- **Stories (50-60%):** User-facing functionality on Android, iOS, Web
- **Tasks (30-40%):** Backend APIs, integrations, infrastructure
- **Tech Tasks (10%):** Architecture, POCs, database design

**Issue type selection:**
- **Story** -> User-facing feature with UI (mobile/web)
- **Task** -> Backend work, API endpoints, infrastructure, analytics
- **Tech Task** -> Architecture, design, POCs, database schema

---

### 5. Apply Platform Prefix to Summary

**CRITICAL:** Every story/task **must** have a platform prefix, taken from `config.yml` `platforms[].prefix`.

**Format:** `[{Platform}] {Feature description}`

**Examples (using the default config):**
- GOOD: `[Android] User views transaction history with filters`
- GOOD: `[iOS] Biometric authentication for login`
- GOOD: `[Web] Account selection dropdown`
- GOOD: `[BE] POST /api/v1/savings/goals endpoint`
- GOOD: `[BE] Database migration for savings schema`
- BAD: `User views transaction history` (missing prefix)
- BAD: `[Droid] User views history` (prefix not in config)

---

### 6. Assign Jira Components

Based on platform prefix, assign the component from `config.yml` `platforms[].component`:

| Prefix | Component |
|--------|-----------|
| `[Android]` | `mobile_android` |
| `[iOS]` | `mobile_ios` |
| `[Web]` | `web` |
| `[BE]` | `backend` |

**Note:** All stories/tasks are created in the delivery project (`jira.delivery_project`), not the planning project.

---

### 7. Generate Story/Task Description

**CRITICAL RULE: Generate FULL description for EVERY story/task**
- NEVER use shortcuts like "Same structure as Android story"
- NEVER reference other stories with "See XYZ for details"
- ALWAYS generate the complete story template structure for each Story
- ALWAYS generate complete Why/What/Where/AC for each Task
- Each story is a standalone document - must be complete on its own

**For Stories (user-facing features):**

Use the **full story template** from `config.yml` `templates.story`. The bundled example template has these 15 sections:

1. **User Story Format:**
   ```
   As a (customer / end user)
   I want to (perform action)
   So that (achieve goal)
   ```

2. **As-Is vs To-Be Table:**
   | As-Is | To-Be | Value/Rationale |
   |-------|-------|-----------------|
   | Current gap | Desired state | Why important |

3. **Acceptance Criteria:**
   - [ ] Criterion 1
   - [ ] Criterion 2
   - [ ] Criterion 3

4. **Use Cases Table:**
   | # | Actor | Action | Expected Outcome |
   |---|-------|--------|------------------|
   | 1 | User | ... | ... |

5. **Error Handling Table:**
   | Error Scenario | Expected Behaviour | Error Message |
   |----------------|-------------------|---------------|
   | ... | ... | ... |

6. **Edge Cases:**
   - Offline behaviour
   - Low connectivity
   - Other edge cases

7. **User Segment Applicability Table** (adapt segments to your product's user model - verification tiers, roles, etc.):
   | User Segment | Applicable? | Notes |
   |--------------|-------------|-------|
   | Tier 1 (basic) | Yes/No | ... |
   | Tier 2 (verified) | Yes/No | ... |
   | Tier 3 (full access) | Yes/No | ... |

8. **Client Type Applicability Table:**
   | Client Type | Applicable? | Notes |
   |-------------|-------------|-------|
   | Personal | Yes/No | ... |
   | Business | Yes/No | ... |

9. **Feature Flags & Remote Config Table:**
   | Flag/Config Key | Default Value | Purpose |
   |-----------------|---------------|---------|
   | ... | ... | ... |

10. **Non-Functional Requirements Table:**
    | Category | Requirement | Example |
    |----------|-------------|---------|
    | Performance | ... | Screen loads <2s on 4G |
    | Security | ... | Data encrypted in transit |
    | Reliability | ... | Handles X users |
    | Accessibility | ... | WCAG 2.1 AA compliant |

11. **Localisation Table** (adapt languages to your markets):
    | Language | Supported? | Notes |
    |----------|------------|-------|
    | English | Yes | Default |
    | [Primary market language] | Yes | Primary market |
    | [Secondary market language] | Yes | ... |
    | [RTL language] | Yes/No | RTL layout |

12. **Endpoints & Contracts Table:**
    | Endpoint | Method | Description | Owner/Team |
    |----------|--------|-------------|------------|
    | ... | ... | ... | ... |

13. **Analytics / Tracking Events Table:**
    | Event Name | Trigger | Parameters | Notes |
    |------------|---------|------------|-------|
    | ... | ... | ... | ... |

14. **Design Links** (e.g. Figma):
    - Design: [link]
    - Prototype: [link]
    - Notes: ...

15. **Nice to Have / Attachments:**
    - Technical diagrams
    - Supporting docs

**For Tasks (backend/technical work):**

Use the **task template** from `config.yml` `templates.task`:

1. **[Why] Context & Impact:**
   - Business context
   - Problem being solved
   - Impact on users/product

2. **[What] What Should Be Done:**
   - Specific scope
   - Included items
   - Excluded items (out of scope)

3. **[Where] Implementation Guidance:**
   - Files to modify
   - References (API specs, designs, similar code)
   - Dependencies

4. **[Acceptance Criteria]:**
   - Functional criteria
   - Non-functional criteria
   - Testing criteria
   - QA validation steps

5. **Technical Details:**
   - API contracts (if applicable)
   - Database changes (if applicable)
   - Security considerations
   - Performance requirements

#### 7.1 Confidence Auto-Fill (Product Brain Integration)

**AFTER generating initial description, apply auto-fill to missing/sparse sections.**

**Purpose:** Reduce PO review time by pre-populating stories with correct patterns from Product Brain.

---

**Step 1: Detect Missing/Sparse Sections**

For each story/task, scan for:
- **Empty sections:** Section header exists but content is `...`, `TBD`, `N/A`, or placeholder
- **Sparse sections:** Section has <50% expected content (e.g., only 1 error scenario when 3+ expected)

**Missing section detection rules:**

**For Stories (15 sections):**
```
1. User Story -> Always required (no auto-fill, must be written manually)
2. As-Is vs To-Be -> Auto-fill if empty or <2 rows
3. Acceptance Criteria -> Auto-fill if <3 criteria
4. Use Cases -> Auto-fill if <2 use cases
5. Error Handling -> Auto-fill if empty (add common errors)
6. Edge Cases -> Auto-fill if empty (add offline, low connectivity)
7. User Segment Applicability -> Auto-fill from the requirements-patterns file (all segments)
8. Client Type Applicability -> Auto-fill from patterns (Personal/Business)
9. Feature Flags -> Auto-fill if empty (generate flag name based on feature)
10. NFRs -> Auto-fill from patterns (Performance, Security, Reliability, Accessibility)
11. Localisation -> Auto-fill from patterns (your supported languages)
12. Endpoints & Contracts -> Auto-fill if backend dependencies detected
13. Analytics Events -> Auto-fill based on screen/action (screen_viewed, {action}_completed)
14. Design Links -> Mark "Design TBD" if missing (do not leave empty)
15. Attachments -> Optional, can be empty
```

**For Tasks (4 sections):**
```
1. [Why] -> Always required (no auto-fill)
2. [What] -> Always required (no auto-fill)
3. [Where] -> Auto-fill with file/directory hints if sparse
4. [Acceptance Criteria] -> Auto-fill if <3 criteria
```

---

**Step 2: Apply Context-Aware Auto-Fill**

Use the requirements-patterns file (from `product.context_files`) to fill missing sections.

**Matching logic:**

1. **Identify feature type** from story summary:
   - Contains "account" -> Use Account Management patterns
   - Contains "transaction" -> Use Transaction Handling patterns
   - Contains "payment", "transfer" -> Use Payments & Transfers patterns
   - Contains "savings", "goal" -> Use Savings & Goals patterns
   - Contains "auth", "login", "biometric" -> Use Security & Authentication patterns

2. **Auto-fill sections based on feature type:**

**Example: Story mentions "account selection"**

**Missing: Error Handling** -> Auto-fill with:
```markdown
| Error Scenario | Expected Behaviour | Error Message |
|----------------|-------------------|---------------|
| Network timeout loading accounts | Show cached accounts, display offline indicator | "Using cached data. Connect to internet for latest balance." |
| No accounts exist (edge case) | Show empty state with CTA to create account | "No accounts yet. Create your first account." |
| API returns 500 error | Show error state with retry button | "Failed to load accounts. Tap to retry." |
```
*(Source: requirements-patterns file -> Network Errors)*

**Missing: Edge Cases** -> Auto-fill with:
```markdown
**Offline behaviour:**
- Show cached account list
- Disable selection if account change requires network
- Display offline indicator

**Low cellular / poor connectivity:**
- Load cached data immediately
- Update balances in background when network improves
- Show loading indicator for balances only

**Other edge cases:**
- Single account: Still show selection screen for consistency
- 100+ accounts: Virtual scrolling for performance
- Very long account names: Truncate with ellipsis after 30 characters
```
*(Source: requirements-patterns file -> Offline Behaviour, Data Boundary Cases)*

**Missing: NFRs** -> Auto-fill with:
```markdown
| Category | Requirement | Example |
|----------|-------------|---------|
| Performance | Screen loads <2s on 4G | Account list loads in <1.5s |
| Security | No sensitive data in logs | Account balances not logged |
| Reliability | Handles 100+ accounts smoothly | Virtual scrolling, no lag |
| Accessibility | Screen reader fully supported | All elements have accessibility labels |
```
*(Source: requirements-patterns file -> Common NFRs)*

**Missing: Analytics Events** -> Auto-fill with:
```markdown
| Event Name | Trigger | Parameters | Notes |
|------------|---------|------------|-------|
| account_selection_screen_viewed | Screen opens | account_count, has_shared_accounts | Analytics platform event |
| account_selected | User taps account card | account_id, account_type, from_screen | Conversion tracking |
| account_selection_cancelled | User backs out | time_spent_ms | Funnel drop-off |
```
*(Generated based on screen name + action, using naming convention from patterns)*

**Missing: User Segment Applicability** -> Auto-fill with:
```markdown
| User Segment | Applicable? | Notes |
|--------------|-------------|-------|
| Tier 1 (basic) | Yes | All users can select accounts |
| Tier 2 (verified) | Yes | Standard functionality |
| Tier 3 (full access) | Yes | Business accounts included |
```
*(Source: requirements-patterns file -> User Segment Applicability, feature applies to all segments)*

**Missing: Localisation** -> Auto-fill with:
```markdown
| Language | Supported? | Notes |
|----------|------------|-------|
| English | Yes | Default |
| [Primary market language] | Yes | Primary market |
| [Secondary market language] | Yes | Secondary market |
| Other | As needed | Follow existing app localization |
```
*(Source: requirements-patterns file -> Supported Languages)*

**Missing: Feature Flags** -> Auto-fill with:
```markdown
| Flag / Config Key | Default Value | Purpose |
|------------------|---------------|---------|
| enable_new_account_selection_ui | false | Gradual rollout of new design |
| account_card_height_dp | 80 | Card height in dp (adjustable for A/B testing) |
```
*(Generated based on feature name, using naming convention from patterns)*

**Missing: Design Links** -> Auto-fill with:
```markdown
**Design:** [Link to design - TBD]
**Prototype:** [Interactive prototype - TBD]

**Notes:**
- Design review needed before implementation
- Coordinate with your design owner for mockups
```
*(Placeholder to prevent empty section, flags need for design)*

---

**Step 3: Preserve Manually-Written Content**

**CRITICAL: Never overwrite manually-written content.**

**Rules:**
- If section is empty/placeholder -> Auto-fill (OK)
- If section has real content (even if sparse) -> Do NOT overwrite
- If section has partial content -> ADD to it (append auto-fill to existing)

**Example:**

**Before auto-fill:**
```markdown
## Error Handling

| Error Scenario | Expected Behaviour | Error Message |
|----------------|-------------------|---------------|
| Invalid account ID | Show error message | "Account not found" |
```

**After auto-fill (APPEND, not replace):**
```markdown
## Error Handling

| Error Scenario | Expected Behaviour | Error Message |
|----------------|-------------------|---------------|
| Invalid account ID | Show error message | "Account not found" |
| Network timeout loading accounts | Show cached accounts, display offline indicator | "Using cached data. Connect to internet for latest balance." |
| API returns 500 error | Show error state with retry button | "Failed to load accounts. Tap to retry." |
```

---

**Step 4: Mark Auto-Filled Sections (Optional)**

For transparency, optionally add comment to auto-filled sections:

```markdown
## Edge Cases

*(Auto-filled from Product Brain patterns - review and adjust if needed)*

**Offline behaviour:**
- Show cached account list
...
```

**Or simpler:** Don't mark, just apply silently. PO will review in Auto-Review phase.

---

**Step 5: Re-Calculate Confidence Score**

**After auto-fill, recalculate confidence score:**

**Before auto-fill:**
```
Story: [Android] User selects account
Confidence: 73% (11/15 sections filled)
Missing: Error Handling, Edge Cases, NFRs, Analytics
```

**After auto-fill:**
```
Story: [Android] User selects account
Confidence: 93% (14/15 sections filled)
Missing: Design link (marked "Design TBD")
```

**Confidence boost:** 73% -> 93% (+20%)

---

**Step 6: Output Auto-Fill Summary**

After processing all stories/tasks, output summary:

```markdown
## Product Brain Auto-Fill Results

**Stories processed:** 18
**Tasks processed:** 10

**Auto-fill applied:**
- Error Handling: 12 stories (67%)
- Edge Cases: 14 stories (78%)
- NFRs: 18 stories (100%)
- Analytics Events: 15 stories (83%)
- User Segment Applicability: 18 stories (100%)
- Localisation: 18 stories (100%)
- Feature Flags: 10 stories (56%)
- Design Links: 8 stories (marked "Design TBD") (44%)

**Confidence improvement:**
- Before auto-fill: Average 78%
- After auto-fill: Average 93%
- Improvement: +15%

**Stories now >90% confidence:** 16/18 (89%)

**Next step:** PO Auto-Review
```

---

**Auto-Fill Pattern Matching Examples:**

| Story Summary Contains | Apply Patterns From | Auto-Fill Sections |
|------------------------|---------------------|-------------------|
| "account", "select", "switch" | Account Management | Error Handling (account errors), Edge Cases (0 accounts, 100+ accounts), Analytics (account_selected) |
| "transaction", "history", "filter" | Transaction Handling | Error Handling (no transactions, API timeout), Edge Cases (10,000+ transactions), Analytics (transaction_filtered) |
| "payment", "transfer", "send" | Payments & Transfers | Error Handling (insufficient balance, daily limit), Security NFRs, Analytics (payment_completed/failed) |
| "savings", "goal" | Savings & Goals | Error Handling (invalid amount), Edge Cases (goal completed, recurring deposits), Analytics (savings_goal_created) |
| "login", "auth", "biometric" | Security & Authentication | Error Handling (invalid credentials, session expired), Security NFRs (encryption, session timeout), Analytics (login_success/failed) |

---

**When NOT to Auto-Fill:**

- **User Story section** (As a... I want... So that...)
  - Reason: Must be feature-specific, requires manual writing
- **As-Is vs To-Be** (if already has 1+ rows)
  - Reason: Likely manually written, context-specific
- **Acceptance Criteria** (if already has 3+ criteria)
  - Reason: Core requirements, should be manually written
- **Endpoints & Contracts** (for frontend-only stories)
  - Reason: No backend dependencies, section not applicable
- **Design Links** (if link already present)
  - Reason: Design already provided

---

**Auto-Fill Quality Checks:**

After auto-fill, verify:
- All auto-filled content is **relevant** to the story
- No generic placeholders (e.g., "Error: Something went wrong" without context)
- Analytics event names follow snake_case convention
- Error messages are **specific** and actionable
- NFR thresholds are **realistic** (2s load time, 99.9% uptime)

If auto-fill produces irrelevant content -> **skip that section**, leave for PO to fill manually.

---

### 8. Assign Priority (P0/P1/P2)

Use the scheme from `config.yml` `process.priority_scheme`. With the default `P0/P1/P2`:

**P0 (Critical) - Must Have:**
- Blocks MVP launch
- Legal/compliance requirement
- Critical security issue
- Dependency for other P0 work

**P1 (High) - Should Have:**
- Important for user experience
- Planned for current release
- High user value
- Not blocking but painful without

**P2 (Medium) - Nice to Have:**
- Can be deferred to next release
- Low user impact
- Optimization/polish
- Future-proofing

**DO NOT estimate story points** - developers will do this during refinement.

---

### 9. Workflow Allocation (Kanban vs Scrum)

**Read `process.workflow` from `config.yml`.**

**If `kanban` (default): DO NOT create sprint allocations.**

Instead of sprint allocation:

**Kanban Workflow Approach:**
- Focus on **priority order** (P0 -> P1 -> P2), NOT sprint numbers
- Highlight **dependencies** (e.g., "PROJ-7 must complete before PROJ-3, PROJ-4")
- Document **blockers** clearly
- Backend tasks typically P0 (must exist before frontend can start)
- Group related work by Epic, not by artificial sprint boundaries
- Document execution order in Control Manifest -> Timeline & Dependencies section

**Example Kanban Timeline:**
```markdown
### Execution Order (Kanban)

**Phase 1: Backend Foundation (P0 - Blocking)**
- PROJ-114: [BE] Database schema (Tech Task, P0)
- PROJ-115: [BE] CRUD API endpoints (Task, P0)
- Timeline: ~1-2 weeks
- Blocks: All frontend stories (PROJ-111, PROJ-112, PROJ-113)

**Phase 2: Platform Implementation (P0)**
- PROJ-111: [Android] User creates goal (Story, P0)
- PROJ-112: [iOS] User creates goal (Story, P0)
- PROJ-113: [Web] Savings dashboard (Story, P0)
- Dependencies: Requires Phase 1 completion
- Timeline: ~2-3 weeks

**Phase 3: Enhancements (P1)**
- PROJ-121: [Analytics] Tracking events (Task, P1)
- Dependencies: None (can start anytime)
- Timeline: ~1 week
```

**If `scrum`:** allocate stories to sprints based on dependencies and priority; keep backend enablers in earlier sprints. Everything else in this skill applies unchanged.

---

### 10. Create Jira Structure (if --create-in-jira)

**Projects (from `config.yml`):**
- Initiative: `jira.initiative_project` (planning/requests, e.g. `PLAN`)
- Stories/Tasks: `jira.delivery_project` (implementation, e.g. `PROJ`)

**Steps:**
1. Verify initiative exists in the planning project (or create placeholder)
2. For each epic:
   - Create epic issue in the delivery project
   - Set epic name, description
   - Link to Initiative using **Relates To** link
   - Set priority
3. For each story/task:
   - **Create issue in the delivery project** (Story/Task type)
   - **Set summary with platform prefix:** `[Android] User creates goal`
   - Set description using appropriate template (story or task)
   - **Link to Epic via Epic Link** (`jira.epic_link_field`) - for S/M/L sizes
   - **OR link to Initiative via Relates To** - for XS size only (breakdown, not blockers)
   - **Assign component** based on platform (from `platforms[].component`)
   - Set priority (per `process.priority_scheme`)
   - **DO NOT set story points** (leave empty)
   - Add labels: platform, feature area, version
4. Link dependencies (blocks/blocked by)
5. Output summary with Jira links

---

### 11. PO Auto-Review (Quality Gate)

**CRITICAL: Run this checklist BEFORE creating any Jira issues.**

This is your final quality gate. If ANY check fails, **DO NOT proceed** with `--create-in-jira`. Fix issues first.

#### Auto-Review Checklist

**For EVERY Epic:**
```
[ ] Epic name describes feature/capability (not "Android Epic", "Backend Work")
[ ] Epic has clear business value description
[ ] Epic links to Initiative via Relates To
[ ] Epic is in the delivery project (not the planning project)
[ ] Priority assigned (per process.priority_scheme)
```

**For EVERY Story:**
```
[ ] Summary has a platform prefix from config.yml (e.g. [Android], [iOS], [Web], [BE])
[ ] Description contains ALL template sections (bundled example template = 15):
    1. User Story (As a... I want... So that...)
    2. As-Is vs To-Be (table)
    3. Acceptance Criteria (checklist)
    4. Use Cases (table)
    5. Error Handling (table)
    6. Edge Cases (offline, low connectivity, etc.)
    7. User Segment Applicability (table)
    8. Client Type Applicability (table)
    9. Feature Flags & Remote Config (table)
    10. Non-Functional Requirements (table)
    11. Localisation & Supported Languages (table)
    12. Endpoints & Contracts (table)
    13. Analytics / Tracking Events (table)
    14. Design Links (links + notes)
    15. Nice to Have / Attachments
[ ] Story links to Epic via Epic Link (jira.epic_link_field) - for S/M/L sizes
   OR links to Initiative via Relates To - for XS size only (breakdown, not blockers)
[ ] Component assigned based on platform (from platforms[].component)
[ ] Priority assigned (per process.priority_scheme)
[ ] Story points field is EMPTY (not estimated)
[ ] Story is in the delivery project (not the planning project)
[ ] INVEST check (see below)
```

**For EVERY Task:**
```
[ ] Summary has platform prefix: [BE] (tasks are typically backend)
[ ] Description contains ALL 4 sections:
    1. [Why] Context & Impact
    2. [What] What Should Be Done
    3. [Where] Implementation Guidance
    4. [Acceptance Criteria]
[ ] Task links to Epic via Epic Link (jira.epic_link_field) - for S/M/L sizes
   OR links to Initiative via Relates To - for XS size only (breakdown, not blockers)
[ ] Component assigned (backend)
[ ] Priority assigned (per process.priority_scheme)
[ ] Story points field is EMPTY
[ ] Task is in the delivery project (not the planning project)
```

#### INVEST Validation (Enhanced)

For each Story, perform **deep INVEST analysis** with scoring.

Each criterion scored: Pass (1 point), Warning (0.5 points), Fail (0 points)

**Overall INVEST Score:** Sum of 6 criteria
- **6.0** -> PASS (excellent)
- **5.0-5.5** -> REVIEW (minor issues)
- **<5.0** -> FAIL (major issues, do not create)

---

**I - Independent** (Can be implemented without waiting for other stories)

**Pass if:**
- Story has NO blocking dependencies on other stories in same epic
- OR Backend dependencies are clearly identified in "Endpoints & Contracts" section
- OR Dependencies are on P0 stories that will be completed earlier

**Warning if:**
- Has 1 dependency, but dependency is scheduled to be completed first
- Depends on backend API, but API is P0 and will be completed earlier

**Fail if:**
- Has 2+ blocking dependencies within same epic
- Depends on story not yet planned/scheduled
- Circular dependency detected

**Check:**
```
1. Scan "Endpoints & Contracts" section for API dependencies
2. If API dependencies exist -> check if corresponding backend Task exists and is P0
3. If story depends on another story -> check dependency order (P0 before P1, etc.)
4. Mark Pass if independent or dependencies are clear and will be completed first
```

---

**N - Negotiable** (Describes "what" without dictating "how")

**Pass if:**
- Acceptance criteria focus on **outcomes**, not implementation steps
- "What" section describes **behavior**, not code changes
- No prescriptive implementation details (e.g., "use library X", "implement algorithm Y")

**Warning if:**
- Some acceptance criteria are overly prescriptive (e.g., "Use RecyclerView adapter")
- Technical approach is mentioned but not mandated

**Fail if:**
- Acceptance criteria read like implementation steps
- Story dictates specific code structure, libraries, or algorithms
- "What" section is a technical specification, not user story

**Check:**
```
1. Read Acceptance Criteria - do they say "User can X" (Pass) or "Code does X" (Fail)?
2. Check [What] section (for Tasks) - is it outcome-focused?
3. Flag Fail if story prescribes HOW instead of WHAT
```

---

**V - Valuable** (Delivers user value independently)

**Pass if:**
- User Story clearly states user benefit ("So that I can...")
- Story delivers **visible** change to user (UI, behavior, feature)
- As-Is vs To-Be table shows clear value/rationale

**Warning if:**
- Value is indirect (e.g., "improves performance" but user can't see it)
- Backend task that enables frontend (valuable, but not directly visible)

**Fail if:**
- No clear user value stated
- Story is technical refactoring with no user impact
- "So that" clause is missing or vague

**Check:**
```
1. Read User Story section - is "So that..." clause present and clear?
2. Read As-Is vs To-Be table - is "Value/Rationale" column filled?
3. Ask: "Can a user see/feel this change?" -> Yes (valuable), No (not valuable)
```

---

**E - Estimable** (Clear enough to estimate)

**Pass if:**
- Scope is clearly defined (no ambiguous requirements)
- Acceptance criteria are specific and measurable
- Technical unknowns are identified (e.g., "Needs POC", "Design TBD")
- Design link present (for UI stories)

**Warning if:**
- Design not finalized ("4 variants exist, need to select")
- Minor unknowns exist but story is otherwise clear
- Missing design link but design is described in text

**Fail if:**
- Scope is vague or undefined
- Acceptance criteria use words like "maybe", "if possible", "TBD"
- Major unknowns (e.g., "Need to research feasibility")
- No design available for UI-heavy story

**Check:**
```
1. Scan Acceptance Criteria for vague language ("TBD", "if needed", "maybe")
2. For UI stories -> check Design Links section, flag Fail if missing and scope unclear
3. Check for unknowns in description -> if present, are they flagged explicitly?
```

---

**S - Small** (Can be completed in reasonable time, ~2-5 days)

**Pass if:**
- Single platform story (Android OR iOS OR Web, not multiple)
- Acceptance criteria count: 3-7 (manageable scope)
- Use cases count: 2-5 (not overly complex)
- Scope is focused on ONE feature/screen/capability

**Warning if:**
- Acceptance criteria count: 8-10 (borderline large)
- Use cases count: 6-8 (complex but doable)
- Story covers 2 related screens (e.g., "Create + Edit")

**Fail if:**
- Acceptance criteria >10 (too large)
- Use cases >8 (too complex)
- Story covers 3+ screens or major workflows
- Summary suggests multiple features (e.g., "User creates, edits, and deletes goals")

**Check:**
```
1. Count acceptance criteria -> Pass 3-7, Warning 8-10, Fail >10
2. Count use cases -> Pass 2-5, Warning 6-8, Fail >8
3. Check summary for multiple verbs -> Fail if "creates, edits, deletes" (should be split)
4. Ask: "Is this 1 feature or 2-3 features?" -> Pass 1 feature, Fail multiple
```

---

**T - Testable** (Clear acceptance criteria, QA can verify)

**Pass if:**
- Acceptance criteria are **specific** (no vague language)
- Each criterion is **measurable** (can be verified true/false)
- Error handling table has >=1 scenario defined
- Edge cases section is filled (offline, low connectivity, etc.)
- Use cases have clear "Expected Outcome" for each

**Warning if:**
- Acceptance criteria are somewhat vague but testable with clarification
- Error handling has 0 scenarios (but story is simple, low risk)
- Edge cases section is sparse

**Fail if:**
- Acceptance criteria use vague language ("should work well", "fast enough")
- No error handling defined for risky features (e.g., payments, auth)
- Use cases missing "Expected Outcome" column
- Criteria are not measurable (e.g., "UI looks good")

**Check:**
```
1. Read each acceptance criterion -> is it pass/fail testable? Yes (Pass), No (Fail - vague)
2. Check Error Handling table -> Pass >=1 scenario, Warning 0 scenarios (if low-risk), Fail 0 scenarios (if high-risk)
3. Check Use Cases table -> are "Expected Outcome" entries clear?
```

---

**Scoring Logic:**

For each story, calculate:
```
INVEST Score = I + N + V + E + S + T

Where each criterion is:
- Pass = 1.0
- Warning = 0.5
- Fail = 0.0
```

**Example:**
```
Story: [Android] User creates savings goal

I - Independent: Pass (1.0) - No blocking dependencies
N - Negotiable: Pass (1.0) - Describes "what", not "how"
V - Valuable: Pass (1.0) - Clear user value in "So that" clause
E - Estimable: Warning (0.5) - Design has 4 variants, not finalized yet
S - Small: Pass (1.0) - 5 acceptance criteria, 3 use cases, single screen
T - Testable: Pass (1.0) - All criteria are specific and measurable

INVEST Score: 5.5 / 6.0 -> REVIEW

Issue: Design not finalized (4 variants exist)
Recommendation: Schedule design review before development starts
```

---

**Action on INVEST failure:**

**If score >=5.0 (PASS or REVIEW):**
- Safe to proceed with creation
- If score 5.0-5.5, note warnings in Control Manifest

**If score <5.0 (FAIL):**
- **DO NOT create in Jira**
- **Flag specific issues:**
  ```
  INVEST FAIL: [Android] User creates, edits, and deletes savings goals
     Score: 3.5 / 6.0

     Issues:
     - Not Small (0.0): Summary covers 3 features (create, edit, delete)
     - Not Testable (0.0): Acceptance criteria vague ("should work smoothly")
     - Not Estimable (0.5): No design available

     Recommendations:
     1. Split into 3 stories:
        - [Android] User creates savings goal
        - [Android] User edits savings goal
        - [Android] User deletes savings goal
     2. Make acceptance criteria specific (replace "smoothly" with measurable criteria)
     3. Request design before breakdown
  ```
- **Offer to auto-fix:**
  - Split large stories into smaller ones
  - Rewrite vague acceptance criteria
  - Add missing sections (error handling, edge cases)

**Output INVEST results in PO Auto-Review summary:**
```markdown
**INVEST Validation:**
- Passed (6.0): 12 stories
- Passed (5.5): 4 stories
- Review (5.0): 2 stories (issues noted in Control Manifest)
- Failed (<5.0): 0 stories

Average INVEST Score: 5.7 / 6.0
```

#### Confidence Score

Calculate confidence score for each story/task based on completeness:

**Scoring formula:**
```
Story confidence = (sections_filled / 15) x 100%
Task confidence = (sections_filled / 4) x 100%
```

**Sections filled** = count non-empty sections (ignore placeholders like "TBD", "...", "N/A")

**Thresholds:**
- **90-100%** -> Ready to create
- **70-89%** -> Review needed (missing critical sections?)
- **<70%** -> Incomplete - DO NOT create

**Action on low confidence:**
- If story <90%, **list missing sections**:
  ```
  Low Confidence: [iOS] User creates goal (73%)
     Missing sections:
     - Design Links (section 14)
     - Analytics Events (section 13)
     - User Segment Applicability (section 7)

     Proceed anyway? (not recommended)
  ```
- Offer to **fill missing sections** before creating

#### Template Compliance Check

**For Stories, verify these critical sections are NOT empty or placeholder:**
1. **As-Is vs To-Be** - must have actual content (not "TBD")
2. **Acceptance Criteria** - minimum 3 criteria
3. **Use Cases** - minimum 2 use cases
4. **Error Handling** - minimum 1 error scenario
5. **Analytics Events** - at least 1 event defined (or explicit "No tracking needed")

**For Tasks, verify:**
1. **[Why]** - explains business context (not just "need to implement")
2. **[What]** - specific scope (not vague "add feature")
3. **[Acceptance Criteria]** - minimum 3 criteria

#### Output Format for Auto-Review

After generating all epics/stories/tasks, output this summary:

```markdown
## PO Auto-Review Results

### Quality Gate: PASSED (or FAILED)

**Breakdown Summary:**
- Epics: 5
- Stories: 18
- Tasks: 10
- Total: 33 issues

**Auto-Review Checks:**

- Platform Prefixes: 28/28 (100%)
- Story Templates: 18/18 stories have all 15 sections (100%)
- Task Templates: 10/10 tasks have 4 sections (100%)
- Epic Links: 28/28 correctly linked
- Components: 28/28 assigned
- Priorities: 28/28 assigned
- Story Points: 0/28 estimated (correct - left empty)
- INVEST Validation: 18/18 stories pass
- Confidence Score: Average 95% (min: 87%, max: 100%)

**Confidence Breakdown:**
- 90-100% (Ready): 16 stories
- 70-89% (Review): 2 stories
  - PROJ-123: [iOS] User creates goal (87%) - Missing: design link
  - PROJ-125: [Web] Savings dashboard (89%) - Missing: analytics events
- <70% (Incomplete): 0 stories

**INVEST Issues:**
- None found

**Template Compliance:**
- Stories with complete As-Is/To-Be: 18/18
- Stories with 3+ acceptance criteria: 18/18
- Stories with 2+ use cases: 18/18
- Tasks with clear [Why] section: 10/10

**Recommendations:**
1. Add design link to PROJ-123 (or mark "Design TBD")
2. Add analytics events to PROJ-125 (or mark "No tracking needed")

**Status:** Safe to proceed with --create-in-jira
(or: Fix issues above before creating in Jira)
```

#### When to STOP and Fix

**CRITICAL - DO NOT create Jira issues if:**
1. Any story missing platform prefix
2. Any story with <90% confidence score (unless user confirms)
3. Any story failing INVEST validation
4. Any story missing critical sections (As-Is/To-Be, Acceptance Criteria, Use Cases)
5. Any issue with wrong project assignment (Initiative in the delivery project instead of the planning project)
6. Any issue missing Epic Link or Relates To link
7. Any issue with story points pre-filled

**Instead:**
- Show Auto-Review summary
- List specific issues
- Offer to fix automatically
- Ask user: "Fix issues before creating in Jira?"

---

### 12. AI Personas Review (Multi-Perspective Validation)

**AFTER PO Auto-Review completes, run AI Personas review for content quality validation.**

AI Personas = 8 specialized AI reviewers that validate breakdown from different domain perspectives.

**Purpose:**
- PO Auto-Review validates **structure** (prefixes, templates, INVEST scoring, confidence)
- AI Personas validate **content quality** (business value, technical feasibility, compliance, etc.)
- Multi-perspective review catches issues that automated checks miss

---

#### 8 AI Personas

See `${CLAUDE_PLUGIN_ROOT}/skills/initiative-breakdown/patterns/ai-personas.md` for full definitions, checklists, and output formats.

| Persona | Focus Areas | Example Checks |
|---------|-------------|----------------|
| **Business Analyst AI** | Business value, user needs, requirements clarity | User story value clear? Success metrics defined? As-Is vs To-Be shows impact? |
| **Requirements Engineer AI** | Completeness, clarity, traceability | All template sections filled? Requirements specific (not vague)? Traceability links exist? |
| **Technical Architect AI** | Technical feasibility, architecture, performance | API contracts defined? Performance NFRs realistic? Security requirements clear? |
| **QA Specialist AI** | Testability, test coverage, QA readiness | Acceptance criteria testable? Edge cases comprehensive? Test data requirements specified? |
| **Product Manager AI** | Strategic alignment, prioritization, roadmap fit | T-shirt sizing documented? Priorities assigned? Timeline realistic? |
| **UX Researcher AI** | User experience, design quality, accessibility | Designs linked? Accessibility requirements clear? User flows intuitive? |
| **Compliance Officer AI** | Legal, regulatory, GDPR compliance | PII not logged? Consent for analytics? Data encryption specified? |
| **DevOps Engineer AI** | Deployment, monitoring, operational readiness | Feature flags defined? Rollout strategy documented? Error logging requirements clear? |

---

#### Execution Flow

```
1. PO Auto-Review (automated structure checks)
   | PASS
   v
2. AI Personas Review (8 specialized content reviews, run in parallel)
   +- Business Analyst AI
   +- Requirements Engineer AI
   +- Technical Architect AI
   +- QA Specialist AI
   +- Product Manager AI
   +- UX Researcher AI
   +- Compliance Officer AI
   \- DevOps Engineer AI
   |
   v
3. Aggregate Results
   |
   v
4. Final Quality Gate Decision
```

---

#### Each Persona Provides

**For each story/task, persona reviews and outputs:**
- **Passed checks** - What meets standards
- **Warnings** - Issues to review (not blocking)
- **Critical issues** - Must fix before Jira creation
- **Recommendations** - Nice-to-have improvements

**Example (Business Analyst AI reviewing PROJ-3):**
```markdown
## Business Analyst Review: PROJ-3

**Overall:** REVIEW

Passed:
- User story has clear business value ("reduces clicks from 4-7 to 2")
- As-Is vs To-Be shows specific pain points and improvements
- Acceptance criteria are outcome-focused (not implementation details)

Warnings:
- Success metric is qualitative ("improves app store ratings") - add quantitative target (e.g., "4.5 -> 4.7 rating")
- Edge cases focus on technical scenarios (100+ accounts) - add user behavior (e.g., "power user with complex portfolio")

Recommendations:
- Consider: What happens if a basic-tier user tries to select a business-tier account? (permission edge case)
```

---

#### Aggregation Logic

**Quality Gate decision based on persona results:**

**FAIL if:**
- ANY persona reports FAIL (critical issue found)
- 2+ personas have critical issues

**REVIEW if:**
- 3+ personas report REVIEW (many warnings)
- 1 persona reports FAIL but issue is minor/fixable quickly

**PASS if:**
- All personas PASS
- OR <3 personas have warnings (and no critical issues)

---

#### Aggregated Output Format

```markdown
## AI Personas Review Summary

**Overall Quality Gate:** PASS / REVIEW / FAIL

**Persona Results:**
- Business Analyst: PASS (2 recommendations)
- Requirements Engineer: PASS
- Technical Architect: REVIEW (1 warning)
- QA Specialist: PASS (1 recommendation)
- Product Manager: FAIL (priorities not assigned)
- UX Researcher: REVIEW (design not finalized)
- Compliance Officer: FAIL (missing consent requirement)
- DevOps Engineer: REVIEW (rollout strategy missing)

---

**Critical Issues (must fix before Jira creation):**
1. Product Manager: Priorities not assigned (all issues have "Unspecified")
   - Fix: PROJ-7 -> P0, PROJ-3/PROJ-4/PROJ-6 -> P1
2. Compliance Officer: Missing user consent for analytics tracking (GDPR Article 6)
   - Fix: Add consent requirement to PROJ-6 acceptance criteria

---

**Warnings (review recommended):**
3. UX Researcher: Design not finalized (4 variants exist, need to pick 1)
   - Recommendation: Complete PROJ-7 design review before starting PROJ-3, PROJ-4
4. DevOps Engineer: Rollout strategy not documented
   - Recommendation: Add rollout plan (10% -> 50% -> 100% over 1 week)
5. Technical Architect: Missing API response format example
   - Recommendation: Add example payload to "Endpoints & Contracts" section

---

**Strengths (what's working well):**
- Template compliance: 100% (all sections filled)
- INVEST scores: 95.8% average
- Business value clearly articulated (reduces clicks by 50%)
- Error handling comprehensive (network, API, validation scenarios)
- Platform coverage complete (Android, iOS)

---

**Action Items (prioritized by severity):**
1. **CRITICAL (must do):**
   - [ ] Assign priorities: PROJ-7 -> P0, PROJ-3/PROJ-4/PROJ-6 -> P1
   - [ ] Add consent requirement to PROJ-6
2. **RECOMMENDED (should do):**
   - [ ] Complete PROJ-7 design review
   - [ ] Document rollout strategy
   - [ ] Add API response format examples
3. **NICE-TO-HAVE (could do):**
   - [ ] Add quantitative success metrics
   - [ ] Expand edge cases with user behavior scenarios

---

**Quality Gate Decision:**
DO NOT proceed with --create-in-jira until critical issues fixed.

**Estimated Fix Time:** 1-2 hours
```

---

#### When to Skip AI Personas Review

**AI Personas review is OPTIONAL. Skip if:**
- Doing quick prototype/POC (not production-ready)
- Very small XS initiative (<5 stories, low risk)
- Time-sensitive urgent fix (skip review, fix later)

**Always run AI Personas review for:**
- Production features with user impact
- Compliance-sensitive features (payments, auth, data privacy)
- Cross-team initiatives (multiple stakeholders)
- Complex initiatives (M/L size, 20+ stories)

---

#### Output Location

**Add AI Personas results to:**
- Console output (summary after PO Auto-Review)
- Control Manifest (`[output.breakdown_dir]/{key}-control-manifest.md`)
  - Add section: "AI Personas Review Results"
  - Include: Persona scores, critical issues, warnings, recommendations

---

### 13. Generate Control Manifest

**After PO Auto-Review AND AI Personas Review complete, generate Control Manifest document.**

Control Manifest is a **comprehensive quality audit trail** that documents:
- Traceability matrix (all links)
- Quality metrics and compliance
- INVEST validation results
- Confidence scores
- Platform coverage analysis
- Risk assessment
- Dependencies and blockers
- Approval sign-off

**File location:** `[output.breakdown_dir]/{initiative-key}-control-manifest.md`

#### Control Manifest Generation Process

**Step 1: Collect Data**

From the breakdown, collect:
- Initiative key, name, size, timeline
- All epics with keys, names, links
- All stories/tasks with keys, summaries, links, platforms, components
- PO Auto-Review results (from section 11)
- Quality metrics (template compliance, INVEST, confidence scores)
- Platform distribution
- Dependencies and risks

**Step 2: Populate Template**

Use template: `${CLAUDE_PLUGIN_ROOT}/skills/initiative-breakdown/templates/control-manifest-template.md`

Replace placeholders:
- `{INITIATIVE_KEY}`, `{INITIATIVE_NAME}`, `{DATE}`, `{SIZE}`, `{STATUS}`
- `{EPIC_COUNT}`, `{STORY_COUNT}`, `{TASK_COUNT}`, `{TOTAL_COUNT}`
- `{ESTIMATED_TIMELINE}`
- All metric tables (Traceability, Quality, INVEST, Confidence, Platform Coverage)
- Risk assessment section
- Dependencies and blockers
- Issues & recommendations

**Step 3: Generate Traceability Matrix**

**Epic -> Initiative:**
```markdown
| Epic Key | Epic Name | Parent Initiative | Link Type | Status |
|----------|-----------|-------------------|-----------|--------|
| PROJ-110 | Savings Goal Management | PLAN-42 | Relates To | OK |
| PROJ-120 | Deposits & Withdrawals | PLAN-42 | Relates To | OK |
```

**Story -> Epic:**
```markdown
| Story Key | Story Summary | Parent Epic | Link Type | Platform | Component | Status |
|-----------|---------------|-------------|-----------|----------|-----------|--------|
| PROJ-111 | [Android] User creates goal | PROJ-110 | Epic Link | Android | mobile_android | OK |
| PROJ-112 | [iOS] User creates goal | PROJ-110 | Epic Link | iOS | mobile_ios | OK |
```

**Step 4: Calculate Quality Metrics**

**Template Compliance:**
```markdown
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Stories with all 15 sections | 100% | 18/18 (100%) | PASS |
| Tasks with 4 sections | 100% | 10/10 (100%) | PASS |
| Platform prefixes | 100% | 28/28 (100%) | PASS |
| Components assigned | 100% | 28/28 (100%) | PASS |
| Priorities assigned | 100% | 28/28 (100%) | PASS |
| Story points empty | 100% | 28/28 (100%) | PASS |
```

**INVEST Compliance:**
```markdown
| Story Key | Independent | Negotiable | Valuable | Estimable | Small | Testable | Overall |
|-----------|-------------|------------|----------|-----------|-------|----------|---------|
| PROJ-111 | Pass | Pass | Pass | Pass | Pass | Pass | PASS |
| PROJ-112 | Pass | Pass | Pass | Pass | Warn | Pass | REVIEW |

INVEST Summary:
- Passed: 16/18 stories (89%)
- Issues: 2/18 stories (11%)
- Failed: 0/18 stories (0%)
```

**Confidence Scores:**
```markdown
| Issue Key | Type | Confidence | Missing Sections | Status |
|-----------|------|------------|------------------|--------|
| PROJ-111 | Story | 100% | None | OK |
| PROJ-112 | Story | 87% | Design link | REVIEW |
| PROJ-113 | Story | 93% | None | OK |

Confidence Summary:
- 90-100% (Ready): 16/18 (89%)
- 70-89% (Review): 2/18 (11%)
- <70% (Incomplete): 0/18 (0%)

Average Confidence: 95%
```

**Step 5: Platform Coverage Analysis**

```markdown
### Distribution by Platform

| Platform | Stories | Tasks | Total | Percentage |
|----------|---------|-------|-------|------------|
| Android | 6 | 0 | 6 | 21% |
| iOS | 6 | 0 | 6 | 21% |
| Web | 6 | 0 | 6 | 21% |
| Backend | 0 | 10 | 10 | 36% |

### Feature Parity Check

| Feature (Epic) | Android | iOS | Web | Backend | Status |
|----------------|---------|-----|-----|---------|--------|
| Savings Goal Management | PROJ-111 | PROJ-112 | PROJ-113 | PROJ-114 | Complete |
| Deposits & Withdrawals | PROJ-121 | PROJ-122 | PROJ-123 | PROJ-124 | Complete |
| Interest Calculation | - | - | PROJ-133 | PROJ-134 | WARNING: Missing Mobile |
```

**Step 6: Risk Assessment**

Identify risks based on:
- External dependencies (APIs, third-party services)
- Technical complexity (new algorithms, performance requirements)
- Incomplete sections (missing designs, unclear requirements)
- INVEST warnings (stories too large, not testable)

```markdown
### High-Risk Areas

| Risk ID | Category | Description | Impact | Likelihood | Mitigation | Owner |
|---------|----------|-------------|--------|------------|------------|-------|
| R-001 | Dependency | Design approval pending | High | Medium | Schedule review ASAP | PO |
| R-002 | Technical | Interest calculation accuracy | High | Low | Add unit tests, financial review | Backend Team |
| R-003 | Scope | Epic "Analytics" has 12 stories | Medium | High | Split into 2 epics | PO |
```

**Step 7: Dependencies & Blockers**

```markdown
### Dependencies

| Dependency ID | Type | Description | Dependent Issues | Status | Due Date |
|---------------|------|-------------|------------------|--------|----------|
| D-001 | External | Design review | PROJ-111, PROJ-112, PROJ-113 | Pending | 2026-04-20 |
| D-002 | Internal | Backend API endpoints | PROJ-121, PROJ-122, PROJ-123 | In Progress | 2026-04-15 |

### Blockers

| Blocker ID | Description | Blocking Issues | Resolution Plan | ETA |
|------------|-------------|-----------------|-----------------|-----|
| B-001 | Design variants not finalized (4 options exist) | PROJ-111, PROJ-112, PROJ-113 | Schedule design review with design owner | 2026-04-18 |
```

**Step 8: Issues & Recommendations**

List all critical issues and warnings from PO Auto-Review:

```markdown
### Critical Issues

{IF_ANY_EXIST}

**Example:**
- PROJ-125: Missing platform prefix in summary
- PROJ-128: Confidence score 65% (below 90% threshold) - Missing: User Segment Applicability, Analytics Events, design link
- PROJ-130: INVEST validation failed (Not Small - 7+ days estimated)

### Warnings

{IF_ANY_EXIST}

**Example:**
- PROJ-112: Missing design link (87% confidence)
- PROJ-115: No analytics events defined
- PROJ-118: INVEST: Not Small (5-6 days estimated, close to threshold)

### Recommendations

1. **Fix critical issues before Jira creation:**
   - Add platform prefix to PROJ-125
   - Complete missing sections in PROJ-128
   - Split PROJ-130 into 2 smaller stories

2. **Review warnings:**
   - Add design links or mark "Design TBD"
   - Define analytics events or mark "No tracking needed"
   - Consider splitting PROJ-118 if complexity increases

3. **Process improvements:**
   - Schedule design review earlier in next initiative
   - Add spike story for interest calculation validation
```

**Step 9: Quality Gate Sign-off**

```markdown
### Quality Gate

**Status:** {PASSED / FAILED}

**Criteria:**
- [x/ ] All epics have Relates To link to Initiative
- [x/ ] All stories/tasks have Epic Link (or Relates To for XS)
- [x/ ] Platform prefixes on all summaries (100%)
- [x/ ] Template compliance >=90% for all stories
- [x/ ] Confidence score >=90% for all stories
- [x/ ] INVEST validation passed for all stories
- [x/ ] No critical blockers unresolved

### Readiness for Jira Creation

- [ ] Safe to proceed with --create-in-jira
- [ ] Review warnings before creating
- [ ] Fix critical issues before creating

{SELECT_ONE_BASED_ON_AUTO_REVIEW_RESULTS}
```

**Step 10: Save Control Manifest**

```bash
# Save to
[output.breakdown_dir]/{initiative-key}-control-manifest.md

# Example
docs/breakdowns/PLAN-42-control-manifest.md
```

#### When to Generate Control Manifest

**Always generate after PO Auto-Review completes.**

Control Manifest serves as:
1. **Audit trail** - What was created, when, quality level
2. **Traceability** - All links documented
3. **Quality record** - Compliance and validation results
4. **Risk register** - Dependencies, blockers, risks identified
5. **Approval document** - PO sign-off before Jira creation

**Output to user:**
```
Control Manifest Generated

File: docs/breakdowns/PLAN-42-control-manifest.md

Summary:
   Quality Gate: PASSED
   Average Confidence: 95%
   INVEST Compliance: 89% (16/18 passed)
   Template Compliance: 100%

Traceability:
   - 5 epics -> PLAN-42 (Relates To)
   - 18 stories -> epics (Epic Link)
   - 10 tasks -> epics (Epic Link)

Warnings:
   - 2 stories need design links

Readiness: Safe to proceed with --create-in-jira
```

---

## Output & Deliverables

After all 4 phases complete and user approves final quality gate:

### 1. Breakdown Markdown Document

Save to: `[output.breakdown_dir]/[initiative-key]-breakdown.md`

**Structure:**
```markdown
# Initiative Breakdown: [Name]

**Initiative:** [PROJ-10]
**Date:** [2026-04-13]
**Status:** Ready for Development

---

## T-Shirt Size Assessment

**Estimated Size:** M (Medium)

**Reasoning:**
- Feature Complexity: 4 major features identified
- Platform Coverage: All platforms (Android, iOS, Web, Backend)
- Integrations: 2 external (analytics platform, identity verification)
- Technical Risk: Medium (new tables, interest calculation)
- Dependencies: Minimal (internal only)

**Estimated Timeline:** 4-6 weeks

**Recommendation:** Appropriate scope for a single initiative. Proceed with breakdown.

---

## Overview

**Problem:** [1-2 sentences]
**Target Users:** [personas]
**Success Metrics:** [key metrics]

---

## Epic Breakdown

### Epic 1: [Feature Name]

**Business Value:** ...
**Dependencies:** ...

#### Stories/Tasks

##### [Android] User creates savings goal (Story, P0)

**As a** customer
**I want to** create a savings goal
**So that** I can save toward objectives

**Component:** mobile_android
**Priority:** P0
**Story Points:** _To be estimated_

---

**As-Is vs To-Be**
| As-Is | To-Be | Value |
|-------|-------|-------|
| ... | ... | ... |

**Acceptance Criteria:**
- [ ] ...

**Use Cases:**
| # | Actor | Action | Expected Outcome |
|---|-------|--------|------------------|
| 1 | ... | ... | ... |

[... full template ...]

---

##### [BE] Savings goal CRUD API (Task, P0)

**Component:** backend
**Priority:** P0
**Story Points:** _To be estimated_

**[Why]**
Users need to create/edit/delete savings goals. Backend API must exist before mobile/web can implement UI.

**[What]**
Implement RESTful API endpoints:
- POST /api/v1/savings/goals
- GET /api/v1/savings/goals/{id}
- PUT /api/v1/savings/goals/{id}
- DELETE /api/v1/savings/goals/{id}

**[Where]**
- File: `backend/app/controllers/savings_goal_controller` (adapt to your stack)
- Reference: See existing `/api/v1/accounts` endpoints

**[Acceptance Criteria]**
- [ ] All CRUD endpoints respond correctly
- [ ] Input validation works
- [ ] API documentation updated

[... full template ...]

---

### Epic 2: [Next Feature]
...

---

## Execution Timeline (Kanban)

### Phase 1: Backend Foundation (P0 - Blocking)
- PROJ-114: [BE] Database schema (Tech Task, P0)
- PROJ-115: [BE] CRUD API endpoints (Task, P0)
- Timeline: ~1-2 weeks
- Blocks: All frontend stories

### Phase 2: Platform Implementation (P0)
- PROJ-111: [Android] User creates goal (Story, P0)
- PROJ-112: [iOS] User creates goal (Story, P0)
- Dependencies: Requires Phase 1
- Timeline: ~2-3 weeks

[Additional phases as needed...]

---

## Dependencies & Risks
...
```

### 2. Control Manifest

Saved to `[output.breakdown_dir]/[initiative-key]-control-manifest.md` (see section 13).

### 3. Jira Issues (if `--create-in-jira`)

- Epics created in the delivery project, linked to the initiative
- Stories and tasks created in the delivery project, linked to epics
- All fields populated from templates
- All constraints from `config.yml` respected (priority, ASCII, components, etc.)

### Console Output (Summary)

```
Initiative Breakdown Complete: PROJ-10 "High-Yield Savings"

T-Shirt Size: M (Medium)
   Timeline: 4-6 weeks
   Status: Appropriate scope for a single initiative

Summary:
   Epics: 5 (feature-based)
   Stories: 18 (with platform prefixes)
   Tasks: 10
   Tech Tasks: 3
   Total: 31 issues

Breakdown saved:
   docs/breakdowns/PROJ-10-breakdown.md

Jira Structure Created:

Epic: PROJ-110 "Savings Goal Management"
  +- PROJ-111: [Android] User creates savings goal (Story, P0) -> Component: mobile_android
  +- PROJ-112: [iOS] User creates savings goal (Story, P0) -> Component: mobile_ios
  +- PROJ-113: [Web] Savings dashboard (Story, P0) -> Component: web
  +- PROJ-114: [BE] Savings CRUD API (Task, P0) -> Component: backend
  \- PROJ-115: [BE] Database schema (Tech Task, P0) -> Component: backend

Epic: PROJ-120 "Deposits & Withdrawals"
  +- PROJ-121: [Android] User deposits to goal (Story, P0) -> Component: mobile_android
  +- PROJ-122: [iOS] User deposits to goal (Story, P0) -> Component: mobile_ios
  \- ...

... [3 more epics]

View in Jira:
   https://your-jira.example.com/browse/PROJ-10
```

---

## Quality Checks

**NOTE:** Quality checks are now **automated** via **PO Auto-Review** (section 11).

The Auto-Review process automatically validates:
- Platform prefixes in all summaries
- Complete template sections (all story sections, 4 for Tasks)
- INVEST criteria compliance
- Confidence scoring (90%+ threshold)
- Epic/Parent link correctness
- Component assignment
- Priority assignment
- Story points NOT estimated

**Before creating Jira issues:**
1. Run **PO Auto-Review** (automatic in process step 11)
2. Review Auto-Review output summary
3. Fix any critical issues or warnings flagged
4. Proceed with `--create-in-jira` only if **Quality Gate: PASSED**

See section 11 for detailed Auto-Review checklist and thresholds.

---

## Examples

### Example 1: Feature-Based Breakdown

**Initiative:** "Transaction History Improvements"

**Epics (feature-based):**
1. **Advanced Filtering** - Filter by date, amount, category
2. **Search Functionality** - Full-text search across transactions
3. **Export & Reporting** - Export to CSV, PDF reports
4. **Performance Optimization** - Handle 10K+ transactions

Each epic -> Stories for Android, iOS, Web + Backend tasks

### Example 2: Story with Platform Prefix

**Summary:** `[Android] User filters transactions by date range`

**Component:** mobile_android
**Priority:** P0
**Story Points:** _To be estimated_

**As a** mobile user
**I want to** filter my transaction history by date range
**So that** I can review specific time periods

**As-Is vs To-Be:**
| As-Is | To-Be | Value |
|-------|-------|-------|
| User sees all transactions (no filter) | User can select date range and see filtered results | Easier to track spending in specific periods |

**Acceptance Criteria:**
- [ ] User taps "Filter" button, sees date range picker
- [ ] User selects start date and end date
- [ ] Transaction list updates to show only transactions in range
- [ ] Filter persists across app restarts

**Use Cases:**
| # | Actor | Action | Expected Outcome |
|---|-------|--------|------------------|
| 1 | User | Opens transaction history | Sees all transactions + filter button |
| 2 | User | Taps filter, selects last 7 days | Sees only transactions from last week |
| 3 | User | Clears filter | Sees all transactions again |

[... rest of template sections ...]

---

## Integration with Other Skills

**Workflow:**
```bash
# 1. Generate PRD
/product-spec "Savings Product"

# 2. Break down initiative
/initiative-breakdown "Savings Product" \
  --prd="docs/specs/savings-product-prd.md" \
  --create-in-jira

# 3. Optional: add analytics tracking spec (if your team has such a skill)
# 4. Optional: publish the breakdown to your wiki (if your team has a
#    Confluence/wiki publishing skill)
```

---

## Integration with Memory / Knowledge Base

The `product-brain-loader` agent loads files from `config.yml`'s `product.context_files`. Recommended structure:

```
memory/
  product/
    context.md                # Product vision, priorities, constraints
    product-definition.md     # What the product is and is not
    requirements-patterns.md  # Reusable story/error patterns
  patterns/
    tshirt-sizing-guide.md
    user-story-format.md
    jira-api-best-practices.md
  templates/
    story-template.md
    task-template.md
    epic-template.md
```

The breakdown will only be as good as this knowledge base. Invest in it.

---

## Patterns This Skill Uses

Top-level (shared across the plugin):
- `${CLAUDE_PLUGIN_ROOT}/patterns/initiative-breakdown-pattern.md` - why feature-based over platform-based
- `${CLAUDE_PLUGIN_ROOT}/patterns/tshirt-sizing-guide.md` - sizing framework with examples

Skill-local (specific to initiative-breakdown):
- `${CLAUDE_PLUGIN_ROOT}/skills/initiative-breakdown/patterns/requirements-patterns.md` - reusable story archetypes
- `${CLAUDE_PLUGIN_ROOT}/skills/initiative-breakdown/patterns/ai-personas.md` - agent persona design for consistency

---

## Typical Session

```
$ /initiative-breakdown PROJ-42 --create-in-jira

[Phase 1] Loading product context...
  - context.md loaded
  - requirements-patterns.md loaded
  - Initiative PROJ-42 fetched from Jira
  Approve context? y

[Phase 2] Sizing...
  Size: M (3 weeks, 2 epics, 8 stories)
  Recommendation: GO
  Approve sizing? y

[Phase 3] Generating breakdown...
  - Epic 1: "User onboarding flow" (4 stories)
  - Epic 2: "Account verification" (4 stories, 2 BE tasks)
  Preview ready. Approve breakdown? y

[Phase 4] Quality review...
  Overall quality: 8.2/10
  INVEST passed: 8/8 stories
  Recommendation: GO
  Create in Jira? y

Created:
  - 2 Epics
  - 8 Stories
  - 2 Backend tasks

Files written:
  docs/breakdowns/PROJ-42-breakdown.md
  docs/breakdowns/PROJ-42-control-manifest.md
```

---

## Why Multi-Agent Orchestration?

### What Changed vs a Single-Pass Skill?

**Before (single-pass):**
- Single monolithic skill with embedded process
- All logic executed sequentially by one agent
- No explicit phases or approval gates
- Quality checks were manual/optional
- Output quality varied

**After (orchestrated):**
- **4 specialized agents** with domain expertise
- **Explicit phases** with clear handoffs
- **Approval gates** between phases
- **Automated quality validation** (INVEST, PO Auto-Review)
- **Control manifest** for audit trail
- **Consistent production-quality output**

### The 4 Specialized Agents

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **product-brain-loader** | Context specialist | Initiative key/PRD | Product Brain context summary, applicable patterns |
| **sizing-validator** | Scope specialist | Initiative details | T-shirt size, GO/NO-GO decision, risk assessment |
| **breakdown-generator** | Decomposition specialist | Size + context | Feature-based epics, platform-specific stories/tasks |
| **quality-reviewer** | Quality assurance specialist | Breakdown | INVEST validation, control manifest, final recommendation |

### Benefits

**Quality:**
- Every story validated against INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- Automated template compliance checks
- Product Brain patterns auto-applied (errors, analytics, NFRs)
- Control manifest provides comprehensive audit trail

**Consistency:**
- Same 4-phase process every time
- Same quality checks every time
- Same output structure every time
- No steps skipped or forgotten

**Transparency:**
- Approval gates show progress
- User controls phase transitions
- Quality issues flagged before Jira creation
- Clear GO/NO-GO decisions with reasoning

**Efficiency:**
- Agents run in parallel where possible
- Context loaded once, reused across phases
- Auto-fill reduces PO review time
- Fewer iterations needed (quality gates catch issues early)

### When to Use This vs. Simple Breakdown?

**Use the orchestrated breakdown when:**
- Production features with user impact
- Complex initiatives (M/L size, 20+ stories)
- Compliance-sensitive features (payments, auth, data privacy)
- Cross-team initiatives (multiple stakeholders)
- You need audit trail / control manifest

**Use a simpler approach when:**
- Quick prototype/POC (not production-ready)
- Very small XS initiative (<5 stories, low risk)
- Time-sensitive urgent fix (accept lower quality, fix later)
- Personal/experimental work (no formal process needed)

---

## Troubleshooting

### Agent Not Loading

**Issue:** "Agent 'product-brain-loader' not found"

**Fix:** Agents are defined in the plugin's `agents/` directory. Check that all 4 agent files exist:
- `${CLAUDE_PLUGIN_ROOT}/agents/product-brain-loader.md`
- `${CLAUDE_PLUGIN_ROOT}/agents/sizing-validator.md`
- `${CLAUDE_PLUGIN_ROOT}/agents/breakdown-generator.md`
- `${CLAUDE_PLUGIN_ROOT}/agents/quality-reviewer.md`

### Quality Gate Failing

**Issue:** "Quality Gate: FAILED - Critical issues found"

**Fix:** Review the critical issues listed in quality review output. Common issues:
- Missing platform prefixes -> Add `[Android]`, `[iOS]`, etc. (from your config)
- INVEST score <5.0 -> Story too large (split it) or not testable (add specific AC)
- Template compliance <90% -> Fill missing sections (use Product Brain patterns)

### Breakdown Taking Too Long

**Issue:** Agents running for >5 minutes each

**Possible causes:**
- Very large initiative (L/XL size) -> Consider decomposing into smaller initiatives first
- Complex Product Brain patterns -> Normal for first run, subsequent runs use cache
- Agent getting stuck -> Check agent logs, may need to interrupt and restart phase

---

## Notes

- **Always feature-based epics**, never platform-based
- **Platform prefix is mandatory** in all story/task summaries
- **Use the full configured templates** - don't skip sections
- **Don't estimate story points** - leave for dev team
- **Assign components** based on platform
- Review breakdown in dry-run before creating in Jira

---

## Why This Exists

Manual initiative breakdown takes hours, relies on the PO's memory of team conventions, and produces inconsistent output. This skill encodes the conventions into config and agents, then runs a deterministic pipeline with human approval at each critical decision point.

The output quality depends on:
1. Quality of your `config.yml`
2. Quality of your `memory/` knowledge base
3. Quality of your story and task templates

Invest in these once. Reuse across every initiative.

---

## See Also

- **Product Brain files:** your `product.context_files` (e.g. `memory/product/`, `memory/patterns/`)
- **Templates:** `templates.story`, `templates.task`, `templates.epic` from `config.yml`
- **Agent definitions:** `${CLAUDE_PLUGIN_ROOT}/agents/`
- **Related skills:** `/product-spec` (PRD generation); your Jira skill/plugin for issue operations
