"""Tests for scripts/eval_prioritize.py - readiness-state eval scoring."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import eval_prioritize as ep  # noqa: E402


# ------------------------------------------------------------------ fixtures


def expected_doc():
    return {
        "items": [
            {"key": "PROJ-501", "state": "READY", "score": 3.0},
            {"key": "PROJ-502", "state": "PARALLEL-OK", "score": 2.1},
            {"key": "PROJ-503", "state": "BLOCKED", "score": 0.3},
        ]
    }


def snapshot(items):
    return {"mode": "initiative", "date": "2026-08-17", "items": items}


def full_match_snapshot():
    return snapshot(
        [
            {"key": "PROJ-501", "state": "READY", "score": 3.0},
            {"key": "PROJ-502", "state": "PARALLEL-OK", "score": 2.1},
            {"key": "PROJ-503", "state": "BLOCKED", "score": 0.3},
        ]
    )


def transcript_with(snap):
    return "report\n```json prioritize-state\n" + json.dumps(snap) + "\n```\n"


# ------------------------------------------------------------------- scoring


def test_score_all_match():
    result = ep.score_run(full_match_snapshot(), expected_doc())
    assert [r["outcome"] for r in result["rows"]] == ["MATCH", "MATCH", "MATCH"]
    assert result["summary"]["state_accuracy"] == 1.0
    assert result["summary"]["extras"] == 0


def test_state_mismatch_case_insensitive_match():
    snap = full_match_snapshot()
    snap["items"][0]["state"] = "ready"  # case difference only -> MATCH
    snap["items"][1]["state"] = "NEEDS-GROOMING"  # real mismatch
    result = ep.score_run(snap, expected_doc())
    outcomes = {r["key"]: r["outcome"] for r in result["rows"]}
    assert outcomes["PROJ-501"] == "MATCH"
    assert outcomes["PROJ-502"] == "MISMATCH"
    row = next(r for r in result["rows"] if r["key"] == "PROJ-502")
    assert "NEEDS-GROOMING" in row["got"]


def test_score_tolerance():
    snap = full_match_snapshot()
    snap["items"][0]["score"] = 3.04  # inside +-0.05
    snap["items"][1]["score"] = 2.5  # off by 0.4 -> score mismatch
    result = ep.score_run(snap, expected_doc())
    outcomes = {r["key"]: r["outcome"] for r in result["rows"]}
    assert outcomes["PROJ-501"] == "MATCH"
    assert outcomes["PROJ-502"] == "MISMATCH"


def test_expected_without_score_ignores_score():
    expected = {"items": [{"key": "PROJ-501", "state": "SHALLOW"}]}
    snap = snapshot([{"key": "PROJ-501", "state": "SHALLOW"}])
    result = ep.score_run(snap, expected)
    assert result["rows"][0]["outcome"] == "MATCH"


def test_missing_and_extra():
    snap = snapshot(
        [
            {"key": "PROJ-501", "state": "READY", "score": 3.0},
            {"key": "PROJ-999", "state": "READY", "score": 1.0},
        ]
    )
    result = ep.score_run(snap, expected_doc())
    outcomes = {r["key"]: r["outcome"] for r in result["rows"]}
    assert outcomes["PROJ-502"] == "MISSING"
    assert outcomes["PROJ-503"] == "MISSING"
    assert result["summary"]["extras"] == 1
    assert result["summary"]["extra_keys"] == ["PROJ-999"]


# --------------------------------------------------------------------- drift


def test_drift_flags_unstable_state():
    stable = full_match_snapshot()
    flapping = full_match_snapshot()
    flapping["items"][0]["state"] = "PARALLEL-OK"
    rows = ep.drift([stable, flapping], expected_doc())
    by_key = {r["key"]: r for r in rows}
    assert by_key["PROJ-501"]["stable"] is False
    assert by_key["PROJ-501"]["states"] == ["READY", "PARALLEL-OK"]
    assert by_key["PROJ-502"]["stable"] is True


# ------------------------------------------------------------------- render


def test_render_markdown_summary_and_misses():
    snap = full_match_snapshot()
    snap["items"][2]["state"] = "READY"
    scores = [ep.score_run(snap, expected_doc())]
    md = ep.render_markdown(scores, ep.drift([snap], expected_doc()))
    assert "PROJ-503" in md
    assert "MISMATCH" in md
    assert "67%" in md


# --------------------------------------------------------------------- main


def _write_fixture(tmp_path):
    (tmp_path / "batch.json").write_text(
        json.dumps({"meta": {}, "issues": {}}), encoding="utf-8"
    )
    (tmp_path / "spine.json").write_text(
        json.dumps({"target": "PROJ-500", "stories": ["PROJ-501"]}), encoding="utf-8"
    )
    (tmp_path / "expected.json").write_text(
        json.dumps(expected_doc()), encoding="utf-8"
    )
    return tmp_path


def test_build_prompt_forbids_jira_and_names_paths(tmp_path):
    fixture = _write_fixture(tmp_path)
    prompt = ep.build_prompt(fixture)
    assert str(fixture / "batch.json") in prompt
    assert str(fixture / "spine.json") in prompt
    assert "do NOT" in prompt and "Jira" in prompt
    assert "prioritize-state" in prompt


def test_main_scores_stubbed_runs_and_min_accuracy(monkeypatch, tmp_path, capsys):
    fixture = _write_fixture(tmp_path)
    monkeypatch.setattr(
        ep,
        "run_agent",
        lambda prompt, cmd, timeout, **kw: transcript_with(full_match_snapshot()),
    )
    assert ep.main(["--fixture", str(fixture)]) == 0
    assert "100%" in capsys.readouterr().out
    miss = full_match_snapshot()
    miss["items"][0]["state"] = "BLOCKED"
    monkeypatch.setattr(
        ep, "run_agent", lambda prompt, cmd, timeout, **kw: transcript_with(miss)
    )
    assert ep.main(["--fixture", str(fixture), "--min-accuracy", "0.9"]) == 1


def test_main_without_snapshot_exits_1(monkeypatch, tmp_path, capsys):
    fixture = _write_fixture(tmp_path)
    monkeypatch.setattr(
        ep, "run_agent", lambda prompt, cmd, timeout, **kw: "no block here"
    )
    assert ep.main(["--fixture", str(fixture)]) == 1
    assert "no valid snapshot" in capsys.readouterr().err
