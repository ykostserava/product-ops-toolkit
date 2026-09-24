#!/usr/bin/env python3
"""Execute one Jira status transition safely - the repo's only transition writer.

Consumers: the /board-sync skill (after explicit human approval at its Gate B)
and jira_apply.py. Reuses scripts/jira_api.py for env/token/base-url (it stays
the only Jira access point). The HTTP layer is local because jira_api's
api_request exits the process on HTTP errors, and a transition POST replies
204 with an empty body.

Rules honored (house conventions, each one a verified 400 or a lost ticket):
    - transition ids vary by issue TYPE and CURRENT status: always enumerated
      live via GET /transitions and matched by target status NAME, never by id;
    - the statuses listed under statuses.one_way in jira-config.json have no
      way back: refused without --yes-one-way;
    - closing requires --resolution (resolution cannot be set after close);
    - payloads must be ASCII (a WAF in front of Jira may reject non-ASCII
      create/update payloads; transliterate first).

Usage:
    python scripts/jira_transition.py --key PROJ-123 --to "In Analysis" \
        [--resolution Done] [--yes-one-way] [--comment "ascii text"] \
        [--dry-run] [--jira-api PATH]

Exit codes (consumer contract):
    0  success + verified (or clean --dry-run; payload printed, nothing sent)
    1  fatal - stderr starting with "AUTH:" means VPN/token (STOP); anything
       else is an unexpected API failure
    2  refused preflight - nothing was written (unreachable target, one-way
       without the flag, missing resolution, non-ASCII payload, already there)
    3  the POST was accepted but the result is UNCONFIRMED - either the
       verification read saw a different status, or that read itself failed.
       Either way the write may have landed: check the issue manually before
       doing anything else. Never read 3 as "nothing happened".

Environment:
    JIRA_PROPOSE_ONLY=1  refuse any real write (exit 2). --dry-run still works.
       Scheduled/headless wrappers set it, so a run with a blanket Bash grant
       cannot write even if the model decides to.
"""

import os
import argparse
import importlib.util
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jira_batch_fetch import resolve_jira_api  # noqa: E402
from jira_config import CONFIG  # noqa: E402

ONE_WAY = tuple(s.lower() for s in CONFIG["statuses"]["one_way"])
CLOSED = CONFIG["statuses"]["closed"].lower()


class Refused(Exception):
    """Preflight guardrail hit - nothing was written (exit 2)."""


class AuthFailure(Exception):
    """VPN/token problem - stop the whole run (exit 1, AUTH: prefix)."""


class VerifyMismatch(Exception):
    """POST accepted but the issue is not in the expected status (exit 3)."""


def load_plugin(path):
    """Import jira_api.py for its env loading + BASE_URL/API_TOKEN/ssl_context."""
    spec = importlib.util.spec_from_file_location("jira_api_module", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # runs load_env(); exits if no token
    except SystemExit:
        raise AuthFailure("JIRA_API_TOKEN not configured (scripts/.env)") from None
    return module


def make_requester(module):
    """HTTP closure over jira_api's connection globals.

    Returns parsed JSON, or None for empty replies (transition POST is 204).
    Raises AuthFailure on 401/403, RuntimeError on other HTTP errors.
    """

    def request(endpoint, method="GET", data=None):
        url = f"{module.BASE_URL}/rest/api/2/{endpoint}"
        auth = getattr(module, "auth_header", None)
        headers = {
            "Authorization": auth() if auth else f"Bearer {module.API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=module.ssl_context) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()[:500] if exc.fp else ""
            if exc.code in (401, 403):
                raise AuthFailure(
                    f"HTTP {exc.code} from Jira - check network/VPN and JIRA_API_TOKEN"
                ) from None
            raise RuntimeError(
                f"HTTP {exc.code} on {method} {endpoint}: {detail}"
            ) from None

    return request


def ensure_ascii(value, label):
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        raise Refused(
            f"{label} contains non-ASCII characters - the payload rule is "
            "ASCII only; transliterate first"
        ) from None


PROPOSE_ONLY_ENV = "JIRA_PROPOSE_ONLY"
_TRUTHY = {"1", "true", "yes", "on"}


def refuse_if_propose_only(dry_run):
    """Raise Refused when the run may only propose.

    Scheduled wrappers run a skill headless with a blanket Bash grant, and
    every script in this family sits in the directory that grant covers - so
    "this mode never writes" was a promise in a prompt. With JIRA_PROPOSE_ONLY
    set the refusal happens here, in the script that would do the writing,
    whatever the model decided to run.

    Any of 1/true/yes/on counts: a wrapper author who writes =true must not get
    silent non-enforcement.
    """
    if dry_run:
        return
    value = (os.environ.get(PROPOSE_ONLY_ENV) or "").strip().lower()
    if value in _TRUTHY:
        raise Refused(
            f"{PROPOSE_ONLY_ENV}={value} is set - this run may only propose. "
            "Re-run without it, or add --dry-run."
        )


def resolve_transition(transitions, to, via, key, current, issuetype):
    """Pick the one transition that lands on `to` - the repo's only resolver.

    Matched by TARGET STATUS NAME because ids vary by issue type and current
    status, and collide across types for different targets (one id can be
    Epic Post Production -> Closed AND Story Ready for testing -> In testing
    on the same instance).

    A target is not a unique key either: from a testing status two transitions
    can land on Closed - "Done" and "Closed" - and offer DIFFERENT resolution
    sets, so attaching a resolution from the other one's screen 400s. Taking
    the first match silently picked one of those screens. When
    several candidates share a target this refuses and asks for `via` (the
    transition NAME) instead of guessing.
    """
    matches = [t for t in transitions if t["to"]["name"].lower() == to.lower()]
    if not matches:
        available = ", ".join(sorted({t["to"]["name"] for t in transitions})) or "none"
        raise Refused(
            f"no transition from '{current}' to '{to}' for {issuetype} "
            f"{key} (available targets: {available})"
        )
    if via:
        by_name = [t for t in matches if t["name"].lower() == via.lower()]
        if not by_name:
            offered = ", ".join(sorted(t["name"] for t in matches))
            raise Refused(
                f"no transition named '{via}' lands on '{to}' for {key} "
                f"(transitions to that target: {offered})"
            )
        return by_name[0]
    if len(matches) > 1:
        offered = ", ".join(
            f"{t['name']} (id {t['id']})"
            for t in sorted(matches, key=lambda t: t["id"])
        )
        raise Refused(
            f"{len(matches)} transitions on {key} land on '{to}' - they can carry "
            f"different resolution screens, so the target alone does not identify "
            f"one. Name it with --via: {offered}"
        )
    return matches[0]


def run(args, request):
    """Resolve, guard, execute, verify. Returns the result dict for stdout."""
    refuse_if_propose_only(args.dry_run)
    ensure_ascii(args.to, "--to")
    if args.comment:
        ensure_ascii(args.comment, "--comment")
    if args.resolution:
        ensure_ascii(args.resolution, "--resolution")

    issue = request(f"issue/{args.key}?fields=status,issuetype")
    current = issue["fields"]["status"]["name"]
    issuetype = issue["fields"]["issuetype"]["name"]
    if current.lower() == args.to.lower():
        raise Refused(f"{args.key} is already in '{current}' - nothing to do")

    transitions = request(f"issue/{args.key}/transitions")["transitions"]
    transition = resolve_transition(
        transitions, args.to, getattr(args, "via", None), args.key, current, issuetype
    )
    target = transition["to"]["name"]

    one_way = target.lower() in ONE_WAY
    if one_way and not args.yes_one_way and not args.dry_run:
        # Deliberately NOT enforced for --dry-run: a preview must never need
        # the arming flag, otherwise callers build fully-armed command lines
        # where dropping --dry-run alone executes a one-way move. The preview
        # reports one_way instead; the real run still refuses without the flag.
        raise Refused(
            f"'{target}' is a ONE-WAY transition (no REST path back) - re-run "
            "with --yes-one-way if this is deliberate"
        )
    if target.lower() == CLOSED and not args.resolution:
        raise Refused(
            "closing requires --resolution (resolution cannot be corrected "
            "after close - a resolution PUT on a closed issue 400s)"
        )

    payload = {"transition": {"id": transition["id"]}}
    if args.resolution:
        payload["fields"] = {"resolution": {"name": args.resolution}}
    if args.comment:
        payload["update"] = {"comment": [{"add": {"body": args.comment}}]}

    if args.dry_run:
        return {
            "dry_run": True,
            "key": args.key,
            "from": current,
            "to": target,
            "transition_id": transition["id"],
            "one_way": one_way,
            "payload": payload,
        }

    request(f"issue/{args.key}/transitions", method="POST", data=payload)
    try:
        after = request(f"issue/{args.key}?fields=status")["fields"]["status"]["name"]
    except Exception as exc:  # noqa: BLE001 - the POST already landed
        # Exit 1 means "nothing was written - STOP" in this file's own
        # contract. Here the transition may HAVE happened and only the verify
        # read failed, so a 500 or a timeout here would report a closed issue
        # as untouched - on a --yes-one-way close there is no way back.
        # Same handling as jira_label.py: exit 3, check the issue manually.
        raise VerifyMismatch(
            f"POST accepted but the verify read failed ({exc}) - the status of "
            f"{args.key} is unconfirmed, check it manually before retrying"
        ) from exc
    if after.lower() != target.lower():
        raise VerifyMismatch(
            f"POST accepted but {args.key} is in '{after}', expected '{target}' "
            "- check the issue manually"
        )
    return {
        "key": args.key,
        "from": current,
        "to": after,
        "transition_id": transition["id"],
        "verified": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--key", required=True, help="issue key, e.g. PROJ-123")
    parser.add_argument("--to", required=True, help="target status NAME (not id)")
    parser.add_argument("--resolution", help="resolution name; REQUIRED when closing")
    parser.add_argument(
        "--via",
        help="transition NAME, when several transitions land on the same target "
        "status (they can carry different resolution screens)",
    )
    parser.add_argument(
        "--yes-one-way",
        action="store_true",
        help="confirm a one-way transition (statuses.one_way in jira-config.json)",
    )
    parser.add_argument("--comment", help="ASCII comment to add with the transition")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve + print the exact payload, send nothing",
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
