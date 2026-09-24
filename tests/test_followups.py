import json
from datetime import date

import pytest

import followups as fu


def _entry(**over):
    base = {
        "id": "fu-2026-08-19-01",
        "what": "Ask Alex about PROJ-328/432",
        "who": "Alex",
        "opened": "2026-08-19",
        "due": None,
        "snoozed_until": None,
        "status": "open",
        "source": "memory:project_insights_menu_2026-08-17.md",
        "closed": None,
        "outcome": None,
    }
    base.update(over)
    return base


def test_validate_accepts_open_entry():
    fu.validate_entry(_entry())


def test_validate_rejects_missing_required_field():
    e = _entry()
    del e["who"]
    with pytest.raises(fu.FollowupsError):
        fu.validate_entry(e)


def test_validate_rejects_unknown_field():
    with pytest.raises(fu.FollowupsError):
        fu.validate_entry(_entry(priority="High"))


def test_validate_rejects_unknown_status():
    with pytest.raises(fu.FollowupsError):
        fu.validate_entry(_entry(status="done"))


def test_validate_rejects_bad_id_format():
    with pytest.raises(fu.FollowupsError, match="id must match"):
        fu.validate_entry(_entry(id="followup-1"))


def test_validate_rejects_closed_without_outcome():
    with pytest.raises(fu.FollowupsError):
        fu.validate_entry(_entry(status="closed", closed="2026-08-20"))


def test_validate_rejects_snoozed_without_until():
    with pytest.raises(fu.FollowupsError):
        fu.validate_entry(_entry(status="snoozed"))


def test_validate_rejects_bad_date():
    with pytest.raises(fu.FollowupsError):
        fu.validate_entry(_entry(opened="19-08-2026"))


def test_load_registry_roundtrip(tmp_path):
    p = tmp_path / "reg.json"
    p.write_text(json.dumps([_entry()]), encoding="utf-8")
    assert fu.load_registry(p) == [_entry()]


def test_load_registry_missing_file_raises(tmp_path):
    with pytest.raises(fu.FollowupsError, match="not found"):
        fu.load_registry(tmp_path / "nope.json")


def test_load_registry_invalid_json_raises(tmp_path):
    p = tmp_path / "reg.json"
    p.write_text("{broken", encoding="utf-8")
    with pytest.raises(fu.FollowupsError, match="JSON"):
        fu.load_registry(p)


def test_load_registry_non_array_root_raises(tmp_path):
    p = tmp_path / "reg.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(fu.FollowupsError, match="array"):
        fu.load_registry(p)


def test_save_registry_validates_before_writing(tmp_path):
    p = tmp_path / "reg.json"
    with pytest.raises(fu.FollowupsError):
        fu.save_registry([_entry(status="bogus")], p)
    assert not p.exists()


def test_next_id_increments_within_day():
    entries = [_entry(id="fu-2026-08-20-01"), _entry(id="fu-2026-08-20-02")]
    assert fu.next_id(entries, date(2026, 8, 20)) == "fu-2026-08-20-03"


def test_next_id_starts_at_one_for_new_day():
    assert fu.next_id([_entry()], date(2026, 8, 20)) == "fu-2026-08-20-01"


def test_add_entry_appends_and_does_not_mutate_input():
    entries = []
    out = fu.add_entry(entries, "Ask X about Y", "X", date(2026, 8, 20), source="radar")
    assert entries == []
    assert [e["id"] for e in out] == ["fu-2026-08-20-01"]
    assert out[0]["status"] == "open"
    assert out[0]["opened"] == "2026-08-20"
    assert out[0]["source"] == "radar"


def test_add_entry_rejects_bad_due_date():
    with pytest.raises(fu.FollowupsError):
        fu.add_entry([], "Ask X", "X", date(2026, 8, 20), due="soon")


def test_close_entry_sets_outcome_and_date_without_mutating_input():
    entries = [_entry()]
    out = fu.close_entry(
        entries, "fu-2026-08-19-01", "resolved: PROJ-328 stays", date(2026, 8, 20)
    )
    assert out[0]["status"] == "closed"
    assert out[0]["closed"] == "2026-08-20"
    assert out[0]["outcome"] == "resolved: PROJ-328 stays"
    assert entries[0]["status"] == "open"


def test_close_entry_refuses_blank_outcome():
    with pytest.raises(fu.FollowupsError, match="outcome"):
        fu.close_entry([_entry()], "fu-2026-08-19-01", "   ", date(2026, 8, 20))


def test_close_entry_refuses_already_closed():
    closed = _entry(status="closed", closed="2026-08-19", outcome="done")
    with pytest.raises(fu.FollowupsError, match="already closed"):
        fu.close_entry([closed], "fu-2026-08-19-01", "again", date(2026, 8, 20))


def test_close_entry_unknown_id_raises():
    with pytest.raises(fu.FollowupsError, match="no entry"):
        fu.close_entry([_entry()], "fu-9999-01-01-01", "x", date(2026, 8, 20))


def test_snooze_entry_sets_status_and_until():
    out = fu.snooze_entry(
        [_entry()], "fu-2026-08-19-01", "2026-08-25", date(2026, 8, 20)
    )
    assert out[0]["status"] == "snoozed"
    assert out[0]["snoozed_until"] == "2026-08-25"


def test_snooze_entry_refuses_past_or_today():
    with pytest.raises(fu.FollowupsError, match="after"):
        fu.snooze_entry([_entry()], "fu-2026-08-19-01", "2026-08-20", date(2026, 8, 20))


def test_snooze_entry_refuses_closed():
    closed = _entry(status="closed", closed="2026-08-19", outcome="done")
    with pytest.raises(fu.FollowupsError, match="closed"):
        fu.snooze_entry([closed], "fu-2026-08-19-01", "2026-08-25", date(2026, 8, 20))


def test_cli_add_then_close_roundtrip(tmp_path, monkeypatch, capsys):
    p = tmp_path / "reg.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("FOLLOWUPS_REGISTRY", str(p))
    assert fu.main(["add", "Ask X", "--who", "X"]) == 0
    entry_id = fu.load_registry(p)[0]["id"]
    assert fu.main(["close", entry_id, "--outcome", "answered"]) == 0
    assert fu.load_registry(p)[0]["status"] == "closed"


def test_cli_error_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FOLLOWUPS_REGISTRY", str(tmp_path / "nope.json"))
    assert fu.main(["list"]) == 1
    assert "ERROR" in capsys.readouterr().err


def test_add_entry_backdates_opened():
    out = fu.add_entry([], "Ask X", "X", date(2026, 8, 21), opened="2026-08-03")
    assert out[0]["opened"] == "2026-08-03"
    assert out[0]["id"].startswith("fu-2026-08-21-")


def test_add_entry_rejects_bad_opened():
    with pytest.raises(fu.FollowupsError):
        fu.add_entry([], "Ask X", "X", date(2026, 8, 21), opened="not-a-date")


def test_cli_list_survives_cp1252_stdout(tmp_path, monkeypatch):
    import io
    import sys as _sys

    p = tmp_path / "reg.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("FOLLOWUPS_REGISTRY", str(p))
    assert (
        fu.main(["add", "Ask Alex \u2013 caf\u00e9 budget", "--who", "Ren\u00e9"]) == 0
    )
    buf = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(_sys, "stdout", buf)
    assert fu.main(["list"]) == 0


# ------------------------------------------------------------------- nudge


def test_validate_accepts_last_nudged_date_and_rejects_bad():
    fu.validate_entry(_entry(last_nudged="2026-08-20"))
    with pytest.raises(fu.FollowupsError):
        fu.validate_entry(_entry(last_nudged="recently"))


def test_nudge_entry_sets_date_without_mutating_input():
    entries = [_entry()]
    out = fu.nudge_entry(entries, "fu-2026-08-19-01", date(2026, 8, 25))
    assert out[0]["last_nudged"] == "2026-08-25"
    assert entries[0].get("last_nudged") is None


def test_nudge_entry_refuses_non_open():
    closed = _entry(status="closed", closed="2026-08-20", outcome="done")
    with pytest.raises(fu.FollowupsError, match="only open"):
        fu.nudge_entry([closed], "fu-2026-08-19-01", date(2026, 8, 25))


def test_candidates_require_min_age():
    young = _entry(opened="2026-08-22")
    old = _entry(id="fu-2026-08-19-02", opened="2026-08-10")
    got = fu.nudge_candidates([young, old], date(2026, 8, 25), min_age=7)
    assert [e["id"] for e in got] == ["fu-2026-08-19-02"]
    assert got[0]["age_days"] == 15


def test_candidates_overdue_beats_min_age():
    young_overdue = _entry(opened="2026-08-23", due="2026-08-24")
    got = fu.nudge_candidates([young_overdue], date(2026, 8, 25), min_age=7)
    assert len(got) == 1
    assert got[0]["overdue_days"] == 1


def test_candidates_exclude_self_but_not_names_containing_an_alias():
    mine = _entry(opened="2026-08-01", who="me")
    mine2 = _entry(id="fu-2026-08-19-02", opened="2026-08-01", who="PO (me)")
    mine3 = _entry(id="fu-2026-08-19-03", opened="2026-08-01", who="PO (self)")
    amelia = _entry(id="fu-2026-08-19-04", opened="2026-08-01", who="waiting on Amelia")
    got = fu.nudge_candidates([mine, mine2, mine3, amelia], date(2026, 8, 25))
    assert [e["who"] for e in got] == ["waiting on Amelia"]


def test_candidates_cooldown_suppresses_recent_nudge():
    recent = _entry(opened="2026-08-01", last_nudged="2026-08-22")
    stale = _entry(id="fu-2026-08-19-02", opened="2026-08-01", last_nudged="2026-08-10")
    got = fu.nudge_candidates([recent, stale], date(2026, 8, 25), cooldown=5)
    assert [e["id"] for e in got] == ["fu-2026-08-19-02"]


def test_candidates_exclude_snoozed_and_closed():
    snoozed = _entry(opened="2026-08-01", status="snoozed", snoozed_until="2026-09-01")
    closed = _entry(
        id="fu-2026-08-19-02",
        opened="2026-08-01",
        status="closed",
        closed="2026-08-20",
        outcome="done",
    )
    assert fu.nudge_candidates([snoozed, closed], date(2026, 8, 25)) == []


def test_candidates_sorted_oldest_first():
    a = _entry(opened="2026-08-10")
    b = _entry(id="fu-2026-08-19-02", opened="2026-08-01")
    got = fu.nudge_candidates([a, b], date(2026, 8, 25))
    assert [e["id"] for e in got] == ["fu-2026-08-19-02", "fu-2026-08-19-01"]


# -------------------------------------------------------- effectively_open


def test_effectively_open_states():
    today = date(2026, 8, 25)
    assert fu.effectively_open(_entry(), today) is True
    expired = _entry(status="snoozed", snoozed_until="2026-08-20")
    live = _entry(status="snoozed", snoozed_until="2026-09-01")
    closed = _entry(status="closed", closed="2026-08-20", outcome="x")
    assert fu.effectively_open(expired, today) is True
    assert fu.effectively_open(live, today) is False
    assert fu.effectively_open(closed, today) is False


def test_candidates_include_expired_snooze():
    e = _entry(opened="2026-08-01", status="snoozed", snoozed_until="2026-08-20")
    got = fu.nudge_candidates([e], date(2026, 8, 25))
    assert [x["id"] for x in got] == ["fu-2026-08-19-01"]


def test_candidates_exclude_live_snooze():
    e = _entry(opened="2026-08-01", status="snoozed", snoozed_until="2026-09-01")
    assert fu.nudge_candidates([e], date(2026, 8, 25)) == []


def test_nudge_unsnoozes_expired_entry():
    e = _entry(status="snoozed", snoozed_until="2026-08-20")
    out = fu.nudge_entry([e], "fu-2026-08-19-01", date(2026, 8, 25))
    assert out[0]["status"] == "open"
    assert out[0]["snoozed_until"] is None
    assert out[0]["last_nudged"] == "2026-08-25"


def test_nudge_refuses_live_snooze():
    e = _entry(status="snoozed", snoozed_until="2026-09-01")
    with pytest.raises(fu.FollowupsError, match="only open"):
        fu.nudge_entry([e], "fu-2026-08-19-01", date(2026, 8, 25))


# --- age buckets and the per-person ping view -------------------------------

TODAY = date(2026, 9, 18)


def test_buckets_split_at_thirty_and_fifteen_days():
    entries = [
        _entry(id="fu-2026-08-01-01", opened="2026-08-18"),  # 31d -> over
        _entry(id="fu-2026-08-01-02", opened="2026-08-19"),  # 30d -> mid
        _entry(id="fu-2026-08-01-03", opened="2026-09-03"),  # 15d -> mid
        _entry(id="fu-2026-08-01-04", opened="2026-09-04"),  # 14d -> recent
    ]
    buckets = fu.buckets(entries, TODAY)
    assert [e["id"] for e in buckets["over"]] == ["fu-2026-08-01-01"]
    assert [e["id"] for e in buckets["mid"]] == ["fu-2026-08-01-02", "fu-2026-08-01-03"]
    assert [e["id"] for e in buckets["recent"]] == ["fu-2026-08-01-04"]


def test_buckets_are_oldest_first_and_carry_age():
    entries = [
        _entry(id="fu-2026-08-01-01", opened="2026-09-10"),
        _entry(id="fu-2026-08-01-02", opened="2026-09-01"),
    ]
    recent, mid = (
        fu.buckets(entries, TODAY)["recent"],
        fu.buckets(entries, TODAY)["mid"],
    )
    assert mid[0]["age_days"] == 17
    assert recent[0]["age_days"] == 8


def test_buckets_use_the_same_open_semantics_as_the_briefing():
    entries = [
        _entry(
            id="fu-2026-08-01-01", status="closed", closed="2026-09-01", outcome="x"
        ),
        _entry(id="fu-2026-08-01-02", status="snoozed", snoozed_until="2026-12-01"),
        _entry(id="fu-2026-08-01-03", status="snoozed", snoozed_until="2026-09-01"),
    ]
    buckets = fu.buckets(entries, TODAY)
    ids = [e["id"] for rows in buckets.values() for e in rows]
    assert ids == ["fu-2026-08-01-03"]  # expired snooze counts, live one does not


def test_ping_summary_collapses_people_and_counts_never_pinged():
    entries = [
        _entry(id="fu-2026-08-01-01", who="Alex", opened="2026-08-01"),
        _entry(id="fu-2026-08-01-02", who="Alex", opened="2026-09-01"),
        _entry(
            id="fu-2026-08-01-03",
            who="Denis",
            opened="2026-09-05",
            last_nudged="2026-09-06",
        ),
    ]
    rows = fu.ping_summary(entries, TODAY)
    alex = next(r for r in rows if r["who"] == "Alex")
    denis = next(r for r in rows if r["who"] == "Denis")
    assert alex["count"] == 2 and alex["oldest_days"] == 48
    assert alex["never_pinged"] == 2
    assert denis["never_pinged"] == 0  # pinged once, cooldown already past


def test_ping_summary_is_oldest_wait_first():
    entries = [
        _entry(id="fu-2026-08-01-01", who="Denis", opened="2026-09-01"),
        _entry(id="fu-2026-08-01-02", who="Alex", opened="2026-08-01"),
    ]
    assert [r["who"] for r in fu.ping_summary(entries, TODAY)] == ["Alex", "Denis"]


def test_ping_summary_skips_items_owned_by_me():
    entries = [_entry(id="fu-2026-08-01-01", who="me", opened="2026-08-01")]
    assert fu.ping_summary(entries, TODAY) == []


def test_cli_stats_prints_buckets_and_pings(tmp_path, monkeypatch, capsys):
    path = tmp_path / "reg.json"
    path.write_text(
        json.dumps([_entry(id="fu-2026-08-01-01", who="Alex", opened="2026-08-01")]),
        encoding="utf-8",
    )
    monkeypatch.setenv("FOLLOWUPS_REGISTRY", str(path))
    assert fu.main(["stats"]) == 0
    out = capsys.readouterr().out
    assert "1 open: 1 over 30d" in out
    assert "Worth a ping:" in out and "Alex" in out
