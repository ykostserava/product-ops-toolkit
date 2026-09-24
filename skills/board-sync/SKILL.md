---
name: board-sync
description: Detect and fix parent/child status inconsistencies on a Jira board (child active while initiative/epic still Backlog; all children closed while parent open; closed parent with open children) plus active issues with no assignee (R4 - proposes a candidate from the dev roster), In-progress issues with an unresolved blocker (R5, flag-only), aging WIP silent for 14+ days (R6, flag-only with devinfo-based judgment), external cross-project dependencies with WAIT/ESCALATE verdicts (R7, flag-only) and a release radar (R8, flag-only): tickets in an upcoming release that are not release-ready near the release date, plus epics waiting for a planned prod release; registry = scripts/releases.json. Read-detect-propose flow with the project-manager agent; EVERY status change or assignment requires explicit per-run human approval - nothing is ever written automatically. Triggers on "board sync", "check board statuses", "initiative statuses", "board status check", "sync parent statuses", "who is unassigned", "release radar", "release readiness".
---

# /board-sync

Keep parent statuses honest: initiatives/epics whose children moved on,
parents closed over still-open children, active issues nobody owns (R4 -
with a proposed candidate assignee), In-progress work running on top of
an unresolved blocker (R5, signal-only), aging WIP - In progress /
Ready for testing silent for 14+ days (R6, signal-only; the agent separates
"quietly progressing in an MR" from "abandoned"), external dependencies -
open issues blocked by open tickets from other projects (R7, signal-only;
WAIT vs ESCALATE with who-to-ping), and the release radar (R8, signal-only):
tickets linked into an upcoming deploy ticket (`scripts/releases.json`, one
entry per release) that are not release-ready inside the release window,
plus R2 epics annotated "waiting for release X". Thin orchestrator:
deterministic detection (`scripts/board_consistency.py`) -> judgment
(`project-manager` agent) -> **gated execution** (`scripts/jira_transition.py`
for status moves, `scripts/jira_assign.py` for assignments). **No transition
or assignment ever runs without your explicit approval in THIS conversation.**

Setup: status names, project key, one-way statuses and parent link types
live in `scripts/jira-config.json` (defaults describe a plain Kanban flow -
edit them before the first live run). Connection: `scripts/jira_api.py` +
`scripts/.env`. Dev roster for R4 candidates: `memory/stakeholders/dev-roster.md`
(columns: Name / aliases, Jira username, Components, Role, Unavailable until).

## Usage

```
/board-sync                 # full flow: detect -> judge -> approve -> execute
/board-sync --report        # detect + judge only, write briefings/ report, ZERO writes
/board-sync --jql "..."     # override the scan scope (default: project = <project_key>)
```

## Scope (hard boundaries)

- Orchestrator only: run the engine, spawn the agent, enforce the gates, relay.
  Do not re-derive detection or judgment yourself.
- **The ONLY Jira writes are: (a) transitions via `scripts/jira_transition.py`
  after Gate B/B2 approval; (b) assignments via `scripts/jira_assign.py` after
  Gate B approval; (c) nothing else.** No other field edits, no comments, no
  links, no rank.
- **Headless / non-interactive runs NEVER execute a transition or an
  assignment** - `--report` or any run where the user cannot answer a gate
  stops at the report. Hard rule, and mechanically held: wrappers set
  `JIRA_PROPOSE_ONLY=1`, which makes both writers refuse anything but
  `--dry-run`.
- House rules: ASCII-only payloads; one-way transitions (`statuses.one_way`)
  get the extra Gate B2.

## Gate 0 - Connectivity preflight

One cheap read: `python scripts/jira_api.py search "project = PROJ" --max=1
--format=brief`. On failure STOP: "Jira unreachable - check network/VPN and
JIRA_API_TOKEN". Print `Gate 0: PASS` or `Gate 0: BLOCKED`.

## Phase 1 - Detect (deterministic, read-only)

```
python scripts/board_consistency.py --out <scratchpad>/board-findings.json
```

Exit 0 clean; exit 2 = partial (report each meta.errors entry as "could not
scan"); exit 1 AUTH = stop Gate-0-style. Print: "N findings (M suppressed by
exceptions, K scan errors)". If N=0: report clean board + suppressed count and
finish - no agent needed.

## Gate A - Scope

STOP for approval: "Analyze these N findings with the project-manager agent
(reads comments/labels of the flagged parents)?" Print `Gate A: PASS` or
`Gate A: STOPPED`.

## Phase 2 - Judge

Spawn the `project-manager` agent (Agent tool; instruct it to follow
`agents/project-manager.md`; pass the findings JSON path). Relay its
proposals table verbatim:

```
id | rule | parent (status) | evidence | proposed transition | candidate | one-way? | recommendation
```

plus its per-finding rationale and proposed exceptions entries. Do not drop
FLAG_ONLY rows - the product owner sees everything.

## Gate B - Execution approval (interactive only)

Ask for a selection by plain reply: **"all / none / <finding ids>"**
(AskUserQuestion only when there are <= 4 findings). `Gate B: STOPPED` on none.

For EACH approved finding, sequentially:
1. `python scripts/jira_transition.py --key <K> --to "<Status>" --dry-run` -
   show the resolved transition id + exact payload. **Never put
   `--yes-one-way` on a preview command line** - the writer's dry-run needs no
   arming flag and reports `one_way: true` in the preview itself (closing
   still needs `--resolution Done` on the preview, unless the user names
   another, so the payload shown is the payload sent). The arming flag is
   added only at step 3, after Gate B2's explicit yes.
   For R1 proposals with `to: null`, first enumerate
   (`python scripts/jira_api.py transitions <K>`) and agree the target with
   the user before the dry-run.
   **R4 (assign) findings instead:** `python scripts/jira_assign.py --key <K>
   --assignee <candidate> --dry-run` with the agent's candidate (the user may
   name someone else at approval). Assignment is reversible - no Gate B2; steps
   2-3 below apply with `jira_assign.py` and exit codes read identically.
2. **Gate B2 (one-way only):** if the target is in `statuses.one_way`, STOP
   again per item showing the payload incl. resolution: "ONE-WAY - no path
   back. Execute?" Only on explicit yes proceed to step 3.
3. Execute (same command without `--dry-run`, adding `--yes-one-way` now if the
   target is one-way), then report by exit code:
   - 0: `Gate B: EXECUTED PROJ-x 'A' -> 'B' (verified)`
   - 2: `Gate B: REFUSED PROJ-x (<stderr reason>, nothing changed)`
   - 3: `Gate B: UNVERIFIED PROJ-x - POST accepted, result unconfirmed (status
     differs, or the verify read failed), CHECK MANUALLY before touching
     anything else`
   - 1: stop the whole loop (AUTH/network or API failure), report remaining as
     not attempted.

## Gate C - Exceptions file (two-way)

**Additions:** for findings the user marked SKIP-as-intentional (or agent
SKIPs the user confirms): show the exact JSON entries destined for
`scripts/board-exceptions.json`, STOP for approval, and only then edit the
file.

**Removals:** for the agent's LIFT (stated condition fulfilled) and DROP
(entry matched nothing) verdicts from its exceptions review: show the exact
entries to delete, STOP for approval, and only then remove them. A lifted
finding resurfaces on the NEXT scan and goes through normal judgment - do not
re-run detection mid-flow.

**Releases registry:** same gate covers `scripts/releases.json` - remove
entries the agent flagged via `stale_releases` (release shipped: fixVersion
released/archived, not mere deploy-ticket closure) after approval; relay the
agent's post-release follow-up list when it does. Additions (a new deploy
ticket) are made here too when the user names one.

Print `Gate C: SAVED <n> / REMOVED <m> exception(s)` or `Gate C: SKIPPED`.

## Override capture (optional - feeds an eval set)

Every human decision that DIFFERS in JUDGMENT from the agent's recommendation
is a future golden case for an eval of the project-manager agent. If you keep
one, capture it while the run's evidence is at hand: a FIX/ASSIGN refused
because the judgment is wrong (not "not now"), a candidate replaced, a
SKIP/FLAG_ONLY the user executes against, a verdict corrected in discussion.
Pure deferrals do not count - ask ONCE at close (one batched question):
"disagree with the recommendation, or just deferring?" Store the frozen
`finding` object and the parent's evidence slice with the user's reason in
their own words; promotion into a fixture stays a separate reviewed step.
Headless `--report` runs have no gates - nothing to capture.

## `--report` mode (headless-safe)

Run Phase 1 + Phase 2 only; write the proposals table + rationale + the agent's
```json board-sync-state``` snapshot to `briefings/board-sync-YYYY-MM-DD.md`.
Then prepend a delta section against the previous dated report and refresh the
latest-pointer:

```
python scripts/board_sync_delta.py <today.md> <previous-dated.md>  # always exit 0
cp briefings/board-sync-YYYY-MM-DD.md briefings/latest-board-sync.md
```

End with: "propose-only report; run /board-sync interactively to act on it."
**Never call jira_transition.py or jira_assign.py in this mode, not even
--dry-run - and never edit board-exceptions.json (the agent's KEEP/LIFT/
DROP verdicts stay in the report; Gate C is interactive-only).**

A scheduled wrapper (cron / Task Scheduler) can run this mode headless with
`JIRA_PROPOSE_ONLY=1` set; there the wrapper captures stdout and owns the file
assembly + delta + latest copy - in that context print the full report as your
final message and do not write the briefings file yourself.

## Close

One line: scanned N issues, F findings -> executed X (transitions+assignments)
/ refused-unverified Y / skipped Z / flagged W, exceptions saved E; gate
outcomes.

## What this is NOT

- Not a hygiene report (stale/component/priority checks belong to a separate
  scan; unassigned-active lives here as R4).
- Not a "what next" recommender - R4 fills a hole on an already-active issue;
  ranking what to pull next is a prioritization skill's job.
- Not a readiness ranker - this fixes status truth.
- Not a bulk-close tool - every transition is individually approved; there is
  no "just close everything" path.

## Verification (safety-ordered, first live run)

1. `pytest tests/test_board_consistency.py tests/test_jira_transition.py` green.
2. Engine read-only scan; eyeball findings vs known board truth (deliberately
   parked epics SHOULD appear before exceptions exist).
3. Wrapper `--dry-run` on a Backlog issue - enumeration + payload, no write.
4. One approved reversible smoke pair on a user-chosen low-stakes ticket
   ALREADY in a two-way status: forward -> verify -> revert (enumerate ids
   first, as always). Do NOT smoke from Backlog if your workflow has no path
   back to it - check `GET /transitions` from the neighbouring statuses
   before assuming any move is reversible. NEVER smoke a one-way status.
5. No-write proof: a full run answering "none" at Gate B and a `--report` run -
   zero transition POSTs in both.
