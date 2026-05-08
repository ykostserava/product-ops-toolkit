# Memory Scaffold

A starter knowledge base structure for product-ops work. The skills and agents in this toolkit assume a `memory/` directory shaped roughly like this — drop it into your project root, fill it in over time, and reference it from your top-level `CLAUDE.md` (or equivalent).

This scaffold is intentionally **empty**. It exists to give you a consistent place to put context so Claude (and your teammates) can find it on day one.

## Structure

```
memory/
+-- product/          # Vision, priorities, current scope, north-star metrics
+-- patterns/         # Reusable conventions: user-story format, error handling, analytics naming, NFRs
+-- templates/        # Per-team variants of PRD / story / task templates (override the toolkit defaults)
+-- decisions/        # ADR-style records of "why we chose X over Y" — dated, append-only
+-- feedback/         # Things Claude (or the team) was told to do / not do, with rationale
+-- stakeholders/     # Who owns what, escalation paths, communication cadence per role
\-- MEMORY.md         # Index file — one line per memory file, keeps the directory navigable
```

## How skills use this directory

| Skill / Agent | Reads from | Why |
|---|---|---|
| `product-spec` | `product/context.md`, `templates/prd-template.md`, `patterns/user-story-format.md` | To produce a PRD that matches your team's voice and constraints |
| `initiative-breakdown` | `product/context.md`, `patterns/initiative-breakdown-pattern.md`, `templates/story-template.md` | To break initiatives into epics/stories using your conventions |
| `product-brain-loader` agent | All of the above + `decisions/`, `stakeholders/` | To assemble full context before Phase 2+ runs |
| `quality-reviewer` agent | `patterns/`, `feedback/` | To enforce team conventions during INVEST validation |

## Seeding strategy

Don't try to fill everything at once. A useful order:

1. **`product/context.md`** — one page: what is this product, who uses it, what are the top 3 priorities this quarter
2. **`patterns/user-story-format.md`** — copy from `templates/user-story-template.md` in this toolkit, adapt to your platform stack
3. **`templates/`** — clone the toolkit's `prd-template.md` / `story-template.md` / `task-template.md` here only when you need to override (the skills will fall back to toolkit defaults otherwise)
4. **`decisions/`** — start logging "why we chose X" the moment you make a decision worth defending later
5. **`stakeholders/`** — populate when handoffs or escalations actually happen, not before
6. **`feedback/`** — start empty; fill it as you correct or confirm Claude's behavior

## MEMORY.md as an index

Keep `MEMORY.md` short — one line per file, under 200 lines total. It is loaded into context every conversation, so the index needs to fit. Example entries:

```
- [Product context](product/context.md) — what we sell, who buys, this-quarter priorities
- [User story format](patterns/user-story-format.md) — Given-When-Then, AC checklist, platform tagging rules
- [Decision: kanban over scrum](decisions/2026-Q1-kanban.md) — flow over cadence, see retro 2026-01-15
- [Feedback: no sprint references](feedback/no-sprints.md) — team is kanban-only, never use sprint vocab
```

## What NOT to put in memory

- Anything derivable from current code (architecture, file paths) — Claude can read the repo
- Git history — `git log` is authoritative
- Conversation-only state ("we just decided X this turn") — that lives in the chat / plan, not memory
- Secrets, tokens, personal data — these belong in `.env`, not here

---

The directories below are created with `.gitkeep` placeholders so the structure survives a fresh clone. Replace them with your actual content as you go.
