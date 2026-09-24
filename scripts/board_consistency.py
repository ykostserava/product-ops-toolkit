#!/usr/bin/env python3
"""Detect parent/child status inconsistencies on a Jira board.

Deterministic engine for the /board-sync skill (project-manager agent): fetches
the project's issue graph via scripts/jira_api.py, builds the three hierarchy
edges (Initiative<-Epic via the configured parent link types; Epic<-Story via
the `epic` command; Story<-Sub-task via the subtasks field) and applies
consistency rules on statusCategory (new/indeterminate/done):

    R1  a child is active while the parent is still in a to-do status
    R2  all children are done but the parent is not closed
        (container edges only - a story with done sub-tasks is NOT closable
        by that fact alone, so the story<-subtask edge is exempt)
    R3  the parent is closed while a child is still open (FLAG-ONLY: there is
        no REST path out of Closed)
    R4  an issue sits in an active status with no assignee (containers exempt:
        Initiative/Epic analysis is PO work; the candidate assignee is proposed
        by the project-manager agent, never by this engine)
    R5  an issue is In progress while an unresolved blocker exists (FLAG-ONLY:
        somebody works on top of an open dependency; Ready for Dev with a
        blocker is deliberately NOT flagged - a staged Kanban queue is normal)
    R6  aging WIP: an In progress / Ready for testing issue with no updates
        for --stale-days days (default 14; FLAG-ONLY - the project-manager
        agent separates "quietly progressing in an MR" from "abandoned" via
        devinfo/comments; no updated field = no finding)
    R7  external dependency radar: any open issue blocked by an open ticket
        from ANOTHER project (key prefix differs; FLAG-ONLY - the agent
        judges WAIT vs ESCALATE and names who to ping; deliberately overlaps
        R5 when the blocked issue is In progress - two distinct signals)
    R8  release radar (FLAG-ONLY): tickets in an upcoming release that are
        not release-ready inside --release-window days of the release date.
        Releases come from scripts/releases.json (one entry per deploy
        ticket the devs create); composition = the deploy ticket's issue
        links into the project, date = fixVersion releaseDate (fallback
        duedate). Additionally annotates R2 findings with release_context
        when the epic waits for a planned release, replacing manual
        exceptions for that case.

Status names, the project key and the parent link types come from
scripts/jira-config.json (see jira_config.py).

plus a summary count of parent/child category mismatches per edge.

READ-ONLY: this script never writes to Jira. Exceptions (deliberate HOLDs) are
suppressed via scripts/board-exceptions.json but still listed in the output.

Usage:
    python scripts/board_consistency.py [--out findings.json]
        [--jql "project = PROJ"] [--exceptions scripts/board-exceptions.json]
        [--releases scripts/releases.json] [--release-window 7]
        [--workers 8] [--timeout 30] [--jira-api PATH] [--today YYYY-MM-DD]

Exit codes (same contract as jira_batch_fetch):
    0  clean
    2  partial - some fetches failed; findings still emitted, see meta.errors
    1  fatal   - stderr starting with "AUTH:" means VPN/token (STOP)
"""

import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jira_batch_fetch import AUTH_RE, AuthFailure, resolve_jira_api  # noqa: E402
from jira_config import CONFIG, lower_set  # noqa: E402

SCHEMA = "board-consistency/1"
_STATUSES = CONFIG["statuses"]
PROJECT_KEY = CONFIG["project_key"]
PARENT_LINK_TYPES = tuple(lower_set(CONFIG["parent_link_types"]))
# Where an Epic goes when its first child starts.
EPIC_ACTIVE_STATUS = _STATUSES["epic_active"]
CLOSED_STATUS = _STATUSES["closed"]
CONTAINER_EDGES = ("initiative_epic", "epic_story")
# R4: statuses where somebody should own the issue (queue statuses stay
# unassigned by design - Kanban pull). Matched by NAME, not category: queue
# statuses such as Ready for Dev often carry category "new".
R4_ACTIVE_STATUSES = lower_set(_STATUSES["r4_active"])
R4_EXEMPT_TYPES = lower_set(_STATUSES["r4_exempt_types"])
# R6: statuses where prolonged silence means stuck work (analysis and queue
# statuses age for prioritization reasons - not staleness).
R6_STALE_STATUSES = lower_set(_STATUSES["r6_stale"])
DEFAULT_STALE_DAYS = 14
# R8: statuses that count as release-ready besides anything in the done
# category (a testing status is deliberately NOT ready - untested work).
R8_READY_STATUSES = lower_set(_STATUSES["r8_ready"])
DEFAULT_RELEASE_WINDOW = 7
DEFAULT_EXCEPTIONS = Path(__file__).parent / "board-exceptions.json"
DEFAULT_RELEASES = Path(__file__).parent / "releases.json"


# ---------------------------------------------------------------- graph build


def simplify(raw):
    """Reduce a raw Jira issue payload to the fields the rules need."""
    fields = raw.get("fields", {})
    status = fields.get("status", {})
    return {
        "key": raw.get("key"),
        "type": fields.get("issuetype", {}).get("name", ""),
        "status": status.get("name", ""),
        "category": status.get("statusCategory", {}).get("key", ""),
        "assignee": (fields.get("assignee") or {}).get("name"),
        "updated": (fields.get("updated") or "")[:10] or None,
        "summary": fields.get("summary", ""),
        "subtasks": [simplify(s) for s in fields.get("subtasks", [])],
        "links": [
            {
                "name": link.get("type", {}).get("name", ""),
                # inward = the other issue points AT us ("is blocked by" side
                # on Jira Server - verify once on your instance)
                "direction": "inward" if link.get("inwardIssue") else "outward",
                "other": simplify(link.get("inwardIssue") or link.get("outwardIssue")),
            }
            for link in fields.get("issuelinks", [])
            if link.get("inwardIssue") or link.get("outwardIssue")
        ],
    }


def _resolve(stub, issues_by_key):
    """Prefer the full search record over a link/subtask stub."""
    return issues_by_key.get(stub["key"], stub)


def build_edges(issues_by_key, epic_children):
    """Yield (edge_name, parent, children) for the three hierarchy levels."""
    edges = []
    for issue in issues_by_key.values():
        if issue["type"].lower() == "initiative":
            children = [
                _resolve(link["other"], issues_by_key)
                for link in issue["links"]
                if link["name"].lower() in PARENT_LINK_TYPES
                and link["other"]["type"].lower() == "epic"
            ]
            if children:
                edges.append(("initiative_epic", issue, children))
        if issue["type"].lower() == "epic":
            children = [
                _resolve(c, issues_by_key) for c in epic_children.get(issue["key"], [])
            ]
            if children:
                edges.append(("epic_story", issue, children))
        if issue["subtasks"]:
            edges.append(
                (
                    "story_subtask",
                    issue,
                    [_resolve(s, issues_by_key) for s in issue["subtasks"]],
                )
            )
    return edges


# --------------------------------------------------------------------- rules


def _finding_id(rule, parent, children):
    digest = hashlib.sha1(
        (rule + parent["key"] + ",".join(sorted(c["key"] for c in children))).encode()
    ).hexdigest()[:4]
    return f"{rule}-{parent['key']}-{digest}"


def _brief(issue):
    return {
        "key": issue["key"],
        "type": issue["type"],
        "status": issue["status"],
        "statusCategory": issue["category"],
    }


def _make_finding(rule, edge, parent, offenders, evidence, proposal):
    return {
        "id": _finding_id(rule, parent, offenders),
        "rule": rule,
        "edge": edge,
        "parent": _brief(parent),
        "children": [_brief(c) for c in offenders],
        "evidence": evidence,
        "proposal": proposal,
        "suppressed_by": None,
    }


def _r1_proposal(parent):
    if parent["type"].lower() == "epic":
        return {
            "action": "transition",
            "key": parent["key"],
            "to": EPIC_ACTIVE_STATUS,
            "one_way": False,
            "resolution": None,
            "executable": True,
            "note": None,
        }
    return {
        "action": "transition",
        "key": parent["key"],
        "to": None,
        "one_way": False,
        "resolution": None,
        "executable": True,
        "note": "target status must be enumerated live (workflow not documented "
        "for this issue type) - pick the forward status at approval time",
    }


def apply_rules(edges):
    """Run R1-R3 over the edges; return (findings, r4_counts)."""
    findings = []
    r4 = {edge: 0 for edge, _, _ in edges} or {}
    for edge, parent, children in edges:
        r4.setdefault(edge, 0)
        active = [c for c in children if c["category"] == "indeterminate"]
        open_ = [c for c in children if c["category"] != "done"]
        r4[edge] += sum(1 for c in children if c["category"] != parent["category"])

        if parent["category"] == "new" and active:
            findings.append(
                _make_finding(
                    "R1",
                    edge,
                    parent,
                    active,
                    f"{len(active)} of {len(children)} children active while "
                    f"{parent['key']} is '{parent['status']}'",
                    _r1_proposal(parent),
                )
            )
        if (
            edge in CONTAINER_EDGES
            and parent["category"] != "done"
            and children
            and all(c["category"] == "done" for c in children)
        ):
            findings.append(
                _make_finding(
                    "R2",
                    edge,
                    parent,
                    children,
                    f"all {len(children)} children done while {parent['key']} is "
                    f"'{parent['status']}'",
                    {
                        "action": "transition",
                        "key": parent["key"],
                        "to": CLOSED_STATUS,
                        "one_way": True,
                        "resolution": "Done",
                        "executable": True,
                        "note": "ONE-WAY: no REST path out of Closed; resolution "
                        "must be right at close time",
                    },
                )
            )
        if parent["category"] == "done" and open_:
            findings.append(
                _make_finding(
                    "R3",
                    edge,
                    parent,
                    open_,
                    f"{parent['key']} is '{parent['status']}' but {len(open_)} "
                    f"children are still open",
                    {
                        "action": "flag",
                        "key": parent["key"],
                        "to": None,
                        "one_way": False,
                        "resolution": None,
                        "executable": False,
                        "note": "cannot reopen a Closed parent via REST; either the "
                        "children should be closed (one-way, per-child "
                        "decision) or this is a real leak",
                    },
                )
            )
    return findings, r4


def apply_r4(issues):
    """Flag issues sitting in an active status with nobody assigned.

    The engine only detects; the CANDIDATE assignee is judgment (roster,
    relatedness, WIP) and belongs to the project-manager agent.
    """
    findings = []
    for issue in issues:
        if issue["assignee"]:
            continue
        if issue["type"].lower() in R4_EXEMPT_TYPES:
            continue
        if issue["status"].lower() not in R4_ACTIVE_STATUSES:
            continue
        findings.append(
            _make_finding(
                "R4",
                "issue",
                issue,
                [],
                f"{issue['key']} is '{issue['status']}' with no assignee",
                {
                    "action": "assign",
                    "key": issue["key"],
                    "to": None,
                    "assignee": None,
                    "one_way": False,
                    "resolution": None,
                    "executable": True,
                    "note": "candidate must come from the project-manager agent "
                    "(roster component -> relatedness -> WIP), decided at "
                    "approval time",
                },
            )
        )
    return findings


def apply_r5(issues):
    """Flag In-progress issues whose Block dependency is not resolved.

    Signal-only (like R3): there is nothing to execute - no REST path parks an
    issue back, and the point is PO awareness that work runs on top of an open
    blocker. In progress ONLY: a Ready for Dev queue behind a blocker is
    deliberate Kanban staging.
    """
    findings = []
    for issue in issues:
        if issue["status"].lower() != "in progress":
            continue
        blockers = [
            lnk["other"]
            for lnk in issue["links"]
            if lnk["name"].lower() == "block"
            and lnk["direction"] == "inward"
            and lnk["other"]["category"] != "done"
        ]
        if not blockers:
            continue
        names = ", ".join(f"{b['key']} ('{b['status']}')" for b in blockers)
        findings.append(
            _make_finding(
                "R5",
                "issue",
                issue,
                blockers,
                f"{issue['key']} is '{issue['status']}' but blocked by {names}",
                {
                    "action": "flag",
                    "key": issue["key"],
                    "to": None,
                    "one_way": False,
                    "resolution": None,
                    "executable": False,
                    "note": "work is running on top of an unresolved blocker - "
                    "PO decision needed (pause, or record as deliberate "
                    "partial-dependency work via an exception)",
                },
            )
        )
    return findings


def apply_r6(issues, today, stale_days=DEFAULT_STALE_DAYS):
    """Flag aging WIP: In progress / Ready for testing with no recent updates.

    Signal-only (like R3/R5). The `updated` timestamp is a coarse proxy - MR
    activity does not touch it - so the project-manager agent downgrades false
    positives via devinfo/comments; the engine only measures silence. Issues
    without an `updated` value are skipped: absence of evidence is not a
    finding.
    """
    findings = []
    today_date = date.fromisoformat(today)
    for issue in issues:
        if issue["status"].lower() not in R6_STALE_STATUSES:
            continue
        if not issue["updated"]:
            continue
        silent_days = (today_date - date.fromisoformat(issue["updated"])).days
        if silent_days < stale_days:
            continue
        findings.append(
            _make_finding(
                "R6",
                "issue",
                issue,
                [],
                f"{issue['key']} is '{issue['status']}' with no updates for "
                f"{silent_days} days (since {issue['updated']})",
                {
                    "action": "flag",
                    "key": issue["key"],
                    "to": None,
                    "one_way": False,
                    "resolution": None,
                    "executable": False,
                    "note": "check devinfo/comments before judging: an active "
                    "MR does not touch the Jira updated field - quiet may "
                    "still be progressing",
                },
            )
        )
    return findings


def _project_of(key):
    return (key or "").split("-", 1)[0]


def apply_r7(issues):
    """Flag open issues whose Block dependency lives in another project.

    Signal-only: the cross-team conversation is human work - the agent only
    judges WAIT vs ESCALATE and names who to ping. Own-project blockers are
    R5 territory; "we block them" (outward) is their dependency, not ours.
    """
    findings = []
    for issue in issues:
        if issue["category"] == "done":
            continue
        externals = [
            lnk["other"]
            for lnk in issue["links"]
            if lnk["name"].lower() == "block"
            and lnk["direction"] == "inward"
            and lnk["other"]["category"] != "done"
            and _project_of(lnk["other"]["key"]) != _project_of(issue["key"])
        ]
        if not externals:
            continue
        names = ", ".join(f"external {b['key']} ('{b['status']}')" for b in externals)
        findings.append(
            _make_finding(
                "R7",
                "issue",
                issue,
                externals,
                f"{issue['key']} depends on {names}",
                {
                    "action": "flag",
                    "key": issue["key"],
                    "to": None,
                    "one_way": False,
                    "resolution": None,
                    "executable": False,
                    "note": "cross-team dependency - agent judges WAIT vs "
                    "ESCALATE from the external ticket's movement; pinging "
                    "the other team stays human",
                },
            )
        )
    return findings


def release_date(raw):
    """Release date of a deploy ticket: fixVersion releaseDate, else duedate."""
    fields = raw.get("fields", {})
    for version in fields.get("fixVersions") or []:
        if version.get("releaseDate"):
            return version["releaseDate"]
    return fields.get("duedate") or None


def release_shipped(raw):
    """Did the release actually ship? EVERY fixVersion must be released or
    archived - one lingering released version next to a pending one (member
    slipped to a hotfix, old version left attached) must NOT pull the entry
    off the radar; a false-live entry just keeps a warning, a false-stale
    one loses the release.

    None when the ticket has no fixVersions to consult (duedate-only deploy
    tickets) - the caller falls back to ticket closure as the signal.
    """
    versions = raw.get("fields", {}).get("fixVersions") or []
    if not versions:
        return None
    return all(v.get("released") or v.get("archived") for v in versions)


def build_releases(entries, raw_by_key, issues_by_key):
    """Registry entries + fetched deploy tickets -> release records.

    Returns (releases, stale_entries, warnings). A release's composition is
    whatever PROJ-* issues the deploy ticket links to (the devs maintain those
    links); members resolve to the full scan record when in scope. An entry is
    stale - the agent proposes removing it - only once the release actually
    shipped (fixVersion released/archived); a deploy ticket closed with the
    fixVersion still unreleased means the build is cut but the store release
    is pending, so the entry stays live with a
    warning. Ticket closure alone decides only when there is no fixVersion.
    Missing raw payloads (fetch failures) are skipped: meta.errors territory.
    """
    releases, stale, warnings = [], [], []
    for entry in entries:
        key = entry.get("release_ticket")
        raw = raw_by_key.get(key)
        if raw is None:
            continue
        ticket = simplify(raw)
        shipped = release_shipped(raw)
        if shipped or (shipped is None and ticket["category"] == "done"):
            stale.append(entry)
            continue
        if ticket["category"] == "done":
            warnings.append(
                f"release {key} deploy ticket is closed but the fixVersion is "
                f"not released - release pending, entry kept on the radar"
            )
        rel_date = release_date(raw)
        if not rel_date:
            warnings.append(
                f"release {key} has no release date (fixVersion releaseDate "
                f"or duedate) - R8 readiness window not evaluated"
            )
        releases.append(
            {
                "entry": entry,
                "ticket": ticket,
                "date": rel_date,
                "platform": entry.get("platform"),
                "members": [
                    _resolve(lnk["other"], issues_by_key)
                    for lnk in ticket["links"]
                    if _project_of(lnk["other"]["key"]) == PROJECT_KEY
                ],
            }
        )
    return releases, stale, warnings


def _release_ready(member):
    return member["category"] == "done" or member["status"].lower() in R8_READY_STATUSES


def apply_r8(releases, today, window=DEFAULT_RELEASE_WINDOW):
    """Flag release members not release-ready near (or past) the release date.

    Signal-only: descope-or-hold is a PO/dev conversation. A release past its
    date but still open keeps firing - overdue is more urgent, not less.
    """
    findings = []
    today_date = date.fromisoformat(today)
    for release in releases:
        if not release["date"]:
            continue
        days_left = (date.fromisoformat(release["date"]) - today_date).days
        if days_left > window:
            continue
        unready = [m for m in release["members"] if not _release_ready(m)]
        if not unready:
            continue
        when = (
            f"{days_left} day(s) left"
            if days_left >= 0
            else f"{-days_left} day(s) overdue"
        )
        findings.append(
            _make_finding(
                "R8",
                "release",
                release["ticket"],
                unready,
                f"{len(unready)} of {len(release['members'])} tickets in "
                f"release {release['ticket']['key']} ({release['platform']}, "
                f"{release['date']}, {when}) not release-ready",
                {
                    "action": "flag",
                    "key": release["ticket"]["key"],
                    "to": None,
                    "one_way": False,
                    "resolution": None,
                    "executable": False,
                    "note": "not ready for the planned release - descope, "
                    "push the date, or rush is a PO/dev decision, not "
                    "an automated one",
                },
            )
        )
    return findings


def annotate_release_context(findings, releases):
    """Attach release info to R2 findings whose epic waits for a release.

    An epic with all children done sits in a deployment status until the prod
    release ships - when the epic or its children are
    in an active release's composition, the finding carries which release and
    when, so the agent can SKIP-with-expiry instead of a manual exception.
    """
    for finding in findings:
        if finding["rule"] != "R2":
            continue
        involved = {finding["parent"]["key"]}
        involved.update(c["key"] for c in finding["children"])
        for release in releases:
            if involved & {m["key"] for m in release["members"]}:
                finding["release_context"] = {
                    "release_ticket": release["ticket"]["key"],
                    "platform": release["platform"],
                    "date": release["date"],
                }
                break


# ---------------------------------------------------------------- exceptions


def load_releases(path):
    p = Path(path)
    if not p.is_file():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("releases", [])


def load_exceptions(path):
    p = Path(path)
    if not p.is_file():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("exceptions", [])


def _entry_matches(entry, finding, today):
    match = entry.get("match", {})
    expires = entry.get("expires")
    if expires and expires < today:
        return False
    if match.get("parent") != finding["parent"]["key"]:
        return False
    if match.get("rule") and match["rule"] != finding["rule"]:
        return False
    if match.get("child") and match["child"] not in (
        c["key"] for c in finding["children"]
    ):
        return False
    return True


def apply_exceptions(findings, exceptions, today):
    """Split findings into (kept, suppressed); warn on expired entries."""
    kept, suppressed, warnings = [], [], []
    for entry in exceptions:
        expires = entry.get("expires")
        if expires and expires < today:
            warnings.append(
                f"stale exception for {entry.get('match', {}).get('parent')} "
                f"expired {expires} - findings resurface"
            )
    for finding in findings:
        hit = next((e for e in exceptions if _entry_matches(e, finding, today)), None)
        if hit:
            finding = dict(
                finding,
                suppressed_by=hit.get("reason", "exception"),
                suppressed_entry=hit,
            )
            suppressed.append(finding)
        else:
            kept.append(finding)
    return kept, suppressed, warnings


def find_unused_exceptions(findings, exceptions, today):
    """Entries (not yet expired) that matched no finding this scan.

    Dead weight for the agent's exceptions review: the condition they guarded
    resolved itself, so the entry only obscures the file. Expired entries are
    excluded - they already surface via the stale-exception warning.
    """
    return [
        entry
        for entry in exceptions
        if not (entry.get("expires") and entry["expires"] < today)
        and not any(_entry_matches(entry, f, today) for f in findings)
    ]


# --------------------------------------------------------------------- fetch


def _run_plugin(jira_api, cmd_args, timeout):
    """One jira_api.py subprocess -> parsed JSON. Raises AuthFailure on 401/403."""
    proc = subprocess.run(
        [sys.executable, str(jira_api), *cmd_args, "--format=json"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        if AUTH_RE.search(proc.stderr or ""):
            raise AuthFailure(proc.stderr.strip()[:200])
        raise RuntimeError(
            f"{' '.join(cmd_args)}: exit {proc.returncode}: {proc.stderr.strip()[:200]}"
        )
    return json.loads(proc.stdout)


def search_all(jira_api, jql, timeout, page_size=100):
    """Keyset-paginated search (jira_api.py has no startAt passthrough)."""
    issues, last_key = [], None
    while True:
        page_jql = (
            f"({jql}) AND key > {last_key} ORDER BY key ASC"
            if last_key
            else f"({jql}) ORDER BY key ASC"
        )
        payload = _run_plugin(
            jira_api, ["search", page_jql, f"--max={page_size}"], timeout
        )
        batch = payload.get("issues", [])
        issues.extend(batch)
        if len(batch) < page_size:
            return issues
        last_key = batch[-1]["key"]


def fetch_epic_children(jira_api, epic_keys, timeout, workers):
    """Parallel `epic <key>` calls. Returns ({epic: [raw issues]}, errors)."""
    children, errors = {}, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_run_plugin, jira_api, ["epic", key], timeout): key
            for key in epic_keys
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                children[key] = future.result()
            except AuthFailure:
                raise
            except Exception as exc:  # noqa: BLE001 - collected, reported, exit 2
                errors.append(f"epic {key}: {exc}")
                children[key] = []
    return children, errors


def fetch_release_tickets(jira_api, keys, timeout):
    """Sequential `get <key>` per deploy ticket (registry is 1-2 entries).

    Returns ({key: raw issue or None}, errors); auth failures propagate.
    """
    raw_by_key, errors = {}, []
    for key in keys:
        try:
            raw_by_key[key] = _run_plugin(jira_api, ["get", key], timeout)
        except AuthFailure:
            raise
        except Exception as exc:  # noqa: BLE001 - collected, reported, exit 2
            errors.append(f"get {key}: {exc}")
            raw_by_key[key] = None
    return raw_by_key, errors


# ---------------------------------------------------------------------- main


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jql", default=f"project = {PROJECT_KEY}")
    parser.add_argument("--out", help="findings JSON path (default: stdout)")
    parser.add_argument("--exceptions", default=str(DEFAULT_EXCEPTIONS))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--jira-api", help="path to jira_api.py (default: sibling)")
    parser.add_argument(
        "--today",
        default=date.today().isoformat(),
        help="override for exception-expiry and R6 staleness checks (tests)",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=DEFAULT_STALE_DAYS,
        help="R6: days without updates before active WIP counts as stale",
    )
    parser.add_argument("--releases", default=str(DEFAULT_RELEASES))
    parser.add_argument(
        "--release-window",
        type=int,
        default=DEFAULT_RELEASE_WINDOW,
        help="R8: days before the release date when readiness is checked",
    )
    args = parser.parse_args(argv)

    jira_api = resolve_jira_api(args.jira_api)
    release_entries = load_releases(args.releases)
    try:
        raw_issues = search_all(jira_api, args.jql, args.timeout)
        issues_by_key = {i["key"]: simplify(i) for i in raw_issues}
        epic_keys = [k for k, v in issues_by_key.items() if v["type"].lower() == "epic"]
        raw_children, errors = fetch_epic_children(
            jira_api, epic_keys, args.timeout, args.workers
        )
        raw_releases, release_errors = fetch_release_tickets(
            jira_api,
            [e.get("release_ticket") for e in release_entries],
            args.timeout,
        )
        errors += release_errors
    except AuthFailure as exc:
        print(
            f"AUTH: Jira auth failed - check network/VPN and JIRA_API_TOKEN ({exc})",
            file=sys.stderr,
        )
        return 1

    epic_children = {
        epic: [simplify(c) for c in children] for epic, children in raw_children.items()
    }
    edges = build_edges(issues_by_key, epic_children)
    findings, mismatch_counts = apply_rules(edges)
    findings += apply_r4(issues_by_key.values())
    findings += apply_r5(issues_by_key.values())
    findings += apply_r6(issues_by_key.values(), args.today, args.stale_days)
    findings += apply_r7(issues_by_key.values())
    releases, stale_releases, release_warnings = build_releases(
        release_entries, raw_releases, issues_by_key
    )
    findings += apply_r8(releases, args.today, args.release_window)
    annotate_release_context(findings, releases)
    exceptions = load_exceptions(args.exceptions)
    kept, suppressed, warnings = apply_exceptions(findings, exceptions, args.today)
    warnings = release_warnings + warnings
    unused = find_unused_exceptions(findings, exceptions, args.today)
    for warning in warnings:
        print(f"WARN: {warning}", file=sys.stderr)

    result = {
        "schema": SCHEMA,
        "scope": {
            "jql": args.jql,
            "issues_scanned": len(issues_by_key),
            "edges": {
                name: sum(1 for e, _, _ in edges if e == name)
                for name in ("initiative_epic", "epic_story", "story_subtask")
            },
        },
        "findings": kept,
        "suppressed": suppressed,
        "unused_exceptions": unused,
        "stale_releases": stale_releases,
        "category_mismatch_counts": mismatch_counts,
        "meta": {"errors": errors, "warnings": warnings},
    }
    payload = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    print(
        f"{len(kept)} finding(s), {len(suppressed)} suppressed, "
        f"{len(errors)} fetch error(s) over {len(issues_by_key)} issues",
        file=sys.stderr,
    )
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
