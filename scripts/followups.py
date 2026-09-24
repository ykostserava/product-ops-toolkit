"""Follow-ups registry: canonical store for open, person-addressed follow-ups.

Registry: scripts/followups.json (override with FOLLOWUPS_REGISTRY env).
Every write goes through this module - skills must never edit the JSON by
hand. Deliberately separate from a product-scope backlog/radar document: that
holds scope gaps with scope-triggers; this registry holds dated follow-ups
addressed to a person ("waiting on X since D").

FOLLOWUPS_SELF_ALIASES (env, comma-separated; default "self,me") names the
registry owner: entries whose `who` is one of these are never nudge targets.
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "followups.json"

ID_RE = re.compile(r"^fu-\d{4}-\d{2}-\d{2}-\d{2}$")
STATUSES = {"open", "snoozed", "closed"}
REQUIRED_FIELDS = {"id", "what", "who", "opened", "status"}
ALL_FIELDS = REQUIRED_FIELDS | {
    "due",
    "snoozed_until",
    "source",
    "closed",
    "outcome",
    "last_nudged",
}
# "who" values marking the registry owner - never a nudge target ("me",
# "PO (me)", "PO (self)"). The non-word boundaries keep an alias from matching
# inside a name ("Amelia" contains "me" and is somebody else).
_SELF_ALIASES = [
    a.strip()
    for a in os.environ.get("FOLLOWUPS_SELF_ALIASES", "self,me").split(",")
    if a.strip()
]
SELF_RE = re.compile(
    r"(?:^|[^\w])(?:" + "|".join(re.escape(a) for a in _SELF_ALIASES) + r")(?:[^\w]|$)",
    re.IGNORECASE,
)
DEFAULT_NUDGE_MIN_AGE = 7  # calendar days before an item is worth a ping
DEFAULT_NUDGE_COOLDOWN = 5  # days between pings for the same item


class FollowupsError(Exception):
    """Registry unreadable or an operation is invalid."""


def registry_path():
    return Path(os.environ.get("FOLLOWUPS_REGISTRY", str(DEFAULT_PATH)))


def _parse_date(value, field):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise FollowupsError(f"{field}: expected YYYY-MM-DD, got {value!r}") from None


def validate_entry(entry):
    if not isinstance(entry, dict):
        raise FollowupsError(f"entry is not an object: {entry!r}")
    label = entry.get("id", "?")
    missing = REQUIRED_FIELDS - entry.keys()
    if missing:
        raise FollowupsError(f"{label}: missing fields {sorted(missing)}")
    unknown = entry.keys() - ALL_FIELDS
    if unknown:
        raise FollowupsError(f"{label}: unknown fields {sorted(unknown)}")
    if not ID_RE.match(entry["id"]):
        raise FollowupsError(
            f"{label}: id must match fu-YYYY-MM-DD-NN, got {entry['id']!r}"
        )
    if entry["status"] not in STATUSES:
        raise FollowupsError(f"{label}: unknown status {entry['status']!r}")
    _parse_date(entry["opened"], "opened")
    for field in ("due", "snoozed_until", "closed", "last_nudged"):
        if entry.get(field) is not None:
            _parse_date(entry[field], field)
    if entry["status"] == "closed" and not (entry.get("outcome") or "").strip():
        raise FollowupsError(f"{label}: closed entry requires a non-empty outcome")
    if entry["status"] == "snoozed" and not entry.get("snoozed_until"):
        raise FollowupsError(f"{label}: snoozed entry requires snoozed_until")


def load_registry(path=None):
    p = Path(path) if path else registry_path()
    if not p.exists():
        raise FollowupsError(f"registry not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise FollowupsError(f"registry is not valid JSON: {e}") from None
    if not isinstance(raw, list):
        raise FollowupsError("registry root must be a JSON array")
    for entry in raw:
        validate_entry(entry)
    return raw


def save_registry(entries, path=None):
    for entry in entries:
        validate_entry(entry)
    p = Path(path) if path else registry_path()
    p.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def next_id(entries, today):
    prefix = f"fu-{today.isoformat()}-"
    taken = [
        int(e["id"][len(prefix) :])
        for e in entries
        if e["id"].startswith(prefix) and e["id"][len(prefix) :].isdigit()
    ]
    return f"{prefix}{max(taken, default=0) + 1:02d}"


def add_entry(entries, what, who, today, due=None, source=None, opened=None):
    # opened backdates real-world follow-ups on import; the id keeps today's
    # date so ids stay collision-free per add-day.
    entry = {
        "id": next_id(entries, today),
        "what": what,
        "who": who,
        "opened": opened or today.isoformat(),
        "due": due,
        "snoozed_until": None,
        "status": "open",
        "source": source,
        "closed": None,
        "outcome": None,
        "last_nudged": None,
    }
    validate_entry(entry)
    return entries + [entry]


def _replace(entries, entry_id, mutate):
    out, found = [], False
    for e in entries:
        if e["id"] == entry_id:
            e = dict(e)
            mutate(e)
            validate_entry(e)
            found = True
        out.append(e)
    if not found:
        raise FollowupsError(f"no entry with id {entry_id}")
    return out


def close_entry(entries, entry_id, outcome, today):
    if not (outcome or "").strip():
        raise FollowupsError("close requires a non-empty outcome")

    def mutate(e):
        if e["status"] == "closed":
            raise FollowupsError(f"{entry_id} is already closed")
        e.update(
            status="closed",
            closed=today.isoformat(),
            outcome=outcome.strip(),
            snoozed_until=None,
        )

    return _replace(entries, entry_id, mutate)


def effectively_open(entry, today):
    """Open - or snoozed with an EXPIRED snoozed_until. Nothing ever flips
    snoozed back to open automatically, so consumers that filter on raw
    status silently lose forgotten snoozes; mirror the briefing's
    snooze-expired semantics instead."""
    if entry.get("status") == "open":
        return True
    if entry.get("status") == "snoozed":
        until = entry.get("snoozed_until")
        try:
            return until is not None and date.fromisoformat(until) <= today
        except (TypeError, ValueError):
            return False
    return False


AGE_EDGES = (30, 15)  # calendar-day boundaries between the three age buckets


def buckets(entries, today, edges=AGE_EDGES):
    """Split the effectively-open registry into age buckets, oldest first.

    Why: a briefing that prints every open item flat, marked STALE past N
    days, ends with almost every row carrying the mark - so the mark says
    nothing and the list gets scrolled past. Buckets put a number on the part
    that actually rotted ("9 items older than 30 days, the oldest 50").

    Units: calendar days since `opened` (not working days - what a person owes
    an answer on does not pause for weekends). Returns {"over": [...],
    "mid": [...], "recent": [...]} with age_days and last_nudged on each.
    """
    old_edge, mid_edge = edges
    out = {"over": [], "mid": [], "recent": []}
    for entry in entries:
        if not effectively_open(entry, today):
            continue
        age = (today - _parse_date(entry["opened"], "opened")).days
        row = {**entry, "age_days": age}
        key = "over" if age > old_edge else "mid" if age >= mid_edge else "recent"
        out[key].append(row)
    for rows in out.values():
        rows.sort(key=lambda r: -r["age_days"])
    return out


def ping_summary(
    entries, today, min_age=DEFAULT_NUDGE_MIN_AGE, cooldown=DEFAULT_NUDGE_COOLDOWN
):
    """Per-person view of who is worth a ping - one row per person, not per item.

    Built from nudge_candidates (same thresholds, one definition of "worth a
    ping"), collapsed by `who` so the briefing can say "waiting on X: 3 items,
    oldest 50d, never pinged" instead of repeating a name three times.
    `never_pinged` is the count with no last_nudged at all - if that equals
    the open count, the nudge drafts the /followups skill offers are being
    written but never recorded as sent.
    """
    people = {}
    for cand in nudge_candidates(entries, today, min_age=min_age, cooldown=cooldown):
        row = people.setdefault(
            cand["who"],
            {"who": cand["who"], "count": 0, "oldest_days": 0, "never_pinged": 0},
        )
        row["count"] += 1
        row["oldest_days"] = max(row["oldest_days"], cand["age_days"])
        if not cand.get("last_nudged"):
            row["never_pinged"] += 1
    return sorted(people.values(), key=lambda r: (-r["oldest_days"], r["who"]))


def nudge_entry(entries, entry_id, today):
    """Record that a ping was actually SENT (the skill only drafts). An
    expired snooze counts as open and is un-snoozed by the ping."""

    def mutate(e):
        if not effectively_open(e, today):
            raise FollowupsError(
                f"{entry_id} is {e['status']} - only open entries get nudged"
            )
        e["last_nudged"] = today.isoformat()
        if e["status"] == "snoozed":
            e.update(status="open", snoozed_until=None)

    return _replace(entries, entry_id, mutate)


def nudge_candidates(
    entries, today, min_age=DEFAULT_NUDGE_MIN_AGE, cooldown=DEFAULT_NUDGE_COOLDOWN
):
    """Open entries waiting on SOMEONE ELSE long enough to deserve a ping.

    A candidate is open, addressed to another person, either overdue or older
    than min_age days, and not pinged within the cooldown. Returns entries
    augmented with age_days / overdue_days, oldest first.
    """
    out = []
    for e in entries:
        if not effectively_open(e, today) or SELF_RE.search(e["who"] or ""):
            continue
        age = (today - _parse_date(e["opened"], "opened")).days
        overdue = (today - _parse_date(e["due"], "due")).days if e.get("due") else None
        if not ((overdue is not None and overdue > 0) or age >= min_age):
            continue
        last = e.get("last_nudged")
        if last and (today - _parse_date(last, "last_nudged")).days < cooldown:
            continue
        out.append({**e, "age_days": age, "overdue_days": overdue})
    out.sort(key=lambda e: -e["age_days"])
    return out


def snooze_entry(entries, entry_id, until, today):
    until_d = _parse_date(until, "snoozed_until")
    if until_d <= today:
        raise FollowupsError(f"snooze date must be after {today.isoformat()}")

    def mutate(e):
        if e["status"] == "closed":
            raise FollowupsError(f"{entry_id} is closed - cannot snooze")
        e.update(status="snoozed", snoozed_until=until_d.isoformat())

    return _replace(entries, entry_id, mutate)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="followups.py", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list", help="print entries (open+snoozed by default)")
    p_list.add_argument("--all", action="store_true", help="include closed")
    p_add = sub.add_parser("add", help="add an open follow-up")
    p_add.add_argument("what")
    p_add.add_argument("--who", required=True)
    p_add.add_argument("--due")
    p_add.add_argument("--source")
    p_add.add_argument("--opened", help="backdate: real start date YYYY-MM-DD")
    p_close = sub.add_parser("close", help="close with an outcome")
    p_close.add_argument("id")
    p_close.add_argument("--outcome", required=True)
    p_snooze = sub.add_parser("snooze", help="hide until a date")
    p_snooze.add_argument("id")
    p_snooze.add_argument("--until", required=True)
    p_nudge = sub.add_parser("nudge", help="record that a ping was sent")
    p_nudge.add_argument("id")
    p_cand = sub.add_parser(
        "nudge-candidates",
        help="JSON of open items waiting on someone else long enough to ping",
    )
    p_cand.add_argument("--min-age", type=int, default=DEFAULT_NUDGE_MIN_AGE)
    p_cand.add_argument("--cooldown", type=int, default=DEFAULT_NUDGE_COOLDOWN)
    p_stats = sub.add_parser(
        "stats", help="age buckets + per-person ping summary (triage view)"
    )
    p_stats.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    # Windows consoles default to cp1252; the registry legitimately holds
    # non-ASCII names and text - never let output encoding kill a read.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    today = date.today()
    try:
        entries = load_registry()
        if args.cmd == "list":
            shown = (
                entries if args.all else [e for e in entries if e["status"] != "closed"]
            )
            if not shown:
                print("No entries.")
            for e in sorted(shown, key=lambda e: e["opened"]):
                due = f"  due={e['due']}" if e.get("due") else ""
                print(
                    f"{e['id']}  [{e['status']:7}]  opened={e['opened']}{due}  who={e['who']}  {e['what']}"
                )
            return 0
        if args.cmd == "stats":
            buck = buckets(entries, today)
            pings = ping_summary(entries, today)
            if args.json:
                print(
                    json.dumps(
                        {"buckets": buck, "pings": pings}, ensure_ascii=False, indent=2
                    )
                )
                return 0
            total = sum(len(v) for v in buck.values())
            old_edge, mid_edge = AGE_EDGES
            print(
                f"{total} open: {len(buck['over'])} over {old_edge}d, "
                f"{len(buck['mid'])} {mid_edge}-{old_edge}d, "
                f"{len(buck['recent'])} under {mid_edge}d"
            )
            for row in buck["over"]:
                pinged = row.get("last_nudged") or "never pinged"
                print(
                    f"  {row['age_days']:>3}d  {row['id']}  {row['who']}  "
                    f"[{pinged}]  {row['what'][:70]}"
                )
            if pings:
                print("\nWorth a ping:")
                for row in pings:
                    print(
                        f"  {row['who']}: {row['count']} item(s), oldest "
                        f"{row['oldest_days']}d, {row['never_pinged']} never pinged"
                    )
            return 0
        if args.cmd == "nudge-candidates":
            cands = nudge_candidates(
                entries, today, min_age=args.min_age, cooldown=args.cooldown
            )
            print(json.dumps(cands, ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "nudge":
            entries = nudge_entry(entries, args.id, today)
        elif args.cmd == "add":
            entries = add_entry(
                entries,
                args.what,
                args.who,
                today,
                due=args.due,
                source=args.source,
                opened=args.opened,
            )
        elif args.cmd == "close":
            entries = close_entry(entries, args.id, args.outcome, today)
        elif args.cmd == "snooze":
            entries = snooze_entry(entries, args.id, args.until, today)
        save_registry(entries)
        print(f"OK: {args.cmd} -> {registry_path()}")
        return 0
    except FollowupsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
