#!/usr/bin/env python3
"""Diff two /board-sync --report files and print a "what changed" section.

Consumes the machine-readable state snapshot each report embeds as its last
fenced block (```json board-sync-state ... ```, emitted per the
project-manager agent output spec). Deterministic diff - no LLM involved.

Findings are keyed by (rule, parent), NOT by raw id: the id embeds a hash of
the children set, so a changed blocker/child list would otherwise show up as
a resolved+new pair instead of the same finding.

Usage:
    python scripts/board_sync_delta.py NEW_REPORT.md PREV_REPORT.md

Prints a markdown "## Delta vs previous run" section to stdout.
ALWAYS exits 0 (the nightly pipeline must never break on a delta problem);
degraded cases print a one-line note instead of a diff and explain on stderr.
"""

import json
import os
import re
import sys

SNAPSHOT_RE = re.compile(r"```json board-sync-state\s*\n(.*?)\n\s*```", re.S)


def extract_snapshot(md_text):
    """Return the parsed last board-sync-state block, or None."""
    blocks = SNAPSHOT_RE.findall(md_text)
    if not blocks:
        return None
    try:
        return json.loads(blocks[-1])
    except json.JSONDecodeError:
        return None


def _by_rule_parent(snap):
    return {
        (f["rule"], f["parent"]): f
        for f in snap.get("findings") or []
        if isinstance(f, dict) and "rule" in f and "parent" in f
    }


def _label(key):
    rule, parent = key
    return f"{rule}-{parent}"


def diff_lines(new_snap, old_snap):
    """Markdown bullet lines describing board movement between two snapshots."""
    lines = []
    old_f, new_f = _by_rule_parent(old_snap), _by_rule_parent(new_snap)

    for key in sorted(new_f.keys() & old_f.keys()):
        o, n = old_f[key], new_f[key]
        if o.get("recommendation") != n.get("recommendation"):
            suffix = f" (candidate {n['candidate']})" if n.get("candidate") else ""
            lines.append(
                f"- {_label(key)}: {o.get('recommendation')} -> "
                f"{n.get('recommendation')}{suffix}"
            )
        elif o.get("candidate") != n.get("candidate"):
            lines.append(
                f"- {_label(key)}: candidate {o.get('candidate')} -> "
                f"{n.get('candidate')}"
            )
    for key in sorted(new_f.keys() - old_f.keys()):
        n = new_f[key]
        suffix = f" (candidate {n['candidate']})" if n.get("candidate") else ""
        lines.append(f"- NEW {_label(key)}: {n.get('recommendation')}{suffix}")
    for key in sorted(old_f.keys() - new_f.keys()):
        lines.append(
            f"- RESOLVED {_label(key)} (was {old_f[key].get('recommendation')})"
        )

    old_sup, new_sup = old_snap.get("suppressed"), new_snap.get("suppressed")
    if old_sup != new_sup:
        lines.append(f"- suppressed: {old_sup} -> {new_sup}")

    return lines


def main(argv):
    if len(argv) != 3:
        print(
            "usage: board_sync_delta.py NEW_REPORT.md PREV_REPORT.md", file=sys.stderr
        )
        return 0

    try:
        new_text = open(argv[1], encoding="utf-8").read()
        old_text = open(argv[2], encoding="utf-8").read()
    except OSError as exc:
        print(f"delta skipped: {exc}", file=sys.stderr)
        return 0

    new_snap, old_snap = extract_snapshot(new_text), extract_snapshot(old_text)
    prev_label = (old_snap or {}).get("date") or os.path.basename(argv[2])

    print(f"## Delta vs previous run ({prev_label})")
    print()
    if new_snap is None:
        print("_Delta unavailable: today's report has no state snapshot._")
        return 0
    if old_snap is None:
        print(
            "_Delta unavailable: previous report has no state snapshot "
            "(skip stub or pre-delta format)._"
        )
        return 0

    lines = diff_lines(new_snap, old_snap)
    if lines:
        print("\n".join(lines))
    else:
        print("- No board changes since the previous run.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
