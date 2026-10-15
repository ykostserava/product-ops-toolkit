"""Tests for pre_mr_marker.py.

The gate marker exists to stop one specific thing: applying review findings,
rewriting the marker as a mechanical step, and pushing content nobody reviewed.
Each case names the input the guard must fire on, or must not.

stdlib unittest on purpose: runs under `unittest discover` and under pytest.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT / "hooks", ROOT / ".claude" / "hooks", ROOT / "scripts"):
    if candidate.is_dir():
        sys.path.insert(0, str(candidate))

import pre_mr_marker as marker  # noqa: E402


def needs_git(cls):
    """Skip without git - unless the environment says git MUST be there.

    CI sets PRE_MR_REQUIRE_GIT=1: an image that lost git would otherwise turn
    this whole file into skips and the job would be green having run nothing.
    Raising at import makes `unittest discover` fail loudly instead.
    """
    if shutil.which("git") is not None:
        return cls
    if os.environ.get("PRE_MR_REQUIRE_GIT") == "1":
        raise RuntimeError(
            "PRE_MR_REQUIRE_GIT=1 but git is not on PATH - these tests would "
            "all skip and the job would report green without running them"
        )
    return unittest.skip("git not on PATH")(cls)


def git(repo, *args):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, env=env, check=False
    )


@needs_git
class MarkerCase(unittest.TestCase):
    """A branch with one commit on top of master."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@t")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "a.txt").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "branch", "-M", "master")
        git(self.repo, "checkout", "-q", "-b", "feat/x")
        (self.repo / "a.txt").write_text("changed\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "work")

    def edit(self, text):
        (self.repo / "a.txt").write_text(text, encoding="utf-8")

    def commit(self, text, message="more"):
        self.edit(text)
        done = git(self.repo, "commit", "-qam", message)
        self.assertEqual(done.returncode, 0, done.stderr)

    def stored(self):
        return json.loads(marker.marker_path(self.repo).read_text(encoding="utf-8"))

    def test_no_marker_blocks(self):
        ok, message = marker.check(self.repo)
        self.assertFalse(ok)
        self.assertIn("has not run", message)

    def test_a_fresh_marker_covers_head(self):
        marker.write(self.repo, base="master")
        ok, _ = marker.check(self.repo)
        self.assertTrue(ok)

    def test_amend_without_content_change_keeps_the_marker(self):
        # The benign case: rewording a commit is not new content, and forcing
        # a re-review there would train people to bypass the gate.
        marker.write(self.repo, base="master")
        git(self.repo, "commit", "-q", "--amend", "-m", "reworded")
        ok, message = marker.check(self.repo)
        self.assertTrue(ok)
        self.assertIn("new commit id", message)

    def test_the_base_moving_does_not_invalidate_the_marker(self):
        # The input this guard must NOT fire on, and the one people hit daily:
        # someone else merges to master, you fetch, your branch is untouched.
        marker.write(self.repo, base="master")
        git(self.repo, "checkout", "-q", "master")
        (self.repo / "theirs.txt").write_text("their work\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "someone else")
        git(self.repo, "checkout", "-q", "feat/x")
        ok, message = marker.check(self.repo)
        self.assertTrue(ok, message)

    def test_a_committed_change_after_marking_blocks(self):
        # THE must-fire input: review findings committed after the gate ran.
        marker.write(self.repo, base="master")
        self.commit("fixed after review\n")
        ok, message = marker.check(self.repo)
        self.assertFalse(ok)
        self.assertIn("content changed", message)

    def test_a_newly_committed_file_blocks(self):
        marker.write(self.repo, base="master")
        (self.repo / "new_helper.py").write_text("x = 1\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "helper")
        ok, message = marker.check(self.repo)
        self.assertFalse(ok)
        self.assertIn("content changed", message)

    # --- a review: the marker names what a push SENDS ----------------------

    def test_an_unreviewed_commit_under_a_restored_working_tree_blocks(self):
        # The digest used to be taken from the working tree. Commit something
        # unreviewed, put the working tree back to the reviewed text, and the
        # old digest matched while the push carried the unreviewed commit.
        marker.write(self.repo, base="master")
        self.commit("unreviewed\n")
        self.edit("changed\n")  # the working tree is the reviewed text again
        ok, message = marker.check(self.repo)
        self.assertFalse(ok, "HEAD carries an unreviewed commit")
        self.assertIn("content changed", message)

    def test_uncommitted_and_untracked_files_do_not_change_the_verdict(self):
        # They are not pushed. The other direction of the case above, and the
        # daily one in a repo with standing work in progress: the marker must
        # not demand a --reason for files the push does not carry.
        marker.write(self.repo, base="master")
        self.edit("work in progress, not committed\n")
        (self.repo / "scratch.py").write_text("x = 1\n", encoding="utf-8")
        ok, message = marker.check(self.repo)
        self.assertTrue(ok, message)

    def test_adding_and_committing_other_files_is_seen_adding_alone_is_not(self):
        # `git add` of a file used to move it between two sections of the old
        # digest, so gate -> add -> commit always needed a --reason. Now the
        # index is not part of the marker at all; the commit is what counts.
        (self.repo / "later.py").write_text("x = 1\n", encoding="utf-8")
        marker.write(self.repo, base="master")
        git(self.repo, "add", "later.py")
        ok, message = marker.check(self.repo)
        self.assertTrue(ok, message)
        git(self.repo, "commit", "-qm", "later")
        ok, _ = marker.check(self.repo)
        self.assertFalse(ok, "a commit made after the gate is new content")

    def test_an_external_diff_driver_cannot_hide_a_change(self):
        # With `diff.external` set (difftastic users) plain `git diff` printed
        # whatever the driver printed, so the old digest did not move when the
        # content did. A tree id does not pass through a diff at all.
        git(self.repo, "config", "diff.external", "true")
        marker.write(self.repo, base="master")
        self.commit("changed behind an external diff\n")
        ok, message = marker.check(self.repo)
        self.assertFalse(ok, message)

    def test_the_marker_is_the_same_from_a_subdirectory(self):
        # `--repo <subdir>`: the old untracked listing was relative to the
        # cwd, so a marker written in one directory did not hold in another.
        sub = self.repo / "pkg"
        sub.mkdir()
        (sub / "m.py").write_text("x = 1\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "pkg")
        marker.write(sub, base="master")
        ok, message = marker.check(self.repo)
        self.assertTrue(ok, message)
        self.assertEqual(marker.marker_path(sub), marker.marker_path(self.repo))
        self.commit("after\n")
        ok, _ = marker.check(sub)
        self.assertFalse(ok)

    def test_a_base_spelled_like_a_flag_is_refused(self):
        # `rev-parse` echoes an unknown flag back, so this used to be stored
        # as the base sha and every later comparison ran against nonsense.
        for bad in ("--output=/dev/null", "-n", "--all", "no-such-ref"):
            with self.subTest(base=bad):
                with self.assertRaises(marker.MarkerError):
                    marker.write(self.repo, base=bad)
                self.assertFalse(marker.marker_path(self.repo).exists())

    def test_the_stored_base_sha_is_an_object_id(self):
        payload = marker.write(self.repo, base="master")
        self.assertTrue(marker.is_sha(payload["base_sha"]))
        self.assertTrue(marker.is_sha(payload["tree"]))
        self.assertEqual(
            payload["base_sha"],
            git(self.repo, "rev-parse", "master").stdout.decode().strip(),
        )

    def test_wrong_typed_fields_block_instead_of_raising(self):
        # `{"digest": 1}` raised TypeError out of check(); the hook catches
        # everything and reads a raise as ALLOW. The slice that raised is gone
        # with the digest; what this pins now is that NO field of the wrong
        # type gets as far as a comparison - the marker is rejected whole.
        good = marker.write(self.repo, base="master")
        for field, value in (
            ("digest", 1),
            ("tree", 1),
            ("tree", ["x"]),
            ("tree", None),
            ("head", 5),
            ("base", {}),
            ("base_sha", 0),
            ("branch", 5),
            ("tree", "not-hex"),
            ("tree", good["tree"].upper()),
            ("tree", good["tree"] + "\n"),
        ):
            with self.subTest(field=field, value=value):
                broken = dict(good, **{field: value})
                marker.marker_path(self.repo).write_text(
                    json.dumps(broken), encoding="utf-8"
                )
                ok, message = marker.check(self.repo)  # must not raise
                self.assertFalse(ok, message)

    def test_a_marker_of_the_previous_format_blocks_and_says_why(self):
        # Written before 2026-10-05: a working-tree digest, no tree id.
        marker.marker_path(self.repo).write_text(
            json.dumps({"head": "x", "base": "master", "digest": "ab" * 32}),
            encoding="utf-8",
        )
        ok, message = marker.check(self.repo)
        self.assertFalse(ok)
        self.assertIn("predates", message)

    def test_the_first_write_after_the_upgrade_compares_commit_ids(self):
        # An earlier-format marker has no tree id. Waiving the reason for it
        # (first cut) reopened the 2026-09-03 case once per clone: old marker,
        # new commits, `write` - nothing asked. The commit id it recorded is
        # compared instead; a bare-sha legacy marker gets the same rule.
        head = marker.git(self.repo, "rev-parse", "HEAD").strip()
        path = marker.marker_path(self.repo)
        for stale in (
            json.dumps({"head": "0" * 40, "base": "master", "digest": "ab" * 32}),
            "0" * 40,
        ):
            with self.subTest(marker=stale[:20], head="moved"):
                path.write_text(stale, encoding="utf-8")
                with self.assertRaises(marker.MarkerError):
                    marker.write(self.repo, base="master")
                marker.write(self.repo, base="master", reason="re-ran the pass")
                self.assertTrue(marker.check(self.repo)[0])
        for same in (
            json.dumps({"head": head, "base": "master", "digest": "ab" * 32}),
            head,
        ):
            with self.subTest(marker=same[:20], head="same"):
                path.write_text(same, encoding="utf-8")
                marker.write(self.repo, base="master")  # same commit: no reason
                self.assertTrue(marker.check(self.repo)[0])

    def test_check_returns_a_verdict_whatever_breaks(self):
        # The hook reads ANY exception from check() as ALLOW. Two that were
        # not on anyone's list: a marker that exhausts the JSON parser's
        # stack, and a git call that times out.
        marker.write(self.repo, base="master")
        marker.marker_path(self.repo).write_text("[" * 50000, encoding="utf-8")
        ok, message = marker.check(self.repo)
        self.assertFalse(ok, message)
        marker.marker_path(self.repo).unlink()
        marker.write(self.repo, base="master")
        self.assertTrue(marker.check(self.repo)[0])
        real_git = marker.git

        def slow(repo, *args):
            raise subprocess.TimeoutExpired(cmd="git", timeout=30)

        marker.git = slow
        self.addCleanup(setattr, marker, "git", real_git)
        ok, message = marker.check(self.repo)
        self.assertFalse(ok, message)
        self.assertIn("TimeoutExpired", message)

    def test_write_refuses_when_git_status_cannot_be_read(self):
        # A status that failed is not a clean tree: with a corrupted index the
        # dirty refusal used to read "0 tracked changes" and mark anyway.
        self.edit("not committed\n")
        real_git = marker.git

        def no_status(repo, *args):
            if args[:1] == ("status",):
                raise marker.MarkerError("git status failed: index file corrupt")
            return real_git(repo, *args)

        marker.git = no_status
        self.addCleanup(setattr, marker, "git", real_git)
        with self.assertRaises(marker.MarkerError):
            marker.write(self.repo, base="master")
        self.assertEqual(marker.uncovered(self.repo), (0, 0))  # the NOTE stays advisory

    def test_remarking_changed_content_needs_a_stated_reason(self):
        marker.write(self.repo, base="master")
        self.commit("fixed after review\n")
        with self.assertRaises(marker.MarkerError) as caught:
            marker.write(self.repo, base="master")
        self.assertIn("adversarial pass", str(caught.exception))
        payload = marker.write(self.repo, base="master", reason="re-ran the pass")
        self.assertEqual(payload["reason"], "re-ran the pass")
        ok, _ = marker.check(self.repo)
        self.assertTrue(ok)

    def test_the_reason_is_kept_so_a_reader_can_see_it(self):
        marker.write(self.repo, base="master")
        self.commit("again\n")
        marker.write(self.repo, base="master", reason="verified by hand")
        stored = self.stored()
        self.assertEqual(stored["reason"], "verified by hand")
        self.assertEqual(stored["base"], "master")

    def test_a_legacy_head_only_marker_still_works_but_says_so(self):
        head = marker.git(self.repo, "rev-parse", "HEAD").strip()
        marker.marker_path(self.repo).write_text(head + "\n", encoding="utf-8")
        ok, message = marker.check(self.repo)
        self.assertTrue(ok)
        self.assertIn("legacy", message)
        self.commit("moved on\n")
        ok, message = marker.check(self.repo)
        self.assertFalse(ok)
        self.assertIn("stale", message)

    def test_a_non_object_marker_blocks_instead_of_raising(self):
        """Review B1: a raise here reads as ALLOW in the hook."""
        for junk in ("0", "[]", '"x"', "true"):
            with self.subTest(junk=junk):
                marker.marker_path(self.repo).write_text(junk, encoding="utf-8")
                ok, msg = marker.check(self.repo)
                self.assertFalse(ok, msg)

    def test_an_undecodable_marker_reads_as_no_marker(self):
        marker.marker_path(self.repo).write_bytes(b"\xff\xfe")
        self.assertIsNone(marker.read_marker(self.repo))
        ok, msg = marker.check(self.repo)
        self.assertFalse(ok, msg)

    def test_cli_exit_codes(self):
        # Quiet: a green CI run must not print BLOCKED lines from a passing test.
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))
        repo = str(self.repo)
        self.assertEqual(marker.main(["--repo", repo, "check"]), 1)
        self.assertEqual(marker.main(["--repo", repo, "write", "--base", "master"]), 0)
        self.assertEqual(marker.main(["--repo", repo, "check"]), 0)
        self.commit("changed again\n")
        self.assertEqual(marker.main(["--repo", repo, "check"]), 1)
        self.assertEqual(marker.main(["--repo", repo, "write", "--base", "master"]), 1)
        self.assertEqual(
            marker.main(["--repo", repo, "write", "--base=--output=/dev/null"]), 1
        )

    def test_write_refuses_a_dirty_tree_unless_told_the_pass_read_head(self):
        # The mirror of the restored-working-tree case: commit the unreviewed
        # state, fix it in the editor, review what the editor shows, mark. The
        # marker names HEAD - the unfixed one - and the push is green. So a
        # tracked change that is not committed stops `write`, and overriding
        # it is a statement (--allow-dirty), not a default.
        self.edit("not committed\n")
        (self.repo / "scratch.py").write_text("x = 1\n", encoding="utf-8")
        self.assertEqual(marker.uncovered(self.repo), (1, 1))
        with self.assertRaises(marker.MarkerError) as caught:
            marker.write(self.repo, base="master")
        self.assertIn("uncommitted", str(caught.exception))
        self.assertFalse(marker.marker_path(self.repo).exists())
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            refused = marker.main(
                ["--repo", str(self.repo), "write", "--base", "master"]
            )
            code = marker.main(
                ["--repo", str(self.repo), "write", "--base", "master", "--allow-dirty"]
            )
        self.assertEqual(refused, 1)
        self.assertEqual(code, 0)
        self.assertIn("NOT covered", err.getvalue())

    def test_untracked_files_alone_do_not_stop_write(self):
        # They cannot be what HEAD carries; a scratch file must not demand a flag.
        (self.repo / "scratch.py").write_text("x = 1\n", encoding="utf-8")
        marker.write(self.repo, base="master")
        self.assertTrue(marker.check(self.repo)[0])

    def test_another_branch_in_between_does_not_waive_the_reason(self):
        # One marker file per git-dir. Exempting "a marker left by another
        # branch" (tried 2026-10-05) let this through: mark feat/x, mark
        # feat/y, come back to feat/x with new commits, re-mark - no reason
        # asked. The cost of NOT exempting is known and accepted: the first
        # write on a new branch states a reason too.
        marker.write(self.repo, base="master")
        git(self.repo, "checkout", "-q", "-b", "feat/y", "master")
        (self.repo / "b.txt").write_text("other work\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "y")
        self.assertFalse(marker.check(self.repo)[0], "feat/x's marker is not feat/y's")
        with self.assertRaises(marker.MarkerError):
            marker.write(self.repo, base="master")
        payload = marker.write(self.repo, base="master", reason="new branch, pass ran")
        self.assertEqual(payload["branch"], "feat/y")
        git(self.repo, "checkout", "-q", "feat/x")
        self.commit("fixed after review\n")
        with self.assertRaises(marker.MarkerError):
            marker.write(self.repo, base="master")

    def test_write_says_what_it_does_not_cover(self):
        (self.repo / "scratch.py").write_text("x = 1\n", encoding="utf-8")
        self.edit("not committed\n")
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = marker.main(
                ["--repo", str(self.repo), "write", "--base", "master", "--allow-dirty"]
            )
        self.assertEqual(code, 0)
        self.assertIn("NOT covered", err.getvalue())
        # and stays quiet on a clean tree
        git(self.repo, "checkout", "-q", "--", "a.txt")
        (self.repo / "scratch.py").unlink()
        self.assertEqual(marker.uncovered(self.repo), (0, 0))
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            marker.main(["--repo", str(self.repo), "write", "--base", "master"])
        self.assertEqual(err.getvalue(), "")

    def test_base_is_discovered_when_not_given(self):
        self.assertEqual(marker.write(self.repo)["base"], "master")


if __name__ == "__main__":
    unittest.main()
