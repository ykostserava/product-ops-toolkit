#!/usr/bin/env python3
"""Diff two nightly /prioritize reports and print a "what changed" section.

Consumes the machine-readable state snapshot each report embeds as its last
fenced block (```json prioritize-state ... ```, emitted per the po-prioritizer
output spec section 9). Deterministic diff - no LLM involved.

Usage:
    python scripts/prioritize_delta.py NEW_REPORT.md PREV_REPORT.md

Prints a markdown "## Delta vs previous run" section to stdout.
ALWAYS exits 0 (the nightly pipeline must never break on a delta problem);
degraded cases print a one-line note instead of a diff and explain on stderr.
"""

import json
import os
import re
import sys

SNAPSHOT_RE = re.compile(r"```json prioritize-state\s*\n(.*?)\n\s*```", re.S)


def extract_snapshot(md_text):
    """Return the parsed last prioritize-state block, or None."""
    blocks = SNAPSHOT_RE.findall(md_text)
    if not blocks:
        return None
    try:
        return json.loads(blocks[-1])
    except json.JSONDecodeError:
        return None


def _by_key(entries):
    return {e["key"]: e for e in entries or [] if isinstance(e, dict) and "key" in e}


def _score_note(old, new):
    old_s, new_s = old.get("score"), new.get("score")
    if old_s is not None and new_s is not None and old_s != new_s:
        return f" (score {old_s} -> {new_s})"
    return ""


def diff_lines(new_snap, old_snap):
    """Markdown bullet lines describing state movement between two snapshots."""
    lines = []

    old_items, new_items = (
        _by_key(old_snap.get("items")),
        _by_key(new_snap.get("items")),
    )
    for key in sorted(new_items.keys() & old_items.keys()):
        o, n = old_items[key], new_items[key]
        if o.get("state") != n.get("state"):
            lines.append(
                f"- {key}: {o.get('state')} -> {n.get('state')}{_score_note(o, n)}"
            )
    for key in sorted(new_items.keys() - old_items.keys()):
        lines.append(
            f"- {key}: entered the assessed set as {new_items[key].get('state')}"
        )
    for key in sorted(old_items.keys() - new_items.keys()):
        lines.append(
            f"- {key}: left the assessed set (was {old_items[key].get('state')})"
        )

    old_inits, new_inits = (
        _by_key(old_snap.get("initiatives")),
        _by_key(new_snap.get("initiatives")),
    )
    for key in sorted(new_inits.keys() & old_inits.keys()):
        o, n = old_inits[key], new_inits[key]
        changes = []
        if o.get("tier") != n.get("tier"):
            changes.append(f"tier {o.get('tier')} -> {n.get('tier')}")
        if o.get("ready_pct") != n.get("ready_pct"):
            changes.append(f"ready {o.get('ready_pct')}% -> {n.get('ready_pct')}%")
        if changes:
            lines.append(f"- {key}: {', '.join(changes)}")

    return lines


def main(argv):
    if len(argv) != 3:
        print(
            "usage: prioritize_delta.py NEW_REPORT.md PREV_REPORT.md", file=sys.stderr
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
            "_Delta unavailable: previous report has no state snapshot (skip stub or pre-delta format)._"
        )
        return 0

    lines = diff_lines(new_snap, old_snap)
    if lines:
        print("\n".join(lines))
    else:
        print("- No state changes since the previous run.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
