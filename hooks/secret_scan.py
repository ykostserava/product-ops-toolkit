#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse hook — block `git commit` when gitleaks finds a secret.

Intercepts Bash/PowerShell commands. If the command is a `git commit` and gitleaks
is installed, scans the staged diff. On a confirmed leak it DENIES the commit;
otherwise it passes through. If gitleaks is not installed, or scanning errors out,
it fails open (allows) so it never hard-blocks a developer who hasn't set up
gitleaks yet. Install gitleaks: https://github.com/gitleaks/gitleaks#installing

Protocol (matches Claude Code PreToolUse): reads the event JSON from stdin, prints
a JSON decision to stdout, exits 0. On any error prints "{}" (fail open).
"""

import json
import re
import shutil
import subprocess
import sys

GIT_COMMIT = re.compile(r"\bgit\s+(?:-c\s+\S+\s+)*commit\b", re.I)


def deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def decide(tool_name: str, tool_input: dict) -> dict:
    if tool_name not in ("Bash", "PowerShell"):
        return {}
    cmd = tool_input.get("command") or ""
    if not GIT_COMMIT.search(cmd):
        return {}
    if shutil.which("gitleaks") is None:
        return {}  # not installed — fail open

    try:
        # `gitleaks git --staged` scans the staged diff. (The older `protect`
        # subcommand was removed in gitleaks 8.30; `git` is the current form.)
        proc = subprocess.run(
            ["gitleaks", "git", "--staged", "--redact", "--no-banner"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception:
        return {}  # scan error — fail open

    # gitleaks exit code 1 == leaks found; anything else (0 clean, or a tool
    # error) is not a confirmed leak, so we do not block on it.
    if proc.returncode == 1:
        detail = (proc.stdout or proc.stderr or "").strip()
        detail = re.sub(r"\x1b\[[0-9;]*m", "", detail)  # strip ANSI color codes
        detail = detail[-1500:] if detail else "gitleaks reported a leak."
        return deny(
            "gitleaks detected a potential secret in the staged diff. Commit blocked.\n"
            "Remove the secret (and rotate it if it was real), then re-stage. To bypass "
            "a false positive, add a gitleaks allowlist entry — do not disable the hook.\n\n"
            + detail
        )
    return {}


def main() -> None:
    try:
        event = json.load(sys.stdin)
        decision = decide(event.get("tool_name", ""), event.get("tool_input", {}) or {})
        sys.stdout.write(json.dumps(decision))
    except Exception:
        sys.stdout.write("{}")  # fail open
    sys.exit(0)


if __name__ == "__main__":
    main()
