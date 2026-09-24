#!/usr/bin/env python3
"""Apply a declarative Jira changeset - one engine instead of a script per package.

Why this exists: every batch of Jira changes tends to become a hand-written
one-off script that re-implements raw HTTP, skips the dry run, and re-types
(or forgets) the rules that keep a payload from 400ing - ASCII only, required
components, a required custom field on Bugs, enumerate transitions instead of
remembering an id, a resolution on every close. Here those rules are checks
with tests, and a package is a FILE to review, not a program to review.

A changeset is DATA: a JSON file next to its draft doc. Ops run in order and
can refer to keys created earlier in the same run by "$id".

    {
      "name": "proj-656-reserved-balance-research",
      "why": "one line - what this package is for",
      "ops": [
        {"op": "create", "id": "research", "project": "PROJ", "issuetype": "10001",
         "summary": "[Backend] Research: ...",
         "description_from": {"doc": "docs/initiatives/x.md", "block": 2},
         "priority": "High", "components": ["Backend"], "labels": ["research"],
         "assignee": "dev.one@example.com",
         "fields": {"customfield_10992": {"value": "2027 Q1"}}},
        {"op": "link", "type": "Relate", "inward": "$research", "outward": "PROJ-656"},
        {"op": "comment", "key": "PROJ-656", "body": "ASCII text"},
        {"op": "update", "key": "PROJ-641", "fields": {"priority": {"name": "High"}}},
        {"op": "assign", "key": "PROJ-641", "assignee": "web.lead@example.com"},
        {"op": "transition", "key": "EXT-16418", "to": "Product roadmap"}
      ]
    }

What it refuses, and why (the team-specific parts come from jira-config.json):
  - any non-ASCII in any payload string (a WAF in front of Jira may reject it);
  - a create in the configured project with no components, when
    create_rules.require_components is on (some projects 400 without them);
  - a create of a configured issue type without the configured risk-class
    custom field (create_rules.risk_class);
  - a create on a component listed under components_requiring_assignee with no
    assignee - the engine refuses rather than picking someone, because choosing
    an assignee is a decision, not a default;
  - a link type the instance does not offer (on Jira Server the name is
    "Relate", and "Relates" 404s) - checked against the live list first;
  - a transition named by id, or one whose target is reachable by two
    transitions with different resolution screens (resolved by target NAME via
    jira_transition.resolve_transition, the one resolver);
  - a close with no resolution, or a resolution the chosen transition's own
    screen does not offer (read live from the transition's fields);
  - a one-way move (statuses.one_way) without "confirm_one_way": true on that
    op - there is no REST path back.

Usage:
    python scripts/jira_apply.py CHANGESET.json --dry-run
    python scripts/jira_apply.py CHANGESET.json --apply

Exit codes: 0 applied and verified (or a clean dry run); 1 fatal (AUTH: on
stderr means network/token); 2 refused in preflight - nothing was written; 3 a
write landed but its verification failed - check the issue by hand before
re-running, never read 3 as "nothing happened".
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jira_batch_fetch import resolve_jira_api  # noqa: E402
from jira_config import CONFIG  # noqa: E402
from jira_transition import (  # noqa: E402
    AuthFailure,
    Refused,
    VerifyMismatch,
    ensure_ascii,
    load_plugin,
    make_requester,
    refuse_if_propose_only,
    resolve_transition,
)

OPS = ("create", "update", "link", "comment", "assign", "transition")
PROJECT_KEY = CONFIG["project_key"]
# create_rules from jira-config.json: require_components, risk_class
# ({field, issuetypes} or null), components_requiring_assignee. Tests swap
# this dict to exercise each rule.
RULES = dict(CONFIG["create_rules"])
ONE_WAY_TARGETS = tuple(s.lower() for s in CONFIG["statuses"]["one_way"])
CLOSED = CONFIG["statuses"]["closed"].lower()
REF_RE = re.compile(r"^\$([A-Za-z0-9_-]+)$")


class Changeset:
    """A parsed changeset plus the keys its ops created, for "$id" references."""

    def __init__(self, data, path):
        self.path = Path(path)
        self.name = data.get("name") or self.path.stem
        self.why = data.get("why") or ""
        self.ops = data.get("ops") or []
        self.created = {}

    def resolve(self, value):
        """ "$id" -> the key that op created. Anything else passes through."""
        if not isinstance(value, str):
            return value
        match = REF_RE.match(value)
        if not match:
            return value
        ref = match.group(1)
        if ref not in self.created:
            raise Refused(
                f"reference ${ref} is not a key created earlier in this changeset "
                f"(known: {sorted(self.created) or 'none'})"
            )
        return self.created[ref]


def load_changeset(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Refused(f"changeset not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise Refused(f"changeset is not valid JSON: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("ops"), list):
        raise Refused("changeset must be an object with an 'ops' array")
    if not data["ops"]:
        raise Refused("changeset has no ops")
    for index, op in enumerate(data["ops"], 1):
        if not isinstance(op, dict) or op.get("op") not in OPS:
            raise Refused(f"op {index}: 'op' must be one of {', '.join(OPS)}")
    return Changeset(data, path)


def fenced_block(doc_path, index):
    """Block `index` (1-based) of a draft doc - the doc stays the source text."""
    text = Path(doc_path).read_text(encoding="utf-8")
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)\n```", text, flags=re.S)
    if len(blocks) < index:
        raise Refused(
            f"{doc_path}: asked for fenced block {index}, found {len(blocks)}"
        )
    return blocks[index - 1].strip()


def ascii_walk(value, label):
    """Every string that will be sent, checked where it is - not at the top."""
    if isinstance(value, str):
        ensure_ascii(value, label)
    elif isinstance(value, dict):
        for key, item in value.items():
            ascii_walk(item, f"{label}.{key}")
    elif isinstance(value, (list, tuple)):
        for position, item in enumerate(value):
            ascii_walk(item, f"{label}[{position}]")


def build_create(op, changeset):
    """The create payload, with the required-field rules applied."""
    fields = dict(op.get("fields") or {})
    project = op.get("project", PROJECT_KEY)
    summary = op.get("summary")
    if not summary:
        raise Refused("create: 'summary' is required")
    description = op.get("description")
    if op.get("description_from"):
        source = op["description_from"]
        description = fenced_block(source["doc"], source.get("block", 1))
    components = op.get("components") or []
    if project == PROJECT_KEY and RULES.get("require_components") and not components:
        raise Refused(
            f"create '{summary[:50]}': {PROJECT_KEY} issues require components "
            "(the API 400s without them)"
        )
    risk = RULES.get("risk_class") or {}
    risk_types = [str(t) for t in risk.get("issuetypes") or []]
    if risk and str(op.get("issuetype")) in risk_types and risk["field"] not in fields:
        raise Refused(
            f"create '{summary[:50]}': issue type {op.get('issuetype')} requires "
            f"the risk-class field {risk['field']} (create_rules.risk_class)"
        )
    gated = [
        c for c in components if c in (RULES.get("components_requiring_assignee") or [])
    ]
    if gated and not op.get("assignee"):
        raise Refused(
            f"create '{summary[:50]}': {gated[0]} work is created assigned - "
            'set "assignee" deliberately (the engine never picks a person)'
        )
    fields.update(
        {
            "project": {"key": project},
            "issuetype": {"id": str(op["issuetype"])},
            "summary": summary,
        }
    )
    if description:
        fields["description"] = description
    if op.get("priority"):
        fields["priority"] = {"name": op["priority"]}
    if components:
        fields["components"] = [{"name": name} for name in components]
    if op.get("labels"):
        fields["labels"] = list(op["labels"])
    if op.get("assignee"):
        fields["assignee"] = {"name": op["assignee"]}
    if op.get("parent"):
        fields["parent"] = {"key": changeset.resolve(op["parent"])}
    ascii_walk(fields, "create")
    return fields


def link_types(request, cache={}):  # noqa: B006 - one lookup per process
    if "names" not in cache:
        data = request("issueLinkType") or {}
        cache["names"] = sorted(t["name"] for t in data.get("issueLinkTypes", []))
    return cache["names"]


def plan_link(op, changeset, request):
    name = op.get("type")
    known = link_types(request)
    if known and name not in known:
        raise Refused(
            f"link type '{name}' is not offered by this instance "
            f"(it has: {', '.join(known)}) - on Jira Server the name is "
            "'Relate', and 'Relates' 404s"
        )
    inward = changeset.resolve(op.get("inward"))
    outward = changeset.resolve(op.get("outward"))
    if not inward or not outward:
        raise Refused("link: both 'inward' and 'outward' are required")
    payload = {
        "type": {"name": name},
        "inwardIssue": {"key": inward},
        "outwardIssue": {"key": outward},
    }
    ascii_walk(payload, "link")
    # Reads as "<inward> <type>s <outward>". On Jira Server the INWARD issue of
    # a Block link is the blocker - the opposite of what the Atlassian Cloud
    # docs suggest. Verify once on your instance, then trust the test.
    return payload, f"{inward} {name.lower()}s {outward}"


def plan_transition(op, changeset, request):
    """Resolve the transition live and check the resolution against its screen."""
    key = changeset.resolve(op.get("key"))
    target = op.get("to")
    if not key or not target:
        raise Refused("transition: 'key' and 'to' are required")
    issue = request(f"issue/{key}?fields=status,issuetype")["fields"]
    current = issue["status"]["name"]
    if current.lower() == target.lower():
        raise Refused(f"{key} is already in '{current}' - drop this op")
    offered = request(f"issue/{key}/transitions?expand=transitions.fields")[
        "transitions"
    ]
    transition = resolve_transition(
        offered, target, op.get("via"), key, current, issue["issuetype"]["name"]
    )
    resolution = op.get("resolution")
    if target.lower() == CLOSED and not resolution:
        raise Refused(
            f"{key}: closing requires a resolution - it cannot be set afterwards "
            "(a resolution PUT on a closed issue 400s)"
        )
    if resolution:
        allowed = [
            value["name"]
            for value in (transition.get("fields", {}).get("resolution", {}) or {}).get(
                "allowedValues", []
            )
        ]
        if allowed and resolution not in allowed:
            raise Refused(
                f"{key}: transition '{transition['name']}' does not offer "
                f"resolution '{resolution}' (its screen has: {', '.join(allowed)})"
            )
    if target.lower() in ONE_WAY_TARGETS and not op.get("confirm_one_way"):
        raise Refused(
            f"{key} -> '{target}' is one-way (no REST path back) - add "
            '"confirm_one_way": true to this op if that is deliberate'
        )
    payload = {"transition": {"id": transition["id"]}}
    if resolution:
        payload["fields"] = {"resolution": {"name": resolution}}
    if op.get("comment"):
        ensure_ascii(op["comment"], "transition.comment")
        payload["update"] = {"comment": [{"add": {"body": op["comment"]}}]}
    return payload, f"{key} {current} -> {target} via '{transition['name']}'"


def preview(op, changeset, request):
    """One line per op for the dry run, plus the payload that would be sent."""
    kind = op["op"]
    if kind == "create":
        fields = build_create(op, changeset)
        if op.get("id"):
            # Placeholder so later ops can resolve "$id" during a dry run.
            changeset.created[op["id"]] = f"<new:{op['id']}>"
        return (
            f"create {fields['project']['key']} type {fields['issuetype']['id']}: "
            f"{fields['summary'][:70]}"
            + (
                f" [{len(fields.get('description', ''))} chars of description]"
                if fields.get("description")
                else " [no description]"
            ),
            {"endpoint": "issue", "payload": {"fields": fields}},
        )
    if kind == "link":
        payload, described = plan_link(op, changeset, request)
        return f"link {described}", {"endpoint": "issueLink", "payload": payload}
    if kind == "transition":
        payload, described = plan_transition(op, changeset, request)
        key = changeset.resolve(op["key"])
        return (
            f"transition {described}",
            {"endpoint": f"issue/{key}/transitions", "payload": payload},
        )
    if kind == "comment":
        key = changeset.resolve(op.get("key"))
        body = op.get("body") or ""
        if not key or not body.strip():
            raise Refused("comment: 'key' and a non-empty 'body' are required")
        ensure_ascii(body, "comment.body")
        return (
            f"comment on {key} ({len(body)} chars)",
            {"endpoint": f"issue/{key}/comment", "payload": {"body": body}},
        )
    if kind == "assign":
        key = changeset.resolve(op.get("key"))
        assignee = op.get("assignee")
        if not key or not assignee:
            raise Refused("assign: 'key' and 'assignee' are required")
        ensure_ascii(assignee, "assign.assignee")
        return (
            f"assign {key} to {assignee}",
            {"endpoint": f"issue/{key}/assignee", "payload": {"name": assignee}},
        )
    key = changeset.resolve(op.get("key"))
    fields = op.get("fields") or {}
    if not key or not fields:
        raise Refused("update: 'key' and a non-empty 'fields' object are required")
    ascii_walk(fields, "update.fields")
    return (
        f"update {key}: {', '.join(sorted(fields))}",
        {"endpoint": f"issue/{key}", "payload": {"fields": fields}},
    )


def verify(op, key, request):
    """Read the issue back and say what landed - the write's own reply is not proof."""
    fields = request(
        f"issue/{key}?fields=summary,status,priority,components,labels,assignee,"
        "issuelinks,resolution"
    )["fields"]
    links = sorted(
        f"{link['type']['name']}:{(link.get('outwardIssue') or link.get('inwardIssue'))['key']}"
        for link in fields.get("issuelinks") or []
    )
    return {
        "key": key,
        "status": (fields.get("status") or {}).get("name"),
        "resolution": (fields.get("resolution") or {}).get("name"),
        "assignee": (fields.get("assignee") or {}).get("name"),
        "components": [c["name"] for c in fields.get("components") or []],
        "labels": fields.get("labels") or [],
        "links": links,
    }


def execute(op, plan, changeset, request):
    """Send one op and verify it. Returns the record for the run log."""
    kind = op["op"]
    method = "PUT" if kind in ("update", "assign") else "POST"
    reply = request(plan["endpoint"], method=method, data=plan["payload"])
    if kind == "create":
        key = reply["key"]
        if op.get("id"):
            changeset.created[op["id"]] = key
    elif kind == "link":
        key = plan["payload"]["outwardIssue"]["key"]
    else:
        key = changeset.resolve(op.get("key"))
    record = {"op": kind, "key": key}
    try:
        record["verified"] = verify(op, key, request)
    except (AuthFailure, KeyError, TypeError, RuntimeError) as exc:
        raise VerifyMismatch(
            f"{kind} on {key} was accepted but could not be verified ({exc}) - "
            "check the issue by hand before re-running"
        ) from None
    if kind == "transition":
        expected = op["to"].lower()
        if (record["verified"]["status"] or "").lower() != expected:
            raise VerifyMismatch(
                f"{key}: transition POST accepted but the issue reads "
                f"'{record['verified']['status']}', expected '{op['to']}'"
            )
    return record


def run(changeset, request, apply_changes):
    refuse_if_propose_only(not apply_changes)
    results = []
    for index, op in enumerate(changeset.ops, 1):
        described, plan = preview(op, changeset, request)
        line = f"{index}. {described}"
        if not apply_changes:
            results.append(
                {"op": op["op"], "plan": described, "payload": plan["payload"]}
            )
            print(line)
            continue
        record = execute(op, plan, changeset, request)
        results.append(record)
        print(f"{line} -> {record['key']} {record['verified']['status'] or ''}")
    return results


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("changeset", help="path to the changeset JSON")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="GET only, write nothing")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--jira-api", help="path to jira_api.py (default: sibling)")
    parser.add_argument(
        "--out", help="where to write the run record (default: beside the changeset)"
    )
    args = parser.parse_args(argv)

    try:
        changeset = load_changeset(args.changeset)
        request = make_requester(load_plugin(resolve_jira_api(args.jira_api)))
        print(f"# {changeset.name}" + (f" - {changeset.why}" if changeset.why else ""))
        print(
            f"# {len(changeset.ops)} op(s), mode: {'APPLY' if args.apply else 'dry run'}"
        )
        results = run(changeset, request, args.apply)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    except AuthFailure as exc:
        print(f"AUTH: {exc}", file=sys.stderr)
        return 1
    except VerifyMismatch as exc:
        print(f"UNCONFIRMED: {exc}", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.apply:
        out = (
            Path(args.out) if args.out else changeset.path.with_suffix(".applied.json")
        )
        out.write_text(
            json.dumps({"changeset": changeset.name, "results": results}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"# record: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
