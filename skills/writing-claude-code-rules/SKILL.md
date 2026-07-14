---
name: writing-claude-code-rules
description: Use when setting up or fixing Claude Code project instructions — deciding what belongs in CLAUDE.md vs .claude/rules/, scoping rules to file paths, or diagnosing why rules get ignored or bloat the context window.
---

# Writing Claude Code Rules

## Overview

Claude Code has two complementary instruction surfaces; use each for what it's good at:

- **`.claude/rules/` (scoped with `paths:`)** — *deterministic in application*: loads only
  when Claude touches matching files, so it prevents **local** mistakes without bloating context.
- **`CLAUDE.md`** — *deterministic in expectation*: always loaded; sets **global** understanding
  and signposts which rules exist.

Rules and CLAUDE.md are **guidance, not enforcement**. For guarantees, use hooks/settings.

## The mechanisms (native — verify against your Claude Code version)

| Surface | When it loads | Use for |
|---|---|---|
| `CLAUDE.md` (root) | always, in full | global expectations + the rules index |
| `.claude/rules/*.md` (no frontmatter) | always | genuinely universal constraints |
| `.claude/rules/*.md` with `paths:` | only when a matching file is read | topic/path-specific guidance |
| nested `subdir/CLAUDE.md` | on demand in that subtree | area-specific instructions |
| `@path` import in CLAUDE.md | always, expanded in full (NOT lazy) | a file you always need |
| skill (`.claude/skills/`) | on demand via description / `/name` | multi-step procedures |
| hooks / settings | enforced by the harness | hard guarantees (secrets, formatting) |

Scoped-rule syntax:

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "**/*.test.ts"
---
# Rule title
Instructions here...
```

## Decide where a rule goes

- Universal and must always hold (style, security, privacy)? → unconditional `.claude/rules/` file.
- Only relevant to certain files/areas? → scoped rule with `paths:` (or a nested `CLAUDE.md`).
- A multi-step procedure / workflow? → a **skill**, not a rule.
- Must be **guaranteed**, not merely encouraged? → a **hook/setting**, not a rule.
- Global "what kind of project is this" + an index of the above? → `CLAUDE.md`.

## Agent vs Skill vs Rule vs Hook — which to create

Same instruction can take four forms. Pick by *what it is*, and name accordingly:

| Form | It is… | Naming | Example |
|------|--------|--------|---------|
| **Rule** (`.claude/rules/`) | a constraint that must hold | what must be true | "API handlers validate input" |
| **Skill** (`.claude/skills/`) | an activity / discipline (multi-step how-to) | the *activity*, verb-first | `writing-claude-code-rules`, `initiative-breakdown` |
| **Agent** (`.claude/agents/`) | a role / specialist that does work | *who* would do it | `backend-auditor`, `quality-reviewer` |
| **Hook / setting** | a guarantee enforced by the harness | n/a (config) | secret-guard, auto-format |

Quick test:
- "What must be true?" → **rule**. "How do I do X?" → **skill**. "Who would do this?" → **agent**. "This must never slip" → **hook**.
- Agent vs skill: an agent is a *persona that could own multiple skills*; a skill is *one activity*. If you'd say "ask the backend specialist" → agent. If you'd say "follow the breakdown procedure" → skill.
- Don't duplicate: an agent references skills; a skill references rules. Same name across forms = confusion — keep them distinct.

## Why rules get ignored (and the fix)

| Symptom | Cause | Fix |
|---|---|---|
| Context bloat, rules "drift" | everything is unconditional | move topic/path rules to `paths:`-scoped files |
| Obeys the constraint but approaches the task wrong | only scoped rules, no global framing | add the expectation + index to `CLAUDE.md` |
| Doesn't know a rule exists | not signposted | index rules in `CLAUDE.md` by task type |
| Key file (README/runbook/design) ignored | not referenced | `@import` it, or reference it from `CLAUDE.md` |
| "Ignored" under pressure | it's guidance only | enforce it with a hook/setting |

## Good vs bad

- ❌ Unconditional: "When editing notebooks, restart kernel and clear outputs." — topic-specific, bloats every session.
- ✅ Scoped: same text in `.claude/rules/notebooks.md` with `paths: ["notebooks/**"]`.
- ❌ `CLAUDE.md`: 300 lines of a step-by-step ML workflow.
- ✅ `CLAUDE.md`: "FastAPI service; tests in `tests/`. For notebooks see the notebooks rule; for API changes see the api rule." — index + expectation.

## Common mistakes

- Treating `@import` as lazy-loading — it loads in full at launch. For lazy, use a `paths:`-scoped rule.
- Putting workflows in rules — workflows belong in skills.
- Expecting `CLAUDE.md` to *guarantee* behavior — guarantees come from hooks/settings.
- One giant `CLAUDE.md` — split universal vs scoped; keep `CLAUDE.md` as the map, not the dumping ground.

## Quick checklist

- [ ] Universal constraints → short unconditional rules.
- [ ] Topic/path constraints → `paths:`-scoped rules.
- [ ] Workflows → skills.
- [ ] Guarantees → hooks/settings.
- [ ] `CLAUDE.md` = global expectations + index to the above.

Source: J. Parreño García, "How Claude Code rules actually work"; mechanism cross-checked against Claude Code memory docs (2026-06-16).
