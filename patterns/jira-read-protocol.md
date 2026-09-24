# Jira read protocol (shared by the judgment agents)

One home for the read-side mechanics every judgment agent uses (the
`project-manager` agent ships here; a prioritization agent would use the same
contract). Agent docs reference this file instead of restating it - when a
rule here changes, every agent changes with it.

## Access point (the ONLY Jira access point)

```
python scripts/jira_api.py <command> <key> --format=json
```

Read-only commands: `get`, `epic`, `subtasks`, `links`, `remotelinks`,
`comments`, `devinfo`, `transitions`, `search "<JQL>" [--max=N]`. The token
and base URL live in `scripts/.env` (see `scripts/.env.example`); many
company Jira instances are reachable only on VPN/office network - an
`AUTH:` failure usually means that, not a revoked token.

A team that already has its own Jira CLI with the same command surface can
point every script at it with `--jira-api PATH` or `JIRA_API=PATH`.

## Batch fetch contract (default path - never per-key loops)

```
python scripts/jira_batch_fetch.py --keys <K1,K2,...> --commands <c1,c2> \
    [--trim readiness] --out <scratchpad>/<name>.json
```

- Commands: `get`, `links`, `comments`, `remotelinks`, `devinfo`. Commands
  apply to ALL keys in the call - when only a subset of keys needs an
  expensive command, make a SECOND smaller batch call for it.
- `devinfo` is expensive (several HTTP calls per key: issue-id resolve + the
  dev-status reads) - fetch it only for keys whose judgment reads MR
  liveness. Payload is flat: `{pullRequests, branches, commits}`.
- `--trim readiness` keeps summary/description/labels plus the custom fields
  listed under `readiness_fields` in `scripts/jira-config.json` (acceptance
  criteria, flagged, baseline dates - ids differ per instance).
- Exit codes: `0` clean; `2` partial - use what arrived and surface every
  failed (key x command) pair from `meta.errors` as an explicit
  "could not verify" (never silently treat missing evidence as evidence);
  `1` fatal - stderr starting with `AUTH:` means network/token, STOP the
  whole run and report (fail fast, never retry auth more than once); any
  other fatal falls back to sequential per-key calls.

## Dev roster (`memory/stakeholders/dev-roster.md`)

A markdown table with columns `Name / aliases | Jira username | Components |
Role | Unavailable until`. Semantics:

- Match names against the "Name / aliases" column case-insensitively. An
  argument matching MORE than one row is ambiguous - list the matches and
  ask/flag, do NOT guess (two people sharing a first name is normal).
- A row maps to: Jira username + component set + role.
- **Role `qa`**: candidate ONLY for testing/regression work (e.g. status
  Ready for testing), never for dev work.
- **Unavailable until** (inclusive): a date today or later = NOT available;
  a PAST date = back and fully available (stale entries never hide anybody).
- Jira usernames may contain `@` - ALWAYS single-quote them in JQL:
  `assignee = 'name@example.com'`.

## Text destined for Jira

ASCII only: `->` not arrows, `EUR` not the symbol, no non-Latin scripts. The
agents never write to Jira themselves - but any comment/label/transition
payload they PREPARE for a skill's gate follows this, and the writers refuse
anything else.
