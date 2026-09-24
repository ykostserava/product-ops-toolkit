"""Tests for scripts/jira_transition.py - guardrails, payloads, exit codes."""

import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import jira_transition  # noqa: E402
from jira_transition import AuthFailure, Refused, VerifyMismatch, run  # noqa: E402


def make_args(**overrides):
    base = dict(
        key="PROJ-100",
        to="In Analysis",
        resolution=None,
        yes_one_way=False,
        comment=None,
        via=None,
        dry_run=False,
        jira_api=None,
    )
    base.update(overrides)
    return Namespace(**base)


class FakeJira:
    """Programmable request double recording every HTTP call."""

    def __init__(self, current="Backlog", transitions=(), after=None):
        self.current = current
        self.transitions = list(transitions)
        self.after = after  # status returned by the post-execute verify GET
        self.calls = []

    def __call__(self, endpoint, method="GET", data=None):
        self.calls.append((method, endpoint, data))
        if endpoint.endswith("/transitions") and method == "GET":
            return {"transitions": self.transitions}
        if method == "POST":
            return None  # Jira replies 204 empty
        if "fields=status,issuetype" in endpoint:
            return {
                "fields": {
                    "status": {"name": self.current},
                    "issuetype": {"name": "Story"},
                }
            }
        return {"fields": {"status": {"name": self.after or self.current}}}

    @property
    def posts(self):
        return [c for c in self.calls if c[0] == "POST"]


T_ANALYSIS = {"id": "21", "name": "Start analysis", "to": {"name": "In Analysis"}}
T_CLOSED = {"id": "571", "name": "Close", "to": {"name": "Closed"}}
T_READY = {"id": "261", "name": "Ready", "to": {"name": "Ready for Dev"}}


def test_case_insensitive_name_match_resolves_id():
    jira = FakeJira(transitions=[T_ANALYSIS])
    result = run(make_args(to="in analysis", dry_run=True), jira)
    assert result["transition_id"] == "21"
    assert result["to"] == "In Analysis"
    assert jira.posts == []


def test_unreachable_target_refused_without_post():
    jira = FakeJira(transitions=[T_ANALYSIS])
    with pytest.raises(Refused, match="no transition from 'Backlog' to 'In Testing'"):
        run(make_args(to="In Testing"), jira)
    assert jira.posts == []


def test_already_in_target_refused():
    jira = FakeJira(current="In Analysis")
    with pytest.raises(Refused, match="already in"):
        run(make_args(to="In Analysis"), jira)
    assert jira.calls[0][0] == "GET"
    assert len(jira.calls) == 1  # refused before even listing transitions


def test_one_way_refused_without_flag():
    jira = FakeJira(transitions=[T_READY])
    with pytest.raises(Refused, match="ONE-WAY"):
        run(make_args(to="Ready for Dev"), jira)
    assert jira.posts == []


def test_one_way_executes_with_flag():
    jira = FakeJira(transitions=[T_READY], after="Ready for Dev")
    result = run(make_args(to="Ready for Dev", yes_one_way=True), jira)
    assert result["verified"] is True
    assert len(jira.posts) == 1


def test_closed_requires_resolution():
    jira = FakeJira(transitions=[T_CLOSED])
    with pytest.raises(Refused, match="resolution"):
        run(make_args(to="Closed", yes_one_way=True), jira)
    assert jira.posts == []


def test_resolution_rides_the_post_payload():
    jira = FakeJira(transitions=[T_CLOSED], after="Closed")
    run(make_args(to="Closed", yes_one_way=True, resolution="Done"), jira)
    (_, _, payload) = jira.posts[0]
    assert payload["fields"] == {"resolution": {"name": "Done"}}
    assert payload["transition"] == {"id": "571"}


def test_comment_rides_the_update_block():
    jira = FakeJira(transitions=[T_ANALYSIS], after="In Analysis")
    run(make_args(comment="starting analysis"), jira)
    (_, _, payload) = jira.posts[0]
    assert payload["update"]["comment"] == [{"add": {"body": "starting analysis"}}]


def test_non_ascii_comment_refused_before_any_call():
    jira = FakeJira(transitions=[T_ANALYSIS])
    with pytest.raises(Refused, match="non-ASCII"):
        run(make_args(comment="start \u2192 go"), jira)
    assert jira.calls == []


def test_dry_run_sends_nothing_and_prints_payload():
    jira = FakeJira(transitions=[T_ANALYSIS])
    result = run(make_args(dry_run=True), jira)
    assert result["dry_run"] is True
    assert result["payload"]["transition"] == {"id": "21"}
    assert jira.posts == []


def test_verify_mismatch_raises():
    jira = FakeJira(transitions=[T_ANALYSIS], after="Backlog")  # status did not move
    with pytest.raises(VerifyMismatch):
        run(make_args(), jira)


def test_a_failed_verify_read_after_a_landed_post_is_not_reported_as_untouched():
    # Exit 1 means "nothing was written - STOP" in this file's contract. If the
    # POST lands and only the verify read fails, saying that would report a
    # closed issue as untouched - and a --yes-one-way close has no way back.
    class FailsOnVerify(FakeJira):
        def __call__(self, path, method="GET", data=None):
            if method == "GET" and "fields=status" in path and self.posts:
                raise RuntimeError("500 from Jira")
            return super().__call__(path, method=method, data=data)

    jira = FailsOnVerify(transitions=[T_ANALYSIS])
    with pytest.raises(VerifyMismatch) as caught:
        run(make_args(), jira)
    assert "verify read failed" in str(caught.value)
    assert jira.posts, "the transition POST must have been sent"


def test_propose_only_refuses_a_real_write(monkeypatch):
    # The nightly wrapper runs the skill headless with a blanket Bash grant,
    # and this script sits in the directory that grant covers. The guarantee
    # "this mode never writes" used to live in the prompt alone.
    monkeypatch.setenv("JIRA_PROPOSE_ONLY", "1")
    jira = FakeJira(transitions=[T_ANALYSIS], after="In Analysis")
    with pytest.raises(Refused, match="JIRA_PROPOSE_ONLY"):
        run(make_args(), jira)
    assert jira.posts == [], "nothing may be sent while propose-only is set"


def test_propose_only_still_allows_a_dry_run(monkeypatch):
    # The input it must NOT fire on: a dry run writes nothing anyway, and
    # blocking it would make the nightly report useless.
    monkeypatch.setenv("JIRA_PROPOSE_ONLY", "1")
    jira = FakeJira(transitions=[T_ANALYSIS])
    assert run(make_args(dry_run=True), jira)["dry_run"] is True


def _wire(monkeypatch, jira):
    monkeypatch.setattr(jira_transition, "resolve_jira_api", lambda cli: "x")
    monkeypatch.setattr(jira_transition, "load_plugin", lambda path: object())
    monkeypatch.setattr(jira_transition, "make_requester", lambda mod: jira)


def test_main_exit_codes(monkeypatch, capsys):
    jira = FakeJira(transitions=[T_ANALYSIS], after="In Analysis")
    _wire(monkeypatch, jira)
    assert jira_transition.main(["--key", "PROJ-100", "--to", "In Analysis"]) == 0
    assert '"verified": true' in capsys.readouterr().out

    _wire(monkeypatch, FakeJira(transitions=[]))
    assert jira_transition.main(["--key", "PROJ-100", "--to", "In Analysis"]) == 2
    assert "REFUSED:" in capsys.readouterr().err

    _wire(monkeypatch, FakeJira(transitions=[T_ANALYSIS], after="Backlog"))
    assert jira_transition.main(["--key", "PROJ-100", "--to", "In Analysis"]) == 3


def test_main_auth_failure_exit_1(monkeypatch, capsys):
    def auth_fail(endpoint, method="GET", data=None):
        raise AuthFailure("HTTP 401 from Jira - check VPN and JIRA_API_TOKEN")

    _wire(monkeypatch, auth_fail)
    assert jira_transition.main(["--key", "PROJ-100", "--to", "In Analysis"]) == 1
    assert capsys.readouterr().err.startswith("AUTH:")


def test_one_way_dry_run_previews_without_arming_flag():
    """A preview must never require --yes-one-way (armed preview command
    lines are one dropped --dry-run away from an irreversible write)."""
    jira = FakeJira(transitions=[T_READY])
    result = run(make_args(to="Ready for Dev", dry_run=True), jira)
    assert result["dry_run"] is True
    assert result["one_way"] is True
    assert jira.posts == []


def test_one_way_close_dry_run_previews_with_resolution_only():
    jira = FakeJira(transitions=[T_CLOSED])
    result = run(make_args(to="Closed", resolution="Done", dry_run=True), jira)
    assert result["one_way"] is True
    assert jira.posts == []


def test_close_dry_run_still_requires_resolution():
    """The resolution guard is payload completeness, not arming - it stays."""
    jira = FakeJira(transitions=[T_CLOSED])
    with pytest.raises(Refused, match="resolution"):
        run(make_args(to="Closed", dry_run=True), jira)
    assert jira.posts == []


def test_real_one_way_still_refused_without_flag_after_preview_relaxation():
    jira = FakeJira(transitions=[T_READY])
    with pytest.raises(Refused, match="ONE-WAY"):
        run(make_args(to="Ready for Dev", dry_run=False), jira)
    assert jira.posts == []


# --- two transitions, one target: the resolution-screen trap ---------------

T_DONE = {"id": "651", "name": "Done", "to": {"name": "Closed"}}


def test_two_transitions_to_the_same_target_refuse_instead_of_guessing():
    """From In testing both "Done" (651) and Closed (571) land on Closed with
    different resolution screens - picking the first 400s on the other's set."""
    jira = FakeJira(current="In testing", transitions=[T_DONE, T_CLOSED])
    with pytest.raises(Refused) as excinfo:
        run(make_args(to="Closed", resolution="Done", yes_one_way=True), jira)
    assert "2 transitions" in str(excinfo.value)
    assert "Done (id 651)" in str(excinfo.value) and "Close (id 571)" in str(
        excinfo.value
    )
    assert jira.posts == []


def test_via_names_which_transition_to_take():
    # via must pick the SECOND candidate: first-match (the old behaviour)
    # would return 651 here and a via='Done' assertion could not tell
    jira = FakeJira(
        current="In testing", transitions=[T_DONE, T_CLOSED], after="Closed"
    )
    run(
        make_args(to="Closed", via="Close", resolution="Done", yes_one_way=True),
        jira,
    )
    assert jira.posts[0][2]["transition"] == {"id": "571"}


def test_via_that_matches_no_candidate_is_refused():
    jira = FakeJira(current="In testing", transitions=[T_DONE, T_CLOSED])
    with pytest.raises(Refused) as excinfo:
        run(
            make_args(to="Closed", via="Deployed", resolution="Done", yes_one_way=True),
            jira,
        )
    assert "no transition named 'Deployed'" in str(excinfo.value)
    assert jira.posts == []


def test_a_single_match_still_needs_no_via():
    jira = FakeJira(transitions=[T_ANALYSIS], after="In Analysis")
    run(make_args(to="In Analysis"), jira)
    assert jira.posts[0][2]["transition"] == {"id": "21"}
