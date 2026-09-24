#!/usr/bin/env python3
"""Eval-candidate registry: live PO overrides -> future golden eval cases.

When a /board-sync (or a prioritization) run ends with the human deciding
DIFFERENTLY from the agent's recommendation (a refused FIX judged wrong, a
corrected candidate, a disputed state), that disagreement is a free golden case
for the judgment evals - if it gets captured with its evidence while the run's
data is still at hand. This script owns the capture side; curation into the
frozen fixtures (findings/evidence/expected, spine/batch/expected) stays a
human-reviewed step.

Registry files (JSONL, one candidate per line, colocated with the fixture
they feed):
    tests/fixtures/board_sync_eval/candidates.jsonl
    tests/fixtures/prioritize_eval/candidates.jsonl

Entry shape (validated on add):
    board-sync: {date?, source, id, rule, parent,
                 agent: {recommendation[, candidate]},
                 human: {decision[, candidate], reason},
                 finding?, evidence?}
    prioritize: {date?, source, key,
                 agent: {state[, score]},
                 human: {state, reason},
                 evidence?}
`finding` / `evidence` are the frozen slices from the run (the finding object,
the batch-fetch issues.<KEY> slice) - optional but strongly encouraged: without
them the case cannot be promoted into a fixture later.

Usage:
    python scripts/eval_candidates.py add --source board-sync --json '<entry>'
    python scripts/eval_candidates.py add --source prioritize < entry.json
    python scripts/eval_candidates.py list [--source ...]

Exit codes: 0 ok (add: appended or exact duplicate skipped); 1 invalid entry
or unreadable registry.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"
REGISTRIES = {
    "board-sync": FIXTURES / "board_sync_eval" / "candidates.jsonl",
    "prioritize": FIXTURES / "prioritize_eval" / "candidates.jsonl",
}


def validate(entry, source):
    """Return a list of problems (empty = valid)."""
    problems = []
    agent = entry.get("agent")
    human = entry.get("human")
    if not isinstance(agent, dict):
        problems.append("agent must be an object")
        agent = {}
    if not isinstance(human, dict):
        problems.append("human must be an object")
        human = {}
    if not (human.get("reason") or "").strip():
        problems.append("human.reason is required (the why of the override)")
    if source == "board-sync":
        for field in ("id", "rule", "parent"):
            if not entry.get(field):
                problems.append(f"{field} is required")
        if not agent.get("recommendation"):
            problems.append("agent.recommendation is required")
        if not human.get("decision"):
            problems.append("human.decision is required")
    else:  # prioritize
        if not entry.get("key"):
            problems.append("key is required")
        if not agent.get("state"):
            problems.append("agent.state is required")
        if not human.get("state"):
            problems.append("human.state is required")
    return problems


def _identity(entry, source):
    """What makes two candidates the same disagreement (date excluded).

    board-sync keys on (rule, parent), NOT the finding id: the id embeds a
    hash of the children set, so the same disagreement resurfaces under a
    new id when a different child goes active - id-based dedup would let
    duplicates through.
    """
    if source == "board-sync":
        return (
            entry.get("rule"),
            entry.get("parent"),
            json.dumps(entry.get("agent"), sort_keys=True),
            json.dumps(entry.get("human"), sort_keys=True),
        )
    return (
        entry.get("key"),
        json.dumps(entry.get("agent"), sort_keys=True),
        json.dumps(entry.get("human"), sort_keys=True),
    )


def load(path):
    if not path.exists():
        return []
    entries = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{n}: invalid JSON ({exc})") from exc
    return entries


def add(entry, source, path):
    problems = validate(entry, source)
    if problems:
        return problems
    entry.setdefault("source", source)
    entry.setdefault("date", datetime.date.today().isoformat())
    existing = load(path)
    if any(_identity(e, source) == _identity(entry, source) for e in existing):
        print(f"duplicate - already registered in {path.name}, nothing added")
        return []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"added 1 candidate -> {path} ({len(existing) + 1} total)")
    return []


def render_list(sources):
    lines = []
    total = 0
    for source in sources:
        path = REGISTRIES[source]
        entries = load(path)
        total += len(entries)
        lines.append(f"## {source} ({len(entries)}) - {path}")
        if not entries:
            lines.append("(no pending candidates)")
        else:
            lines.append("| date | case | agent said | human decided | reason |")
            lines.append("|---|---|---|---|---|")
            for e in entries:
                agent, human = e.get("agent") or {}, e.get("human") or {}
                if source == "board-sync":
                    case = f"{e.get('rule')} {e.get('parent')} ({e.get('id')})"
                    said = agent.get("recommendation", "?")
                    if agent.get("candidate"):
                        said += f" ({agent['candidate']})"
                    decided = human.get("decision", "?")
                    if human.get("candidate"):
                        decided += f" ({human['candidate']})"
                else:
                    case = e.get("key", "?")
                    said = agent.get("state", "?")
                    if agent.get("score") is not None:
                        said += f" ({agent['score']})"
                    decided = human.get("state", "?")
                frozen = "" if e.get("evidence") else " [no evidence frozen]"
                lines.append(
                    f"| {e.get('date', '?')} | {case} | {said} | {decided} "
                    f"| {human.get('reason', '')}{frozen} |"
                )
        lines.append("")
    lines.append(
        f"{total} pending candidate(s). Promotion into the frozen fixtures "
        "(+ expected.json) is a human-reviewed step - delete promoted lines."
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add", help="register one override candidate")
    p_add.add_argument("--source", choices=sorted(REGISTRIES), required=True)
    p_add.add_argument("--json", help="the entry as inline JSON (default: read stdin)")
    p_list = sub.add_parser("list", help="show pending candidates")
    p_list.add_argument("--source", choices=sorted(REGISTRIES))
    args = parser.parse_args(argv)

    if args.cmd == "add":
        raw = args.json if args.json is not None else sys.stdin.read()
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"entry is not valid JSON: {exc}", file=sys.stderr)
            return 1
        if not isinstance(entry, dict):
            print("entry must be a JSON object", file=sys.stderr)
            return 1
        try:
            problems = add(entry, args.source, REGISTRIES[args.source])
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if problems:
            for p in problems:
                print(f"invalid entry: {p}", file=sys.stderr)
            return 1
        return 0

    sources = [args.source] if args.source else sorted(REGISTRIES)
    try:
        print(render_list(sources))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
