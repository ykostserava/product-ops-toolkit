"""Tests for scripts/prioritize_delta.py - snapshot extraction + diff."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from prioritize_delta import diff_lines, extract_snapshot, main  # noqa: E402


def make_report(snapshot=None, garbage_fence=False):
    body = "# Report\n\nSome prose.\n\n"
    if garbage_fence:
        body += "```json prioritize-state\nnot json at all\n```\n"
    elif snapshot is not None:
        body += f"```json prioritize-state\n{json.dumps(snapshot)}\n```\n"
    return body


SNAP_OLD = {
    "mode": "roadmap",
    "date": "2026-08-11",
    "items": [
        {"key": "PROJ-124", "state": "READY", "score": 3.0},
        {"key": "PROJ-321", "state": "READY", "score": 3.6},
        {"key": "PROJ-999", "state": "BLOCKED", "score": 0.3},
    ],
    "initiatives": [{"key": "PROJ-170", "tier": 1, "ready_pct": 83}],
}
SNAP_NEW = {
    "mode": "roadmap",
    "date": "2026-08-12",
    "items": [
        {"key": "PROJ-124", "state": "BLOCKED", "score": 0.3},
        {"key": "PROJ-321", "state": "READY", "score": 3.6},
        {"key": "PROJ-500", "state": "READY", "score": 2.1},
    ],
    "initiatives": [{"key": "PROJ-170", "tier": 1, "ready_pct": 100}],
}


def test_extract_snapshot_returns_last_block():
    md = make_report(SNAP_OLD) + make_report(SNAP_NEW)
    assert extract_snapshot(md)["date"] == "2026-08-12"


def test_extract_snapshot_none_when_absent():
    assert extract_snapshot("# Report\nno snapshot here\n") is None


def test_extract_snapshot_none_on_malformed_json():
    assert extract_snapshot(make_report(garbage_fence=True)) is None


def test_diff_reports_state_change_with_score():
    lines = diff_lines(SNAP_NEW, SNAP_OLD)
    assert "- PROJ-124: READY -> BLOCKED (score 3.0 -> 0.3)" in lines


def test_diff_reports_entered_and_left():
    lines = diff_lines(SNAP_NEW, SNAP_OLD)
    assert "- PROJ-500: entered the assessed set as READY" in lines
    assert "- PROJ-999: left the assessed set (was BLOCKED)" in lines


def test_diff_reports_initiative_ready_pct():
    lines = diff_lines(SNAP_NEW, SNAP_OLD)
    assert "- PROJ-170: ready 83% -> 100%" in lines


def test_diff_silent_on_unchanged_item():
    assert not any("PROJ-321" in line for line in diff_lines(SNAP_NEW, SNAP_OLD))


def test_diff_empty_when_identical():
    assert diff_lines(SNAP_OLD, SNAP_OLD) == []


def test_main_no_changes_message(tmp_path, capsys):
    new = tmp_path / "new.md"
    old = tmp_path / "old.md"
    new.write_text(make_report(SNAP_OLD), encoding="utf-8")
    old.write_text(make_report(SNAP_OLD), encoding="utf-8")
    assert main(["prog", str(new), str(old)]) == 0
    out = capsys.readouterr().out
    assert "## Delta vs previous run (2026-08-11)" in out
    assert "- No state changes since the previous run." in out


def test_main_graceful_when_prev_has_no_snapshot(tmp_path, capsys):
    new = tmp_path / "new.md"
    old = tmp_path / "old.md"
    new.write_text(make_report(SNAP_NEW), encoding="utf-8")
    old.write_text("# WL prioritize pre-run - SKIPPED\n", encoding="utf-8")
    assert main(["prog", str(new), str(old)]) == 0
    assert "previous report has no state snapshot" in capsys.readouterr().out


def test_main_graceful_on_missing_file(tmp_path, capsys):
    new = tmp_path / "new.md"
    new.write_text(make_report(SNAP_NEW), encoding="utf-8")
    assert main(["prog", str(new), str(tmp_path / "absent.md")]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""  # nothing lands in the report on a read failure
    assert "delta skipped" in captured.err
