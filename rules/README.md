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
| `file-placement.md` | Where new files go; frozen paths |
| `audit-panel.md` | Three blind auditors before code on a new scheme |
| `mechanics-over-promises.md` | Rules need tests/hooks/gates, not prose |
```

## Example rules

| File | Type | Demonstrates |
|------|------|--------------|
| `examples/team-process.md` | unconditional | encoding hard process constraints so Claude never proposes ceremonies/resources your team doesn't have |
| `examples/issue-tracker.md` | unconditional | API hygiene + defaults + a confirm-before-create gate for issue trackers |
| `examples/api-access.md` | unconditional | credential lookup order and a fail-fast policy for flaky internal APIs |
| `examples/doc-output.md` | `paths:`-scoped | output standards that load only when writing documentation files |
| `examples/file-placement.md` | unconditional | a routing table for new files so nothing lands loose in the root, plus the frozen paths automation depends on |
| `examples/audit-panel.md` | unconditional | when a design gets three blind auditors before code, and the test that keeps the panel honest |
| `examples/mechanics-over-promises.md` | unconditional | the meta-rule: a rule ships with a test, hook or gate in the same commit - with the acceptance, quality and budget conventions that follow from it |

Each example is deliberately short. A rule that needs 200 lines is usually a skill
(procedure) or a hook (guarantee) in disguise — see the decision table in
`skills/writing-claude-code-rules/SKILL.md`.
