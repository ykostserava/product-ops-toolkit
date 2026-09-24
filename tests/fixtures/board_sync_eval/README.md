# board-sync judgment eval fixture

Input for `scripts/eval_board_sync.py`: the project-manager agent is run
headless against these FROZEN files (no Jira access) and its verdicts are
scored against `expected.json`.

| File | What it is |
|---|---|
| `findings.json` | frozen `board_consistency.py` output (schema `board-consistency/1`) |
| `evidence.json` | frozen `jira_batch_fetch.py` output for every key the agent may read (`get` / `comments` / `devinfo`); a key deliberately ABSENT here exercises the "could not verify intent" path |
| `expected.json` | golden verdicts: `recommendation` per finding id (case-insensitive), `candidate` when present must match exactly, plus `exceptions_review` verdicts per (rule, parent) |
| `candidates.jsonl` | live human overrides captured by `/board-sync` via `scripts/eval_candidates.py` - the curation queue; promote by hand |

**This shipped set is a SEED**: four synthetic findings that cover one rule
each (R1 FIX, R2-with-release-context SKIP, R3 FLAG_ONLY, R4 ASSIGN) and one
suppressed finding whose exception the agent must review. It proves the
layout and the scoring machinery, not your team's judgment. A real golden set
grows from your own board: every time a human overrides the agent at Gate B,
`/board-sync` records the case in `candidates.jsonl`; promote the reviewed ones
into `findings.json` / `evidence.json` / `expected.json`.

Time-relative judgments (R6 staleness, R7 movement windows, R8 release dates)
assume the eval runs close to the freeze date - re-freeze timestamps when a
case goes stale rather than accepting a drifting score.

Run: `python scripts/eval_board_sync.py --runs 3 --min-accuracy 0.9`
(each run spends real agent tokens; the unit tests in
`tests/test_eval_board_sync.py` cover only the scoring and drift machinery).
