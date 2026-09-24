"""Tests for scripts/eval_board_sync.py - judgment eval scoring and drift."""

import os
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import eval_board_sync as ebs  # noqa: E402


# ------------------------------------------------------------------ fixtures


def expected_doc():
    return {
        "findings": [
            {
                "id": "R1-PROJ-108-aaaa",
                "rule": "R1",
                "parent": "PROJ-108",
                "recommendation": "FIX",
            },
            {
                "id": "R4-PROJ-420-bbbb",
                "rule": "R4",
                "parent": "PROJ-420",
                "recommendation": "ASSIGN",
                "candidate": "dev.one@example.com",
            },
        ],
        "exceptions_review": [{"rule": "R2", "parent": "PROJ-94", "verdict": "KEEP"}],
    }


def snapshot(findings=None, review=None):
    snap = {"date": "2026-08-17", "findings": findings or [], "suppressed": 1}
    if review is not None:
        snap["exceptions_review"] = review
    return snap


def full_match_snapshot():
    return snapshot(
        findings=[
            {
                "id": "R1-PROJ-108-aaaa",
                "rule": "R1",
                "parent": "PROJ-108",
                "recommendation": "FIX",
            },
            {
                "id": "R4-PROJ-420-bbbb",
                "rule": "R4",
                "parent": "PROJ-420",
                "recommendation": "ASSIGN",
                "candidate": "dev.one@example.com",
            },
        ],
        review=[{"rule": "R2", "parent": "PROJ-94", "verdict": "KEEP"}],
    )


def transcript_with(snap):
    return "report text\n```json board-sync-state\n" + json.dumps(snap) + "\n```\n"


# ------------------------------------------------------------------- scoring


def test_score_all_match_and_accuracy():
    result = ebs.score_run(full_match_snapshot(), expected_doc())
    assert [r["outcome"] for r in result["rows"]] == ["MATCH", "MATCH"]
    assert result["summary"]["findings_accuracy"] == 1.0
    assert result["summary"]["review_accuracy"] == 1.0
    assert result["summary"]["extras"] == 0


def test_score_candidate_mismatch_counts_as_miss():
    snap = full_match_snapshot()
    snap["findings"][1]["candidate"] = "dev.three@example.com"
    result = ebs.score_run(snap, expected_doc())
    row = next(r for r in result["rows"] if r["id"] == "R4-PROJ-420-bbbb")
    assert row["outcome"] == "MISMATCH"
    assert "dev.three" in row["got"]
    assert result["summary"]["findings_accuracy"] == 0.5


def test_score_missing_and_extra():
    snap = snapshot(
        findings=[
            {
                "id": "R1-PROJ-108-aaaa",
                "rule": "R1",
                "parent": "PROJ-108",
                "recommendation": "FIX",
            },
            {
                "id": "R9-PROJ-999-ffff",
                "rule": "R9",
                "parent": "PROJ-999",
                "recommendation": "FIX",
            },
        ]
    )
    result = ebs.score_run(snap, expected_doc())
    outcomes = {r["id"]: r["outcome"] for r in result["rows"]}
    assert outcomes["R4-PROJ-420-bbbb"] == "MISSING"
    assert result["summary"]["extras"] == 1
    assert result["summary"]["findings_accuracy"] == 0.5


def test_exceptions_review_scored_by_rule_parent():
    snap = full_match_snapshot()
    snap["exceptions_review"] = [{"rule": "R2", "parent": "PROJ-94", "verdict": "LIFT"}]
    result = ebs.score_run(snap, expected_doc())
    assert [r["outcome"] for r in result["review_rows"]] == ["MISMATCH"]
    assert result["summary"]["review_accuracy"] == 0.0
    # absent block entirely -> all review rows MISSING
    result = ebs.score_run(snapshot(findings=[]), expected_doc())
    assert [r["outcome"] for r in result["review_rows"]] == ["MISSING"]


def test_recommendation_match_is_case_insensitive():
    snap = full_match_snapshot()
    snap["findings"][0]["recommendation"] = "fix"
    result = ebs.score_run(snap, expected_doc())
    assert result["rows"][0]["outcome"] == "MATCH"


# --------------------------------------------------------------------- drift


def test_drift_flags_unstable_recommendation():
    stable = full_match_snapshot()
    flapping = full_match_snapshot()
    flapping["findings"][0]["recommendation"] = "SKIP"
    rows = ebs.drift([stable, flapping], expected_doc())
    by_id = {r["id"]: r for r in rows}
    assert by_id["R1-PROJ-108-aaaa"]["stable"] is False
    assert by_id["R1-PROJ-108-aaaa"]["recommendations"] == ["FIX", "SKIP"]
    assert by_id["R4-PROJ-420-bbbb"]["stable"] is True


# ------------------------------------------------------------------- render


def test_render_markdown_lists_misses_and_summary():
    snap = full_match_snapshot()
    snap["findings"][0]["recommendation"] = "SKIP"
    scores = [ebs.score_run(snap, expected_doc())]
    md = ebs.render_markdown(scores, ebs.drift([snap], expected_doc()))
    assert "R1-PROJ-108-aaaa" in md
    assert "MISMATCH" in md
    assert "50%" in md


# ------------------------------------------------------------------ agent io


def _fake_claude(tmp_path, body):
    """A stand-in for the claude CLI that runs on every platform.

    run_agent execs `claude_cmd` directly, so the stand-in has to be
    executable as a program. A bare .py is not on Linux or macOS (no shebang,
    no exec bit), which made this test Windows-only and red everywhere else.
    """
    script = tmp_path / "fake_claude_body.py"
    script.write_text(body, encoding="utf-8")
    if os.name == "nt":
        cmd = tmp_path / "fake_claude.bat"
        cmd.write_text(f'@"{sys.executable}" "{script}" %*\n', encoding="ascii")
    else:
        cmd = tmp_path / "fake_claude"
        cmd.write_text(f"#!{sys.executable}\n" + body, encoding="utf-8")
        cmd.chmod(0o755)
    return str(cmd)


def test_run_agent_decodes_utf8_transcript(tmp_path):
    # An agent report legally contains emoji/smart quotes; without a
    # forced UTF-8 decode Windows falls back to cp1252 and the reader thread
    # dies on bytes like 0x9d (the tail of a right double quote).
    body = (
        "import sys\n"
        "sys.stdout.buffer.write('ok \u2705 \U0001f7e2 \u201d'.encode('utf-8'))\n"
    )
    out = ebs.run_agent("prompt", _fake_claude(tmp_path, body), 30)
    assert "\u2705" in out and "\u201d" in out


# --------------------------------------------------------------------- main


def _write_fixture(tmp_path):
    (tmp_path / "findings.json").write_text(
        json.dumps({"schema": "board-consistency/1", "findings": []}), encoding="utf-8"
    )
    (tmp_path / "evidence.json").write_text(
        json.dumps({"meta": {}, "issues": {}}), encoding="utf-8"
    )
    (tmp_path / "expected.json").write_text(
        json.dumps(expected_doc()), encoding="utf-8"
    )
    return tmp_path


def test_build_prompt_forbids_jira_and_names_paths(tmp_path):
    fixture = _write_fixture(tmp_path)
    prompt = ebs.build_prompt(fixture)
    assert str(fixture / "findings.json") in prompt
    assert str(fixture / "evidence.json") in prompt
    assert "do NOT" in prompt and "Jira" in prompt
    assert "board-sync-state" in prompt


def test_main_scores_stubbed_runs_and_min_accuracy(monkeypatch, tmp_path, capsys):
    fixture = _write_fixture(tmp_path)
    monkeypatch.setattr(
        ebs,
        "run_agent",
        lambda prompt, cmd, timeout, **kw: transcript_with(full_match_snapshot()),
    )
    assert ebs.main(["--fixture", str(fixture)]) == 0
    assert "100%" in capsys.readouterr().out
    # perfect run still fails an impossible bar? no - passes; failing bar needs a miss
    miss = full_match_snapshot()
    miss["findings"][0]["recommendation"] = "SKIP"
    monkeypatch.setattr(
        ebs, "run_agent", lambda prompt, cmd, timeout, **kw: transcript_with(miss)
    )
    assert ebs.main(["--fixture", str(fixture), "--min-accuracy", "0.9"]) == 1


def test_main_without_snapshot_exits_1(monkeypatch, tmp_path, capsys):
    fixture = _write_fixture(tmp_path)
    monkeypatch.setattr(
        ebs,
        "run_agent",
        lambda prompt, cmd, timeout, **kw: "no snapshot in this transcript",
    )
    assert ebs.main(["--fixture", str(fixture)]) == 1
    assert "no valid snapshot" in capsys.readouterr().err


def test_main_writes_report_file(monkeypatch, tmp_path):
    fixture = _write_fixture(tmp_path)
    monkeypatch.setattr(
        ebs,
        "run_agent",
        lambda prompt, cmd, timeout, **kw: transcript_with(full_match_snapshot()),
    )
    out = tmp_path / "eval.md"
    assert ebs.main(["--fixture", str(fixture), "--out", str(out)]) == 0
    assert "100%" in out.read_text(encoding="utf-8")
