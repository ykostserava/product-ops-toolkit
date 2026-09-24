"""Tests for pre_mr_marker.py.

The gate marker exists to stop one specific thing: applying review findings,
rewriting the marker as a mechanical step, and pushing a diff nobody reviewed.
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


def git(repo, *args):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, env=env, check=False
    )


@unittest.skipIf(shutil.which("git") is None, "git not on PATH")
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

    def test_no_marker_blocks(self):
        ok, message = marker.check(self.repo)
        self.assertFalse(ok)
        self.assertIn("has not run", message)

    def test_a_fresh_marker_covers_the_tree(self):
        marker.write(self.repo, base="master")
        ok, _ = marker.check(self.repo)
        self.assertTrue(ok)

    def test_amend_without_content_change_keeps_the_marker(self):
        # The benign case: rewording a commit is not a new diff, and forcing a
        # re-review there would train people to bypass the gate.
        marker.write(self.repo, base="master")
        git(self.repo, "commit", "-q", "--amend", "-m", "reworded")
        ok, message = marker.check(self.repo)
        self.assertTrue(ok)
        self.assertIn("new commit id", message)

    def test_the_base_moving_does_not_invalidate_the_marker(self):
        # The input this guard must NOT fire on, and the one people hit daily:
        # someone else merges to master, you fetch, your diff is untouched.
        # Re-resolving the base ref on every check would demand a stated reason
        # for a change that is not yours.
        marker.write(self.repo, base="master")
        git(self.repo, "checkout", "-q", "master")
        (self.repo / "theirs.txt").write_text("their work\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "someone else")
        git(self.repo, "checkout", "-q", "feat/x")
        ok, message = marker.check(self.repo)
        self.assertTrue(ok, message)

    def test_a_content_change_after_marking_blocks(self):
        # THE must-fire input: review findings applied after the gate ran.
        marker.write(self.repo, base="master")
        self.edit("fixed after review\n")
        ok, message = marker.check(self.repo)
        self.assertFalse(ok)
        self.assertIn("diff changed", message)

    def test_a_new_untracked_file_blocks(self):
        # A new script is part of the diff before it is ever `git add`ed.
        marker.write(self.repo, base="master")
        (self.repo / "new_helper.py").write_text("x = 1\n", encoding="utf-8")
        ok, message = marker.check(self.repo)
        self.assertFalse(ok)
        self.assertIn("diff changed", message)

    def test_a_non_ascii_untracked_file_is_covered(self):
        # git C-quotes such a name unless -z is used; the quoted string is not
        # a file, so its CONTENT was never hashed and editing it after the gate
        # changed nothing. The name alone is not enough.
        scratch = self.repo / "caf\u00e9-\u0441\u0447\u0451\u0442.py"
        scratch.write_text("T = 10\n", encoding="utf-8")
        marker.write(self.repo, base="master")
        scratch.write_text("T = 999  # added after the review\n", encoding="utf-8")
        ok, message = marker.check(self.repo)
        self.assertFalse(ok, "editing a non-ASCII untracked file must invalidate")
        self.assertIn("diff changed", message)

    def test_remarking_a_changed_diff_needs_a_stated_reason(self):
        marker.write(self.repo, base="master")
        self.edit("fixed after review\n")
        with self.assertRaises(marker.MarkerError) as caught:
            marker.write(self.repo, base="master")
        self.assertIn("adversarial pass", str(caught.exception))
        payload = marker.write(self.repo, base="master", reason="re-ran the pass")
        self.assertEqual(payload["reason"], "re-ran the pass")
        ok, _ = marker.check(self.repo)
        self.assertTrue(ok)

    def test_the_reason_is_kept_so_a_reader_can_see_it(self):
        marker.write(self.repo, base="master")
        self.edit("again\n")
        marker.write(self.repo, base="master", reason="verified by hand")
        stored = json.loads(marker.marker_path(self.repo).read_text(encoding="utf-8"))
        self.assertEqual(stored["reason"], "verified by hand")
        self.assertEqual(stored["base"], "master")

    def test_a_legacy_head_only_marker_still_works_but_says_so(self):
        head = marker.git(self.repo, "rev-parse", "HEAD").strip()
        marker.marker_path(self.repo).write_text(head + "\n", encoding="utf-8")
        ok, message = marker.check(self.repo)
        self.assertTrue(ok)
        self.assertIn("legacy", message)
        self.edit("moved on\n")
        git(self.repo, "commit", "-qam", "more")
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
        repo = str(self.repo)
        self.assertEqual(marker.main(["--repo", repo, "check"]), 1)
        self.assertEqual(marker.main(["--repo", repo, "write", "--base", "master"]), 0)
        self.assertEqual(marker.main(["--repo", repo, "check"]), 0)
        self.edit("changed again\n")
        self.assertEqual(marker.main(["--repo", repo, "check"]), 1)
        self.assertEqual(marker.main(["--repo", repo, "write", "--base", "master"]), 1)

    def test_base_is_discovered_when_not_given(self):
        self.assertEqual(marker.write(self.repo)["base"], "master")


if __name__ == "__main__":
    unittest.main()
