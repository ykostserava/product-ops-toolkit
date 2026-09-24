---
name: jira-package
description: Write a batch of Jira changes (create/update/link/comment/assign/transition) as a reviewable changeset file and apply it through scripts/jira_apply.py instead of hand-writing another one-off script - the engine enforces the payload rules (ASCII, required components/fields from jira-config.json, enumerated transitions, resolution on close, one-way confirmation) and verifies every write by reading it back. Dry run first, per-item approval, then apply. Triggers on "create tickets", "create a Jira ticket", "jira package", "batch create tickets", "put these decisions into Jira", "move this to Jira".
---

# /jira-package

Turn an agreed package of Jira changes into DATA that can be reviewed, then
ship it with one engine. The alternative this replaces - a fresh script per
package - re-implements raw HTTP every time, usually skips the dry run, and
re-types (or forgets) the rules that keep a payload from 400ing.

**Never write a new one-off script for Jira writes.** If the engine cannot
express the change, say so and propose the missing op - do not go around it.

Engine: `scripts/jira_apply.py` (rules in `tests/test_jira_apply.py`).
Team settings: `scripts/jira-config.json` - project key, one-way statuses,
`create_rules` (required components, a required risk-class field per issue
type, components whose new issues must name an assignee).
Connection: `scripts/jira_api.py` + `scripts/.env` (see `.env.example`).

## Flow

1. **Scope first.** The package must already be agreed: which tickets, which
   fields, which links. If the scope is still open, that is an interview
   (`/grill-me`) or a product question, not this skill. Confirm scope with
   the product owner before creating stories - especially "does this already
   exist on another platform?".
2. **Duplicates.** For every NEW issue run `/dup-check` on its summary. A
   confirmed duplicate drops out of the package before anything is written.
3. **Write the changeset** to `docs/initiatives/<name>.changeset.json`. Long
   descriptions live in the draft doc beside it (`docs/initiatives/<name>.md`)
   as fenced blocks, referenced with `description_from` - the doc stays the
   text under review, the changeset stays a payload.
4. **Dry run:** `python scripts/jira_apply.py <changeset> --dry-run`.
   It writes nothing (GET only), resolves `$id` references, validates the link
   types against the live instance and enumerates transitions. Exit 2 =
   refused, fix the changeset; exit 1 with `AUTH:` = network/token, stop.
5. **Show the plan and get a per-item yes.** Print the dry-run lines in the
   answer. Executing without an explicit approval is forbidden - drafts sit
   behind a per-item gate.
6. **Apply:** `python scripts/jira_apply.py <changeset> --apply`. Every op
   is verified by reading the issue back; the run record lands beside the
   changeset as `<name>.applied.json`. Exit 3 = a write landed but could not
   be verified: check that issue by hand, never re-run blindly.
7. **Record.** Commit the changeset + the applied record. Open follow-ups go
   to `/followups`, not into the answer.

## Ops

| op | required | notes |
|----|----------|-------|
| `create` | `issuetype`, `summary` (+ components when `require_components`) | `id` names it for `$id` refs; `description_from: {doc, block}`; `parent` for sub-tasks |
| `update` | `key`, `fields` | raw field payload, ASCII-checked recursively |
| `link` | `type`, `inward`, `outward` | type name checked against the live list; on Jira Server a `Block` link's **inward issue is the blocker** |
| `comment` | `key`, `body` | wiki markup (Server) - ASCII |
| `assign` | `key`, `assignee` | username, not display name (display names collide) |
| `transition` | `key`, `to` | target status NAME; `via` when two transitions share a target; `resolution` on close; `confirm_one_way: true` for statuses listed under `statuses.one_way` |

## What the engine refuses (do not work around these)

- non-ASCII anywhere in a payload (transliterate) - a WAF in front of Jira
  may reject it, and the rule keeps payloads portable;
- a create with no components when `create_rules.require_components` is on;
  a configured issue type without its risk-class field;
- a create on a component listed in `components_requiring_assignee` with no
  assignee (the engine names the gap, it never picks a person);
- a link type the instance does not offer;
- a transition picked by id, or a target reached by two transitions with
  different resolution screens without naming which one (`via`);
- a close with no resolution, or one the chosen transition's screen lacks;
- a one-way move without `confirm_one_way` on that op.

Safety switch: `JIRA_PROPOSE_ONLY=1` in the environment makes `--apply`
refuse (exit 2) while `--dry-run` keeps working - set it in any scheduled or
headless wrapper.

## What this is NOT

- Not a scoping tool - it ships an agreed package, it does not decide one.
- Not a bulk editor for the whole board: a changeset is one package with one
  reason, small enough that its dry run can be read in the answer.
- Not a substitute for review of the commit that carries the changeset.
