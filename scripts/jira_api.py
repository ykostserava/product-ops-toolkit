#!/usr/bin/env python3
"""Minimal Jira REST client + CLI - the ONLY Jira access point for scripts/.

Stdlib only. Every other script in this directory talks to Jira either by
running this file as a subprocess (`python scripts/jira_api.py get PROJ-1
--format=json`) or by importing it for its connection globals (BASE_URL,
API_TOKEN, ssl_context) and building its own request on top. Keeping one
access point means one place for the token, one place for TLS settings, one
place for the auth scheme.

Configuration (environment first, then a .env file - see load_env):
    JIRA_BASE_URL     https://your-jira.example.com
    JIRA_API_TOKEN    a personal access token (Server/DC) or API token (Cloud)
    JIRA_AUTH         bearer (default; Server/DC PAT) or basic (Cloud: email +
                      API token, needs JIRA_USERNAME)
    JIRA_USERNAME     only for JIRA_AUTH=basic
    JIRA_SSL_VERIFY   false to accept a self-signed internal CA (default true)

Usage:
    python scripts/jira_api.py search "project = PROJ" [--max=50] [--format=json|brief]
    python scripts/jira_api.py get PROJ-123
    python scripts/jira_api.py epic PROJ-10          # children via Epic Link / parent
    python scripts/jira_api.py subtasks PROJ-123
    python scripts/jira_api.py links PROJ-123
    python scripts/jira_api.py remotelinks PROJ-123
    python scripts/jira_api.py comments PROJ-123
    python scripts/jira_api.py transitions PROJ-123
    python scripts/jira_api.py devinfo PROJ-123      # MRs/branches (Server dev-status)
    python scripts/jira_api.py projects | fields

Read-only by design: the writers (jira_transition.py, jira_assign.py,
jira_apply.py) import make_requester from jira_transition and go through their
own preflight guards. Exit 1 on any HTTP error, with "API Error <code>" on
stderr - the batch scripts match that text to tell auth failures from the rest.
"""

import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SEARCH_FIELDS = (
    "key,summary,status,issuetype,assignee,priority,created,updated,parent,"
    "subtasks,issuelinks,fixVersions,duedate,labels,components"
)


def load_env_file(env_path):
    """Read KEY=VALUE lines into os.environ without overriding what is set."""
    if not env_path.is_file():
        return False
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    return True


def load_env():
    """First .env found wins: next to this file, repo root, current directory."""
    if os.environ.get("JIRA_API_TOKEN"):
        return
    here = Path(__file__).resolve().parent
    for candidate in (here / ".env", here.parent / ".env", Path.cwd() / ".env"):
        if load_env_file(candidate):
            return


load_env()

BASE_URL = os.environ.get("JIRA_BASE_URL", "https://your-jira.example.com").rstrip("/")
API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
AUTH_SCHEME = os.environ.get("JIRA_AUTH", "bearer").lower()
USERNAME = os.environ.get("JIRA_USERNAME", "")

ssl_context = ssl.create_default_context()
if os.environ.get("JIRA_SSL_VERIFY", "true").lower() in ("0", "false", "no"):
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

if not API_TOKEN and not ({"--help", "-h"} & set(sys.argv[1:])):
    print("Error: JIRA_API_TOKEN must be set", file=sys.stderr)
    print(
        "Set it in the environment or in a .env file next to scripts/jira_api.py "
        "(JIRA_BASE_URL, JIRA_API_TOKEN, optional JIRA_AUTH=basic + JIRA_USERNAME)",
        file=sys.stderr,
    )
    sys.exit(1)


def auth_header():
    if AUTH_SCHEME == "basic":
        raw = f"{USERNAME}:{API_TOKEN}".encode()
        return f"Basic {base64.b64encode(raw).decode()}"
    return f"Bearer {API_TOKEN}"


def api_request(endpoint, method="GET", data=None):
    """One authenticated call. Exits 1 on HTTP errors (CLI contract)."""
    url = f"{BASE_URL}/rest/api/2/{endpoint}"
    headers = {
        "Authorization": auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ssl_context) as response:
            raw = response.read().decode()
            return json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:500] if exc.fp else ""
        print(f"API Error {exc.code}: {exc.reason}", file=sys.stderr)
        if detail:
            print(f"  {detail}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Connection error: {exc.reason} ({BASE_URL})", file=sys.stderr)
        sys.exit(1)


# ------------------------------------------------------------------- reads


def search_issues(jql, max_results=50):
    query = urllib.parse.urlencode(
        {"jql": jql, "maxResults": max_results, "fields": SEARCH_FIELDS}
    )
    return api_request(f"search?{query}")


def get_issue(key):
    return api_request(f"issue/{key}")


def get_subtasks(key):
    issue = get_issue(key)
    return [get_issue(s["key"]) for s in issue.get("fields", {}).get("subtasks", [])]


def get_epic_issues(epic_key):
    """Children of an epic across the three ways Jira expresses it."""
    seen, out = set(), []
    for jql in (
        f'"Epic Link" = {epic_key}',
        f"parent = {epic_key}",
        f'"Parent Link" = {epic_key}',
    ):
        try:
            issues = search_issues(jql, max_results=100).get("issues", [])
        except SystemExit:
            continue  # the field does not exist on this instance
        for issue in issues:
            if issue["key"] not in seen:
                seen.add(issue["key"])
                out.append(issue)
    return out


def get_linked_issues(key):
    links = get_issue(key).get("fields", {}).get("issuelinks", [])
    out = []
    for link in links:
        ltype = link.get("type", {})
        for side, direction in (("outwardIssue", "outward"), ("inwardIssue", "inward")):
            if side in link:
                out.append(
                    {
                        "direction": direction,
                        "type": ltype.get("name", ""),
                        "description": ltype.get(direction, ""),
                        "issue": link[side],
                    }
                )
    return out


def get_remote_links(key):
    return api_request(f"issue/{key}/remotelink")


def get_comments(key):
    return api_request(f"issue/{key}/comment")


def get_transitions(key):
    return api_request(f"issue/{key}/transitions")


def get_dev_info(key):
    """Jira Server/DC dev-status: MRs, branches, commits. Empty when absent."""
    issue_id = get_issue(key).get("id")
    out = {"pullRequests": [], "branches": [], "commits": []}
    if not issue_id:
        return out
    for app in ("gitlab", "github", "bitbucket", "stash"):
        for data_type, slot in (
            ("pullrequest", "pullRequests"),
            ("branch", "branches"),
            ("repository", "commits"),
        ):
            query = urllib.parse.urlencode(
                {"issueId": issue_id, "applicationType": app, "dataType": data_type}
            )
            url = f"{BASE_URL}/rest/dev-status/latest/issue/detail?{query}"
            req = urllib.request.Request(
                url,
                headers={"Authorization": auth_header(), "Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, context=ssl_context) as response:
                    payload = json.loads(response.read().decode())
            except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
                continue
            for detail in payload.get("detail", []):
                if slot == "commits":
                    for repo in detail.get("repositories", []):
                        out["commits"].extend(repo.get("commits", []))
                else:
                    out[slot].extend(detail.get(slot, []))
    return out


def format_brief(issue):
    f = issue.get("fields", {})
    status = (f.get("status") or {}).get("name", "")
    assignee = (f.get("assignee") or {}).get("displayName", "unassigned")
    return f"{issue.get('key')} [{status}] {f.get('summary', '')[:70]} ({assignee})"


# --------------------------------------------------------------------- CLI


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    output_format, max_results, positional = "json", 50, []
    for arg in args:
        if arg.startswith("--format="):
            output_format = arg.split("=", 1)[1]
        elif arg.startswith("--max="):
            max_results = int(arg.split("=", 1)[1])
        else:
            positional.append(arg)
    command = positional[0].lower()
    key = positional[1] if len(positional) > 1 else None

    needs_key = {
        "get": get_issue,
        "epic": get_epic_issues,
        "subtasks": get_subtasks,
        "links": get_linked_issues,
        "remotelinks": get_remote_links,
        "comments": get_comments,
        "transitions": get_transitions,
        "devinfo": get_dev_info,
    }
    if command == "search":
        if not key:
            print("Error: search needs a JQL string", file=sys.stderr)
            return 1
        result = search_issues(key, max_results)
        if output_format == "brief":
            for issue in result.get("issues", []):
                print(format_brief(issue))
            print(f"\nTotal: {result.get('total', 0)} issues")
            return 0
    elif command in needs_key:
        if not key:
            print(f"Error: {command} needs an issue key", file=sys.stderr)
            return 1
        result = needs_key[command](key)
        if output_format == "brief":
            if command in ("get",):
                print(format_brief(result))
            elif command in ("epic", "subtasks"):
                for issue in result:
                    print(format_brief(issue))
            elif command == "transitions":
                for t in result.get("transitions", []):
                    print(f"{t['id']}: {t['name']} -> {t['to']['name']}")
            else:
                print(json.dumps(result, indent=2))
            return 0
    elif command == "projects":
        result = api_request("project")
    elif command == "fields":
        result = api_request("field")
    else:
        print(f"Unknown command: {command} (run with --help)", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
