"""Tests for scripts/jira_batch_fetch.py - stubbed plugin, no network."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "jira_batch_fetch.py"

# Mirrors scripts/jira_api.py output shapes. Behavior is keyed off the issue key:
#   PROJ-AUTH -> stderr "API Error 401", exit 1 (any command)
#   PROJ-FAIL -> for `links` only: stderr "API Error 500", exit 1
#   PROJ-SLOW -> sleeps 5s (for --timeout tests)
STUB_CODE = r"""
import json, sys, time
cmd, key = sys.argv[1], sys.argv[2]
if key == "PROJ-AUTH":
    sys.stderr.write("API Error 401: Unauthorized\n"); sys.exit(1)
if key == "PROJ-FAIL" and cmd == "links":
    sys.stderr.write("API Error 500: Internal Server Error\n"); sys.exit(1)
if key == "PROJ-SLOW":
    time.sleep(5)
if cmd == "get":
    print(json.dumps({"key": key, "fields": {
        "summary": "Story " + key,
        "description": "long description body with AC and OQ text",
        "status": {"name": "Backlog", "statusCategory": {"key": "new", "name": "To Do"}},
        "priority": {"name": "High"},
        "issuetype": {"name": "Story", "subtask": False},
        "assignee": {"displayName": "Dev One", "avatarUrls": {"48x48": "http://x"}},
        "components": [{"id": "1", "name": "iOS", "self": "http://x"}],
        "customfield_10097": "GWT acceptance criteria",
        "customfield_10990": None,
        "customfield_10192": "2026-08-01",
        "customfield_10196": None,
        "issuelinks": [{"type": {"name": "Blocks", "inward": "is blocked by", "outward": "blocks"},
                        "outwardIssue": {"key": "PROJ-999", "fields": {
                            "summary": "Blocked story",
                            "status": {"name": "Backlog", "statusCategory": {"key": "new", "name": "To Do"}},
                            "issuetype": {"name": "Story"}, "priority": {"name": "Medium"}}}}],
        "labels": ["size-S"]}}))
elif cmd == "links":
    print(json.dumps([{"direction": "outward", "type": "Blocks", "description": "blocks",
        "issue": {"key": "PROJ-999", "fields": {
            "summary": "Blocked story",
            "status": {"name": "Backlog", "statusCategory": {"key": "new", "name": "To Do"}},
            "issuetype": {"name": "Story"}, "priority": {"name": "Medium"}}}}]))
elif cmd == "comments":
    print(json.dumps({"total": 1, "comments": [{
        "id": "5", "author": {"displayName": "PO", "avatarUrls": {}},
        "body": "no design needed", "created": "2026-07-01T10:00:00.000+0000",
        "updateAuthor": {"displayName": "PO"}}]}))
elif cmd == "remotelinks":
    print(json.dumps([{"id": 1, "object": {"url": "https://design.example.com/f/1", "title": "Design", "icon": {}}}]))
elif cmd == "devinfo":
    print(json.dumps({"pullRequests": [{
        "id": "!7", "name": "PROJ-1 fix", "status": "OPEN", "url": "https://gitlab/x",
        "lastUpdate": "2026-08-20T16:10:00.000+0200", "author": {"name": "Dev One"}}],
        "branches": [{"name": "feature/PROJ-1", "url": "https://gitlab/y"}],
        "commits": [{"id": "abc", "message": "wip"}, {"id": "def", "message": "fix"}]}))
else:
    sys.stderr.write("unknown command\n"); sys.exit(1)
"""


@pytest.fixture
def stub(tmp_path):
    p = tmp_path / "jira_api.py"
    p.write_text(STUB_CODE, encoding="utf-8")
    return p


def run_fetch(*args, env_extra=None):
    env = os.environ.copy()
    env.pop("JIRA_API", None)  # tests control resolution explicitly
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_happy_path_merged_json(stub, tmp_path):
    out = tmp_path / "merged.json"
    r = run_fetch(
        "--keys",
        "PROJ-1,PROJ-2",
        "--commands",
        "get,links,comments",
        "--jira-api",
        str(stub),
        "--out",
        str(out),
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data["issues"]) == {"PROJ-1", "PROJ-2"}
    assert data["issues"]["PROJ-1"]["get"]["key"] == "PROJ-1"
    assert isinstance(data["issues"]["PROJ-1"]["links"], list)
    assert data["issues"]["PROJ-2"]["comments"]["total"] == 1
    assert data["meta"]["errors"] == []
    assert data["meta"]["commands"] == ["get", "links", "comments"]


def test_stdout_when_no_out_flag(stub):
    r = run_fetch("--keys", "PROJ-1", "--commands", "get", "--jira-api", str(stub))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["issues"]["PROJ-1"]["get"]["key"] == "PROJ-1"


def test_env_var_resolution(stub):
    r = run_fetch(
        "--keys", "PROJ-1", "--commands", "get", env_extra={"JIRA_API": str(stub)}
    )
    assert r.returncode == 0, r.stderr


def test_keys_file_and_dedup(stub, tmp_path):
    kf = tmp_path / "keys.txt"
    kf.write_text("PROJ-1\nPROJ-2\nPROJ-1\n", encoding="utf-8")
    r = run_fetch("--keys-file", str(kf), "--commands", "get", "--jira-api", str(stub))
    assert r.returncode == 0, r.stderr
    assert set(json.loads(r.stdout)["issues"]) == {"PROJ-1", "PROJ-2"}


def test_auth_abort_does_not_wait_for_inflight_calls(stub):
    import time

    start = time.monotonic()
    r = run_fetch(
        "--keys",
        "PROJ-AUTH,PROJ-SLOW",
        "--commands",
        "get",
        "--jira-api",
        str(stub),
        "--timeout",
        "20",
        "--workers",
        "2",
    )
    elapsed = time.monotonic() - start
    assert r.returncode == 1
    assert r.stderr.startswith("AUTH:")
    assert elapsed < 4, f"abort took {elapsed:.1f}s - waited for in-flight call"


def test_auth_failure_aborts_whole_run(stub):
    r = run_fetch(
        "--keys",
        "PROJ-1,PROJ-AUTH,PROJ-2",
        "--commands",
        "get",
        "--jira-api",
        str(stub),
    )
    assert r.returncode == 1
    assert r.stderr.startswith("AUTH:")


def test_partial_failure_exit_2_with_meta_errors(stub):
    r = run_fetch(
        "--keys", "PROJ-1,PROJ-FAIL", "--commands", "get,links", "--jira-api", str(stub)
    )
    assert r.returncode == 2
    data = json.loads(r.stdout)
    assert data["issues"]["PROJ-FAIL"]["links"]["error"].startswith("exit 1")
    assert (
        data["issues"]["PROJ-FAIL"]["get"]["key"] == "PROJ-FAIL"
    )  # rest still fetched
    assert data["meta"]["errors"] == [
        {
            "key": "PROJ-FAIL",
            "command": "links",
            "error": data["issues"]["PROJ-FAIL"]["links"]["error"],
        }
    ]


def test_timeout_is_partial_not_fatal(stub):
    r = run_fetch(
        "--keys",
        "PROJ-SLOW",
        "--commands",
        "get",
        "--jira-api",
        str(stub),
        "--timeout",
        "1",
    )
    assert r.returncode == 2
    data = json.loads(r.stdout)
    assert "timeout" in data["issues"]["PROJ-SLOW"]["get"]["error"].lower()


def test_missing_plugin_is_fatal_non_auth(tmp_path):
    r = run_fetch(
        "--keys",
        "PROJ-1",
        "--commands",
        "get",
        "--jira-api",
        str(tmp_path / "missing.py"),
    )
    assert r.returncode == 1
    assert not r.stderr.startswith("AUTH:")
    assert "not found" in r.stderr.lower()


def test_unknown_command_exits_1_not_2(stub):
    r = run_fetch(
        "--keys", "PROJ-1", "--commands", "get,frobnicate", "--jira-api", str(stub)
    )
    assert r.returncode == 1
    assert "unknown command" in r.stderr.lower()


def test_empty_commands_exits_1(stub):
    r = run_fetch("--keys", "PROJ-1", "--commands", ",", "--jira-api", str(stub))
    assert r.returncode == 1
    assert "no commands given" in r.stderr.lower()


def test_usage_error_exits_1_not_2():
    # argparse default would exit 2 - reserved for "partial" in this contract
    r = run_fetch("--keys", "PROJ-1")  # --commands missing
    assert r.returncode == 1


def test_missing_keys_file_is_fatal_non_auth(stub, tmp_path):
    r = run_fetch(
        "--keys-file",
        str(tmp_path / "missing.txt"),
        "--commands",
        "get",
        "--jira-api",
        str(stub),
    )
    assert r.returncode == 1
    assert not r.stderr.startswith("AUTH:")
    assert "keys file not found" in r.stderr.lower()


def test_trim_readiness(stub, tmp_path):
    # The custom fields the trim keeps come from jira-config.json
    # (readiness_fields) - point the subprocess at a config of its own.
    config = tmp_path / "jira-config.json"
    config.write_text(
        json.dumps(
            {
                "readiness_fields": {
                    "acceptance_criteria": "customfield_10097",
                    "flagged": "customfield_10990",
                    "baseline_start": "customfield_10192",
                    "baseline_end": "customfield_10196",
                }
            }
        ),
        encoding="utf-8",
    )
    r = run_fetch(
        "--keys",
        "PROJ-1",
        "--commands",
        "get,links,comments,remotelinks",
        "--jira-api",
        str(stub),
        "--trim",
        "readiness",
        env_extra={"JIRA_CONFIG": str(config)},
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    fields = data["issues"]["PROJ-1"]["get"]["fields"]
    # labels kept: gate (iv) reads the size-XS..XL estimate from them
    assert fields["labels"] == ["size-S"]
    # noise dropped
    assert "avatarUrls" not in json.dumps(data)
    # description kept: AC/GWT and open-question markers live there when the AC field is null
    assert fields["description"] == "long description body with AC and OQ text"
    # DoR-gate fields kept
    assert fields["customfield_10097"] == "GWT acceptance criteria"
    assert fields["customfield_10990"] is None
    assert fields["customfield_10192"] == "2026-08-01"
    assert fields["customfield_10196"] is None
    assert fields["status"] == {
        "name": "Backlog",
        "statusCategory": {"key": "new", "name": "To Do"},
    }
    assert fields["priority"] == {"name": "High"}
    assert fields["issuetype"] == {"name": "Story"}
    assert fields["assignee"] == {"displayName": "Dev One"}
    assert fields["components"] == [{"name": "iOS"}]
    assert fields["issuelinks"][0]["outwardIssue"]["key"] == "PROJ-999"
    # links list trimmed but keeps direction/type + nested issue status
    link = data["issues"]["PROJ-1"]["links"][0]
    assert link["direction"] == "outward" and link["type"] == "Blocks"
    assert link["issue"]["fields"]["status"]["statusCategory"]["key"] == "new"
    # comments flattened
    assert data["issues"]["PROJ-1"]["comments"]["comments"] == [
        {
            "author": "PO",
            "created": "2026-07-01T10:00:00.000+0000",
            "body": "no design needed",
        }
    ]
    # remotelinks -> url+title only
    assert data["issues"]["PROJ-1"]["remotelinks"] == [
        {"url": "https://design.example.com/f/1", "title": "Design"}
    ]
    assert data["meta"]["trim"] == "readiness"


def test_no_trim_is_raw_passthrough(stub):
    r = run_fetch("--keys", "PROJ-1", "--commands", "get", "--jira-api", str(stub))
    fields = json.loads(r.stdout)["issues"]["PROJ-1"]["get"]["fields"]
    assert fields["description"] == "long description body with AC and OQ text"


def test_devinfo_raw_and_trimmed(stub):
    raw = run_fetch(
        "--keys", "PROJ-1", "--commands", "devinfo", "--jira-api", str(stub)
    )
    assert raw.returncode == 0, raw.stderr
    payload = json.loads(raw.stdout)["issues"]["PROJ-1"]["devinfo"]
    assert payload["pullRequests"][0]["url"] == "https://gitlab/x"  # untrimmed

    trimmed = run_fetch(
        "--keys",
        "PROJ-1",
        "--commands",
        "devinfo",
        "--trim",
        "readiness",
        "--jira-api",
        str(stub),
    )
    assert trimmed.returncode == 0, trimmed.stderr
    payload = json.loads(trimmed.stdout)["issues"]["PROJ-1"]["devinfo"]
    assert payload["pullRequests"] == [
        {
            "name": "PROJ-1 fix",
            "status": "OPEN",
            "lastUpdate": "2026-08-20T16:10:00.000+0200",
        }
    ]
    assert payload["branches"] == [{"name": "feature/PROJ-1"}]
    assert payload["commits"] == 2  # count, not bodies
