"""Tests for scripts/board_consistency.py - graph, rules R1-R8, exceptions."""

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import board_consistency as bc  # noqa: E402


# ------------------------------------------------------------------ fixtures


def raw_issue(
    key, itype, status, category, subtasks=(), links=(), assignee=None, updated=None
):
    return {
        "key": key,
        "fields": {
            "summary": f"{key} summary",
            "issuetype": {"name": itype},
            "status": {"name": status, "statusCategory": {"key": category}},
            "assignee": {"name": assignee} if assignee else None,
            "updated": f"{updated}T10:00:00.000+0200" if updated else None,
            "subtasks": list(subtasks),
            "issuelinks": list(links),
        },
    }


def link(name, other_raw, inward=True):
    side = "inwardIssue" if inward else "outwardIssue"
    return {"type": {"name": name}, side: other_raw}


def graph(*raws, epic_children=None):
    issues = {r["key"]: bc.simplify(r) for r in raws}
    children = {
        epic: [bc.simplify(c) for c in kids]
        for epic, kids in (epic_children or {}).items()
    }
    return bc.build_edges(issues, children)


EPIC_BACKLOG = raw_issue("PROJ-10", "Epic", "Backlog", "new")
STORY_ACTIVE = raw_issue("PROJ-11", "Story", "In Progress", "indeterminate")
STORY_DONE = raw_issue("PROJ-12", "Story", "Closed", "done")


# ------------------------------------------------------------------ R1 rules


def test_r1_epic_story_edge_fires_with_epic_target():
    edges = graph(EPIC_BACKLOG, STORY_ACTIVE, epic_children={"PROJ-10": [STORY_ACTIVE]})
    findings, _ = bc.apply_rules(edges)
    assert [f["rule"] for f in findings] == ["R1"]
    f = findings[0]
    assert f["edge"] == "epic_story"
    assert f["proposal"]["to"] == "In analysis"
    assert f["proposal"]["executable"] is True


def test_r1_initiative_edge_via_implements_and_relates():
    for link_name in ("Implements", "Relates"):
        epic_active = raw_issue("PROJ-20", "Epic", "In analysis", "indeterminate")
        initiative = raw_issue(
            "PROJ-1",
            "Initiative",
            "Backlog",
            "new",
            links=[link(link_name, epic_active)],
        )
        findings, _ = bc.apply_rules(graph(initiative, epic_active))
        assert [f["rule"] for f in findings] == ["R1"], link_name
        assert findings[0]["edge"] == "initiative_epic"
        # Initiative workflow is undocumented - no target status guessed.
        assert findings[0]["proposal"]["to"] is None
        assert "enumerated live" in findings[0]["proposal"]["note"]


def test_r1_story_subtask_edge():
    sub = raw_issue("PROJ-31", "Sub-task", "In Progress", "indeterminate")
    story = raw_issue("PROJ-30", "Story", "Backlog", "new", subtasks=[sub])
    findings, _ = bc.apply_rules(graph(story, sub))
    assert [f["rule"] for f in findings] == ["R1"]
    assert findings[0]["edge"] == "story_subtask"


def test_r1_silent_when_parent_already_active():
    epic = raw_issue("PROJ-10", "Epic", "In analysis", "indeterminate")
    findings, _ = bc.apply_rules(
        graph(epic, STORY_ACTIVE, epic_children={"PROJ-10": [STORY_ACTIVE]})
    )
    assert findings == []


def test_unfamiliar_link_types_ignored():
    epic_active = raw_issue("PROJ-20", "Epic", "In analysis", "indeterminate")
    initiative = raw_issue(
        "PROJ-1", "Initiative", "Backlog", "new", links=[link("Blocks", epic_active)]
    )
    assert bc.apply_rules(graph(initiative, epic_active))[0] == []


# ------------------------------------------------------------------ R2 rules


def test_r2_fires_when_all_children_done():
    findings, _ = bc.apply_rules(
        graph(EPIC_BACKLOG, STORY_DONE, epic_children={"PROJ-10": [STORY_DONE]})
    )
    assert [f["rule"] for f in findings] == ["R2"]
    p = findings[0]["proposal"]
    assert (p["to"], p["one_way"], p["resolution"]) == ("Closed", True, "Done")


def test_r2_silent_with_mixed_children_and_childless_parents():
    mixed = graph(
        EPIC_BACKLOG,
        STORY_DONE,
        STORY_ACTIVE,
        epic_children={"PROJ-10": [STORY_DONE, STORY_ACTIVE]},
    )
    findings, _ = bc.apply_rules(mixed)
    assert all(f["rule"] != "R2" for f in findings)
    childless = graph(EPIC_BACKLOG)
    assert bc.apply_rules(childless)[0] == []


def test_r2_exempt_on_story_subtask_edge():
    sub_done = raw_issue("PROJ-31", "Sub-task", "Closed", "done")
    story = raw_issue(
        "PROJ-30", "Story", "In Progress", "indeterminate", subtasks=[sub_done]
    )
    findings, _ = bc.apply_rules(graph(story, sub_done))
    assert findings == []  # done sub-tasks alone never close a story


# ------------------------------------------------------------------ R3 rules


def test_r3_flag_only_not_executable():
    epic_closed = raw_issue("PROJ-10", "Epic", "Closed", "done")
    findings, _ = bc.apply_rules(
        graph(epic_closed, STORY_ACTIVE, epic_children={"PROJ-10": [STORY_ACTIVE]})
    )
    assert [f["rule"] for f in findings] == ["R3"]
    assert findings[0]["proposal"]["action"] == "flag"
    assert findings[0]["proposal"]["executable"] is False


def test_unknown_status_name_with_done_category_behaves_done():
    weird = raw_issue("PROJ-40", "Story", "Weird Custom Final", "done")
    findings, _ = bc.apply_rules(
        graph(EPIC_BACKLOG, weird, epic_children={"PROJ-10": [weird]})
    )
    assert [f["rule"] for f in findings] == ["R2"]


# ------------------------------------------------------------------ R4 rules


def simplified(*raws):
    return [bc.simplify(r) for r in raws]


def test_simplify_captures_assignee():
    with_dev = bc.simplify(
        raw_issue(
            "PROJ-61",
            "Task",
            "In Progress",
            "indeterminate",
            assignee="dev@example.com",
        )
    )
    without = bc.simplify(raw_issue("PROJ-62", "Task", "In Progress", "indeterminate"))
    assert with_dev["assignee"] == "dev@example.com"
    assert without["assignee"] is None


def test_r4_fires_on_active_unassigned_issue():
    findings = bc.apply_r4(
        simplified(raw_issue("PROJ-60", "Story", "In Progress", "indeterminate"))
    )
    assert [f["rule"] for f in findings] == ["R4"]
    f = findings[0]
    assert f["parent"]["key"] == "PROJ-60"
    assert f["children"] == []
    assert f["proposal"]["action"] == "assign"
    assert f["proposal"]["executable"] is True
    assert f["proposal"]["one_way"] is False
    # the engine never picks a person - the candidate comes from the agent
    assert f["proposal"]["assignee"] is None


def test_r4_covers_ready_statuses_case_insensitively():
    findings = bc.apply_r4(
        simplified(
            raw_issue("PROJ-63", "Acceptance bug", "Ready for Dev", "new"),
            raw_issue("PROJ-64", "Task", "Ready For Testing", "indeterminate"),
        )
    )
    assert sorted(f["parent"]["key"] for f in findings) == ["PROJ-63", "PROJ-64"]


def test_r4_silent_on_backlog_assigned_closed_and_containers():
    quiet = simplified(
        raw_issue("PROJ-65", "Story", "Backlog", "new"),
        raw_issue("PROJ-66", "Story", "PBR Needed", "new"),
        raw_issue(
            "PROJ-67",
            "Story",
            "In Progress",
            "indeterminate",
            assignee="dev@example.com",
        ),
        raw_issue("PROJ-68", "Epic", "In analysis", "indeterminate"),
        raw_issue("PROJ-69", "Initiative", "In analysis", "indeterminate"),
        raw_issue("PROJ-70", "Story", "Closed", "done"),
    )
    assert bc.apply_r4(quiet) == []


def test_r4_suppressed_by_exception():
    findings = bc.apply_r4(
        simplified(raw_issue("PROJ-71", "Story", "In Progress", "indeterminate"))
    )
    kept, suppressed, _ = bc.apply_exceptions(
        findings, [entry("PROJ-71", rule="R4")], "2026-08-12"
    )
    assert kept == [] and len(suppressed) == 1


def test_main_includes_r4_findings(monkeypatch, tmp_path):
    active_unassigned = raw_issue("PROJ-72", "Task", "In Progress", "indeterminate")
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")
    monkeypatch.setattr(bc, "search_all", lambda api, jql, timeout: [active_unassigned])
    monkeypatch.setattr(
        bc, "fetch_epic_children", lambda api, keys, timeout, workers: ({}, [])
    )
    out = tmp_path / "findings.json"
    assert (
        bc.main(
            [
                "--out",
                str(out),
                "--exceptions",
                str(tmp_path / "no.json"),
                "--releases",
                str(tmp_path / "no-rel.json"),
            ]
        )
        == 0
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [f["rule"] for f in data["findings"]] == ["R4"]


# ------------------------------------------------------------------ R5 rules


def test_simplify_captures_link_direction():
    blocker = raw_issue("PROJ-80", "Task", "Backlog", "new")
    blocked = bc.simplify(
        raw_issue(
            "PROJ-81",
            "Task",
            "In progress",
            "indeterminate",
            links=[link("Block", blocker, inward=True)],
        )
    )
    blocking = bc.simplify(
        raw_issue(
            "PROJ-82",
            "Task",
            "In progress",
            "indeterminate",
            links=[link("Block", blocker, inward=False)],
        )
    )
    assert blocked["links"][0]["direction"] == "inward"
    assert blocking["links"][0]["direction"] == "outward"


def test_r5_fires_on_in_progress_with_open_blocker():
    # Direction semantics on Jira Server: the BLOCKER
    # sits on the inwardIssue side ("is blocked by").
    blocker = raw_issue("PROJ-80", "Task", "Backlog", "new")
    findings = bc.apply_r5(
        simplified(
            raw_issue(
                "PROJ-81",
                "Task",
                "In progress",
                "indeterminate",
                assignee="dev@example.com",
                links=[link("Block", blocker, inward=True)],
            )
        )
    )
    assert [f["rule"] for f in findings] == ["R5"]
    f = findings[0]
    assert f["parent"]["key"] == "PROJ-81"
    assert [c["key"] for c in f["children"]] == ["PROJ-80"]
    assert f["proposal"]["action"] == "flag"
    assert f["proposal"]["executable"] is False


def test_r5_silent_on_done_blocker_relates_outward_and_rfd():
    done_blocker = raw_issue("PROJ-83", "Task", "Closed", "done")
    open_blocker = raw_issue("PROJ-84", "Task", "Backlog", "new")
    quiet = simplified(
        raw_issue(
            "PROJ-85",
            "Task",
            "In progress",
            "indeterminate",
            links=[link("Block", done_blocker, inward=True)],
        ),
        raw_issue(
            "PROJ-86",
            "Task",
            "In progress",
            "indeterminate",
            links=[link("Relates", open_blocker, inward=True)],
        ),
        # blocks others itself - not blocked
        raw_issue(
            "PROJ-87",
            "Task",
            "In progress",
            "indeterminate",
            links=[link("Block", open_blocker, inward=False)],
        ),
        # deliberate scope decision: Ready for Dev queue with
        # a blocker is normal Kanban staging - R5 checks In progress ONLY
        raw_issue(
            "PROJ-88",
            "Task",
            "Ready for Dev",
            "new",
            links=[link("Block", open_blocker, inward=True)],
        ),
    )
    assert bc.apply_r5(quiet) == []


def test_r5_suppressed_by_exception():
    blocker = raw_issue("PROJ-80", "Task", "Backlog", "new")
    findings = bc.apply_r5(
        simplified(
            raw_issue(
                "PROJ-89",
                "Task",
                "In progress",
                "indeterminate",
                links=[link("Block", blocker, inward=True)],
            )
        )
    )
    kept, suppressed, _ = bc.apply_exceptions(
        findings, [entry("PROJ-89", rule="R5")], "2026-08-12"
    )
    assert kept == [] and len(suppressed) == 1


def test_main_includes_r5_findings(monkeypatch, tmp_path):
    blocker = raw_issue("PROJ-90", "Task", "Backlog", "new")
    blocked = raw_issue(
        "PROJ-91",
        "Task",
        "In progress",
        "indeterminate",
        assignee="dev@example.com",
        links=[link("Block", blocker, inward=True)],
    )
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")
    monkeypatch.setattr(bc, "search_all", lambda api, jql, timeout: [blocked])
    monkeypatch.setattr(
        bc, "fetch_epic_children", lambda api, keys, timeout, workers: ({}, [])
    )
    out = tmp_path / "findings.json"
    assert (
        bc.main(
            [
                "--out",
                str(out),
                "--exceptions",
                str(tmp_path / "no.json"),
                "--releases",
                str(tmp_path / "no-rel.json"),
            ]
        )
        == 0
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [f["rule"] for f in data["findings"]] == ["R5"]


# ------------------------------------------------------------------ R6 rules


def test_simplify_captures_updated_date():
    fresh = bc.simplify(
        raw_issue(
            "PROJ-95", "Task", "In progress", "indeterminate", updated="2026-08-10"
        )
    )
    absent = bc.simplify(raw_issue("PROJ-96", "Task", "In progress", "indeterminate"))
    assert fresh["updated"] == "2026-08-10"
    assert absent["updated"] is None


def test_r6_fires_on_stale_in_progress_and_ready_for_testing():
    findings = bc.apply_r6(
        simplified(
            raw_issue(
                "PROJ-95", "Task", "In progress", "indeterminate", updated="2026-07-24"
            ),
            raw_issue(
                "PROJ-96",
                "Story",
                "Ready For Testing",
                "indeterminate",
                updated="2026-07-01",
            ),
        ),
        today="2026-08-14",
    )
    assert [f["rule"] for f in findings] == ["R6", "R6"]
    f = findings[0]
    assert f["parent"]["key"] == "PROJ-95"
    assert "21 days" in f["evidence"]
    assert "since 2026-07-24" in f["evidence"]
    assert f["proposal"]["action"] == "flag"
    assert f["proposal"]["executable"] is False


def test_r6_silent_under_threshold_other_statuses_and_missing_updated():
    quiet = simplified(
        # 13 days - under the default 14
        raw_issue(
            "PROJ-95", "Task", "In progress", "indeterminate", updated="2026-08-01"
        ),
        # stale but not an R6 status
        raw_issue("PROJ-96", "Task", "Ready for Dev", "new", updated="2026-05-01"),
        raw_issue(
            "PROJ-97", "Task", "In analysis", "indeterminate", updated="2026-05-01"
        ),
        raw_issue("PROJ-98", "Task", "Closed", "done", updated="2026-05-01"),
        # no updated data - never flag on absence of evidence
        raw_issue("PROJ-99", "Task", "In progress", "indeterminate"),
    )
    assert bc.apply_r6(quiet, today="2026-08-14") == []


def test_r6_threshold_configurable():
    week_old = simplified(
        raw_issue(
            "PROJ-95", "Task", "In progress", "indeterminate", updated="2026-08-06"
        )
    )
    assert bc.apply_r6(week_old, today="2026-08-14") == []
    findings = bc.apply_r6(week_old, today="2026-08-14", stale_days=7)
    assert [f["rule"] for f in findings] == ["R6"]


def test_r6_suppressed_by_exception():
    findings = bc.apply_r6(
        simplified(
            raw_issue(
                "PROJ-95", "Task", "In progress", "indeterminate", updated="2026-07-01"
            )
        ),
        today="2026-08-14",
    )
    kept, suppressed, _ = bc.apply_exceptions(
        findings, [entry("PROJ-95", rule="R6")], "2026-08-14"
    )
    assert kept == [] and len(suppressed) == 1


def test_main_includes_r6_findings_and_stale_days_flag(monkeypatch, tmp_path):
    stale = raw_issue(
        "PROJ-95",
        "Task",
        "In progress",
        "indeterminate",
        assignee="dev@example.com",
        updated="2026-08-04",
    )
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")
    monkeypatch.setattr(bc, "search_all", lambda api, jql, timeout: [stale])
    monkeypatch.setattr(
        bc, "fetch_epic_children", lambda api, keys, timeout, workers: ({}, [])
    )
    out = tmp_path / "findings.json"
    common = [
        "--out",
        str(out),
        "--exceptions",
        str(tmp_path / "no.json"),
        "--releases",
        str(tmp_path / "no-rel.json"),
    ]
    # 10 days of silence: default 14-day threshold stays quiet...
    assert bc.main([*common, "--today", "2026-08-14"]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["findings"] == []
    # ...the tightened one fires
    assert bc.main([*common, "--today", "2026-08-14", "--stale-days", "7"]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [f["rule"] for f in data["findings"]] == ["R6"]


# ------------------------------------------------------------------ R7 rules


def test_r7_fires_on_open_external_blocker_even_for_backlog_parent():
    ext = raw_issue("EXT-114331", "Task", "Backlog", "new")
    findings = bc.apply_r7(
        simplified(
            raw_issue(
                "PROJ-342",
                "Epic",
                "Backlog",
                "new",
                links=[link("Block", ext, inward=True)],
            )
        )
    )
    assert [f["rule"] for f in findings] == ["R7"]
    f = findings[0]
    assert f["parent"]["key"] == "PROJ-342"
    assert [c["key"] for c in f["children"]] == ["EXT-114331"]
    assert "external EXT-114331" in f["evidence"]
    assert f["proposal"]["action"] == "flag"
    assert f["proposal"]["executable"] is False


def test_r7_silent_on_same_project_closed_external_outward_and_done_parent():
    own_blocker = raw_issue("PROJ-418", "Task", "Backlog", "new")
    ext_closed = raw_issue("EXT-1", "Task", "Closed", "done")
    ext_open = raw_issue("REL-2", "Task", "Backlog", "new")
    quiet = simplified(
        # same-project blocker = R5 territory, not an external dependency
        raw_issue(
            "PROJ-50",
            "Task",
            "In progress",
            "indeterminate",
            links=[link("Block", own_blocker, inward=True)],
        ),
        raw_issue(
            "PROJ-51",
            "Task",
            "Backlog",
            "new",
            links=[link("Block", ext_closed, inward=True)],
        ),
        # we block THEM - their problem, not our dependency
        raw_issue(
            "PROJ-52",
            "Task",
            "Backlog",
            "new",
            links=[link("Block", ext_open, inward=False)],
        ),
        raw_issue(
            "PROJ-53",
            "Task",
            "Closed",
            "done",
            links=[link("Block", ext_open, inward=True)],
        ),
    )
    assert bc.apply_r7(quiet) == []


def test_r7_suppressed_by_exception():
    ext = raw_issue("EXT-9", "Task", "Backlog", "new")
    findings = bc.apply_r7(
        simplified(
            raw_issue(
                "PROJ-54", "Task", "Backlog", "new", links=[link("Block", ext, True)]
            )
        )
    )
    kept, suppressed, _ = bc.apply_exceptions(
        findings, [entry("PROJ-54", rule="R7")], "2026-08-14"
    )
    assert kept == [] and len(suppressed) == 1


def test_main_includes_r7_findings(monkeypatch, tmp_path):
    ext = raw_issue("EXT-9", "Task", "Backlog", "new")
    blocked = raw_issue(
        "PROJ-55", "Task", "Backlog", "new", links=[link("Block", ext, inward=True)]
    )
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")
    monkeypatch.setattr(bc, "search_all", lambda api, jql, timeout: [blocked])
    monkeypatch.setattr(
        bc, "fetch_epic_children", lambda api, keys, timeout, workers: ({}, [])
    )
    out = tmp_path / "findings.json"
    assert (
        bc.main(
            [
                "--out",
                str(out),
                "--exceptions",
                str(tmp_path / "no.json"),
                "--releases",
                str(tmp_path / "no-rel.json"),
            ]
        )
        == 0
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [f["rule"] for f in data["findings"]] == ["R7"]


# ------------------------------------------------------------------ R8 rules


def raw_release(
    key, status, category, links=(), fix_date=None, duedate=None, released=False
):
    raw = raw_issue(key, "Task", status, category, links=links)
    raw["fields"]["fixVersions"] = (
        [{"name": "Android16.12.0", "releaseDate": fix_date, "released": released}]
        if fix_date
        else []
    )
    raw["fields"]["duedate"] = duedate
    return raw


def release_entry(ticket="REL-23770", platform="android"):
    return {"release_ticket": ticket, "platform": platform}


def test_release_date_prefers_fix_version_over_duedate():
    both = raw_release(
        "REL-1", "Backlog", "new", fix_date="2026-08-19", duedate="2026-08-25"
    )
    due_only = raw_release("REL-2", "Backlog", "new", duedate="2026-08-25")
    neither = raw_release("REL-3", "Backlog", "new")
    assert bc.release_date(both) == "2026-08-19"
    assert bc.release_date(due_only) == "2026-08-25"
    assert bc.release_date(neither) is None


def test_build_releases_resolves_project_members_and_flags_dateless():
    member_stub = raw_issue("PROJ-114", "Task", "Closed", "done")
    full_member = raw_issue(
        "PROJ-114", "Task", "Closed", "done", assignee="dev@example.com"
    )
    ticket = raw_release(
        "REL-23770",
        "Backlog",
        "new",
        links=[link("Relates", member_stub), link("Relates", EPIC_BACKLOG)],
        fix_date="2026-08-19",
    )
    dateless = raw_release(
        "REL-9", "Backlog", "new", links=[link("Relates", member_stub)]
    )
    issues_by_key = {"PROJ-114": bc.simplify(full_member)}
    releases, stale, warnings = bc.build_releases(
        [release_entry(), release_entry("REL-9")],
        {"REL-23770": ticket, "REL-9": dateless},
        issues_by_key,
    )
    assert len(releases) == 2
    first = releases[0]
    assert first["ticket"]["key"] == "REL-23770"
    assert first["date"] == "2026-08-19"
    assert first["platform"] == "android"
    # PROJ-10 is an Epic link but still PROJ-* -> member; the point of the filter
    # is dropping foreign keys, and members resolve to the full scan record
    assert sorted(m["key"] for m in first["members"]) == ["PROJ-10", "PROJ-114"]
    resolved = next(m for m in first["members"] if m["key"] == "PROJ-114")
    assert resolved["assignee"] == "dev@example.com"
    assert stale == []
    assert any("REL-9" in w and "no release date" in w for w in warnings)


def test_build_releases_reports_closed_ticket_as_stale_and_skips_missing():
    closed = raw_release(
        "REL-5", "Closed", "done", fix_date="2026-08-01", released=True
    )
    releases, stale, warnings = bc.build_releases(
        [release_entry("REL-5"), release_entry("REL-6")],
        {"REL-5": closed, "REL-6": None},
        {},
    )
    assert releases == []
    assert [e["release_ticket"] for e in stale] == ["REL-5"]
    assert warnings == []  # fetch failure of REL-6 is meta.errors territory


def test_build_releases_closed_ticket_with_unreleased_version_stays_live():
    # Deploy ticket closed once the build is
    # cut, but the fixVersion is still released=false - the store release is
    # pending, so the radar must keep watching, not propose removal.
    closed_pending = raw_release(
        "REL-5", "Closed", "done", fix_date="2026-08-26", released=False
    )
    releases, stale, warnings = bc.build_releases(
        [release_entry("REL-5")], {"REL-5": closed_pending}, {}
    )
    assert [r["ticket"]["key"] for r in releases] == ["REL-5"]
    assert stale == []
    assert any("REL-5" in w and "release pending" in w for w in warnings)


def test_build_releases_closed_ticket_without_fix_version_is_stale():
    # No fixVersion to consult (duedate-only deploy ticket) -> ticket closure
    # stays the staleness signal, as before.
    closed_dateless = raw_release("REL-5", "Closed", "done", duedate="2026-08-01")
    releases, stale, warnings = bc.build_releases(
        [release_entry("REL-5")], {"REL-5": closed_dateless}, {}
    )
    assert releases == []
    assert [e["release_ticket"] for e in stale] == ["REL-5"]


def test_build_releases_archived_version_counts_as_shipped():
    # Ticket deliberately OPEN so the old category=='done' branch cannot mask
    # the assertion - only the archived flag makes this stale.
    open_archived = raw_release(
        "REL-5", "In progress", "indeterminate", fix_date="2026-08-01"
    )
    open_archived["fields"]["fixVersions"][0]["archived"] = True
    releases, stale, warnings = bc.build_releases(
        [release_entry("REL-5")], {"REL-5": open_archived}, {}
    )
    assert releases == []
    assert [e["release_ticket"] for e in stale] == ["REL-5"]


def test_build_releases_released_version_on_open_ticket_is_stale():
    # Release shipped but the deploy ticket was never closed - the radar's
    # job (readiness before the release) is done; propose removal.
    open_released = raw_release(
        "REL-5", "In progress", "indeterminate", fix_date="2026-08-01", released=True
    )
    releases, stale, warnings = bc.build_releases(
        [release_entry("REL-5")], {"REL-5": open_released}, {}
    )
    assert releases == []
    assert [e["release_ticket"] for e in stale] == ["REL-5"]


def test_build_releases_mixed_versions_stay_live_until_all_shipped():
    # One released version lingering next to a pending one (member slipped to
    # a hotfix) must NOT pull the entry off the radar.
    mixed = raw_release("REL-5", "Closed", "done", fix_date="2026-08-20", released=True)
    mixed["fields"]["fixVersions"].append(
        {"name": "Android16.12.1", "releaseDate": "2026-08-27", "released": False}
    )
    releases, stale, warnings = bc.build_releases(
        [release_entry("REL-5")], {"REL-5": mixed}, {}
    )
    assert [r["ticket"]["key"] for r in releases] == ["REL-5"]
    assert stale == []
    assert any("REL-5" in w and "release pending" in w for w in warnings)


def _release(members, *, date="2026-08-19", status="Backlog", category="new"):
    ticket = raw_release("REL-23770", status, category, fix_date=date)
    return {
        "entry": release_entry(),
        "ticket": bc.simplify(ticket),
        "date": date,
        "platform": "android",
        "members": simplified(*members),
    }


def test_r8_fires_on_unready_member_inside_window():
    findings = bc.apply_r8(
        [
            _release(
                [
                    raw_issue("PROJ-436", "Task", "In progress", "indeterminate"),
                    raw_issue("PROJ-114", "Task", "Closed", "done"),
                ]
            )
        ],
        today="2026-08-17",
    )
    assert [f["rule"] for f in findings] == ["R8"]
    f = findings[0]
    assert f["parent"]["key"] == "REL-23770"
    assert [c["key"] for c in f["children"]] == ["PROJ-436"]
    assert "2026-08-19" in f["evidence"]
    assert "2 day(s) left" in f["evidence"]
    assert f["proposal"]["action"] == "flag"
    assert f["proposal"]["executable"] is False


def test_r8_ready_for_beta_release_counts_as_ready():
    findings = bc.apply_r8(
        [
            _release(
                [
                    raw_issue("PROJ-263", "Task", "Ready for beta release", "new"),
                    raw_issue("PROJ-114", "Task", "Closed", "done"),
                ]
            )
        ],
        today="2026-08-17",
    )
    assert findings == []


def test_r8_silent_outside_window_and_dateless():
    member = raw_issue("PROJ-436", "Task", "In progress", "indeterminate")
    far = _release([member], date="2026-09-30")
    dateless = _release([member], date=None)
    assert bc.apply_r8([far, dateless], today="2026-08-17") == []
    # the same far release fires once the window is widened
    findings = bc.apply_r8([far], today="2026-08-17", window=60)
    assert [f["rule"] for f in findings] == ["R8"]


def test_r8_fires_when_date_passed_but_release_still_open():
    findings = bc.apply_r8(
        [_release([raw_issue("PROJ-436", "Task", "In progress", "indeterminate")])],
        today="2026-08-21",
    )
    assert [f["rule"] for f in findings] == ["R8"]
    assert "2 day(s) overdue" in findings[0]["evidence"]


def test_r8_suppressed_by_exception():
    findings = bc.apply_r8(
        [_release([raw_issue("PROJ-436", "Task", "In progress", "indeterminate")])],
        today="2026-08-17",
    )
    kept, suppressed, _ = bc.apply_exceptions(
        findings, [entry("REL-23770", rule="R8")], "2026-08-17"
    )
    assert kept == [] and len(suppressed) == 1


def test_release_context_annotates_r2_findings_only_on_overlap():
    in_release = raw_issue("PROJ-114", "Story", "Closed", "done")
    outside = raw_issue("PROJ-999", "Story", "Closed", "done")
    epic_in = raw_issue("PROJ-107", "Epic", "On Stage", "indeterminate")
    epic_out = raw_issue("PROJ-94", "Epic", "On Stage", "indeterminate")
    findings, _ = bc.apply_rules(
        graph(
            epic_in,
            epic_out,
            in_release,
            outside,
            epic_children={"PROJ-107": [in_release], "PROJ-94": [outside]},
        )
    )
    assert sorted(f["parent"]["key"] for f in findings) == ["PROJ-107", "PROJ-94"]
    bc.annotate_release_context(findings, [_release([in_release])])
    by_parent = {f["parent"]["key"]: f for f in findings}
    ctx = by_parent["PROJ-107"]["release_context"]
    assert ctx == {
        "release_ticket": "REL-23770",
        "platform": "android",
        "date": "2026-08-19",
    }
    assert "release_context" not in by_parent["PROJ-94"]


def test_release_context_matches_epic_itself_in_composition():
    epic = raw_issue("PROJ-107", "Epic", "On Stage", "indeterminate")
    done_child = raw_issue("PROJ-999", "Story", "Closed", "done")
    findings, _ = bc.apply_rules(
        graph(epic, done_child, epic_children={"PROJ-107": [done_child]})
    )
    bc.annotate_release_context(findings, [_release([epic])])
    assert findings[0]["release_context"]["release_ticket"] == "REL-23770"


def test_load_releases_missing_file_empty(tmp_path):
    assert bc.load_releases(tmp_path / "absent.json") == []


def test_fetch_release_tickets_collects_errors(monkeypatch):
    def fake_run(jira_api, cmd_args, timeout):
        if cmd_args[1] == "REL-6":
            raise RuntimeError("boom")
        return raw_release("REL-23770", "Backlog", "new", fix_date="2026-08-19")

    monkeypatch.setattr(bc, "_run_plugin", fake_run)
    raw_by_key, errors = bc.fetch_release_tickets("api", ["REL-23770", "REL-6"], 30)
    assert raw_by_key["REL-23770"]["key"] == "REL-23770"
    assert raw_by_key["REL-6"] is None
    assert errors and "REL-6" in errors[0]


def test_main_includes_r8_findings_stale_releases_and_window(monkeypatch, tmp_path):
    member = raw_issue(
        "PROJ-436", "Task", "In progress", "indeterminate", assignee="dev@example.com"
    )
    ticket = raw_release(
        "REL-23770",
        "Backlog",
        "new",
        links=[link("Relates", member)],
        fix_date="2026-08-19",
    )
    closed = raw_release("REL-5", "Closed", "done")
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")
    monkeypatch.setattr(bc, "search_all", lambda api, jql, timeout: [member])
    monkeypatch.setattr(
        bc, "fetch_epic_children", lambda api, keys, timeout, workers: ({}, [])
    )
    monkeypatch.setattr(
        bc,
        "fetch_release_tickets",
        lambda api, keys, timeout: ({"REL-23770": ticket, "REL-5": closed}, []),
    )
    releases_file = tmp_path / "releases.json"
    releases_file.write_text(
        json.dumps({"releases": [release_entry(), release_entry("REL-5")]}),
        encoding="utf-8",
    )
    out = tmp_path / "findings.json"
    common = [
        "--out",
        str(out),
        "--exceptions",
        str(tmp_path / "no.json"),
        "--releases",
        str(releases_file),
        "--today",
        "2026-08-17",
    ]
    # 2 days to release: a 1-day window stays quiet...
    assert bc.main([*common, "--release-window", "1"]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["findings"] == []
    assert [e["release_ticket"] for e in data["stale_releases"]] == ["REL-5"]
    # ...the default 7-day window fires
    assert bc.main(common) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [f["rule"] for f in data["findings"]] == ["R8"]


def test_main_annotates_r2_with_release_context(monkeypatch, tmp_path):
    done_child = raw_issue("PROJ-114", "Story", "Closed", "done")
    epic = raw_issue("PROJ-107", "Epic", "On Stage", "indeterminate")
    ticket = raw_release(
        "REL-23770",
        "Backlog",
        "new",
        links=[link("Relates", done_child)],
        fix_date="2026-08-19",
    )
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")
    monkeypatch.setattr(bc, "search_all", lambda api, jql, timeout: [epic, done_child])
    monkeypatch.setattr(
        bc,
        "fetch_epic_children",
        lambda api, keys, timeout, workers: ({"PROJ-107": [done_child]}, []),
    )
    monkeypatch.setattr(
        bc,
        "fetch_release_tickets",
        lambda api, keys, timeout: ({"REL-23770": ticket}, []),
    )
    releases_file = tmp_path / "releases.json"
    releases_file.write_text(
        json.dumps({"releases": [release_entry()]}), encoding="utf-8"
    )
    out = tmp_path / "findings.json"
    assert (
        bc.main(
            [
                "--out",
                str(out),
                "--exceptions",
                str(tmp_path / "no.json"),
                "--releases",
                str(releases_file),
                "--today",
                "2026-08-17",
            ]
        )
        == 0
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    r2 = next(f for f in data["findings"] if f["rule"] == "R2")
    assert r2["release_context"]["release_ticket"] == "REL-23770"


def test_main_release_fetch_error_exits_2(monkeypatch, tmp_path):
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")
    monkeypatch.setattr(bc, "search_all", lambda api, jql, timeout: [])
    monkeypatch.setattr(
        bc, "fetch_epic_children", lambda api, keys, timeout, workers: ({}, [])
    )
    monkeypatch.setattr(
        bc,
        "fetch_release_tickets",
        lambda api, keys, timeout: ({"REL-23770": None}, ["get REL-23770: boom"]),
    )
    releases_file = tmp_path / "releases.json"
    releases_file.write_text(
        json.dumps({"releases": [release_entry()]}), encoding="utf-8"
    )
    out = tmp_path / "findings.json"
    assert (
        bc.main(
            [
                "--out",
                str(out),
                "--exceptions",
                str(tmp_path / "no.json"),
                "--releases",
                str(releases_file),
            ]
        )
        == 2
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["meta"]["errors"] == ["get REL-23770: boom"]


# ----------------------------------------------------------------- ids / etc


def test_finding_ids_stable_under_child_reordering():
    a = raw_issue("PROJ-51", "Story", "Closed", "done")
    b = raw_issue("PROJ-52", "Story", "Closed", "done")
    f1, _ = bc.apply_rules(graph(EPIC_BACKLOG, a, b, epic_children={"PROJ-10": [a, b]}))
    f2, _ = bc.apply_rules(graph(EPIC_BACKLOG, b, a, epic_children={"PROJ-10": [b, a]}))
    assert f1[0]["id"] == f2[0]["id"]


def test_category_mismatch_counts():
    _, r4 = bc.apply_rules(
        graph(
            EPIC_BACKLOG,
            STORY_ACTIVE,
            STORY_DONE,
            epic_children={"PROJ-10": [STORY_ACTIVE, STORY_DONE]},
        )
    )
    assert r4["epic_story"] == 2


# --------------------------------------------------------------- exceptions


def entry(parent, rule=None, child=None, expires=None):
    return {
        "match": {"rule": rule, "parent": parent, "child": child},
        "reason": "parked",
        "added": "2026-08-12",
        "expires": expires,
    }


def sample_findings():
    findings, _ = bc.apply_rules(
        graph(EPIC_BACKLOG, STORY_ACTIVE, epic_children={"PROJ-10": [STORY_ACTIVE]})
    )
    return findings


def test_exception_parent_wildcard_suppresses():
    kept, suppressed, warnings = bc.apply_exceptions(
        sample_findings(), [entry("PROJ-10")], "2026-08-12"
    )
    assert kept == [] and len(suppressed) == 1
    assert suppressed[0]["suppressed_by"] == "parked"
    assert warnings == []


def test_exception_rule_and_child_scoping():
    kept, suppressed, _ = bc.apply_exceptions(
        sample_findings(), [entry("PROJ-10", rule="R2")], "2026-08-12"
    )
    assert len(kept) == 1 and suppressed == []  # R1 finding, R2-scoped entry
    kept, suppressed, _ = bc.apply_exceptions(
        sample_findings(), [entry("PROJ-10", child="PROJ-99")], "2026-08-12"
    )
    assert len(kept) == 1 and suppressed == []  # different child


def test_suppressed_finding_carries_full_entry():
    _, suppressed, _ = bc.apply_exceptions(
        sample_findings(), [entry("PROJ-10", expires="2026-09-01")], "2026-08-12"
    )
    e = suppressed[0]["suppressed_entry"]
    assert e["reason"] == "parked"
    assert e["added"] == "2026-08-12"
    assert e["expires"] == "2026-09-01"


def test_unused_exceptions_reported():
    matching = entry("PROJ-10")
    dead = entry("PROJ-777")
    expired_dead = entry("PROJ-888", expires="2026-08-01")
    unused = bc.find_unused_exceptions(
        sample_findings(), [matching, dead, expired_dead], "2026-08-12"
    )
    # the expired entry already has its own warn mechanic - not double-reported
    assert unused == [dead]


def test_main_emits_unused_exceptions(monkeypatch, tmp_path):
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")
    monkeypatch.setattr(bc, "search_all", lambda api, jql, timeout: [EPIC_BACKLOG])
    monkeypatch.setattr(
        bc, "fetch_epic_children", lambda api, keys, timeout, workers: ({}, [])
    )
    exc_file = tmp_path / "exceptions.json"
    exc_file.write_text(
        json.dumps({"exceptions": [entry("PROJ-777")]}), encoding="utf-8"
    )
    out = tmp_path / "findings.json"
    assert (
        bc.main(
            [
                "--out",
                str(out),
                "--exceptions",
                str(exc_file),
                "--releases",
                str(tmp_path / "no-rel.json"),
            ]
        )
        == 0
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [e["match"]["parent"] for e in data["unused_exceptions"]] == ["PROJ-777"]


def test_expired_exception_warns_and_does_not_suppress():
    kept, suppressed, warnings = bc.apply_exceptions(
        sample_findings(), [entry("PROJ-10", expires="2026-08-01")], "2026-08-12"
    )
    assert len(kept) == 1 and suppressed == []
    assert any("stale exception" in w for w in warnings)


# -------------------------------------------------------------- fetch / main


def test_fetch_epic_children_collects_errors(monkeypatch):
    def fake_run(jira_api, cmd_args, timeout):
        if cmd_args[1] == "PROJ-2":
            raise RuntimeError("boom")
        return [raw_issue("PROJ-11", "Story", "Backlog", "new")]

    monkeypatch.setattr(bc, "_run_plugin", fake_run)
    children, errors = bc.fetch_epic_children("api", ["PROJ-1", "PROJ-2"], 30, 2)
    assert children["PROJ-2"] == [] and len(children["PROJ-1"]) == 1
    assert errors and "PROJ-2" in errors[0]


def test_main_partial_fetch_exits_2(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")
    monkeypatch.setattr(
        bc,
        "search_all",
        lambda api, jql, timeout: [EPIC_BACKLOG, STORY_ACTIVE],
    )
    monkeypatch.setattr(
        bc,
        "fetch_epic_children",
        lambda api, keys, timeout, workers: ({"PROJ-10": []}, ["epic PROJ-10: boom"]),
    )
    out = tmp_path / "findings.json"
    assert (
        bc.main(
            [
                "--out",
                str(out),
                "--exceptions",
                str(tmp_path / "no.json"),
                "--releases",
                str(tmp_path / "no-rel.json"),
            ]
        )
        == 2
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["meta"]["errors"] == ["epic PROJ-10: boom"]
    assert data["scope"]["issues_scanned"] == 2


def test_main_auth_failure_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(bc, "resolve_jira_api", lambda cli: "api")

    def raise_auth(api, jql, timeout):
        raise bc.AuthFailure("401")

    monkeypatch.setattr(bc, "search_all", raise_auth)
    assert bc.main([]) == 1
    assert capsys.readouterr().err.startswith("AUTH:")


def test_search_all_paginates_by_key(monkeypatch):
    pages = {
        None: [raw_issue(f"PROJ-{i}", "Story", "Backlog", "new") for i in range(100)],
        "PROJ-99": [raw_issue("PROJ-100", "Story", "Backlog", "new")],
    }
    calls = []

    def fake_run(jira_api, cmd_args, timeout):
        jql = cmd_args[1]
        calls.append(jql)
        key = "PROJ-99" if "key > PROJ-99" in jql else None
        return {"issues": pages[key]}

    monkeypatch.setattr(bc, "_run_plugin", fake_run)
    issues = bc.search_all("api", "project = PROJ", 30)
    assert len(issues) == 101
    assert len(calls) == 2 and "ORDER BY key ASC" in calls[0]
