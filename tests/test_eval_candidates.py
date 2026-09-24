"""Unit tests for scripts/eval_candidates.py (registry machinery only)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import eval_candidates  # noqa: E402


def bs_entry(**over):
    entry = {
        "source": "board-sync",
        "id": "R1-PROJ-520-a1b2",
        "rule": "R1",
        "parent": "PROJ-520",
        "agent": {"recommendation": "FIX"},
        "human": {"decision": "SKIP", "reason": "deliberately parked"},
    }
    entry.update(over)
    return entry


def pr_entry(**over):
    entry = {
        "source": "prioritize",
        "key": "PROJ-124",
        "agent": {"state": "READY", "score": 3.0},
        "human": {"state": "NEEDS-GROOMING", "reason": "AC is stale"},
    }
    entry.update(over)
    return entry


def test_validate_ok_both_sources():
    assert eval_candidates.validate(bs_entry(), "board-sync") == []
    assert eval_candidates.validate(pr_entry(), "prioritize") == []


def test_validate_requires_reason():
    entry = bs_entry(human={"decision": "SKIP", "reason": "  "})
    problems = eval_candidates.validate(entry, "board-sync")
    assert any("reason" in p for p in problems)


def test_validate_board_sync_required_fields():
    problems = eval_candidates.validate({"human": {"reason": "x"}}, "board-sync")
    joined = " ".join(problems)
    for field in ("id", "rule", "parent", "agent", "decision"):
        assert field in joined


def test_validate_prioritize_required_fields():
    problems = eval_candidates.validate({"human": {"reason": "x"}}, "prioritize")
    joined = " ".join(problems)
    for field in ("key", "state"):
        assert field in joined


def test_add_appends_and_fills_defaults(tmp_path):
    path = tmp_path / "candidates.jsonl"
    entry = bs_entry()
    del entry["source"]
    assert eval_candidates.add(entry, "board-sync", path) == []
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["source"] == "board-sync"
    assert saved["date"]  # auto-filled


def test_add_dedups_same_disagreement(tmp_path):
    path = tmp_path / "candidates.jsonl"
    assert eval_candidates.add(bs_entry(), "board-sync", path) == []
    assert eval_candidates.add(bs_entry(date="2026-09-01"), "board-sync", path) == []
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]
    assert len(lines) == 1  # date alone does not make it a new case


def test_add_dedups_across_finding_id_change(tmp_path):
    # The finding id embeds a children-set hash and changes between scans -
    # the same disagreement under a new id must still dedup.
    path = tmp_path / "candidates.jsonl"
    eval_candidates.add(bs_entry(), "board-sync", path)
    eval_candidates.add(bs_entry(id="R1-PROJ-520-ffff"), "board-sync", path)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]
    assert len(lines) == 1


def test_add_keeps_distinct_disagreements(tmp_path):
    path = tmp_path / "candidates.jsonl"
    eval_candidates.add(bs_entry(), "board-sync", path)
    other = bs_entry(id="R2-PROJ-523-c3d4", rule="R2", parent="PROJ-523")
    eval_candidates.add(other, "board-sync", path)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]
    assert len(lines) == 2


def test_add_rejects_invalid(tmp_path):
    path = tmp_path / "candidates.jsonl"
    problems = eval_candidates.add({"human": {}}, "board-sync", path)
    assert problems
    assert not path.exists()


def test_load_rejects_corrupt_line(tmp_path):
    path = tmp_path / "candidates.jsonl"
    path.write_text('{"ok": 1}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        eval_candidates.load(path)


def test_render_list_marks_missing_evidence(tmp_path, monkeypatch):
    bs = tmp_path / "bs.jsonl"
    pr = tmp_path / "pr.jsonl"
    monkeypatch.setattr(
        eval_candidates, "REGISTRIES", {"board-sync": bs, "prioritize": pr}
    )
    eval_candidates.add(bs_entry(), "board-sync", bs)
    eval_candidates.add(pr_entry(evidence={"get": {}}), "prioritize", pr)
    out = eval_candidates.render_list(["board-sync", "prioritize"])
    assert "R1 PROJ-520 (R1-PROJ-520-a1b2)" in out
    assert "[no evidence frozen]" in out  # board-sync entry has none
    assert "PROJ-124" in out
    assert "READY (3.0)" in out
    assert "2 pending candidate(s)" in out
