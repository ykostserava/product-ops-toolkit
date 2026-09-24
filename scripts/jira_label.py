#!/usr/bin/env python3
"""Add/remove Jira issue labels safely - the repo's only label writer.

Consumers: the /prioritize skill (size labels approved at its Gate W). Labels
are REVERSIBLE, so no one-way gate exists here - but the same contract as
jira_transition.py applies: preflight guards, ASCII-only, post-execute
verification, identical exit codes. Reuses jira_transition's module loader
and HTTP layer (scripts/jira_api.py stays the only Jira access point).
Deliberately generic: it knows nothing about "size-*"
semantics - the consumer validates those; any ASCII label works.

The update uses add/remove operations, never "set", so labels added
concurrently by others are not clobbered.

Usage:
    python scripts/jira_label.py --key PROJ-123 --add size-S [--add ...] \
        [--remove size-M ...] [--dry-run] [--jira-api PATH]

Exit codes (consumer contract, same as jira_transition.py):
    0  success + verified (or clean --dry-run; payload printed, nothing sent)
    1  fatal - stderr starting with "AUTH:" means VPN/token (STOP)
    2  refused preflight - nothing was written (no effective ops, conflicting
       add+remove, non-ASCII label)
    3  PUT accepted but post-execute verification saw different labels -
       check the issue manually before doing anything else
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


def _current_labels(request, key):
    return set(request(f"issue/{key}?fields=labels")["fields"].get("labels") or [])


def run(args, request):
    """Guard, execute, verify. Returns the result dict for stdout."""
    refuse_if_propose_only(args.dry_run)
    adds = list(dict.fromkeys(args.add or []))
    removes = list(dict.fromkeys(args.remove or []))
    if not adds and not removes:
        raise Refused("nothing requested - pass --add and/or --remove")
    for label in adds + removes:
        ensure_ascii(label, f"label '{label}'")
    conflict = sorted(set(adds) & set(removes))
    if conflict:
        raise Refused(f"label(s) in both --add and --remove: {', '.join(conflict)}")

    current = _current_labels(request, args.key)
    effective_add = [label for label in adds if label not in current]
    effective_remove = [label for label in removes if label in current]
    skipped = sorted(
        (set(adds) - set(effective_add)) | (set(removes) - set(effective_remove))
    )
    if not effective_add and not effective_remove:
        raise Refused(
            f"{args.key} already has the requested label state - nothing to do"
        )

    payload = {
        "update": {
            "labels": [{"add": label} for label in effective_add]
            + [{"remove": label} for label in effective_remove]
        }
    }
    if args.dry_run:
        return {
            "dry_run": True,
            "key": args.key,
            "add": effective_add,
            "remove": effective_remove,
            "skipped_noop": skipped,
            "payload": payload,
        }

    request(f"issue/{args.key}", method="PUT", data=payload)
    try:
        after = _current_labels(request, args.key)
    except Exception as exc:  # noqa: BLE001 - the PUT already landed
        # Exit 1 tells the consumer "nothing was written - stop"; here the
        # write may HAVE landed and only the verification read failed, so this
        # must surface as exit 3 (check the issue manually), never exit 1.
        raise VerifyMismatch(
            f"PUT accepted but the verify read failed ({exc}) - "
            f"labels on {args.key} are unconfirmed, check manually"
        ) from exc
    missing = [label for label in effective_add if label not in after]
    lingering = [label for label in effective_remove if label in after]
    if missing or lingering:
        raise VerifyMismatch(
            f"PUT accepted but {args.key} labels are {sorted(after)} - missing "
            f"adds {missing}, lingering removes {lingering} - check manually"
        )
    return {
        "key": args.key,
        "add": effective_add,
        "remove": effective_remove,
        "skipped_noop": skipped,
        "labels": sorted(after),
        "verified": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--key", required=True, help="issue key, e.g. PROJ-123")
    parser.add_argument(
        "--add", action="append", default=[], help="label to add (repeatable)"
    )
    parser.add_argument(
        "--remove", action="append", default=[], help="label to remove (repeatable)"
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
