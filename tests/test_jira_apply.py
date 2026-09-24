"""Tests for scripts/jira_apply.py - the declarative Jira changeset engine.

Every refusal here stands for a verified failure the one-off scripts kept
re-learning: a 400 from the WAF on non-ASCII, a 400 for missing components or
Risk Class, a 404 on the link type "Relates", a resolution the chosen
transition's screen does not offer, a one-way move with no way back.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import jira_apply as wja  # noqa: E402
from jira_transition import Refused, VerifyMismatch  # noqa: E402

# The create rules under test, independent of whatever jira-config.json says
# on the machine running the suite.
RULES = {
    "require_components": True,
    "risk_class": {"field": "customfield_10106", "issuetypes": ["1"]},
    "components_requiring_assignee": ["Web"],
}


@pytest.fixture(autouse=True)
def _rules(monkeypatch):
    monkeypatch.setattr(wja, "RULES", dict(RULES))
    monkeypatch.setattr(wja, "PROJECT_KEY", "PROJ")
    monkeypatch.setattr(wja, "ONE_WAY_TARGETS", ("closed", "ready for dev"))
    monkeypatch.setattr(wja, "CLOSED", "closed")


LINK_TYPES = {"issueLinkTypes": [{"name": "Relate"}, {"name": "Block"}]}


class FakeJira:
    """Programmable double recording every call; GET-only during a dry run."""

    def __init__(self, status="Backlog", issuetype="Task", transitions=(), after=None):
        self.status = status
        self.issuetype = issuetype
        self.transitions = list(transitions)
        self.after = after
        self.calls = []
        self.created = 0

    def __call__(self, endpoint, method="GET", data=None):
        self.calls.append((method, endpoint, data))
        if endpoint == "issueLinkType":
            return LINK_TYPES
        if endpoint.startswith("issue/") and "/transitions" in endpoint:
            return {"transitions": self.transitions}
        if method == "POST" and endpoint == "issue":
            self.created += 1
            return {"key": f"PROJ-{700 + self.created}"}
        if method in ("POST", "PUT"):
            return None
        if "fields=status,issuetype" in endpoint:
            return {
                "fields": {
                    "status": {"name": self.status},
                    "issuetype": {"name": self.issuetype},
                }
            }
        return {
            "fields": {
                "status": {"name": self.after or self.status},
                "resolution": None,
                "assignee": {"name": "dev.one@example.com"},
                "components": [{"name": "Backend"}],
                "labels": ["research"],
                "issuelinks": [],
                "summary": "s",
            }
        }

    @property
    def writes(self):
        return [c for c in self.calls if c[0] in ("POST", "PUT")]


def changeset(tmp_path, ops, name="pkg"):
    path = tmp_path / f"{name}.changeset.json"
    path.write_text(
        json.dumps({"name": name, "ops": ops}, ensure_ascii=False), encoding="utf-8"
    )
    return wja.load_changeset(path)


def create_op(**over):
    base = {
        "op": "create",
        "project": "PROJ",
        "issuetype": "12010",
        "summary": "[Backend] Research: something",
        "description": "h2. Why\n\nbecause",
        "components": ["Backend"],
    }
    base.update(over)
    return base


# --- the shape of a changeset ----------------------------------------------


def test_missing_file_is_refused(tmp_path):
    with pytest.raises(Refused, match="not found"):
        wja.load_changeset(tmp_path / "nope.json")


def test_invalid_json_is_refused(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(Refused, match="not valid JSON"):
        wja.load_changeset(path)


def test_unknown_op_name_is_refused(tmp_path):
    with pytest.raises(Refused, match="must be one of"):
        changeset(tmp_path, [{"op": "delete", "key": "PROJ-1"}])


def test_empty_changeset_is_refused(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"ops": []}), encoding="utf-8")
    with pytest.raises(Refused, match="no ops"):
        wja.load_changeset(path)


# --- create: the required-field rules --------------------------------------


def test_create_without_components_is_refused(tmp_path):
    cs = changeset(tmp_path, [create_op(components=[])])
    with pytest.raises(Refused, match="require components"):
        wja.build_create(cs.ops[0], cs)


def test_a_bug_without_risk_class_is_refused(tmp_path):
    cs = changeset(tmp_path, [create_op(issuetype="1")])
    with pytest.raises(Refused, match="risk-class field customfield_10106"):
        wja.build_create(cs.ops[0], cs)


def test_a_bug_with_risk_class_passes(tmp_path):
    cs = changeset(
        tmp_path,
        [create_op(issuetype="1", fields={"customfield_10106": {"value": "RC2"}})],
    )
    fields = wja.build_create(cs.ops[0], cs)
    assert fields["customfield_10106"] == {"value": "RC2"}


def test_web_work_must_name_an_assignee(tmp_path):
    cs = changeset(tmp_path, [create_op(components=["Web"])])
    with pytest.raises(Refused, match="Web work is created assigned"):
        wja.build_create(cs.ops[0], cs)


def test_web_work_with_an_assignee_passes(tmp_path):
    cs = changeset(
        tmp_path,
        [create_op(components=["Web"], assignee="web.lead@example.com")],
    )
    fields = wja.build_create(cs.ops[0], cs)
    assert fields["assignee"] == {"name": "web.lead@example.com"}


def test_non_ascii_anywhere_in_a_create_is_refused(tmp_path):
    cs = changeset(
        tmp_path, [create_op(summary="Research: reserved balance \u2192 holds")]
    )
    with pytest.raises(Refused, match="non-ASCII"):
        wja.build_create(cs.ops[0], cs)


def test_non_ascii_inside_a_nested_custom_field_is_refused(tmp_path):
    cs = changeset(
        tmp_path, [create_op(fields={"customfield_10992": {"value": "2027 Q1 \u20ac"}})]
    )
    with pytest.raises(Refused, match="non-ASCII"):
        wja.build_create(cs.ops[0], cs)


def test_summary_is_required(tmp_path):
    op = create_op()
    del op["summary"]
    cs = changeset(tmp_path, [op])
    with pytest.raises(Refused, match="summary"):
        wja.build_create(cs.ops[0], cs)


def test_description_comes_from_a_doc_block(tmp_path):
    doc = tmp_path / "draft.md"
    doc.write_text(
        "# d\n\n```\nthe summary\n```\n\n```\nh2. Body\n\ntext\n```\n", encoding="utf-8"
    )
    cs = changeset(
        tmp_path,
        [create_op(description=None, description_from={"doc": str(doc), "block": 2})],
    )
    fields = wja.build_create(cs.ops[0], cs)
    assert fields["description"] == "h2. Body\n\ntext"


def test_asking_for_a_block_the_doc_does_not_have_is_refused(tmp_path):
    doc = tmp_path / "draft.md"
    doc.write_text("```\nonly one\n```\n", encoding="utf-8")
    with pytest.raises(Refused, match="found 1"):
        wja.fenced_block(doc, 2)


# --- references between ops ------------------------------------------------


def test_a_later_op_resolves_the_key_an_earlier_create_made(tmp_path):
    cs = changeset(
        tmp_path,
        [
            create_op(id="research"),
            {
                "op": "link",
                "type": "Relate",
                "inward": "$research",
                "outward": "PROJ-656",
            },
        ],
    )
    jira = FakeJira()
    wja.run(cs, jira, apply_changes=True)
    link_payload = [c for c in jira.writes if c[1] == "issueLink"][0][2]
    assert link_payload["inwardIssue"]["key"] == "PROJ-701"
    assert link_payload["outwardIssue"]["key"] == "PROJ-656"


def test_an_unknown_reference_is_refused(tmp_path):
    cs = changeset(
        tmp_path,
        [{"op": "link", "type": "Relate", "inward": "$ghost", "outward": "PROJ-1"}],
    )
    with pytest.raises(Refused, match=r"\$ghost"):
        wja.run(cs, FakeJira(), apply_changes=False)


# --- links -----------------------------------------------------------------


def test_the_relates_typo_is_caught_against_the_live_list(tmp_path):
    cs = changeset(
        tmp_path,
        [{"op": "link", "type": "Relates", "inward": "PROJ-1", "outward": "PROJ-2"}],
    )
    with pytest.raises(Refused, match="Relate"):
        wja.run(cs, FakeJira(), apply_changes=False)


def test_block_direction_is_described_as_it_renders(tmp_path):
    cs = changeset(
        tmp_path,
        [{"op": "link", "type": "Block", "inward": "PROJ-321", "outward": "PROJ-323"}],
    )
    _, described = wja.plan_link(cs.ops[0], cs, FakeJira())
    assert described == "PROJ-321 blocks PROJ-323"


# --- transitions -----------------------------------------------------------

T_ROADMAP = {"id": "331", "name": "To roadmap", "to": {"name": "Product roadmap"}}
T_CLOSE = {
    "id": "571",
    "name": "Close",
    "to": {"name": "Closed"},
    "fields": {
        "resolution": {"allowedValues": [{"name": "Done"}, {"name": "Won't Do"}]}
    },
}
T_DONE = {
    "id": "651",
    "name": "Done",
    "to": {"name": "Closed"},
    "fields": {
        "resolution": {
            "allowedValues": [{"name": "Done"}, {"name": "Deployed on production"}]
        }
    },
}


def test_a_transition_is_resolved_by_target_name_not_by_id(tmp_path):
    cs = changeset(
        tmp_path, [{"op": "transition", "key": "EXT-1", "to": "Product roadmap"}]
    )
    jira = FakeJira(transitions=[T_ROADMAP], after="Product roadmap")
    wja.run(cs, jira, apply_changes=True)
    assert jira.writes[0][2] == {"transition": {"id": "331"}}


def test_closing_without_a_resolution_is_refused(tmp_path):
    cs = changeset(
        tmp_path,
        [
            {
                "op": "transition",
                "key": "PROJ-1",
                "to": "Closed",
                "confirm_one_way": True,
            }
        ],
    )
    jira = FakeJira(status="In testing", transitions=[T_CLOSE])
    with pytest.raises(Refused, match="requires a resolution"):
        wja.run(cs, jira, apply_changes=False)
    assert jira.writes == []


def test_a_resolution_the_chosen_screen_does_not_offer_is_refused(tmp_path):
    cs = changeset(
        tmp_path,
        [
            {
                "op": "transition",
                "key": "PROJ-1",
                "to": "Closed",
                "via": "Close",
                "resolution": "Deployed on production",
                "confirm_one_way": True,
            }
        ],
    )
    jira = FakeJira(status="In testing", transitions=[T_CLOSE, T_DONE])
    with pytest.raises(Refused, match="does not offer resolution"):
        wja.run(cs, jira, apply_changes=False)


def test_two_transitions_to_one_target_need_via(tmp_path):
    cs = changeset(
        tmp_path,
        [
            {
                "op": "transition",
                "key": "PROJ-1",
                "to": "Closed",
                "resolution": "Done",
                "confirm_one_way": True,
            }
        ],
    )
    jira = FakeJira(status="In testing", transitions=[T_CLOSE, T_DONE])
    with pytest.raises(Refused, match="2 transitions"):
        wja.run(cs, jira, apply_changes=False)


def test_a_one_way_move_needs_the_confirmation_in_the_op(tmp_path):
    cs = changeset(
        tmp_path,
        [
            {
                "op": "transition",
                "key": "PROJ-1",
                "to": "Closed",
                "resolution": "Done",
                "via": "Close",
            }
        ],
    )
    jira = FakeJira(status="In testing", transitions=[T_CLOSE, T_DONE])
    with pytest.raises(Refused, match="one-way"):
        wja.run(cs, jira, apply_changes=False)


def test_a_transition_to_the_current_status_is_refused(tmp_path):
    cs = changeset(tmp_path, [{"op": "transition", "key": "EXT-1", "to": "Backlog"}])
    with pytest.raises(Refused, match="already in"):
        wja.run(cs, FakeJira(status="Backlog"), apply_changes=False)


def test_a_transition_that_does_not_land_where_it_claimed_is_unconfirmed(tmp_path):
    cs = changeset(
        tmp_path, [{"op": "transition", "key": "EXT-1", "to": "Product roadmap"}]
    )
    jira = FakeJira(transitions=[T_ROADMAP], after="Backlog")  # did not move
    with pytest.raises(VerifyMismatch, match="expected 'Product roadmap'"):
        wja.run(cs, jira, apply_changes=True)


# --- comment / assign / update ---------------------------------------------


def test_a_non_ascii_comment_is_refused(tmp_path):
    cs = changeset(
        tmp_path, [{"op": "comment", "key": "PROJ-1", "body": "done \u2014 yes"}]
    )
    with pytest.raises(Refused, match="non-ASCII"):
        wja.run(cs, FakeJira(), apply_changes=False)


def test_an_empty_comment_is_refused(tmp_path):
    cs = changeset(tmp_path, [{"op": "comment", "key": "PROJ-1", "body": "   "}])
    with pytest.raises(Refused, match="non-empty"):
        wja.run(cs, FakeJira(), apply_changes=False)


def test_update_with_no_fields_is_refused(tmp_path):
    cs = changeset(tmp_path, [{"op": "update", "key": "PROJ-1", "fields": {}}])
    with pytest.raises(Refused, match="non-empty 'fields'"):
        wja.run(cs, FakeJira(), apply_changes=False)


def test_assign_sends_a_put(tmp_path):
    cs = changeset(
        tmp_path,
        [
            {
                "op": "assign",
                "key": "PROJ-1",
                "assignee": "web.lead@example.com",
            }
        ],
    )
    jira = FakeJira()
    wja.run(cs, jira, apply_changes=True)
    assert jira.writes[0][0] == "PUT"
    assert jira.writes[0][2] == {"name": "web.lead@example.com"}


# --- dry run vs apply ------------------------------------------------------


def test_a_dry_run_writes_nothing(tmp_path):
    cs = changeset(
        tmp_path,
        [
            create_op(id="research"),
            {
                "op": "link",
                "type": "Relate",
                "inward": "$research",
                "outward": "PROJ-656",
            },
            {"op": "transition", "key": "EXT-1", "to": "Product roadmap"},
        ],
    )
    jira = FakeJira(transitions=[T_ROADMAP])
    results = wja.run(cs, jira, apply_changes=False)
    assert jira.writes == []
    assert [r["op"] for r in results] == ["create", "link", "transition"]


def test_a_dry_run_still_resolves_references_so_later_ops_are_checked(tmp_path):
    cs = changeset(
        tmp_path,
        [
            create_op(id="research"),
            {
                "op": "link",
                "type": "Relate",
                "inward": "$research",
                "outward": "PROJ-656",
            },
        ],
    )
    results = wja.run(cs, FakeJira(), apply_changes=False)
    assert "<new:research>" in results[1]["plan"]


def test_apply_verifies_every_write_by_reading_the_issue_back(tmp_path):
    cs = changeset(tmp_path, [create_op(id="research")])
    jira = FakeJira()
    results = wja.run(cs, jira, apply_changes=True)
    assert results[0]["verified"]["components"] == ["Backend"]
    reads = [c for c in jira.calls if c[0] == "GET" and "issuelinks" in c[1]]
    assert reads, "apply must read the issue back"


def test_propose_only_blocks_an_apply(tmp_path, monkeypatch):
    monkeypatch.setenv("JIRA_PROPOSE_ONLY", "1")
    cs = changeset(tmp_path, [create_op()])
    jira = FakeJira()
    with pytest.raises(Refused, match="propose"):
        wja.run(cs, jira, apply_changes=True)
    assert jira.writes == []


def test_propose_only_still_allows_a_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("JIRA_PROPOSE_ONLY", "1")
    cs = changeset(tmp_path, [create_op()])
    assert wja.run(cs, FakeJira(), apply_changes=False)
