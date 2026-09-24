# po-prioritizer judgment eval fixture

Input for `scripts/eval_prioritize.py`: the po-prioritizer agent is run
headless in initiative mode against these FROZEN files (no Jira access) and
its `prioritize-state` snapshot is scored against `expected.json`.

| File | What it is |
|---|---|
| `spine.json` | frozen Phase 1: the target epic and its story keys |
| `batch.json` | frozen `jira_batch_fetch.py --trim readiness` output (`get` / `links` / `comments`, plus `remotelinks` where the design-URL fallback was fetched) |
| `expected.json` | golden roll-up state per story and the V x R x U score (tolerance +-0.05), each with a one-line `why` |
| `candidates.jsonl` | live human overrides captured by `/prioritize` via `scripts/eval_candidates.py` - the curation queue |

The fixture is synthetic and self-contained. `PROJ-501..508` cover the
readiness-state matrix (READY, PARALLEL-OK, NEEDS-GROOMING, BLOCKED across
the four Definition-of-Ready gates); `PROJ-510..515` are adversarial traps
where the obvious reading is wrong: everything green except vague AC, an open
question already marked RESOLVED, a missing design task with a design URL in
remote links, a Flagged impediment with no blocking link, a blocker that is
already closed, a yellow design tempting PARALLEL-OK while an open question
still fails gate (iv).

Custom field ids in `batch.json` (`customfield_10097` = acceptance criteria,
`customfield_10990` = flagged) are placeholders that match the
`readiness_fields` example in `scripts/jira-config.json`; when you re-freeze
from your own instance, both change together.

Run: `python scripts/eval_prioritize.py --runs 3 --min-accuracy 0.9`
(each run spends real agent tokens; `tests/test_eval_prioritize.py` covers
only the scoring machinery).
