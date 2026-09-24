#!/usr/bin/env python3
"""Set one Jira issue assignee safely - the repo's only assignee writer.

Consumers: the /board-sync skill (R4 findings, after explicit human approval at
its Gate B). Assignment is REVERSIBLE, so no one-way gate exists here - but the
same contract as jira_transition.py applies: preflight guards, ASCII-only,
post-execute verification, identical exit codes. Reuses jira_transition's
module loader and HTTP layer (scripts/jira_api.py stays the only Jira access
point).

Usage:
    python scripts/jira_assign.py --key PROJ-123 --assignee dev@example.com \
        [--dry-run] [--jira-api PATH]

Exit codes (consumer contract, same as jira_transition.py):
    0  success + verified (or clean --dry-run; payload printed, nothing sent)
    1  fatal - stderr starting with "AUTH:" means VPN/token (STOP)
    2  refused preflight - nothing was written (already assigned to the same
       person, non-ASCII username)
    3  the PUT was accepted but the result is UNCONFIRMED - either the
       verification read saw a different assignee, or that read itself
       failed. Either way the write may have landed: check the issue
       manually. Never read 3 as "nothing happened".

Environment:
    JIRA_PROPOSE_ONLY=1  refuse any real write (exit 2). --dry-run still works.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jira_batch_fetch import resolve_jira_api  # noqa: E402
from jira_transition import (  # noqa: E402
    AuthFailure,
    Refused,
    VerifyMismatch,
    ensure_ascii,
    load_plugin,
    make_requester,
    refuse_if_propose_only,
)


def _current_assignee(request, key):
    assignee = request(f"issue/{key}?fields=assignee")["fields"].get("assignee")
    return (assignee or {}).get("name")


def run(args, request):
    """Guard, execute, verify. Returns the result dict for stdout."""
    refuse_if_propose_only(args.dry_run)
    ensure_ascii(args.assignee, "--assignee")

    current = _current_assignee(request, args.key)
    if current and current.lower() == args.assignee.lower():
        raise Refused(f"{args.key} is already assigned to '{current}' - nothing to do")

    payload = {"name": args.assignee}
    if args.dry_run:
        return {
            "dry_run": True,
            "key": args.key,
            "from": current,
            "assignee": args.assignee,
            "payload": payload,
        }

    request(f"issue/{args.key}/assignee", method="PUT", data=payload)
    try:
        after = _current_assignee(request, args.key)
    except Exception as exc:  # noqa: BLE001 - the PUT already landed
        # Same window as jira_transition and jira_label: the write happened
        # and only the verification read failed, so this must not surface as
        # the exit code consumers read as "nothing was written - stop".
        raise VerifyMismatch(
            f"PUT accepted but the verify read failed ({exc}) - the assignee "
            f"of {args.key} is unconfirmed, check it manually"
        ) from exc
    if (after or "").lower() != args.assignee.lower():
        raise VerifyMismatch(
            f"PUT accepted but {args.key} assignee is '{after}', expected "
            f"'{args.assignee}' - check the issue manually"
        )
    return {
        "key": args.key,
        "from": current,
        "assignee": after,
        "verified": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--key", required=True, help="issue key, e.g. PROJ-123")
    parser.add_argument(
        "--assignee", required=True, help="Jira username, e.g. dev@example.com"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the exact payload, send nothing",
    )
    parser.add_argument("--jira-api", help="path to jira_api.py (default: sibling)")
    args = parser.parse_args(argv)

    try:
        request = make_requester(load_plugin(resolve_jira_api(args.jira_api)))
        result = run(args, request)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    except AuthFailure as exc:
        print(f"AUTH: {exc}", file=sys.stderr)
        return 1
    except VerifyMismatch as exc:
        print(f"VERIFY MISMATCH: {exc}", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
