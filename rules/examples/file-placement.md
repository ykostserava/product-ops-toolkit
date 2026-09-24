# Structure and file placement (hard rules)

Keep the repo tidy: every new file goes to its folder, never loose in the root.
Automation depends on some paths; they are frozen below.

**Top-level layout:**
- `src/` - application code; `tests/` - unit tests
- `scripts/` - all `.py` / `.sh` tooling (briefings, audits, data pulls)
- `memory/` - knowledge base (product context, templates, patterns, decisions)
- `data/` - raw datasets (analytics exports, store reviews)
- `docs/` - ALL documentation (routing table below)
- `prototypes/` - HTML/UI prototypes
- `briefings/` `audits/` - automation output (gitignored, regenerated)
- `archive/` - retired material
- `.claude/skills/` - custom workflows; `.claude/rules/` - always-loaded rules

**Where new files go - route by type, do NOT drop in root:**

| New artifact | Destination |
|--------------|-------------|
| PRD / spec / brief | `docs/specs/` |
| ADR (one decision per file) | `docs/decisions/` |
| Initiative draft, ticket draft, changeset | `docs/initiatives/` |
| Research, competitive analysis | `docs/research/` |
| Vision / strategy | `docs/strategy/` |
| Roadmap | `docs/roadmap/` |
| User stories / backlog | `docs/backlog/` |
| Epic/story breakdown | `docs/breakdowns/` |
| Slides / speaker notes | `docs/slides/` |
| Setup / integration guides | `docs/setup/` |
| Planning, QA strategy, sizing | `docs/planning/` |
| Session handoff | `briefings/handoffs/` (gitignored, survives the session) |
| Analytics docs | `docs/analytics/` |
| Architecture analysis | `docs/architecture/` |
| Raw data export (json/csv) | `data/` |
| Script (`.py`/`.sh`) | `scripts/` |
| HTML prototype | `prototypes/` |

**Invariants:**
- **Root = config-only.** Allowed in root: `CLAUDE.md`, `README.md`,
  `pyproject.toml`, dotfiles. Anything else needs a home above.
- **No loose files in `docs/` root** either - only the index lives there.
- **Temp/API dumps are not artifacts** - API response dumps (`tmp_*`,
  `resp_*`) are throwaway; delete, don't keep.
- **Frozen paths** (automation depends on them - don't move/rename without
  updating callers): `briefings/`, `audits/`, `scripts/`, `memory/`, and any
  script a scheduler calls by path.

When a `STRUCTURE.md` (or similar source of truth) exists, this file
duplicates its routing on purpose so it is always loaded - change both in the
same commit.
