# Initiative Breakdown Skill

Automatically breaks down initiatives into **feature-based epics**, then into **platform-specific stories and tasks** using configurable templates.

**Key features:**
- Feature-based epic breakdown (not platform-based)
- Platform prefixes configurable via `config.yml`
- Configurable story and task templates
- Component assignment based on platform
- No story point estimation (left to dev team)
- 4 specialized agents with approval gates between phases

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

1. **Analyzes** initiative scope (from Jira or PRD)
2. **Determines T-shirt size** (XS/S/M/L/XL) and validates scope
   - XS -> recommends creating Epic only
   - XL -> recommends decomposition into smaller initiatives
   - S/M/L -> proceeds with breakdown
3. **Identifies** 3-7 **feature-based** epics (not platform-based)
4. **Breaks down** each epic into platform-specific stories and tasks using prefixes from `config.yml`
5. **Generates** full templates (story template, task template)
6. **Assigns** Jira components (configurable)
7. **Assigns** priorities (P0/P1/P2 or your scheme)
8. **Does NOT estimate** story points - left for dev team
9. **Creates** Jira structure (optional, via `--create-in-jira`)

## Configuration

Before first use, create `config.yml` next to `SKILL.md`. See the "Setup" section of [SKILL.md](SKILL.md) for the full schema.

## Output

### Markdown Document

Saved to `docs/breakdowns/[initiative-key]-breakdown.md`

Contains:
- Initiative overview
- Epic breakdown with descriptions
- All stories / tasks with acceptance criteria
- Sprint allocation (if applicable)
- Dependencies and risks
- Jira links

### Control Manifest

Saved to `docs/breakdowns/[initiative-key]-control-manifest.md`

Quality audit with traceability, INVEST scores, platform coverage, risk assessment, GO/NO-GO recommendation.

### Jira Structure

If `--create-in-jira` flag used:

```
Initiative (parent)
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
- `patterns/` - reference patterns used by the breakdown
- `templates/` - control manifest template
