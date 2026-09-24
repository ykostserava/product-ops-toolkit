"""PreToolUse guard: block non-ASCII payloads in shell commands that actually
CALL the Jira/Confluence APIs. Why: a WAF in front of a corporate Jira may
reject Unicode in create/update payloads with an opaque 400, and an ASCII-only
payload rule is cheap to keep. (Stored UTF-8 is NOT mangled by the API - do not
cite mangling as the reason; the WAF rejection is.)

Reads the hook JSON from stdin and denies the tool call only when all three
hold:

  1. the command names a Jira/Confluence endpoint - a literal host whose
     name contains "jira." / "confluence." / "atlassian." (add your own via
     GUARD_JIRA_HOSTS, comma-separated), the env vars the skills call through
     ($JIRA_URL, $CONFLUENCE_BASE, ...), or scripts/jira_api.py ($JIRA),
  2. the command actually sends a request (curl, wget, PowerShell Invoke-*,
     python requests/urllib/httpx/jira, node fetch/axios, jira_api's
     add-comment), and
  3. the command contains a character outside ASCII.

Condition 2 is what keeps the guard off LOCAL work: writing a non-English
note that merely mentions the host is not a payload. Silent (allow) otherwise.

Known edges (a regex cannot see comments or prose): a sender word inside a
trailing '# comment' or a note ('urlopen', 'irm') still counts, and so does
code written as DATA (a heredoc that writes a script calling urlopen); the
httpie CLI is not recognised (nobody in the toolkit uses it, and its name
collides with the word 'http' in prose and with URL schemes). The repo's
own Jira writer scripts are not senders here - they enforce ASCII themselves
and their names appear in far more local commands than invocations.

Wiring (see hooks/README.md): PreToolUse, matcher Bash|PowerShell.
"""

import json
import os
import re
import sys

# 1. a Jira/Confluence endpoint: literal host, or the env var the skills use
_EXTRA_HOSTS = [
    re.escape(h.strip())
    for h in os.environ.get("GUARD_JIRA_HOSTS", "").split(",")
    if h.strip()
]
TARGET = re.compile(
    r"\b(jira|confluence|atlassian)\.[a-z0-9.-]+"
    + "".join("|" + h for h in _EXTRA_HOSTS)
    + r"|JIRA_URL"
    r"|JIRA_BASE_URL"
    r"|CONFLUENCE_BASE(_URL)?"
    r"|jira_api\.py"
    r"|\$\{?JIRA\}?(?![A-Za-z0-9_])",  # the jira_api.py handle the skills use
    re.IGNORECASE,
)

# 2. something that actually performs the request
SENDER = re.compile(
    r"(^|[\s;|&(`'\"\\])"  # backslash: \curl bypasses aliases, still curl
    r"(curl|wget)\b"
    r"|Invoke-(WebRequest|RestMethod)\b"
    r"|\b(iwr|irm)\b"
    r"|\b(WebClient|HttpClient)\b"
    r"|requests\.(get|post|put|patch|delete|request)\b"
    r"|\b(post|put|patch|delete)\("  # from requests import post; post(...)
    r"|\.request\(\s*['\"](POST|PUT|PATCH|DELETE)"  # Session/urllib3 .request
    r"|\bJIRA\("  # the jira python library (no space before the paren: code, not prose)
    r"|urllib\.request|urlopen\b|http\.client"
    r"|httpx\.|axios\.|fetch\s*\("
    r"|\badd-comment\b",  # a CLI's comment write: python "$JIRA" add-comment
    re.IGNORECASE,
)

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

cmd = (data.get("tool_input") or {}).get("command") or ""

if not (TARGET.search(cmd) and SENDER.search(cmd)):
    sys.exit(0)

bad = sorted({c for c in cmd if ord(c) > 127})
if bad:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Blocked: non-ASCII characters "
                        + ascii("".join(bad))
                        + " in a request to the Jira/Confluence API "
                        "(ASCII-only payload rule - a WAF may reject Unicode "
                        "in create/update payloads). Replace arrows, non-Latin "
                        "scripts, curly quotes and symbols with ASCII and retry."
                    ),
                }
            }
        )
    )
sys.exit(0)
