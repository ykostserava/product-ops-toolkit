---
name: whats-next
description: Recommend what a developer should pull next from the board - read live from Jira via the po-prioritizer readiness engine (4 Definition-of-Ready gates, V x R x U, Kanban finish-first). Read-only - never writes to Jira. Triggers on "what's next", "whats next", "what should I pick up", "dev finished a task", "what should <name> pull next".
---

# /whats-next

Tell a developer (or the product owner on their behalf) **what to pull
next**: their own unfinished work first, then the highest-value READY story
matching their components, with the "why" attached. Thin orchestrator over
the `po-prioritizer` agent's **whats-next mode**. **Strictly read-only** -
there is no comment option and no write gate; nothing is ever written to Jira.

## Usage

```
/whats-next Alex          # dev by roster name/alias (case-insensitive)
/whats-next iOS           # explicit component - skips the roster
```

Roster: `memory/stakeholders/dev-roster.md` (name/aliases -> Jira username +
components; semantics in `patterns/jira-read-protocol.md`). An argument
matching neither a roster alias nor a component name used on your board gets
a "not in roster" answer with the current roster names - the agent never
guesses.

## Scope (hard boundaries)

- Orchestrator only: run the `po-prioritizer` agent in whats-next mode, relay
  its three blocks. Do not re-derive readiness or ranking yourself.
- **Never write to Jira. Period.** No add-comment, no fields, no transitions.
  If the user wants the queue posted somewhere, that is `/prioritize --comment`.
- Kanban wording (no sprints), no story-point estimation.

## Gate 0 - Connectivity preflight

Same as /prioritize: one cheap read
(`python scripts/jira_api.py search "project = PROJ" --max=1 --format=brief`).
On failure STOP: "Jira unreachable - check network/VPN and JIRA_API_TOKEN".
Print `Gate 0: PASS` or `Gate 0: BLOCKED`.

## Run

No Gate A - the pool is automatic and the contract is "answer now". Spawn the
agent (Agent tool; instruct it to follow `agents/po-prioritizer.md`, whats-next
mode; pass the dev/component argument). Relay its output verbatim:

1. **Finish yours first** (dev mode; may be empty) - their open In Progress /
   In Review items.
2. **Pull next** - top pick + up to 2 runners-up (`Key | Score | why`);
   PARALLEL-OK picks carry the "design in progress - parallel start is a
   product decision" note. Relay those questions; do not resolve them.
3. **Nothing ready?** - top-3 grooming gaps ("unblock X to make it pullable")
   when block 2 is empty.

Relay the agent's pool/narrowing line and any "no component" hygiene note -
never drop them.

## Close

One line: pool size, N assessed, the pick (or "none ready"), Gate 0 outcome,
"read-only - nothing written to Jira".

## What this is NOT

- Not a Jira mutator - zero writes, by design.
- Not /prioritize - that ranks a whole initiative/roadmap for the owner;
  /whats-next answers one dev's "what do I pull".
- Not an auto-assigner - assigning the picked story is a write; the dev/owner
  does it in Jira (or through `/jira-package`).

## Verification (read-only)

- `/whats-next <roster name>` with Jira reachable: Block 1 matches the dev's
  actual open items; the pick is explainable; the transcript contains no Jira
  mutation calls.
- `/whats-next <component>`: component mode works without the roster.
- `/whats-next <unknown>`: clean "not in roster" message listing roster names.
