"""Write and check the /pre-mr gate marker.

The marker used to hold a HEAD sha. That is not what the gate verifies: an
`amend` moves HEAD without changing a line, and - the case that actually bit us
in an earlier review - applying review findings CHANGES the diff while the marker gets
rewritten as a mechanical step, so a regression introduced by the fixes reached
the branch with the gate reporting green.

The marker therefore records the CONTENT that a push sends: the tree id of
HEAD. Rewording a commit keeps the tree and the marker; committing a changed
line does not. Re-marking a changed tree is still possible - the gate is a
discipline, not a lock - but it has to be stated: `write` refuses without
--reason, and the reason is kept in the marker so the next reader can see the
content was re-marked rather than re-reviewed.

Earlier the marker held a sha256 over `git diff <base>` of the WORKING
TREE plus every untracked file. A review showed four ways that
measured something other than what gets pushed: `diff.external` / textconv
rewrote the hashed text, an unreviewed commit under a restored working tree
passed, untracked files were listed relative to the cwd, and `git add` of a
reviewed file changed the digest. A push sends HEAD, so HEAD's tree is what
the marker names now - and uncommitted or untracked files are simply not
covered: commit first, then run the gate. `write` REFUSES while tracked files
have uncommitted changes (a pass that read the working tree is not a pass on
HEAD) unless --allow-dirty states that the pass read `<base>...HEAD`, and
prints a note about untracked files.

    python hooks/pre_mr_marker.py write --base origin/master
    python hooks/pre_mr_marker.py write --base origin/master --reason "..."
    python hooks/pre_mr_marker.py check          # exit 0 = marker covers HEAD
    python hooks/pre_mr_marker.py show
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKER_NAME = "pre-mr-ok"
DEFAULT_BASES = ("origin/master", "origin/main", "master", "main")
# An object id as git prints it: sha1 (40) or sha256 (64), lower-case hex.
SHA_RX = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
# Every field a marker may carry is a string. Anything else is not a marker.
STRING_FIELDS = (
    "head",
    "tree",
    "base",
    "base_sha",
    "branch",
    "digest",
    "reason",
    "written_at",
)


class MarkerError(Exception):
    pass


def git(repo, *args):
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
    return done.stdout.decode("utf-8", "replace")


def is_sha(value):
    return isinstance(value, str) and SHA_RX.fullmatch(value) is not None


def marker_path(repo):
    # Absolute, so a marker written with `--repo <subdir>` and one checked from
    # the root are the same file.
    return Path(git(repo, "rev-parse", "--absolute-git-dir").strip()) / MARKER_NAME


def resolve_commit(repo, ref):
    """The commit a ref names, or MarkerError.

    `rev-parse <x>` echoes an unknown flag back as if it were its answer, so
    `--base=--output=/dev/null` used to be stored as the base sha. A base that
    starts with a dash is refused outright, the rest is verified to be a
    commit, and the answer must look like an object id.
    """
    if not isinstance(ref, str) or not ref or ref.startswith("-"):
        raise MarkerError(f"not a ref: {ref!r}")
    try:
        out = git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}").strip()
    except MarkerError:
        raise MarkerError(f"base {ref!r} does not name a commit") from None
    if not is_sha(out):
        raise MarkerError(f"base {ref!r} did not resolve to a commit id")
    return out


def pick_base(repo, given=None):
    if given:
        resolve_commit(repo, given)  # raises if it is not a commit
        return given
    for ref in DEFAULT_BASES:
        try:
            resolve_commit(repo, ref)
            return ref
        except MarkerError:
            continue
    raise MarkerError(
        "no base ref found (tried " + ", ".join(DEFAULT_BASES) + "); pass --base"
    )


def head_tree(repo):
    """Tree id of HEAD - the content `git push` sends for this branch.

    One object id straight from git: no diff text in between, so nothing a
    user's diff configuration (`diff.external`, textconv, colour, prefixes)
    can rewrite, and no working-tree or cwd dependence.
    """
    out = git(repo, "rev-parse", "--verify", "--quiet", "HEAD^{tree}").strip()
    if not is_sha(out):
        raise MarkerError("HEAD has no tree id")
    return out


def dirty_counts(repo):
    """(tracked files with uncommitted changes, untracked files) - what the
    marker does NOT cover. Raises MarkerError when git cannot say: `write`
    refuses on a dirty tree, and a status that failed is not a clean tree
    (a corrupted index used to read as "nothing to refuse")."""
    try:
        out = git(repo, "status", "--porcelain", "--no-renames", "-z")
    except (OSError, subprocess.SubprocessError) as exc:
        raise MarkerError(f"git status failed: {exc}") from exc
    entries = [e for e in out.split(chr(0)) if e]
    untracked = sum(1 for e in entries if e.startswith("??"))
    return len(entries) - untracked, untracked


def uncovered(repo):
    """dirty_counts for the advisory NOTE only: never raises."""
    try:
        return dirty_counts(repo)
    except MarkerError:
        return 0, 0


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
    except (ValueError, RecursionError):
        # Legacy marker: a bare HEAD sha, written before content digests.
        # RecursionError: a file of several thousand `[` is not JSON either,
        # and json.loads says so by exhausting the stack.
        return {"head": raw, "tree": None, "base": None, "legacy": True}
    if not isinstance(data, dict):
        # `0`, `[]`, `"x"`, `true` parse as JSON but are not markers. Returning
        # them raw made check() raise, and the hook turns a raise into ALLOW -
        # a one-token forgery (review, B1). Treat as a stale legacy
        # marker: it never matches HEAD, so it blocks.
        return {"head": raw, "tree": None, "base": None, "legacy": True}
    for field in STRING_FIELDS:
        if field in data and not isinstance(data[field], str):
            # `{"digest": 1}` reached a slice in check() and raised TypeError;
            # same route to ALLOW as the non-object case (found in review).
            return {"malformed": True}
    return data


def base_sha_for(repo, base):
    """Merge-base with the base ref, resolved once and stored for the reader:
    it says what the reviewed diff was measured against. The verdict does not
    depend on it - HEAD's tree does not change when master moves.
    """
    sha = resolve_commit(repo, base)
    try:
        merged = git(repo, "merge-base", sha, "HEAD").strip()
    except MarkerError:
        return sha  # unrelated histories: the base itself is the best answer
    return merged if is_sha(merged) else sha


def current_branch(repo):
    try:
        return git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    except MarkerError:
        return ""


def write(repo, base=None, reason=None, today=None, allow_dirty=False):
    base = pick_base(repo, base)
    base_sha = base_sha_for(repo, base)
    tree = head_tree(repo)
    head = git(repo, "rev-parse", "HEAD").strip()
    branch = current_branch(repo)
    tracked, _ = dirty_counts(repo)
    if tracked and not allow_dirty:
        # The marker names HEAD. With tracked changes not committed, the pass
        # may have read the working tree: commit the unreviewed state, fix it
        # in the editor, review what the editor shows, mark - and the unfixed
        # HEAD goes out green.
        raise MarkerError(
            f"{tracked} tracked file(s) have uncommitted changes, and the "
            "marker covers HEAD only. Commit (or stash) them and run the pass "
            "on the committed diff; if the pass DID read `<base>...HEAD` and "
            "the changes are unrelated work in progress, say so with "
            "--allow-dirty."
        )
    previous = read_marker(repo)
    # The marker file is one per git-dir, not one per branch, so the first
    # write on a NEW branch also meets a different tree and needs a reason
    # ("new branch" is one). Exempting a marker left by another branch was
    # tried on 2026-10-05 and withdrawn: mark A, mark B, come back to A with
    # new commits - and the re-mark of A asked for nothing. `branch` is stored
    # for the reader only.
    # A marker of an EARLIER format (a working-tree `digest`, or a bare HEAD
    # sha) holds no tree id, so the commit id it recorded is compared instead:
    # the same commit needs no reason, anything else does. Waiving the reason
    # for the first write after the upgrade (first cut, 2026-10-05) reopened
    # the 2026-09-03 case once per clone - and check() tells the user to do
    # exactly that write.
    changed = False
    if previous and not previous.get("malformed"):
        if is_sha(previous.get("tree")):
            changed = previous["tree"] != tree
        elif isinstance(previous.get("head"), str):
            changed = previous["head"] != head
    if changed:
        if not reason:
            raise MarkerError(
                "the committed content changed since the gate ran - re-run the "
                "adversarial pass (step 3) on the CURRENT diff, then mark it "
                'with --reason "<what you re-verified>". Marking without '
                "re-running is how a regression introduced by review fixes "
                "reaches review."
            )
    stamp = (today or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "head": head,
        "base": base,
        "base_sha": base_sha,
        "tree": tree,
        "branch": branch,
        "written_at": stamp,
    }
    if reason:
        payload["reason"] = reason
    marker_path(repo).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return payload


def check(repo):
    """(ok, message). ok=False means the push should be blocked.

    Never raises: the hook that calls this turns any exception into ALLOW, so
    whatever goes wrong in here - a git that times out, a marker file that
    breaks the parser in a way nobody listed - has to come back as a verdict.
    """
    try:
        return _check(repo)
    except Exception as exc:  # noqa: BLE001 - see the docstring
        return False, f"cannot evaluate the marker ({type(exc).__name__}: {exc})"


def _check(repo):
    try:
        marker = read_marker(repo)
    except MarkerError as exc:
        # e.g. a git too old for --absolute-git-dir: a raise from here would
        # reach the hook's catch-all and read as ALLOW.
        return False, f"cannot locate the marker: {exc}"
    if marker is None:
        return False, "no marker: the /pre-mr gate has not run for this tree"
    if not isinstance(marker, dict) or marker.get("malformed"):
        return False, "marker is malformed - re-run the gate"
    try:
        head = git(repo, "rev-parse", "HEAD").strip()
    except MarkerError as exc:
        return False, f"cannot read HEAD: {exc}"
    if marker.get("legacy"):
        if marker.get("head") == head:
            return True, "legacy marker (HEAD only) - rewrite it with this script"
        return False, "legacy marker is stale: HEAD moved since the gate ran"
    if not is_sha(marker.get("tree")):
        if marker.get("digest"):
            return False, (
                "marker predates the tree-keyed format (it hashed the working "
                "tree, not what a push sends) - commit, re-run the gate and "
                "write the marker again (with --reason if HEAD moved since)"
            )
        return False, "marker is malformed - re-run the gate"
    try:
        tree = head_tree(repo)
    except MarkerError as exc:
        return False, f"cannot read the tree of HEAD: {exc}"
    if tree != marker["tree"]:
        return False, (
            "the committed content changed since the gate ran "
            f"(marked tree {marker['tree'][:12]}, HEAD is {tree[:12]})"
        )
    if marker.get("head") != head:
        return True, "same content, new commit id - marker still covers HEAD"
    return True, "marker covers HEAD"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pre_mr_marker.py", description=__doc__)
    ap.add_argument("--repo", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_write = sub.add_parser("write", help="record that the gate passed")
    p_write.add_argument("--base", help="ref the diff is measured against")
    p_write.add_argument("--reason", help="required when re-marking changed content")
    p_write.add_argument(
        "--allow-dirty",
        action="store_true",
        help="tracked files have uncommitted changes, and the pass read "
        "<base>...HEAD, not the working tree",
    )
    sub.add_parser("check", help="does the marker cover HEAD?")
    sub.add_parser("show", help="print the marker")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "write":
            payload = write(
                args.repo,
                base=args.base,
                reason=args.reason,
                allow_dirty=args.allow_dirty,
            )
            print(f"marked tree {payload['tree'][:12]} (base {payload['base']})")
            tracked, untracked = uncovered(args.repo)
            if tracked or untracked:
                print(
                    f"NOTE: {tracked} tracked file(s) with uncommitted changes and "
                    f"{untracked} untracked file(s) are NOT covered - the marker "
                    "names HEAD, which is what a push sends. If the pass read "
                    "them, commit and mark again.",
                    file=sys.stderr,
                )
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
