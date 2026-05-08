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

constraints:
  # Team guardrails the breakdown must respect.
  # Example: "No dedicated designers - don't assume design resources"
  - "Describe any hard rules here"
```

The skill reads this config at every invocation and applies it to agent prompts.

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
- Story/Task -> Epic: **Epic Link** (customfield varies per instance)
- Story/Task -> Initiative (only for XS initiatives with no Epic): **Relates To**

### 4. Config-Driven Constraints

All team-specific rules (ASCII-only, no sprint references, no budget features, etc.) live in `config.yml` under `constraints`. Agents read them and enforce them automatically.

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

Each phase is handled by a specialized agent (see `agents/` directory). Between phases, a human approves or redirects.

---

## Phase 1: Context Loading

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
Product Context Loaded

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
       3. Identify high-risk areas
       4. Output sizing decision

     Context from Phase 1: [pass initiative details]"
   ```

2. Agent outputs:
   - T-shirt size (XS/S/M/L/XL)
   - Reasoning
   - Estimated timeline
   - Epic and story count estimates
   - Recommendation: GO / NO-GO / NEEDS DECOMPOSITION
   - Risk areas

### Approval Gate 2

```
T-Shirt Size Assessment

Size: [S/M/L/XL]
Timeline: [weeks]
Epic Count: [N]
Story Count: [N]

Recommendation: [GO / NO-GO / NEEDS DECOMPOSITION]

Reasoning: [Summary from agent]
High-Risk Areas: [Flagged risks]

Proceed to Phase 3: Breakdown? [Y/n/adjust]
```

**If XL:** stop. Ask user to decompose into 2-4 smaller initiatives first. Show agent's suggested vertical slices.

**If XS:** ask user to confirm skipping Epic layer (stories link directly to Initiative).

If "No": ask what to adjust, re-run Phase 2.
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
       2. Generate N feature-based epics with:
          description, user value, scope, dependencies, success criteria
       3. For each epic, generate platform-specific stories and tasks:
          - Use the story and task templates from config.yml
          - Apply platform prefixes from config.yml
          - Assign components and priorities
       4. Apply patterns loaded in Phase 1 (errors, analytics, NFRs)
       5. Respect all constraints from config.yml
       6. Output: full markdown breakdown with all epics and stories

     Size: [from Phase 2]
     Epics needed: [from Phase 2]
     Stories needed: [from Phase 2]"
   ```

2. Agent outputs:
   - N epics with complete descriptions
   - M stories using the configured story template
   - K tasks using the configured task template
   - Platform distribution
   - High-risk stories flagged
   - Missing information noted (design TBD, API spec needed, etc.)

### Approval Gate 3

```
Breakdown Generated

Structure:
- N Epics (feature-based)
- M Stories (platform-specific)
- K Tasks

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

If "revise": ask what to change (epic structure, story scope, priorities), re-run Phase 3.
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
          Score each criterion (pass 1.0, partial 0.5, fail 0.0)
          Overall INVEST score must be >= 5.0
       2. Run PO auto-review:
          - Template completeness
          - Consistency (naming, priorities, platforms)
          - Constraint compliance (from config.yml)
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

     Breakdown from Phase 3: [pass full breakdown]"
   ```

2. Agent outputs:
   - INVEST validation results per story
   - PO auto-review results
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
- Stories complete: [N/M] ([%])
- Tasks complete: [K/L] ([%])

Critical Issues: [List of MUST-FIX]
Warnings: [List of should-review]

Control Manifest: docs/breakdowns/[key]-control-manifest.md

Final Recommendation: [GO / GO WITH REVISIONS / NO-GO]

Proceed with Jira creation? [Y/n/fix-issues]
```

**If GO:**
- User approves -> create issues in Jira (if `--create-in-jira`)
- Save breakdown markdown to `docs/breakdowns/[key]-breakdown.md`
- Save control manifest to `docs/breakdowns/[key]-control-manifest.md`

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

## Output Artifacts

The skill produces three artifacts:

### 1. Breakdown Markdown (`docs/breakdowns/[key]-breakdown.md`)

Full hierarchy: Initiative -> Epics -> Stories -> Tasks. Each item uses the template configured in `config.yml`.

### 2. Control Manifest (`docs/breakdowns/[key]-control-manifest.md`)

Quality audit with:
- Traceability matrix (which story implements which requirement)
- INVEST scores per story
- Platform coverage gaps
- Risk assessment
- Dependencies and blockers
- GO / NO-GO decision with rationale

See `${CLAUDE_PLUGIN_ROOT}/skills/initiative-breakdown/templates/control-manifest-template.md`.

### 3. Jira Issues (if `--create-in-jira`)

- Epics created under the initiative project, linked to the initiative
- Stories and tasks created under the delivery project, linked to epics
- All fields populated from templates
- All constraints from `config.yml` respected (priority, ASCII, components, etc.)

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

## Why This Exists

Manual initiative breakdown takes hours, relies on the PO's memory of team conventions, and produces inconsistent output. This skill encodes the conventions into config and agents, then runs a deterministic pipeline with human approval at each critical decision point.

The output quality depends on:
1. Quality of your `config.yml`
2. Quality of your `memory/` knowledge base
3. Quality of your story and task templates

Invest in these once. Reuse across every initiative.
