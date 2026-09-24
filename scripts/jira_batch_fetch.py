#!/usr/bin/env python3
"""Batch-fetch Jira issue data in parallel via scripts/jira_api.py.

Reusable read primitive for the judgment agents (board-sync, dup-check,
prioritization). Fans out (key x command) pairs over ThreadPoolExecutor
subprocesses of jira_api.py and merges results into one JSON document.
jira_api.py stays the ONLY Jira access point (token in scripts/.env).

Usage:
    python scripts/jira_batch_fetch.py --keys PROJ-1,PROJ-2 --commands get,links,comments \
        [--keys-file keys.txt] [--workers 8] [--timeout 30] [--out merged.json] \
        [--trim readiness] [--jira-api PATH]

Exit codes (consumer contract):
    0  clean
    2  partial - some (key x command) reads failed; see meta.errors
    1  fatal   - stderr starting with "AUTH:" means auth/VPN/token (STOP);
                 any other fatal means the run is unusable (consumer may
                 fall back to sequential per-story reads)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jira_config import CONFIG  # noqa: E402

VALID_COMMANDS = ("get", "links", "comments", "remotelinks", "devinfo")
AUTH_RE = re.compile(r"API Error 40[13]|Unauthorized|Forbidden|JIRA_API_TOKEN", re.I)
DEFAULT_JIRA_API = Path(__file__).parent / "jira_api.py"


class AuthFailure(Exception):
    """Any 401/403/token failure - aborts the whole run (rule 04 fail-fast)."""


class Cli(argparse.ArgumentParser):
    def error(self, message):
        # argparse default exits 2, which this contract reserves for "partial"
        self.exit(1, f"{self.prog}: error: {message}\n")


def fatal(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def resolve_jira_api(cli_value):
    """--jira-api > $JIRA_API > the jira_api.py next to this file.

    The override exists for a team that already has its own Jira CLI with the
    same command surface (search/get/epic/... --format=json): point at it and
    every script in this directory uses it unchanged.
    """
    for value in (cli_value, os.environ.get("JIRA_API")):
        if value:
            p = Path(value).expanduser()
            if not p.is_file():
                fatal(f"jira_api.py not found at {p}")
            return p
    if not DEFAULT_JIRA_API.is_file():
        fatal(
            f"jira_api.py not found at {DEFAULT_JIRA_API}; pass --jira-api or set JIRA_API"
        )
    return DEFAULT_JIRA_API


def run_one(jira_api, command, key, timeout):
    """One jira_api.py subprocess. Returns parsed JSON or {"error": ...}; raises AuthFailure."""
    try:
        proc = subprocess.run(
            [sys.executable, str(jira_api), command, key, "--format=json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s"}
    if proc.returncode != 0:
        blob = (proc.stdout or "") + (proc.stderr or "")
        if AUTH_RE.search(blob):
            raise AuthFailure(blob.strip()[:300])
        return {"error": f"exit {proc.returncode}: {blob.strip()[:300]}"}
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {"error": f"non-JSON output: {proc.stdout.strip()[:300]}"}


def is_error(payload):
    # Error slots are exactly {"error": ...}; real payloads are lists or multi-key dicts,
    # so shape-matching cannot collide.
    return isinstance(payload, dict) and set(payload.keys()) == {"error"}


# The readiness trim keeps summary/description/labels plus whatever custom
# fields the team's readiness gates read (acceptance criteria, flagged, baseline
# dates ...) - those ids differ per instance, so they come from jira-config.json
# under readiness_fields: {"label": "customfield_NNNNN"}.
READINESS_PLAIN_FIELDS = ("summary", "description", "labels") + tuple(
    CONFIG.get("readiness_fields", {}).values()
)


def _trim_status(status):
    status = status or {}
    cat = status.get("statusCategory") or {}
    return {
        "name": status.get("name"),
        "statusCategory": {"key": cat.get("key"), "name": cat.get("name")},
    }


def _trim_name(obj):
    return {"name": (obj or {}).get("name")}


def _trim_linked_issue(issue):
    issue = issue or {}
    f = issue.get("fields") or {}
    return {
        "key": issue.get("key"),
        "fields": {
            "summary": f.get("summary"),
            "status": _trim_status(f.get("status")),
            "issuetype": _trim_name(f.get("issuetype")),
            "priority": _trim_name(f.get("priority")),
        },
    }


def _trim_issuelink(link):
    ltype = link.get("type") or {}
    out = {
        "type": {
            "name": ltype.get("name"),
            "inward": ltype.get("inward"),
            "outward": ltype.get("outward"),
        }
    }
    for side in ("inwardIssue", "outwardIssue"):
        if side in link:
            out[side] = _trim_linked_issue(link[side])
    return out


def trim_get(payload):
    f = payload.get("fields") or {}
    fields = {k: f.get(k) for k in READINESS_PLAIN_FIELDS}
    fields["status"] = _trim_status(f.get("status"))
    fields["priority"] = _trim_name(f.get("priority"))
    fields["issuetype"] = _trim_name(f.get("issuetype"))
    assignee = f.get("assignee")
    fields["assignee"] = (
        {"displayName": assignee.get("displayName")} if assignee else None
    )
    fields["components"] = [{"name": c.get("name")} for c in f.get("components") or []]
    fields["issuelinks"] = [_trim_issuelink(ln) for ln in f.get("issuelinks") or []]
    return {"key": payload.get("key"), "fields": fields}


def trim_links(payload):
    return [
        {
            "direction": ln.get("direction"),
            "type": ln.get("type"),
            "description": ln.get("description"),
            "issue": _trim_linked_issue(ln.get("issue")),
        }
        for ln in payload
    ]


def trim_comments(payload):
    return {
        "total": payload.get("total"),
        "comments": [
            {
                "author": (c.get("author") or {}).get("displayName"),
                "created": c.get("created"),
                "body": c.get("body"),
            }
            for c in payload.get("comments") or []
        ],
    }


def trim_remotelinks(payload):
    return [
        {
            "url": (r.get("object") or {}).get("url"),
            "title": (r.get("object") or {}).get("title"),
        }
        for r in payload
    ]


def trim_devinfo(payload):
    # devinfo shape is flat: {pullRequests, branches, commits}. Liveness checks
    # need PR status/recency and branch names - drop commit bodies and URLs.
    return {
        "pullRequests": [
            {
                "name": pr.get("name"),
                "status": pr.get("status"),
                "lastUpdate": pr.get("lastUpdate"),
            }
            for pr in payload.get("pullRequests") or []
        ],
        "branches": [{"name": br.get("name")} for br in payload.get("branches") or []],
        "commits": len(payload.get("commits") or []),
    }


TRIMMERS = {
    "get": trim_get,
    "links": trim_links,
    "comments": trim_comments,
    "remotelinks": trim_remotelinks,
    "devinfo": trim_devinfo,
}


def maybe_trim(command, payload, trim_profile):
    if trim_profile != "readiness" or is_error(payload):
        return payload
    try:
        return TRIMMERS[command](payload)
    except (AttributeError, TypeError):
        return payload  # unexpected shape: raw beats crash


def main(argv=None):
    ap = Cli(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keys", default="", help="comma-separated issue keys")
    ap.add_argument("--keys-file", help="file with one issue key per line")
    ap.add_argument(
        "--commands",
        required=True,
        help=f"comma-separated subset of: {','.join(VALID_COMMANDS)}",
    )
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=30, help="seconds per jira_api call")
    ap.add_argument("--out", help="write merged JSON here (default: stdout)")
    ap.add_argument("--trim", choices=["readiness"])
    ap.add_argument(
        "--jira-api", help="explicit path to a jira_api.py (default: sibling)"
    )
    args = ap.parse_args(argv)

    commands = [c.strip() for c in args.commands.split(",") if c.strip()]
    bad = [c for c in commands if c not in VALID_COMMANDS]
    if bad:
        fatal(
            f"unknown command(s): {', '.join(bad)} (valid: {', '.join(VALID_COMMANDS)})"
        )
    if not commands:
        fatal("no commands given")

    keys = [k.strip() for k in args.keys.split(",") if k.strip()]
    if args.keys_file:
        kf = Path(args.keys_file)
        if not kf.is_file():
            fatal(f"keys file not found: {kf}")
        keys += [
            ln.strip()
            for ln in kf.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    keys = list(dict.fromkeys(keys))  # dedup, keep order
    if not keys:
        fatal("no keys given (use --keys or --keys-file)")

    jira_api = resolve_jira_api(args.jira_api)

    issues = {k: {} for k in keys}
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_one, jira_api, c, k, args.timeout): (k, c)
            for k in keys
            for c in commands
        }
        try:
            for fut in as_completed(futures):
                k, c = futures[fut]
                payload = fut.result()
                if is_error(payload):
                    errors.append({"key": k, "command": c, "error": payload["error"]})
                issues[k][c] = maybe_trim(c, payload, args.trim)
        except AuthFailure as exc:
            pool.shutdown(wait=False, cancel_futures=True)
            print(
                f"AUTH: Jira auth failed - check network/VPN and JIRA_API_TOKEN "
                f"(scripts/.env). Detail: {exc}",
                file=sys.stderr,
                flush=True,
            )
            # Use os._exit to bypass normal interpreter exit: ThreadPoolExecutor
            # registers an atexit hook that joins non-daemon workers, blocking until
            # in-flight subprocesses finish. Fatal auth errors must abort immediately
            # without waiting for timeouts (up to --timeout seconds per call).
            os._exit(1)

    doc = {
        "meta": {
            "keys": keys,
            "commands": commands,
            "workers": args.workers,
            "trim": args.trim,
            "jira_api": str(jira_api),
            "errors": errors,
        },
        "issues": issues,
    }
    text = json.dumps(doc, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(
            f"wrote {args.out} ({len(keys)} keys x {len(commands)} commands, "
            f"{len(errors)} errors)"
        )
    else:
        print(text)
    sys.exit(2 if errors else 0)


if __name__ == "__main__":
    main()
