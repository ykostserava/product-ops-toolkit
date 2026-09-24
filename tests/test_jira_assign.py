"""Tests for scripts/jira_assign.py - guardrails, payloads, exit codes."""

import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import jira_assign  # noqa: E402
from jira_assign import AuthFailure, Refused, VerifyMismatch, run  # noqa: E402


def make_args(**overrides):
    base = dict(
        key="PROJ-100",
        assignee="dev@example.com",
        dry_run=False,
        jira_api=None,
    )
    base.update(overrides)
    return Namespace(**base)


class FakeJira:
    """Programmable request double recording every HTTP call."""

    def __init__(self, current=None, after=None):
        self.current = current  # assignee username before the PUT
        self.after = after  # assignee returned by the post-execute verify GET
        self.calls = []
        self.put_done = False

    def __call__(self, endpoint, method="GET", data=None):
        self.calls.append((method, endpoint, data))
        if method == "PUT":
            self.put_done = True
            return None  # Jira replies 204 empty
        name = (self.after if self.put_done else self.current) or None
        return {"fields": {"assignee": {"name": name} if name else None}}

    @property
    def puts(self):
        return [c for c in self.calls if c[0] == "PUT"]


def test_propose_only_refuses_a_real_write(monkeypatch):
    # The nightly wrappers run a skill headless with a blanket Bash grant and
    # this script sits in the directory that grant covers, so "this mode never
    # writes" used to live in the prompt alone.
    monkeypatch.setenv("JIRA_PROPOSE_ONLY", "1")
    jira = FakeJira()
    with pytest.raises(Refused, match="JIRA_PROPOSE_ONLY"):
        run(make_args(), jira)
    assert not getattr(jira, "puts", []), (
        "nothing may be sent while propose-only is set"
    )


def test_propose_only_accepts_any_truthy_spelling(monkeypatch):
    # A wrapper author writing =true must not get silent non-enforcement.
    for value in ("true", "YES", "on"):
        monkeypatch.setenv("JIRA_PROPOSE_ONLY", value)
        with pytest.raises(Refused):
            run(make_args(), FakeJira())


def test_propose_only_does_not_block_a_dry_run(monkeypatch):
    # The input it must NOT fire on: a dry run writes nothing anyway.
    monkeypatch.setenv("JIRA_PROPOSE_ONLY", "1")
    assert run(make_args(dry_run=True), FakeJira())["dry_run"] is True


def test_assigns_and_verifies():
    jira = FakeJira(current=None, after="dev@example.com")
    result = run(make_args(), jira)
    assert result["verified"] is True
    assert result["assignee"] == "dev@example.com"
    (_, endpoint, payload) = jira.puts[0]
    assert endpoint == "issue/PROJ-100/assignee"
    assert payload == {"name": "dev@example.com"}


def test_reassignment_allowed_and_reports_previous():
    jira = FakeJira(current="other@example.com", after="dev@example.com")
    result = run(make_args(), jira)
    assert result["from"] == "other@example.com"
    assert len(jira.puts) == 1


def test_already_assigned_refused_without_put():
    jira = FakeJira(current="dev@example.com")
    with pytest.raises(Refused, match="already assigned"):
        run(make_args(), jira)
    assert jira.puts == []


def test_non_ascii_assignee_refused_before_any_call():
    jira = FakeJira()
    with pytest.raises(Refused, match="non-ASCII"):
        run(make_args(assignee="d\u00e9v@example.com"), jira)
    assert jira.calls == []


def test_dry_run_sends_nothing_and_prints_payload():
    jira = FakeJira(current=None)
    result = run(make_args(dry_run=True), jira)
    assert result["dry_run"] is True
    assert result["payload"] == {"name": "dev@example.com"}
    assert jira.puts == []


def test_verify_mismatch_raises():
    jira = FakeJira(current=None, after=None)  # assignee did not stick
    with pytest.raises(VerifyMismatch):
        run(make_args(), jira)


def _wire(monkeypatch, jira):
    monkeypatch.setattr(jira_assign, "resolve_jira_api", lambda cli: "x")
    monkeypatch.setattr(jira_assign, "load_plugin", lambda path: object())
    monkeypatch.setattr(jira_assign, "make_requester", lambda mod: jira)


def test_main_exit_codes(monkeypatch, capsys):
    _wire(monkeypatch, FakeJira(current=None, after="dev@example.com"))
    args = ["--key", "PROJ-100", "--assignee", "dev@example.com"]
    assert jira_assign.main(args) == 0
    assert '"verified": true' in capsys.readouterr().out

    _wire(monkeypatch, FakeJira(current="dev@example.com"))
    assert jira_assign.main(args) == 2
    assert "REFUSED:" in capsys.readouterr().err

    _wire(monkeypatch, FakeJira(current=None, after=None))
    assert jira_assign.main(args) == 3


def test_main_auth_failure_exit_1(monkeypatch, capsys):
    def auth_fail(endpoint, method="GET", data=None):
        raise AuthFailure("HTTP 401 from Jira - check VPN and JIRA_API_TOKEN")

    _wire(monkeypatch, auth_fail)
    assert jira_assign.main(["--key", "PROJ-100", "--assignee", "d@example.com"]) == 1
    assert capsys.readouterr().err.startswith("AUTH:")
