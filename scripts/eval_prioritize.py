#!/usr/bin/env python3
"""Judgment eval for the po-prioritizer agent (readiness states + scores).

Runs the agent headless against a FROZEN fixture (enumerated spine +
pre-fetched batch data, no Jira access) and scores the `prioritize-state`
snapshot against golden expected states/scores. Built to measure verdict
drift: the same story flipping READY -> other between two same-day runs is
a real failure mode, and this turns it into a number.

NOT a pytest suite - each run spends real agent tokens. Unit tests cover the
scoring machinery only (tests/test_eval_prioritize.py).

Fixture layout (default tests/fixtures/prioritize_eval/):
    spine.json      {"target": "PROJ-500", "stories": [keys...]} - Phase 1 frozen
    batch.json      frozen jira_batch_fetch --trim readiness output
    expected.json   {"items": [{key, state[, score]}]} - golden roll-ups;
                    score compared with +-0.05 tolerance when present
    candidates.jsonl  live human overrides captured by /prioritize via
                      scripts/eval_candidates.py - the curation queue for new
                      golden cases (promote by hand, owner-reviewed)

The shipped fixture is synthetic: one epic whose stories cover the whole
readiness-state matrix plus six adversarial conflicting-signal traps - see
tests/fixtures/prioritize_eval/README.md.

Usage:
    python scripts/eval_prioritize.py [--fixture DIR] [--runs 1]
        [--claude-cmd claude] [--timeout 900] [--out report.md]
        [--min-accuracy 0.0..1.0]

Exit codes: 0 report produced (and accuracy >= --min-accuracy when given);
1 = no valid snapshot in any run, or accuracy below --min-accuracy.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from eval_board_sync import run_agent  # noqa: E402
from prioritize_delta import extract_snapshot  # noqa: E402

DEFAULT_FIXTURE = (
    Path(__file__).parent.parent / "tests" / "fixtures" / "prioritize_eval"
)
# The agent definition the eval subject must follow: a project-local copy
# first, then this toolkit's agents/ directory (override with --agent-doc).
AGENT_DOC = next(
    (
        p
        for p in (
            Path(".claude") / "agents" / "po-prioritizer.md",
            Path(__file__).resolve().parents[1] / "agents" / "po-prioritizer.md",
        )
        if p.is_file()
    ),
    Path(".claude") / "agents" / "po-prioritizer.md",
)
SCORE_TOLERANCE = 0.05


# ------------------------------------------------------------------- scoring


def _got_text(item):
    text = item.get("state", "?")
    if item.get("score") is not None:
        text += f" ({item['score']})"
    return text


def score_run(snapshot, expected):
    """Diff one prioritize-state snapshot against the golden items."""
    got_by_key = {i.get("key"): i for i in snapshot.get("items", [])}
    rows = []
    for exp in expected.get("items", []):
        got = got_by_key.pop(exp["key"], None)
        expected_text = exp["state"] + (f" ({exp['score']})" if "score" in exp else "")
        if got is None:
            rows.append(
                {
                    "key": exp["key"],
                    "expected": expected_text,
                    "got": "-",
                    "outcome": "MISSING",
                }
            )
            continue
        state_ok = (got.get("state") or "").upper() == exp["state"].upper()
        score_ok = (
            "score" not in exp
            or got.get("score") is not None
            and abs(got["score"] - exp["score"]) <= SCORE_TOLERANCE
        )
        rows.append(
            {
                "key": exp["key"],
                "expected": expected_text,
                "got": _got_text(got),
                "outcome": "MATCH" if state_ok and score_ok else "MISMATCH",
            }
        )
    matched = sum(1 for r in rows if r["outcome"] == "MATCH")
    return {
        "rows": rows,
        "summary": {
            "state_accuracy": matched / len(rows) if rows else 1.0,
            "extras": len(got_by_key),
            "extra_keys": sorted(k for k in got_by_key if k),
        },
    }


def drift(snapshots, expected):
    """Per golden item: the state each run produced."""
    rows = []
    for exp in expected.get("items", []):
        states = []
        for snap in snapshots:
            # Same duplicate-key resolution as score_run (dict keeps the LAST
            # occurrence) so the two tables never disagree about one run.
            got = {i.get("key"): i for i in snap.get("items", [])}.get(exp["key"])
            states.append((got or {}).get("state"))
        rows.append(
            {"key": exp["key"], "states": states, "stable": len(set(states)) == 1}
        )
    return rows


# -------------------------------------------------------------------- render


def render_markdown(scores, drift_rows, model=None):
    title = "# po-prioritizer judgment eval"
    if model:
        title += f" (model: {model})"
    lines = [title, ""]
    for i, score in enumerate(scores, 1):
        s = score["summary"]
        lines.append(
            f"## Run {i}: states {round(s['state_accuracy'] * 100)}%, "
            f"extras {s['extras']}"
        )
        lines.append("")
        lines.append("| key | expected | got | outcome |")
        lines.append("|---|---|---|---|")
        for r in score["rows"]:
            lines.append(
                f"| {r['key']} | {r['expected']} | {r['got']} | {r['outcome']} |"
            )
        if s["extra_keys"]:
            lines.append("")
            lines.append(f"Extra items (not in golden): {', '.join(s['extra_keys'])}")
        lines.append("")
    if len(scores) > 1:
        unstable = [r for r in drift_rows if not r["stable"]]
        lines.append(
            f"## Drift over {len(scores)} runs: "
            f"{len(drift_rows) - len(unstable)}/{len(drift_rows)} stable"
        )
        for r in unstable:
            lines.append(f"- {r['key']}: {r['states']}")
        lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------ agent io


def build_prompt(fixture_dir, agent_doc=None):
    fixture = Path(fixture_dir)
    return (
        f"Act as the po-prioritizer agent: read and follow {agent_doc or AGENT_DOC} "
        f"exactly, initiative mode with --dry-run.\n"
        f"Phase 1 is FROZEN: the spine is {fixture / 'spine.json'} "
        f"(target + story keys) - use it as-is.\n"
        f"Phase 2 data is PRE-FETCHED at {fixture / 'batch.json'} "
        f"(jira_batch_fetch --trim readiness format: "
        f"issues.<KEY>.get/.links/.comments, plus .remotelinks where the "
        f"design-URL fallback check was fetched). This is an offline eval - do "
        f"NOT call Jira, jira_batch_fetch, jira_api.py or any network "
        f"tool; missing data for a key means 'could not verify' for that "
        f"gate.\n"
        f"Produce the full report and END with the ```json prioritize-state``` "
        f"snapshot covering EVERY story from the spine with its roll-up state "
        f"and score. The snapshot is what gets scored."
    )


# ---------------------------------------------------------------------- main


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--claude-cmd", default="claude")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--out", help="write the markdown report here too")
    parser.add_argument(
        "--model",
        help="pin the model for every run (alias like sonnet/haiku or a full "
        "id); default inherits the CLI's configured model. A/B reports "
        "should be named eval-ab-* so a pre-merge gate can ignore them.",
    )
    parser.add_argument(
        "--agent-doc",
        help="path to the po-prioritizer agent definition (default: "
        ".claude/agents/po-prioritizer.md, else this toolkit's agents/)",
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        help="exit 1 when mean state accuracy over valid runs is below this",
    )
    args = parser.parse_args(argv)

    fixture = Path(args.fixture)
    expected = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))
    prompt = build_prompt(fixture, args.agent_doc)

    snapshots, failures = [], []
    for i in range(args.runs):
        try:
            transcript = run_agent(
                prompt, args.claude_cmd, args.timeout, model=args.model
            )
        except Exception as exc:  # noqa: BLE001 - reported per run
            failures.append(f"run {i + 1}: {exc}")
            continue
        snap = extract_snapshot(transcript)
        if snap is None:
            failures.append(f"run {i + 1}: transcript has no snapshot block")
            continue
        snapshots.append(snap)
    for failure in failures:
        print(f"WARN: {failure}", file=sys.stderr)
    if not snapshots:
        print("no valid snapshot in any run - nothing to score", file=sys.stderr)
        return 1

    scores = [score_run(snap, expected) for snap in snapshots]
    report = render_markdown(scores, drift(snapshots, expected), model=args.model)
    print(report)
    if args.out:
        Path(args.out).write_text(report + "\n", encoding="utf-8")

    mean_accuracy = sum(s["summary"]["state_accuracy"] for s in scores) / len(scores)
    if args.min_accuracy is not None:
        if mean_accuracy < args.min_accuracy:
            print(
                f"accuracy {mean_accuracy:.2f} below required {args.min_accuracy}",
                file=sys.stderr,
            )
            return 1
        # Extras are fabrications relative to the golden spine - they must
        # fail the gate even when every expected item matches.
        total_extras = sum(s["summary"]["extras"] for s in scores)
        if total_extras:
            print(
                f"{total_extras} extra item(s) not in the golden set - "
                "fabrications fail the gate",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
