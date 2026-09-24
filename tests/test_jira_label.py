"""Tests for scripts/jira_label.py - guardrails, payloads, exit codes."""

import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import jira_label  # noqa: E402
from jira_label import AuthFailure, Refused, VerifyMismatch, run  # noqa: E402


def make_args(**overrides):
    base = dict(
        key="PROJ-100",
        add=["size-S"],
        remove=[],
        dry_run=False,
        jira_api=None,
    )
    base.update(overrides)
    return Namespace(**base)


class FakeJira:
    """Programmable request double recording every HTTP call."""

    def __init__(self, current=(), after=None):
        self.current = list(current)  # labels before the PUT
        self.after = after  # labels returned by the verify GET (None = same as current)
        self.calls = []
        self.put_done = False

    def __call__(self, endpoint, method="GET", data=None):
        self.calls.append((method, endpoint, data))
        if method == "PUT":
            self.put_done = True
            return None  # Jira replies 204 empty
        labels = (
            self.after if (self.put_done and self.after is not None) else self.current
        )
        return {"fields": {"labels": list(labels)}}

    @property
    def puts(self):
        return [c for c in self.calls if c[0] == "PUT"]


def test_propose_only_refuses_a_real_write(monkeypatch):
    # Scheduled wrappers run a skill headless with a blanket Bash grant and
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


def test_adds_and_verifies():
    jira = FakeJira(current=[], after=["size-S"])
    result = run(make_args(), jira)
    assert result["verified"] is True
    assert result["add"] == ["size-S"]
    (_, endpoint, payload) = jira.puts[0]
    assert endpoint == "issue/PROJ-100"
    assert payload == {"update": {"labels": [{"add": "size-S"}]}}


def test_add_and_remove_combo_is_one_atomic_put():
    jira = FakeJira(current=["size-M"], after=["size-S"])
    result = run(make_args(add=["size-S"], remove=["size-M"]), jira)
    assert result["verified"] is True
    assert len(jira.puts) == 1
    (_, _, payload) = jira.puts[0]
    assert payload == {"update": {"labels": [{"add": "size-S"}, {"remove": "size-M"}]}}


def test_noop_add_dropped_rest_proceeds():
    jira = FakeJira(current=["research"], after=["research", "size-S"])
    result = run(make_args(add=["research", "size-S"]), jira)
    assert result["add"] == ["size-S"]
    assert result["skipped_noop"] == ["research"]
    (_, _, payload) = jira.puts[0]
    assert payload == {"update": {"labels": [{"add": "size-S"}]}}


def test_remove_of_absent_label_dropped_rest_proceeds():
    jira = FakeJira(current=[], after=["size-S"])
    result = run(make_args(add=["size-S"], remove=["size-XL"]), jira)
    assert result["remove"] == []
    assert result["skipped_noop"] == ["size-XL"]
    assert result["verified"] is True


def test_all_ops_noop_refused_without_put():
    jira = FakeJira(current=["size-S"])
    with pytest.raises(Refused, match="nothing to do"):
        run(make_args(add=["size-S"]), jira)
    assert jira.puts == []


def test_nothing_requested_refused():
    jira = FakeJira()
    with pytest.raises(Refused, match="nothing requested"):
        run(make_args(add=[], remove=[]), jira)
    assert jira.calls == []


def test_conflicting_add_and_remove_refused():
    jira = FakeJira()
    with pytest.raises(Refused, match="both"):
        run(make_args(add=["size-S"], remove=["size-S"]), jira)
    assert jira.calls == []


def test_non_ascii_label_refused_before_any_call():
    jira = FakeJira()
    with pytest.raises(Refused, match="non-ASCII"):
        run(make_args(add=["gr\u00f6\u00dfe-S"]), jira)
    assert jira.calls == []


def test_dry_run_sends_nothing_and_prints_payload():
    jira = FakeJira(current=[])
    result = run(make_args(dry_run=True), jira)
    assert result["dry_run"] is True
    assert result["payload"] == {"update": {"labels": [{"add": "size-S"}]}}
    assert jira.puts == []


def test_verify_mismatch_raises():
    jira = FakeJira(current=[], after=[])  # add did not stick
    with pytest.raises(VerifyMismatch):
        run(make_args(), jira)


def _wire(monkeypatch, jira):
    monkeypatch.setattr(jira_label, "resolve_jira_api", lambda cli: "x")
    monkeypatch.setattr(jira_label, "load_plugin", lambda path: object())
    monkeypatch.setattr(jira_label, "make_requester", lambda mod: jira)


def test_main_exit_codes(monkeypatch, capsys):
    _wire(monkeypatch, FakeJira(current=[], after=["size-S"]))
    args = ["--key", "PROJ-100", "--add", "size-S"]
    assert jira_label.main(args) == 0
    assert '"verified": true' in capsys.readouterr().out

    _wire(monkeypatch, FakeJira(current=["size-S"]))
    assert jira_label.main(args) == 2
    assert "REFUSED:" in capsys.readouterr().err

    _wire(monkeypatch, FakeJira(current=[], after=[]))
    assert jira_label.main(args) == 3
    assert "VERIFY MISMATCH:" in capsys.readouterr().err


def test_main_auth_failure_exit_1(monkeypatch, capsys):
    def auth_fail(endpoint, method="GET", data=None):
        raise AuthFailure("HTTP 401 from Jira - check VPN and JIRA_API_TOKEN")

    _wire(monkeypatch, auth_fail)
    assert jira_label.main(["--key", "PROJ-100", "--add", "size-S"]) == 1
    assert capsys.readouterr().err.startswith("AUTH:")


def test_verify_read_failure_after_put_is_verify_mismatch_not_error():
    """Once the PUT landed, a failing verify read must exit 3 (check manually),
    never exit 1 (which the consumer contract reads as 'nothing was written')."""

    class FlakyVerify(FakeJira):
        def __call__(self, endpoint, method="GET", data=None):
            if self.put_done and method == "GET":
                raise RuntimeError("verify read lost")
            return super().__call__(endpoint, method, data)

    jira = FlakyVerify(current=[])
    with pytest.raises(VerifyMismatch, match="unconfirmed"):
        run(make_args(), jira)
    assert len(jira.puts) == 1


def test_repeated_add_deduplicated_in_payload():
    jira = FakeJira(current=[], after=["size-S"])
    run(make_args(add=["size-S", "size-S"]), jira)
    (_, _, payload) = jira.puts[0]
    assert payload == {"update": {"labels": [{"add": "size-S"}]}}
