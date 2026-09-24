"""Write and check the /pre-mr gate marker.

The marker used to hold a HEAD sha. That is not what the gate verifies: an
`amend` moves HEAD without changing a line, and - the case that actually bit us
in an earlier review - applying review findings CHANGES the diff while the marker gets
rewritten as a mechanical step, so a regression introduced by the fixes reached
the branch with the gate reporting green.

The marker therefore records a digest of the reviewed CONTENT (tracked changes
against the base plus untracked files). Re-marking a changed diff is still
possible - the gate is a discipline, not a lock - but it now has to be stated:
`write` refuses without --reason, and the reason is kept in the marker so the
next reader can see the diff was re-marked rather than re-reviewed.

    python hooks/pre_mr_marker.py write --base origin/master
    python hooks/pre_mr_marker.py write --base origin/master --reason "..."
    python hooks/pre_mr_marker.py check          # exit 0 = marker covers this tree
    python hooks/pre_mr_marker.py show
"""

import argparse
import hashlib
import os
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

NUL = chr(0)
NUL_BYTE = bytes([0])
MARKER_NAME = "pre-mr-ok"
DEFAULT_BASES = ("origin/master", "origin/main", "master", "main")


class MarkerError(Exception):
    pass


def git(repo, *args, binary=False):
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        timeout=30,
    )
    if done.returncode != 0:
        raise MarkerError(
            f"git {' '.join(args)} failed: "
            f"{done.stderr.decode('utf-8', 'replace').strip()}"
        )
    return done.stdout if binary else done.stdout.decode("utf-8", "replace")


def marker_path(repo):
    git_dir = git(repo, "rev-parse", "--git-dir").strip()
    path = Path(git_dir)
    if not path.is_absolute():
        path = Path(repo) / path
    return path / MARKER_NAME


def pick_base(repo, given=None):
    if given:
        return given
    for ref in DEFAULT_BASES:
        try:
            git(repo, "rev-parse", "--verify", "--quiet", ref)
            return ref
        except MarkerError:
            continue
    raise MarkerError(
        "no base ref found (tried " + ", ".join(DEFAULT_BASES) + "); pass --base"
    )


def content_digest(repo, base):
    """Digest of what a reviewer would have read.

    Tracked changes against the base (committed AND uncommitted, so a working
    tree edit after the pass invalidates the marker) plus every untracked file,
    because a new script is part of the diff even before it is added.

    Paths stay BYTES the whole way. Decoding them to str and re-encoding is how
    a filename that is not valid UTF-8 - ordinary enough on Linux and macOS -
    raised UnicodeEncodeError here, which check() did not catch and the hook
    turned into an unconditional allow: the gate reporting green with nobody
    having reviewed anything.
    """
    sha = hashlib.sha256()
    sha.update(git(repo, "diff", base, "--", binary=True))
    listing = git(repo, "ls-files", "-o", "--exclude-standard", "-z", binary=True)
    for raw in sorted(p for p in listing.split(NUL_BYTE) if p):
        sha.update(b"\0untracked\0" + raw + b"\0")
        try:
            sha.update((Path(repo) / os.fsdecode(raw)).read_bytes())
        except (OSError, ValueError) as exc:
            # Unreadable, or a name this platform cannot even turn into a path
            # (Windows cannot fsdecode arbitrary bytes). Record the fact and
            # move on: the NAME bytes are already in the digest above, so the
            # file appearing, vanishing or being renamed still invalidates the
            # marker. Crashing here would be worse than useless - the hook
            # catches everything and fails open, so a crash reads as "allow".
            detail = getattr(exc, "strerror", None) or type(exc).__name__
            sha.update(f"<unreadable: {detail}>".encode("utf-8"))
    return sha.hexdigest()


def read_marker(repo):
    try:
        raw = marker_path(repo).read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        # ValueError covers UnicodeDecodeError: two invalid bytes in the
        # marker file used to raise out of check(), and the hook reads a
        # raise as ALLOW (review round 2). Undecodable = no marker.
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        # Legacy marker: a bare HEAD sha, written before content digests.
        return {"head": raw, "digest": None, "base": None, "legacy": True}
    if not isinstance(data, dict):
        # `0`, `[]`, `"x"`, `true` parse as JSON but are not markers. Returning
        # them raw made check() raise, and the hook turns a raise into ALLOW -
        # a one-token forgery (review, B1). Treat as a stale legacy
        # marker: it never matches HEAD, so it blocks.
        return {"head": raw, "digest": None, "base": None, "legacy": True}
    return data


def base_sha_for(repo, base):
    """Merge-base with the base ref, resolved once and stored.

    Storing the ref NAME would re-resolve on every check, so a plain `git
    fetch` after anyone merges to master would invalidate every teammate's
    marker and demand a stated reason for a diff that did not change.
    """
    try:
        return git(repo, "merge-base", base, "HEAD").strip()
    except MarkerError:
        return git(repo, "rev-parse", base).strip()


def write(repo, base=None, reason=None, today=None):
    base = pick_base(repo, base)
    base_sha = base_sha_for(repo, base)
    digest = content_digest(repo, base_sha)
    head = git(repo, "rev-parse", "HEAD").strip()
    previous = read_marker(repo)
    if previous and previous.get("digest") and previous["digest"] != digest:
        if not reason:
            raise MarkerError(
                "the diff changed since the gate ran - re-run the adversarial "
                "pass (step 3) on the CURRENT diff, then mark it with "
                '--reason "<what you re-verified>". Marking without re-running '
                "is how a regression introduced by review fixes reaches review."
            )
    stamp = (today or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "head": head,
        "base": base,
        "base_sha": base_sha,
        "digest": digest,
        "written_at": stamp,
    }
    if reason:
        payload["reason"] = reason
    marker_path(repo).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return payload


def check(repo):
    """(ok, message). ok=False means the push should be blocked."""
    marker = read_marker(repo)
    if marker is None:
        return False, "no marker: the /pre-mr gate has not run for this tree"
    if not isinstance(marker, dict):
        return False, "marker is not an object - re-run the gate"
    head = git(repo, "rev-parse", "HEAD").strip()
    if marker.get("legacy"):
        if marker.get("head") == head:
            return True, "legacy marker (HEAD only) - rewrite it with this script"
        return False, "legacy marker is stale: HEAD moved since the gate ran"
    if not marker.get("digest") or not marker.get("base"):
        return False, "marker is malformed - re-run the gate"
    # base_sha pins the comparison point; markers written before it fall back
    # to the ref name and keep the old (fetch-sensitive) behaviour.
    against = marker.get("base_sha") or marker["base"]
    try:
        digest = content_digest(repo, against)
    except MarkerError as exc:
        return False, f"cannot recompute the digest: {exc}"
    if digest != marker["digest"]:
        return False, (
            "the diff changed since the gate ran "
            f"(marked {marker['digest'][:12]}, now {digest[:12]})"
        )
    if marker.get("head") != head:
        return True, "same content, new commit id - marker still covers this tree"
    return True, "marker covers this tree"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pre_mr_marker.py", description=__doc__)
    ap.add_argument("--repo", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_write = sub.add_parser("write", help="record that the gate passed")
    p_write.add_argument("--base", help="ref the diff is measured against")
    p_write.add_argument("--reason", help="required when re-marking a changed diff")
    sub.add_parser("check", help="does the marker cover the current tree?")
    sub.add_parser("show", help="print the marker")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "write":
            payload = write(args.repo, base=args.base, reason=args.reason)
            print(f"marked {payload['digest'][:12]} (base {payload['base']})")
            return 0
        if args.cmd == "check":
            ok, message = check(args.repo)
            print(("OK: " if ok else "BLOCKED: ") + message)
            return 0 if ok else 1
        marker = read_marker(args.repo)
        print(
            json.dumps(marker, indent=2, ensure_ascii=False) if marker else "no marker"
        )
        return 0
    except MarkerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
