# Rules

`.claude/rules/` is Claude Code's second instruction surface next to `CLAUDE.md`:
small markdown files, each holding **one constraint that must hold**. A rule without
frontmatter loads every session; a rule with a `paths:` frontmatter block loads only
when Claude touches a matching file — so heavy, topic-specific guidance stays out of
the context window until it is actually needed.

This directory ships **example rules** distilled from a real product-team setup, plus
the method for writing your own (see the bundled `writing-claude-code-rules` skill).

## Why this beats one giant CLAUDE.md

- **CLAUDE.md** = the map: what the project is, global expectations, an index of rules.
- **rules/** = the constraints: modular, reviewable one by one, path-scoped where possible.
- **hooks/** = the guarantees: things that must never slip (see `../hooks/`).

A 500-line CLAUDE.md gets skimmed; ten 20-line rules, each loading exactly when
relevant, get followed.

## Install

Copy the examples you want into your project and edit them to match your team:

```bash
mkdir -p .claude/rules
cp rules/examples/*.md .claude/rules/
```

Then add a short index table to your `CLAUDE.md` so Claude knows the rules exist:

```markdown
Detailed rules live in `.claude/rules/`:

| Rule file | What it governs |
|-----------|-----------------|
| `team-process.md` | Workflow method, roles, resource constraints |
| `issue-tracker.md` | API hygiene, priority defaults, scope confirmation |
| `api-access.md` | Credential lookup order, fail-fast on auth errors |
| `doc-output.md`  | Output standards for docs (path-scoped to docs/) |
```

## Example rules

| File | Type | Demonstrates |
|------|------|--------------|
| `examples/team-process.md` | unconditional | encoding hard process constraints so Claude never proposes ceremonies/resources your team doesn't have |
| `examples/issue-tracker.md` | unconditional | API hygiene + defaults + a confirm-before-create gate for issue trackers |
| `examples/api-access.md` | unconditional | credential lookup order and a fail-fast policy for flaky internal APIs |
| `examples/doc-output.md` | `paths:`-scoped | output standards that load only when writing documentation files |

Each example is deliberately short. A rule that needs 200 lines is usually a skill
(procedure) or a hook (guarantee) in disguise — see the decision table in
`skills/writing-claude-code-rules/SKILL.md`.
