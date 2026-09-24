"""Tests for guard_jira_ascii.py, the hook that blocks non-ASCII Jira payloads.

A guard that can block a teammate's command ships with the input it must fire
on AND the input it must not: the first version fired on a script writing a
local file and on an append to a non-English note, both of which only
MENTIONED the host.

Non-ASCII payloads are spelled with escapes so this file stays pure ASCII.
stdlib unittest (pytest collects it too).
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = next(
    (
        p
        for p in (
            ROOT / ".claude" / "hooks" / "guard_jira_ascii.py",
            ROOT / "hooks" / "guard_jira_ascii.py",
        )
        if p.is_file()
    ),
    None,
)

CYRILLIC = "\u041a\u0438\u0440\u0438\u043b\u043b\u0438\u0446\u0430"
EM_DASH = "\u2014"
ARROW = "\u2192"
GUILLEMETS = "\u00ab\u00bb"
HOST = "https://jira.example.com"

MUST_DENY = {
    "curl to the literal host with a Cyrillic payload": (
        "curl -X POST "
        + HOST
        + '/rest/api/2/issue -d \'{"summary":"'
        + CYRILLIC
        + "\"}'"
    ),
    "curl through $JIRA_URL (how the QA skills call it)": (
        'curl -s -H "Authorization: Bearer $T" '
        '"$JIRA_URL/rest/api/2/issue/PROJ-1/comment" '
        '-d \'{"body":"Ready for testing ' + ARROW + " In testing\"}'"
    ),
    "PowerShell Invoke-RestMethod with an em dash": (
        'Invoke-RestMethod -Uri "' + HOST + '/rest/api/2/issue" '
        '-Body \'{"summary":"Test Plan ' + EM_DASH + " PROJ-1\"}'"
    ),
    "python urlopen against the host": (
        "python -c 'import urllib.request; urllib.request.urlopen(\""
        + HOST
        + '/rest/api/2/issue", data="'
        + CYRILLIC
        + "\".encode())'"
    ),
    "confluence through $CONFLUENCE_BASE": (
        'curl -X PUT "$CONFLUENCE_BASE/rest/api/content/123" -d \'{"title":"'
        + CYRILLIC
        + "\"}'"
    ),
    "backslash-escaped curl (bypasses aliases, still curl)": (
        "\\curl -X POST "
        + HOST
        + '/rest/api/2/issue -d \'{"summary":"'
        + CYRILLIC
        + "\"}'"
    ),
    "python requests imported as a bare post()": (
        "python -c \"from requests import post; post('"
        + HOST
        + "/rest/api/2/issue', json={'summary': '"
        + CYRILLIC
        + "'})\""
    ),
    "the jira python library": (
        "python -c \"from jira import JIRA; JIRA('"
        + HOST
        + "', token_auth=t).add_comment('PROJ-1', '"
        + CYRILLIC
        + "')\""
    ),
    "the plugin add-comment through $JIRA (the documented write path)": (
        'python "$JIRA" add-comment PROJ-1 "' + CYRILLIC + '"'
    ),
    "a requests Session .request('POST', ...)": (
        "python -c \"import requests; requests.Session().request('POST', '"
        + HOST
        + "/rest/api/2/issue', json={'x': '"
        + CYRILLIC
        + "'})\""
    ),
    # Latin-1 range (128..255): pins the boundary at 127, not at 255
    "curl with guillemets, the lowest non-ASCII block": (
        "curl -X POST "
        + HOST
        + '/rest/api/2/issue -d \'{"summary":"'
        + GUILLEMETS
        + "\"}'"
    ),
}

MUST_ALLOW = {
    # the two real false positives the first version had
    "appending a Russian note that mentions the host": (
        "cat scratch.md >> memory/notes.md  # " + CYRILLIC + " jira.example.com"
    ),
    "a local script that writes a file and mentions the host": (
        "python build_env.py  # JIRA_URL=" + HOST + ", " + CYRILLIC
    ),
    # neighbours that must stay quiet
    "an ASCII-only request to the host": (
        "curl -s " + HOST + "/rest/api/2/issue/PROJ-1"
    ),
    # '~' is 0x7E, the last printable ASCII char and the JQL contains-operator.
    # It does not pin `> 127` from below: the neighbours 126/128 only change the
    # fate of U+007F (DEL) and U+0080 (a C1 control), neither typed in a command.
    "a JQL search with the ~ operator": (
        'curl -s "' + HOST + '/rest/api/2/search?jql=summary~test"'
    ),
    "Cyrillic with no Jira target at all": ('git commit -m "' + CYRILLIC + '"'),
    "grepping a local file for the host": (
        'grep -n "jira.example.com" notes.md  # ' + CYRILLIC
    ),
    # a URL scheme is not a sender
    "a Russian note that contains a link to the host": (
        'echo "' + CYRILLIC + " " + HOST + '/browse/PROJ-1" >> notes.md'
    ),
    # the word http in prose is not a sender either (httpie is not recognised)
    "a Russian note about an HTTP 400 from the host": (
        'echo "' + CYRILLIC + " HTTP 400 " + HOST + '" >> memory/notes.md'
    ),
    "a commit message mentioning http and the host": (
        'git commit -m "fix http timeout ' + CYRILLIC + " " + HOST + '"'
    ),
    "a plugin READ through $JIRA with a Russian comment": (
        'python "$JIRA" get PROJ-1  # ' + CYRILLIC
    ),
    # the repo's writer scripts are not senders: editing/committing them with a
    # target word in the message is routine local work (review finding N-S6)
    "a commit touching a Jira writer script, message names JIRA_URL": (
        'git commit -m "fix(jira): jira_apply.py reads JIRA_URL from .env '
        + CYRILLIC
        + '"'
    ),
    # 'JIRA (' with a space is prose, 'JIRA(' is the library (N-S7)
    "a Russian note saying JIRA (PROJ-1) with a link": (
        'echo "'
        + CYRILLIC
        + " JIRA (PROJ-1) https://"
        + HOST
        + '/browse/PROJ-1" >> notes.md'
    ),
}


def run(command):
    """Return the hook's permissionDecision, or None when it stays silent."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError("hook exited %s: %s" % (result.returncode, result.stderr))
    out = result.stdout.strip()
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


@unittest.skipIf(HOOK is None, "hook not found in this layout")
class GuardJiraAsciiCase(unittest.TestCase):
    def test_denies_non_ascii_payloads(self):
        for label, command in MUST_DENY.items():
            with self.subTest(label):
                self.assertEqual(run(command), "deny")

    def test_allows_local_work_and_ascii_requests(self):
        for label, command in MUST_ALLOW.items():
            with self.subTest(label):
                self.assertIsNone(run(command))

    def test_malformed_stdin_is_silent(self):
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input="not json",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
