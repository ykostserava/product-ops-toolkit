---
name: prioritize
description: Propose a prioritized, readiness-aware order for an initiative's stories - or rank the initiative roadmap - reading from Jira (source of truth). Assesses the 4 Definition-of-Ready gates (design, AC/INVEST, dependencies, estimate + open questions), prints a ranked queue + gaps-to-start-dev, and is propose-only by default (writes only behind explicit per-item gates: an optional epic comment, and with --apply, transitions + size labels). Triggers on "prioritize", "what's ready", "rank this initiative", or "what should we pick next".
---

# /prioritize

Give the product owner a **ranked, readiness-aware queue** for an initiative
(or the whole roadmap), read live from Jira, so you can see what dev can pull
now and exactly what is missing before the rest can start. Thin orchestrator:
it enforces gates and delegates the assessment to the `po-prioritizer` agent.
**Propose-only by default** - nothing is written to Jira unless you
explicitly approve it at a gate: an optional single epic comment (Gate B), and
with `--apply`, proposed transitions and size labels (Gate W/W2).

Setup: project key, status names and the readiness custom fields (acceptance
criteria, flagged, baseline dates) come from `scripts/jira-config.json`; the
connection from `scripts/.env`.

## Usage

```
/prioritize PROJ-169                    # rank stories under an epic/initiative
/prioritize EXT-113354                  # rank another project's initiative through its linked epics
/prioritize roadmap                     # rank initiatives against each other (uses the default JQL below)
/prioritize roadmap --roadmap-jql="..." # override the roadmap query
/prioritize PROJ-169 --comment          # also propose posting the summary as an epic comment (gated)
/prioritize PROJ-169 --apply            # after the report, offer gated write-back of proposed transitions + size labels (Gate W)
/prioritize PROJ-169 --dry-run          # read-only, never even propose a comment
```

`--dry-run` wins over `--apply`: the "Proposed writes" section is still
printed, but Gate W never opens (safe preview).

**Default roadmap JQL** (used when no `--roadmap-jql` is passed):
```
project = PROJ AND issuetype = Initiative AND statusCategory != Done ORDER BY priority DESC, key ASC
```
Roadmap items are whatever issue type sits ABOVE your epics (here
`Initiative`); adjust the JQL if your hierarchy differs. Roadmap mode also
surfaces each initiative's baseline start / end dates (the `baseline_start` /
`baseline_end` readiness fields) for timeline orientation - shown in the tier
table, never a ranking input.

## Scope (hard boundaries)

- Orchestrator only: run the `po-prioritizer` agent, enforce the gates, relay
  its report. Do not re-derive readiness or ranking yourself.
- **The ONLY Jira writes are: (a) the optional single epic comment after
  Gate B; (b) transitions via `scripts/jira_transition.py` after Gate W
  approval + Gate W2 (one-way confirm); (c) labels via `scripts/jira_label.py`
  after Gate W approval. Nothing else** - no rank, no priority, no other
  fields.
- **Headless / non-interactive runs NEVER write.** Any run where no human can
  answer a gate stops at the report, `--apply` or not; a scheduled wrapper
  sets `JIRA_PROPOSE_ONLY=1` so the writers refuse regardless.
- Kanban wording (no sprints), ASCII-only in any Jira payload, no story-point
  estimation.

## Gate 0 - Connectivity preflight

One cheap read (`python scripts/jira_api.py get <target-key> --format=brief`,
or a 1-row `search` for roadmap mode). On failure STOP: "Jira unreachable -
check network/VPN and JIRA_API_TOKEN". Print `Gate 0: PASS` or `Gate 0: BLOCKED`.

## Phase 1 - Enumerate + Gate A (scope)

Spawn the agent to enumerate the spine (Agent tool; instruct it to follow
`agents/po-prioritizer.md`; pass the target, mode, and flags). It returns the
story/initiative count.

Print: "Found N stories under <target>" (or "M initiatives for roadmap").
**STOP for approval**: "Assess readiness and rank these?" Print `Gate A: PASS`
or `Gate A: STOPPED`. Only proceed on approval.

## Phase 2 - Assess + rank

On Gate A pass, let the agent run its readiness assessment (4 DoR gates,
graded design) and ranking (V x R x U), and print its full report: ranked
queue, 4-gate readiness map, gaps-to-start-dev, readiness-vs-priority
reconciliation, and (roadmap mode) the tier table with baseline columns plus
any behind-baseline or no-baseline-set flags. The agent fetches per-story
data via `scripts/jira_batch_fetch.py` (one parallel batch call with
`--trim readiness`) instead of sequential per-story reads; sequential remains
its fallback, and partial-fetch gaps (exit 2) must appear in the report as
"could not verify" rows, never silently dropped.

**Design YELLOW items:** the agent surfaces each "design in progress, start
in parallel?" question. Relay them; these are decisions for the owner, not
blockers - do not drop or auto-resolve them.

## Gate B - Write confirmation (only if `--comment` and NOT `--dry-run`)

If `--comment` was passed: show the exact ASCII-only wiki-markup comment body
the agent prepared, plus the ranking it summarizes. **STOP for explicit
approval.** Only on approval, post it once through `/jira-package` (a
one-op `comment` changeset) or the equivalent single call. Verify the body is
ASCII first (`->` not arrows, `EUR` not the symbol, no non-Latin script).
Print `Gate B: POSTED <epic-key>` or `Gate B: SKIPPED`. Default (no
`--comment`) posts nothing.

## Gate W - Write-back approval (only if `--apply` and NOT `--dry-run`; interactive only; after Gate B)

The agent's report section 8 "Proposed writes" is the ONLY source of
proposals. If it is empty: print "no writes proposed" and skip this gate.

1. Print the proposals table with ids `T1..Tn` (transitions) and `L1..Ln` (labels):
   ```
   id | key | operation | evidence
   T1 | PROJ-355 | Backlog -> Ready for Dev | 4/4 gates: design N/A, AC 8/10, deps clear, size-S
   L1 | PROJ-321 | add size-S | source: description "Estimate: S"
   ```
2. Ask for a selection by plain reply: **"all / none / <ids>"**
   (AskUserQuestion when there are <= 4 proposals). The same reply may add
   **manual size labels** as lines shaped `PROJ-118 = M`. Validate each: size
   in XS/S/M/L/XL; the key must be in this run's assessed pool (reject foreign
   keys). If the story already has a different `size-*` label, the op becomes
   a replace: `--remove size-<old> --add size-<new>` in ONE jira_label.py
   call. Manual TRANSITIONS are NOT accepted here - only agent-proposed ones.
   `Gate W: SKIPPED` on "none".
3. For EACH approved item, sequentially:
   - **Transition (T*):** `python scripts/jira_transition.py --key <K> --to "Ready for Dev" --dry-run` -
     show the resolved transition id + exact payload (the preview needs NO
     arming flag and reports `one_way: true`; never put `--yes-one-way` on a
     preview command line). Then **Gate W2** whenever the target is in
     `statuses.one_way`: STOP per item: "ONE-WAY - no REST path back.
     Execute?" Only on explicit yes, run the command again without
     `--dry-run` and WITH `--yes-one-way` (added only at this step).
   - **Label (L*):** `python scripts/jira_label.py --key <K> --add size-X [--remove size-Y] --dry-run` -
     show the payload, then execute (same command without `--dry-run`).
     Agent-proposed replace rows map to the same one-call shape. Reversible -
     no W2.
4. Report per exit code, per item:
   - 0: `Gate W: EXECUTED <K> <op> (verified)`
   - 2: `Gate W: REFUSED <K> (<stderr reason>, nothing changed)` - continue
   - 3: `Gate W: UNVERIFIED <K> - accepted, result unconfirmed (state differs,
     or the verify read failed), CHECK MANUALLY` - continue, call it out
     separately in the close line
   - 1: stop the WHOLE loop (AUTH/network or API failure); report remaining
     items as not attempted.

## Override capture (eval candidates - interactive runs only)

When the user DISPUTES an assessed story's roll-up state or score in
conversation ("this isn't ready, the AC is stale", "PROJ-x should not be
blocked") - or refuses a Gate W transition because the READY verdict itself
is wrong (not "not now") - that disagreement is a future golden case for
`scripts/eval_prioritize.py`. Capture it while the run's batch data is still
at hand, one entry per disputed story, reason = the user's own words:

```
python scripts/eval_candidates.py add --source prioritize --json '{"key": "PROJ-x", "agent": {"state": "READY", "score": 3.0}, "human": {"state": "NEEDS-GROOMING", "reason": "<their words>"}, "evidence": {...the batch issues.<KEY> slice...}}'
```

This writes only to `tests/fixtures/prioritize_eval/candidates.jsonl` (repo
file, no gate needed; the script dedups). Include the `evidence` slice -
without it the case cannot be promoted into the frozen fixture. Promotion +
expected.json stays a separate human-reviewed step. Pure deferrals and
priority preferences are NOT overrides - only readiness/score judgments the
user calls wrong. Mention captures in the close line when any happened.

## Close

One-line summary: N assessed, X ready / Y groom / Z blocked; Gate 0/A/B
outcomes; any design-parallel decisions still open; with --apply: writes
executed X (T/L) / refused Y / unverified Z / skipped W.

## What this is NOT

- Not an unattended Jira mutator - every write sits behind a per-item gate
  (B for the comment, W/W2 for transitions and labels); rank and any other
  field stay out of scope.
- Not the breakdown skill - that verifies and breaks down a new initiative;
  `/prioritize` ranks the readiness of one that already has stories.
- Not a code-verifier - unknowns are surfaced, never resolved.

## Verification

- `/prioritize <epic>` (or `--dry-run`) prints the proposal and touches nothing.
- Golden fixture: `python scripts/eval_prioritize.py --runs 3` scores the
  agent against `tests/fixtures/prioritize_eval/`.
- `/prioritize <epic> --apply --dry-run`: "Proposed writes" section present,
  Gate W never opens, zero write calls in the transcript.
- Interactive `--apply` answering "none" at Gate W: zero POST/PUT.
- Label smoke on a low-stakes ticket: approve one `size-*` add, verify, then
  remove it via `scripts/jira_label.py --remove` (fully reversible).
- Transition path: dry-run only until the first genuine use behind W + W2.
