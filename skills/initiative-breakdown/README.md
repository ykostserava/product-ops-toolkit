# Initiative Breakdown Skill

Automatically breaks down initiatives into **feature-based epics**, then into **platform-specific stories and tasks** using configurable templates.

**Key features:**
- Feature-based epic breakdown (not platform-based)
- Platform prefixes configurable via `config.yml`
- Configurable story and task templates (full multi-section format)
- Component assignment based on platform
- No story point estimation (left to dev team)
- 4 specialized agents with approval gates between phases
- Confidence auto-fill from your Product Brain patterns
- INVEST scoring, PO auto-review, and optional 8-persona AI review
- Control manifest as a quality audit trail

## Quick Start

```bash
# Basic usage - analyze existing initiative
/initiative-breakdown PROJ-10

# Create Jira structure automatically
/initiative-breakdown PROJ-10 --create-in-jira

# From PRD file
/initiative-breakdown "High-Yield Savings" --prd="docs/specs/savings-prd.md" --create-in-jira

# Preview before creating
/initiative-breakdown PROJ-10 --dry-run
```

## What It Does

1. **Loads** your Product Brain context (files listed in `config.yml`)
2. **Analyzes** initiative scope (from Jira or PRD)
3. **Determines T-shirt size** (XS/S/M/L/XL) and validates scope
   - XS -> skips the Epic layer, links stories directly to the Initiative
   - XL -> stops and recommends decomposition into smaller initiatives
   - S/M/L -> proceeds with breakdown
   - Optionally validates scope against your availability/visibility docs
4. **Identifies** 3-7 **feature-based** epics (not platform-based)
5. **Breaks down** each epic into platform-specific stories and tasks using prefixes from `config.yml`
6. **Generates** full templates (story template, task template) - every story is a complete standalone document
7. **Auto-fills** missing sections (errors, edge cases, NFRs, analytics) from your requirements patterns
8. **Assigns** Jira components and priorities (P0/P1/P2 or your scheme)
9. **Does NOT estimate** story points - left for dev team
10. **Validates** quality: INVEST scoring, confidence scores, PO auto-review, optional AI personas review
11. **Generates** a control manifest (traceability, quality metrics, risks, GO/NO-GO)
12. **Creates** Jira structure (optional, via `--create-in-jira`)

## Configuration

Before first use, create `config.yml` next to `SKILL.md`. See the "Setup" section of [SKILL.md](SKILL.md) for the full schema (product context files, workflow, Jira projects, platform prefixes, templates, constraints).

## Output

### Markdown Document

Saved to `[output.breakdown_dir]/[initiative-key]-breakdown.md`

Contains:
- Initiative overview and T-shirt size assessment
- Epic breakdown with descriptions
- All stories / tasks with full template sections
- Execution order (Kanban) or sprint allocation (Scrum)
- Dependencies and risks
- Jira links

### Control Manifest

Saved to `[output.breakdown_dir]/[initiative-key]-control-manifest.md`

Quality audit with traceability matrix, INVEST scores, confidence scores, platform coverage, risk assessment, dependencies/blockers, and a GO/NO-GO recommendation.

### Jira Structure

If `--create-in-jira` flag used:

```
Initiative (parent, in the planning project)
+-- Epic 1
|   +-- Story 1.1
|   +-- Story 1.2
|   \-- Task 1.3
\-- Epic 2
    +-- Story 2.1
    \-- Tech Task 2.2
```

## Issue Types & Platform Prefixes

Platforms are configured in `config.yml`. Example:

| Type | Usage | Prefix Examples |
|------|-------|-----------------|
| **Story** | User-facing features | `[Android] User creates goal`, `[iOS] Transaction filtering`, `[Web] Account switching` |
| **Task** | Backend, infra, analytics | `[BE] API endpoints`, `[Analytics] Event definitions` |
| **Tech Task** | Architecture, POCs, DB design | `[BE] Database schema design`, `[BE] Caching strategy POC` |

**CRITICAL:** all summaries must carry a platform prefix.

## Quality Gates

The final quality gate combines:

- **PO Auto-Review** - structure checks: prefixes, template completeness, links, components, priorities, empty story points
- **INVEST validation** - each story scored 0-6 across Independent/Negotiable/Valuable/Estimable/Small/Testable; <5.0 blocks creation
- **Confidence scores** - sections filled vs template; <90% flags a story for review
- **AI Personas review (optional)** - 8 domain reviewers (BA, Requirements Engineer, Architect, QA, PM, UX, Compliance, DevOps) validate content quality

Issues are flagged with fixes offered before anything is created in Jira.

## Options

| Flag | Description |
|------|-------------|
| `--create-in-jira` | Create all issues in Jira automatically |
| `--dry-run` | Preview without creating issues |
| `--prd="path"` | Use PRD file as input |

## Tips

- Always use `--dry-run` first to review
- Review dependencies before creating in Jira
- Link to designs / PRDs in epic descriptions
- Update breakdown as scope changes
- Invest in your Product Brain files - auto-fill quality depends on them

## Estimated Time Saved

Manual breakdown of a medium-sized initiative (5 epics, ~25 stories): **2-4 hours** including template filling.

With this skill: **10-15 minutes** + review time.

Time saved scales with frequency - a PO doing 4-5 breakdowns per month recovers days of work per quarter.

## Related Skills

- `/product-spec` - create PRD first
- Jira / Confluence plugins - for reading and writing to those systems

## See Also

- [SKILL.md](SKILL.md) - full orchestration logic
- `agents/` - the 4 specialized agent definitions
- `patterns/` - reference patterns used by the breakdown (including AI personas)
- `templates/` - control manifest template
