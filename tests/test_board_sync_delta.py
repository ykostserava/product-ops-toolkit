"""Tests for scripts/board_sync_delta.py - snapshot extraction + diff."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from board_sync_delta import diff_lines, extract_snapshot, main  # noqa: E402


def make_report(snapshot=None, garbage_fence=False):
    body = "# Report\n\nSome prose.\n\n"
    if garbage_fence:
        body += "```json board-sync-state\nnot json at all\n```\n"
    elif snapshot is not None:
        body += f"```json board-sync-state\n{json.dumps(snapshot)}\n```\n"
    return body


SNAP_OLD = {
    "date": "2026-08-12",
    "findings": [
        {
            "id": "R3-PROJ-285-0f8b",
            "rule": "R3",
            "parent": "PROJ-285",
            "recommendation": "FLAG_ONLY",
        },
        {
            "id": "R4-PROJ-233-d2e9",
            "rule": "R4",
            "parent": "PROJ-233",
            "recommendation": "ASSIGN",
            "candidate": "dev.three@example.com",
        },
        {
            "id": "R4-PROJ-231-08a7",
            "rule": "R4",
            "parent": "PROJ-231",
            "recommendation": "FLAG_ONLY",
        },
    ],
    "suppressed": 2,
}
SNAP_NEW = {
    "date": "2026-08-13",
    "findings": [
        # same (rule, parent) as before but different children-hash id - the
        # diff must treat it as the SAME finding, not a resolved+new pair
        {
            "id": "R3-PROJ-285-ffff",
            "rule": "R3",
            "parent": "PROJ-285",
            "recommendation": "FLAG_ONLY",
        },
        {
            "id": "R4-PROJ-231-08a7",
            "rule": "R4",
            "parent": "PROJ-231",
            "recommendation": "ASSIGN",
            "candidate": "dev.two@example.com",
        },
        {
            "id": "R5-PROJ-347-68cb",
            "rule": "R5",
            "parent": "PROJ-347",
            "recommendation": "FLAG_ONLY",
        },
    ],
    "suppressed": 3,
}


def test_extract_snapshot_returns_last_block():
    md = make_report(SNAP_OLD) + make_report(SNAP_NEW)
    assert extract_snapshot(md)["date"] == "2026-08-13"


def test_extract_snapshot_none_when_absent():
    assert extract_snapshot("# Report\nno snapshot here\n") is None


def test_extract_snapshot_none_on_malformed_json():
    assert extract_snapshot(make_report(garbage_fence=True)) is None


def test_diff_reports_new_finding():
    assert "- NEW R5-PROJ-347: FLAG_ONLY" in diff_lines(SNAP_NEW, SNAP_OLD)


def test_diff_reports_resolved_finding():
    assert "- RESOLVED R4-PROJ-233 (was ASSIGN)" in diff_lines(SNAP_NEW, SNAP_OLD)


def test_diff_reports_recommendation_change_with_candidate():
    lines = diff_lines(SNAP_NEW, SNAP_OLD)
    assert "- R4-PROJ-231: FLAG_ONLY -> ASSIGN (candidate dev.two@example.com)" in lines


def test_diff_keys_by_rule_and_parent_not_raw_id():
    # PROJ-285's id churned (children hash) but rule+parent+recommendation are
    # unchanged - must stay silent
    assert not any("PROJ-285" in line for line in diff_lines(SNAP_NEW, SNAP_OLD))


def test_diff_reports_candidate_only_change():
    old = {
        "date": "d",
        "findings": [
            {
                "id": "x",
                "rule": "R4",
                "parent": "PROJ-1",
                "recommendation": "ASSIGN",
                "candidate": "a@example.com",
            }
        ],
        "suppressed": 0,
    }
    new = {
        "date": "d",
        "findings": [
            {
                "id": "x",
                "rule": "R4",
                "parent": "PROJ-1",
                "recommendation": "ASSIGN",
                "candidate": "b@example.com",
            }
        ],
        "suppressed": 0,
    }
    assert "- R4-PROJ-1: candidate a@example.com -> b@example.com" in diff_lines(
        new, old
    )


def test_diff_reports_suppressed_count_change():
    assert "- suppressed: 2 -> 3" in diff_lines(SNAP_NEW, SNAP_OLD)


def test_diff_empty_when_identical():
    assert diff_lines(SNAP_OLD, SNAP_OLD) == []


def test_diff_ignores_exceptions_review_field():
    # forward-compat: the exceptions-lifecycle snapshot section must not break
    # or pollute the findings diff
    old = dict(SNAP_OLD)
    new = dict(SNAP_OLD)
    new["exceptions_review"] = [
        {"parent": "PROJ-94", "rule": "R2", "verdict": "KEEP"},
        {"parent": "PROJ-95", "rule": "R2", "verdict": "LIFT"},
    ]
    assert diff_lines(new, old) == []


def test_main_no_changes_message(tmp_path, capsys):
    new = tmp_path / "new.md"
    old = tmp_path / "old.md"
    new.write_text(make_report(SNAP_OLD), encoding="utf-8")
    old.write_text(make_report(SNAP_OLD), encoding="utf-8")
    assert main(["prog", str(new), str(old)]) == 0
    out = capsys.readouterr().out
    assert "## Delta vs previous run (2026-08-12)" in out
    assert "- No board changes since the previous run." in out


def test_main_graceful_when_prev_has_no_snapshot(tmp_path, capsys):
    new = tmp_path / "new.md"
    old = tmp_path / "old.md"
    new.write_text(make_report(SNAP_NEW), encoding="utf-8")
    old.write_text("# board-sync report - SKIPPED\n", encoding="utf-8")
    assert main(["prog", str(new), str(old)]) == 0
    assert "previous report has no state snapshot" in capsys.readouterr().out


def test_main_graceful_on_missing_file(tmp_path, capsys):
    new = tmp_path / "new.md"
    new.write_text(make_report(SNAP_NEW), encoding="utf-8")
    assert main(["prog", str(new), str(tmp_path / "absent.md")]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""  # nothing lands in the report on a read failure
    assert "delta skipped" in captured.err
