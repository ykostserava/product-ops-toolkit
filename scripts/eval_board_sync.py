#!/usr/bin/env python3
"""Judgment eval for the project-manager agent (board-sync).

Runs the agent headless against a FROZEN fixture (findings + pre-fetched
evidence, no Jira access) and scores its verdicts against a golden
expected.json curated from real PO decisions. Turns judgment quality into a
number instead of a feeling, and measures verdict drift across repeated runs.

NOT a pytest suite - each run spends real agent tokens. Unit tests cover the
scoring/drift/render machinery only (tests/test_eval_board_sync.py).

Fixture layout (default tests/fixtures/board_sync_eval/):
    findings.json   frozen board_consistency.py output (schema board-consistency/1)
    evidence.json   frozen jira_batch_fetch.py output (get/comments/devinfo)
    expected.json   {"findings": [{id, rule, parent, recommendation[, candidate]}],
                     "exceptions_review": [{rule, parent, verdict}]}
    candidates.jsonl  live human overrides captured by /board-sync via
                      scripts/eval_candidates.py - the curation queue for new
                      golden cases (promote by hand, owner-reviewed)

The fixture shipped with this toolkit is a SEED (a handful of synthetic
findings) that demonstrates the layout; a real golden set is curated from your
own board's decisions over time - see tests/fixtures/board_sync_eval/README.md.

Usage:
    python scripts/eval_board_sync.py [--fixture DIR] [--runs 1]
        [--claude-cmd claude] [--timeout 900] [--out report.md]
        [--min-accuracy 0.0..1.0]

Exit codes: 0 report produced (and accuracy >= --min-accuracy when given);
1 = no valid snapshot in any run, or accuracy below --min-accuracy.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from board_sync_delta import extract_snapshot  # noqa: E402
from claude_cli import headless_env  # noqa: E402

DEFAULT_FIXTURE = (
    Path(__file__).parent.parent / "tests" / "fixtures" / "board_sync_eval"
)
# The agent definition the eval subject must follow: a project-local copy
# first, then this toolkit's agents/ directory (override with --agent-doc).
AGENT_DOC = next(
    (
        p
        for p in (
            Path(".claude") / "agents" / "project-manager.md",
            Path(__file__).resolve().parents[1] / "agents" / "project-manager.md",
        )
        if p.is_file()
    ),
    Path(".claude") / "agents" / "project-manager.md",
)


# ------------------------------------------------------------------- scoring


def score_run(snapshot, expected):
    """Diff one snapshot against the golden verdicts."""
    got_by_id = {f.get("id"): f for f in snapshot.get("findings", [])}
    rows = []
    for exp in expected.get("findings", []):
        got = got_by_id.pop(exp["id"], None)
        if got is None:
            rows.append({**_row(exp), "outcome": "MISSING", "got": "-"})
            continue
        rec_ok = (got.get("recommendation") or "").upper() == exp[
            "recommendation"
        ].upper()
        cand_ok = "candidate" not in exp or got.get("candidate") == exp["candidate"]
        got_text = got.get("recommendation", "?")
        if got.get("candidate"):
            got_text += f" ({got['candidate']})"
        rows.append(
            {
                **_row(exp),
                "outcome": "MATCH" if rec_ok and cand_ok else "MISMATCH",
                "got": got_text,
            }
        )
    review_rows = []
    got_review = {
        (r.get("rule"), r.get("parent")): r
        for r in snapshot.get("exceptions_review", [])
    }
    for exp in expected.get("exceptions_review", []):
        got = got_review.get((exp["rule"], exp["parent"]))
        if got is None:
            outcome, got_text = "MISSING", "-"
        elif (got.get("verdict") or "").upper() == exp["verdict"].upper():
            outcome, got_text = "MATCH", got["verdict"]
        else:
            outcome, got_text = "MISMATCH", got.get("verdict", "?")
        review_rows.append(
            {
                "rule": exp["rule"],
                "parent": exp["parent"],
                "expected": exp["verdict"],
                "got": got_text,
                "outcome": outcome,
            }
        )
    return {
        "rows": rows,
        "review_rows": review_rows,
        "summary": {
            "findings_accuracy": _accuracy(rows),
            "review_accuracy": _accuracy(review_rows),
            "extras": len(got_by_id),
            "extra_ids": sorted(k for k in got_by_id if k),
        },
    }


def _row(exp):
    expected_text = exp["recommendation"]
    if exp.get("candidate"):
        expected_text += f" ({exp['candidate']})"
    return {
        "id": exp["id"],
        "rule": exp["rule"],
        "parent": exp["parent"],
        "expected": expected_text,
    }


def _accuracy(rows):
    if not rows:
        return 1.0
    return sum(1 for r in rows if r["outcome"] == "MATCH") / len(rows)


def drift(snapshots, expected):
    """Per expected finding: the recommendation each run produced."""
    rows = []
    for exp in expected.get("findings", []):
        recs = []
        for snap in snapshots:
            # Same duplicate-id resolution as score_run (dict keeps the LAST
            # occurrence) so the two tables never disagree about one run.
            got = {f.get("id"): f for f in snap.get("findings", [])}.get(exp["id"])
            recs.append((got or {}).get("recommendation"))
        rows.append(
            {
                "id": exp["id"],
                "recommendations": recs,
                "stable": len(set(recs)) == 1,
            }
        )
    return rows


# -------------------------------------------------------------------- render


def _pct(value):
    return f"{round(value * 100)}%"


def render_markdown(scores, drift_rows, model=None):
    title = "# board-sync judgment eval"
    if model:
        title += f" (model: {model})"
    lines = [title, ""]
    for i, score in enumerate(scores, 1):
        s = score["summary"]
        lines.append(
            f"## Run {i}: findings {_pct(s['findings_accuracy'])}, "
            f"exceptions review {_pct(s['review_accuracy'])}, "
            f"extras {s['extras']}"
        )
        lines.append("")
        lines.append("| id | rule | parent | expected | got | outcome |")
        lines.append("|---|---|---|---|---|---|")
        for r in score["rows"]:
            lines.append(
                f"| {r['id']} | {r['rule']} | {r['parent']} | {r['expected']} "
                f"| {r['got']} | {r['outcome']} |"
            )
        if score["review_rows"]:
            lines.append("")
            lines.append("| exceptions review | expected | got | outcome |")
            lines.append("|---|---|---|---|")
            for r in score["review_rows"]:
                lines.append(
                    f"| {r['rule']} {r['parent']} | {r['expected']} | {r['got']} "
                    f"| {r['outcome']} |"
                )
        if s["extra_ids"]:
            lines.append("")
            lines.append(f"Extra findings (not in golden): {', '.join(s['extra_ids'])}")
        lines.append("")
    if len(scores) > 1:
        unstable = [r for r in drift_rows if not r["stable"]]
        lines.append(
            f"## Drift over {len(scores)} runs: "
            f"{len(drift_rows) - len(unstable)}/{len(drift_rows)} stable"
        )
        for r in unstable:
            lines.append(f"- {r['id']}: {r['recommendations']}")
        lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------ agent io


def build_prompt(fixture_dir, agent_doc=None):
    fixture = Path(fixture_dir)
    return (
        f"Act as the project-manager agent: read and follow {agent_doc or AGENT_DOC} "
        f"exactly.\n"
        f"Findings JSON to judge: {fixture / 'findings.json'}\n"
        f"ALL evidence is PRE-FETCHED at {fixture / 'evidence.json'} "
        f"(jira_batch_fetch format: issues.<KEY>.get/.comments/.devinfo). "
        f"This is an offline eval - do NOT call Jira, jira_batch_fetch, "
        f"jira_api.py or any network tool; a key absent from the evidence "
        f"file means 'could not verify intent'.\n"
        f"The roster is at memory/stakeholders/dev-roster.md as usual.\n"
        f"Produce the full report and END with the ```json board-sync-state``` "
        f"snapshot block covering EVERY finding (and exceptions_review when "
        f"applicable). The snapshot is what gets scored."
    )


def run_agent(prompt, claude_cmd, timeout, model=None):
    """One headless agent run; returns the transcript text.

    model=None inherits the CLI's default model - NOTE that this is whatever
    the local config says, not necessarily the agent frontmatter's `sonnet`.
    Pass --model explicitly for A/B comparisons (name such reports eval-ab-*
    so a pre-merge gate that reads eval reports can ignore them).
    """
    env = headless_env()
    cmd = [claude_cmd, "-p", prompt, "--allowedTools", "Read,Grep,Glob"]
    if model:
        cmd += ["--model", model]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        # transcripts may contain emoji/smart quotes - never let Windows
        # decode them as cp1252 (0x9d kills the reader thread)
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude exit {proc.returncode}: {proc.stderr.strip()[:300]}"
        )
    return proc.stdout


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
        help="path to the project-manager agent definition (default: "
        ".claude/agents/project-manager.md, else this toolkit's agents/)",
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        help="exit 1 when mean findings accuracy over valid runs is below this",
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

    if args.min_accuracy is not None:
        # Gate on the WORST axis, not findings alone: fabricated findings
        # (extras) and a flunked exceptions review must fail the gate even
        # when every expected finding matches.
        mean_findings = sum(s["summary"]["findings_accuracy"] for s in scores) / len(
            scores
        )
        mean_review = sum(s["summary"]["review_accuracy"] for s in scores) / len(scores)
        mean_accuracy = min(mean_findings, mean_review)
        total_extras = sum(s["summary"]["extras"] for s in scores)
        if mean_accuracy < args.min_accuracy:
            print(
                f"accuracy {mean_accuracy:.2f} (findings {mean_findings:.2f}, "
                f"review {mean_review:.2f}) below required {args.min_accuracy}",
                file=sys.stderr,
            )
            return 1
        if total_extras:
            print(
                f"{total_extras} extra finding(s) not in the golden set - "
                "fabrications fail the gate",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
