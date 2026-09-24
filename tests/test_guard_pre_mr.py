"""Tests for guard_pre_mr.py, the hook that blocks a push past the gate.

It had none. A review found two bypasses and a false positive in an hour, all
of which are cases below: the component that can block a teammate's push ships
with the input it must fire on AND the input it must not.

stdlib unittest (pytest collects it too).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = next(
    (
        p
        for p in (
            ROOT / ".claude" / "hooks" / "guard_pre_mr.py",
            ROOT / "hooks" / "guard_pre_mr.py",
        )
        if p.is_file()
    ),
    None,
)
MARKER = HOOK.with_name("pre_mr_marker.py") if HOOK else None

BLOCK, ALLOW = 2, 0


def git(repo, *args):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, env=env, check=False
    )


@unittest.skipIf(shutil.which("git") is None, "git not on PATH")
@unittest.skipIf(HOOK is None, "hook not found in this layout")
class GuardCase(unittest.TestCase):
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
        (self.repo / "a.txt").write_text("mine\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "work")

    def verdict(self, command, env=None, hook=None, cwd=None, tool_name="Bash"):
        payload = json.dumps(
            {"tool_name": tool_name, "tool_input": {"command": command}}
        )
        done = subprocess.run(
            [sys.executable, str(hook or HOOK)],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(cwd or self.repo),
            env=dict(os.environ, **(env or {})),
            timeout=20,
        )
        return done.returncode

    def push(self, prefix="", suffix=""):
        return f"{prefix}git push origin feat/x{suffix}"

    # --- must fire -----------------------------------------------------------

    def test_a_plain_push_without_a_marker_is_blocked(self):
        self.assertEqual(self.verdict(self.push()), BLOCK)

    def test_a_dry_run_followed_by_a_real_push_is_blocked(self):
        # Matching only the FIRST segment let the dry run vouch for the push.
        self.assertEqual(
            self.verdict("git push --dry-run origin feat/x && " + self.push()), BLOCK
        )

    def test_a_push_inside_a_powershell_conditional_is_blocked(self):
        # The form this harness prescribes for PowerShell, where && is absent.
        self.assertEqual(
            self.verdict("git status; if ($?) { " + self.push() + " }"), BLOCK
        )

    def test_a_push_in_a_backtick_substitution_is_blocked(self):
        tick = chr(96)
        self.assertEqual(self.verdict("out=" + tick + self.push() + tick), BLOCK)

    def test_a_push_with_git_options_before_it_is_blocked(self):
        self.assertEqual(
            self.verdict("git -c core.pager=cat push origin feat/x"), BLOCK
        )

    # --- must NOT fire -------------------------------------------------------

    def test_a_dry_run_alone_is_allowed(self):
        self.assertEqual(self.verdict("git push --dry-run origin feat/x"), ALLOW)

    def test_a_branch_deletion_is_allowed(self):
        self.assertEqual(self.verdict("git push --delete origin feat/x"), ALLOW)

    def test_an_explicit_bypass_is_allowed(self):
        self.assertEqual(self.verdict("PRE_MR_BYPASS=1 " + self.push()), ALLOW)

    def test_a_quoted_mention_is_not_a_push(self):
        self.assertEqual(self.verdict("echo 'git push origin feat/x'"), ALLOW)

    def test_a_commit_message_containing_the_word_is_not_a_push(self):
        self.assertEqual(self.verdict('git commit -m "ready to push"'), ALLOW)

    def test_a_push_split_by_a_powershell_line_continuation_is_blocked(self):
        # PowerShell joins tokens with a backtick before a newline, and this
        # harness prescribes it for long commands. The detector required push
        # to follow git across whitespace only, so this walked straight past.
        tick = chr(96)
        self.assertEqual(self.verdict("git " + tick + "\npush origin feat/x"), BLOCK)

    def test_a_cd_into_an_unknown_variable_judges_the_current_directory(self):
        # `cd $UNSET` is `cd ""` or a bare `cd`: the shell stays put or goes
        # HOME - the push cannot land in some third repo. Failing open here
        # was the cheapest bypass of all (review round 2). A `-C`
        # with an unresolved variable still fails open: that one really does
        # name a repo we cannot see.
        self.assertEqual(
            self.verdict("cd $NO_SUCH_VAR_FOR_THE_GATE; " + self.push()), BLOCK
        )

    def test_a_variable_assigned_in_the_same_command_is_resolved(self):
        command = f"D={self.repo.as_posix()}; cd $D; " + self.push()
        self.assertEqual(self.verdict(command), BLOCK)

    def test_a_windows_style_variable_is_resolved_from_the_environment(self):
        # %TEMP% and friends are ordinary on Windows; refusing to expand them
        # made the gate skip itself on a routine command.
        self.assertEqual(
            self.verdict(
                "cd %GATE_TEST_REPO%; " + self.push(),
                env={"GATE_TEST_REPO": str(self.repo)},
            ),
            BLOCK,
        )

    # --- review an earlier review: four ways the gate said ALLOW without a marker ---

    def test_git_exe_and_prefixed_spellings_are_judged(self):
        """B3: `git.exe` is this machine's own spelling; sudo/env/path forms
        run the same binary. Each used to slip past the detector -> exit 0."""
        for spelling in (
            "git.exe push origin feat/x",
            "sudo git push origin feat/x",
            "env git push origin feat/x",
            "/usr/bin/git push origin feat/x",
            "C:/Git/bin/git.exe push origin feat/x",
        ):
            with self.subTest(spelling=spelling):
                self.assertEqual(self.verdict(spelling), BLOCK)

    def test_every_push_segment_is_judged(self):
        """B2: a harmless first push (a repo on master) used to vouch for an
        unreviewed second one in the same command."""
        other = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, other, True)
        git(other, "init", "-q")
        git(other, "config", "user.email", "t@t")
        git(other, "config", "user.name", "t")
        (other / "b.txt").write_text("x\n", encoding="utf-8")
        git(other, "add", "-A")
        git(other, "commit", "-qm", "base")
        git(other, "branch", "-M", "master")
        cmd = f"git -C {other.as_posix()} push origin master; " + self.push()
        self.assertEqual(self.verdict(cmd), BLOCK)

    def test_the_bypass_token_inside_a_string_does_not_disarm(self):
        """B4: the bypass used to be a substring test over the whole line."""
        for cmd in (
            'echo "use PRE_MR_BYPASS=1 to skip"; ' + self.push(),
            'git commit -m "PRE_MR_BYPASS=1 note" && ' + self.push(),
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.verdict(cmd), BLOCK)

    def test_an_exported_bypass_is_still_allowed(self):
        self.assertEqual(self.verdict("export PRE_MR_BYPASS=1; " + self.push()), ALLOW)

    def test_a_non_object_marker_is_not_a_marker(self):
        """B1: `0` / `[]` / `"x"` / `true` parse as JSON, made check() raise,
        and the fail-open hook read the raise as ALLOW."""
        for junk in ("0", "[]", '"x"', "true"):
            with self.subTest(junk=junk):
                (self.repo / ".git" / "pre-mr-ok").write_text(junk, encoding="utf-8")
                self.assertEqual(self.verdict(self.push()), BLOCK)

    # --- review round 2 -------------------------------------------

    def other_repo(self, branch, prefix="tmp"):
        other = Path(tempfile.mkdtemp(prefix=prefix))
        self.addCleanup(shutil.rmtree, other, True)
        git(other, "init", "-q")
        git(other, "config", "user.email", "t@t")
        git(other, "config", "user.name", "t")
        (other / "b.txt").write_text("x\n", encoding="utf-8")
        git(other, "add", "-A")
        git(other, "commit", "-qm", "base")
        git(other, "branch", "-M", branch)
        return other.as_posix()

    def test_a_delimiter_inside_a_string_is_not_a_command_position(self):
        """Round 2, finding 1: `;` inside quotes made the token 'command position'."""
        for cmd in (
            'git commit -m "note; PRE_MR_BYPASS=1 applied" && ' + self.push(),
            'echo "step one; PRE_MR_BYPASS=1 here"; ' + self.push(),
            "printf 'x|PRE_MR_BYPASS=1 y'; " + self.push(),
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.verdict(cmd), BLOCK)

    def test_lookalike_bypass_values_do_not_disarm(self):
        for prefix in ("PRE_MR_BYPASS=10 ", "PRE_MR_BYPASS=1x "):
            with self.subTest(prefix=prefix):
                self.assertEqual(self.verdict(prefix + self.push()), BLOCK)

    def test_a_prefix_bypass_covers_only_its_own_command(self):
        """Round 2, finding 7: `X=1 cmd_a; cmd_b` - the shell scopes X to cmd_a."""
        cmd = "PRE_MR_BYPASS=1 git push origin other; " + self.push()
        self.assertEqual(self.verdict(cmd), BLOCK)

    def test_the_real_push_first_is_judged_too(self):
        """Pins EVERY segment, not the last one (the mutation `real[-1:]`
        kept the earlier test green)."""
        master = self.other_repo("master")
        cmd = self.push() + f"; git -C {master} push origin master"
        self.assertEqual(self.verdict(cmd), BLOCK)

    def test_more_spellings_that_still_run_git(self):
        """Round 2, finding 6: case, quoted path with spaces, wrapper options,
        env after a wrapper, and every wrapper word."""
        for spelling in (
            "GIT push origin feat/x",
            "git.EXE push origin feat/x",
            '"C:/Program Files/Git/bin/git.exe" push origin feat/x',
            "env FOO=1 git push origin feat/x",
            "sudo -u me git push origin feat/x",
            "time git push origin feat/x",
            "nohup git push origin feat/x",
            "command git push origin feat/x",
            "winpty git push origin feat/x",
        ):
            with self.subTest(spelling=spelling):
                self.assertEqual(self.verdict(spelling), BLOCK)

    def test_a_cd_inside_a_string_does_not_redirect_the_judged_repo(self):
        """Round 2, finding 8: the cd scanner was quote-unaware too."""
        master = self.other_repo("master")
        cmd = f'echo "step; cd {master}"; ' + self.push()
        self.assertEqual(self.verdict(cmd), BLOCK)

    def test_a_cd_on_its_own_line_is_seen(self):
        """Was S1: multi-line is the Bash tool's normal shape. A cd into a
        master repo on its own line must make the next push ALLOWED - if the
        cd were invisible the gate would judge feat/x and block."""
        master = self.other_repo("master")
        self.assertEqual(self.verdict(f"cd {master}\ngit push origin master"), ALLOW)

    def test_an_undecodable_marker_is_not_a_marker(self):
        """Round 2, finding 2: two invalid bytes raised UnicodeDecodeError out
        of check(), and the fail-open hook read that as ALLOW."""
        (self.repo / ".git" / "pre-mr-ok").write_bytes(b"\xff\xfe")
        self.assertEqual(self.verdict(self.push()), BLOCK)

    def test_the_legacy_path_rejects_a_non_object_marker(self):
        """Round 2, finding 3: the hook's own fallback (digest module absent)
        still did json.loads(raw).get(...) on a non-object -> raise -> ALLOW."""
        lone = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, lone, True)
        shutil.copy(HOOK, lone / "guard_pre_mr.py")  # no pre_mr_marker beside it
        for junk in ("0", "[]", "true"):
            with self.subTest(junk=junk):
                (self.repo / ".git" / "pre-mr-ok").write_text(junk, encoding="utf-8")
                self.assertEqual(
                    self.verdict(self.push(), hook=lone / "guard_pre_mr.py"), BLOCK
                )

    def test_the_legacy_path_rejects_an_undecodable_marker(self):
        """Round 3: read_marker got (OSError, ValueError) in round 2, the
        hook's own fallback reader kept `except OSError` - undecodable bytes
        raised out of judge() and the per-segment fail-open skipped it."""
        lone = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, lone, True)
        shutil.copy(HOOK, lone / "guard_pre_mr.py")  # no pre_mr_marker beside it
        hook = lone / "guard_pre_mr.py"
        head = git(self.repo, "rev-parse", "HEAD").stdout.decode().strip()
        # Control: the fallback IS the code under test here - a bare-HEAD
        # marker is the one thing it accepts. Without this, the case below
        # would pass even if the copy never reached the legacy branch.
        (self.repo / ".git" / "pre-mr-ok").write_text(head, encoding="utf-8")
        self.assertEqual(self.verdict(self.push(), hook=hook), ALLOW)
        (self.repo / ".git" / "pre-mr-ok").write_bytes(b"\xff\xfe")
        self.assertEqual(self.verdict(self.push(), hook=hook), BLOCK)

    # --- review round 3: the cd walk, repo steering, PowerShell ---

    def feat_from_master(self, command):
        """Run `command` with cwd = a repo on MASTER; the command cds/steers
        into self.repo (feat/x, no marker). BLOCK proves the steer was seen."""
        return self.verdict(command, cwd=self.other_repo("master"))

    def test_a_quoted_cd_argument_is_read(self):
        """Round 3 B1: the argument was read from the blanked text, where a
        quoted path is all spaces - so it was never read at all."""
        feat = self.repo.as_posix()
        for q in ('"', "'"):
            with self.subTest(quote=q):
                cmd = f"cd {q}{feat}{q}; git push origin feat/x"
                self.assertEqual(self.feat_from_master(cmd), BLOCK)
        # and the ALLOW direction: a quoted master path with a space in it
        master = self.other_repo("master", prefix="with space ")
        self.assertEqual(self.verdict(f'cd "{master}"; git push origin master'), ALLOW)

    def test_a_cd_followed_by_more_statements_is_still_seen(self):
        """Round 3 B2: `\\S+` glued the `;` onto the path."""
        feat = self.repo.as_posix()
        for cmd in (
            f"cd {feat}; ls; git push origin feat/x",
            f"cd {feat}; echo hi && git push origin feat/x",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.feat_from_master(cmd), BLOCK)

    def test_quote_pairing_follows_the_shell(self):
        """Round 3 B3 asked for the cd between `it's` and `can't` to be seen.
        bash disagrees: from the first apostrophe to the second is ONE quoted
        word, the cd never runs, and the push goes from the cwd - which the
        hook therefore judges (ALLOW from master is the correct verdict)."""
        feat = self.repo.as_posix()
        paired = f"echo it's && cd {feat} && echo can't && git push origin feat/x"
        self.assertEqual(self.feat_from_master(paired), ALLOW)

    def test_an_apostrophe_inside_double_quotes_does_not_unblank_the_string(self):
        """Round 4 B1: the round-3 odd-quote fallback re-read the raw text on
        `"..., don't ..."` and a `cd <master>` inside the string steered the
        verdict to master - ALLOW for a push that lands on feat/x."""
        master = self.other_repo("master")
        cmd = f'git commit -m "wip; cd {master} ok, don\'t care"; ' + self.push()
        self.assertEqual(self.verdict(cmd), BLOCK)

    def test_an_assigned_variable_keeps_its_value_before_a_delimiter(self):
        """Round 4 S1: ASSIGN_RX's `\\S+` swallowed the `;` of `R=/x;`."""
        feat = self.repo.as_posix()
        self.assertEqual(
            self.feat_from_master(f'R={feat}; cd "$R"; git push origin feat/x'), BLOCK
        )
        master = self.other_repo("master")
        self.assertEqual(
            self.verdict(f'R={master}; cd "$R"; git push origin master'), ALLOW
        )

    def test_repo_steering_precedence_follows_git(self):
        """Round 4 S2/S3: --git-dir beats GIT_DIR beats -C; GIT_DIR after the
        verb (a trailing comment) is not steering."""
        feat = self.repo.as_posix()
        master = self.other_repo("master")
        for cmd in (
            f"git -C {master} --git-dir={feat}/.git push origin feat/x",
            f"GIT_DIR={feat}/.git git -C {master} push origin feat/x",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.feat_from_master(cmd), BLOCK)
        trailing = f"git push origin feat/x # GIT_DIR={master}/.git"
        self.assertEqual(self.verdict(trailing), BLOCK)

    def test_work_tree_space_form_still_matches_the_segment(self):
        """Pins the opts grammar: without `--work-tree <dir>` in it the
        segment would not match at all and the push would be invisible."""
        feat = self.repo.as_posix()
        cmd = f"git --work-tree {feat} --git-dir {feat}/.git push origin feat/x"
        self.assertEqual(self.feat_from_master(cmd), BLOCK)

    def test_powershell_bypass_spellings(self):
        """Round 4 S4: the quoted value was blanked before matching, and the
        name is case-insensitive in PowerShell."""
        for cmd in (
            '$env:PRE_MR_BYPASS = "1"; git push origin feat/x',
            "$Env:pre_mr_bypass=1; git push origin feat/x",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.verdict(cmd, tool_name="PowerShell"), ALLOW)

    # --- review round 5 --------------------------------------------

    def test_the_powershell_bypass_spelling_is_a_command_not_a_string(self):
        """Round 5 B1: matched on the raw text, `$env:PRE_MR_BYPASS=1` inside
        a string disarmed the gate - and did so on Bash payloads, where it is
        not even a command."""
        cases = (
            (
                'git commit -m "note; $env:PRE_MR_BYPASS=1 applied" && ' + self.push(),
                "Bash",
            ),
            ("$env:PRE_MR_BYPASS=1; " + self.push(), "Bash"),
            (
                'Write-Host "step; $env:PRE_MR_BYPASS=1 here"; ' + self.push(),
                "PowerShell",
            ),
        )
        for cmd, shell in cases:
            with self.subTest(cmd=cmd, shell=shell):
                self.assertEqual(self.verdict(cmd, tool_name=shell), BLOCK)

    def test_a_dry_run_flag_in_a_trailing_comment_is_not_a_dry_run(self):
        self.assertEqual(self.verdict(self.push(suffix=" # --dry-run")), BLOCK)
        # and a `#` inside a quoted value does not hide a real --dry-run (r6 S2)
        self.assertEqual(self.verdict(self.push(suffix=' -o "x # y" --dry-run')), ALLOW)

    # --- review round 6 --------------------------------------------

    def test_powershell_escaped_quote_cannot_expose_an_in_string_bypass(self):
        """Round 6 B1: rewriting `= "1"` before blanking dropped two quotes and
        re-paired the line; with a backtick-escaped quote the bypass inside
        the string was honoured. The value is now read from the original at
        the offset found on the blanked text."""
        cmd = 'Write-Host "he said `"; $env:PRE_MR_BYPASS = "1" ok"; ' + self.push()
        self.assertEqual(self.verdict(cmd, tool_name="PowerShell"), BLOCK)
        cmd = 'echo "a`" ; $env:PRE_MR_BYPASS = "1" b"; ' + self.push()
        self.assertEqual(self.verdict(cmd, tool_name="PowerShell"), BLOCK)
        # the legal spellings still work
        for ok in (
            "${env:PRE_MR_BYPASS}=1; " + self.push(),
            '$env:PRE_MR_BYPASS = "1"; ' + self.push(),
        ):
            with self.subTest(cmd=ok):
                self.assertEqual(self.verdict(ok, tool_name="PowerShell"), ALLOW)

    def test_an_escaped_quote_does_not_close_a_bash_string(self):
        """Same class as the PowerShell backtick case, bash spelling: `\\"`
        inside a double-quoted string paired with the opener and left
        `; PRE_MR_BYPASS=1` outside the blank."""
        cmd = 'echo "a \\"; PRE_MR_BYPASS=1 \\" b"; ' + self.push()
        self.assertEqual(self.verdict(cmd), BLOCK)
        cmd = 'echo "a \\"; cd ' + self.other_repo("master") + ' \\" b"; ' + self.push()
        self.assertEqual(self.verdict(cmd), BLOCK)

    def test_quote_escapes_are_per_shell(self):
        """Round 7 B1: a bash string ending in a backtick substitution, or a
        PowerShell string ending in a backslash, must still CLOSE - otherwise
        the blank swallows the cd that follows and the wrong repo is judged."""
        feat = self.repo.as_posix()
        bash = f'echo "on `pwd`"; cd {feat}; echo "ok"; git push origin feat/x'
        self.assertEqual(self.feat_from_master(bash), BLOCK)
        ps = f'Write-Host "C:\\proj\\"; cd {feat}; Write-Host "ok"; git push origin feat/x'
        self.assertEqual(
            self.verdict(ps, cwd=self.other_repo("master"), tool_name="PowerShell"),
            BLOCK,
        )

    def test_flags_inside_a_quoted_value_are_not_flags(self):
        self.assertEqual(self.verdict(self.push(suffix=' -o "fix -n flag"')), BLOCK)

    def test_a_command_substitution_in_dash_c_is_unresolvable(self):
        """Round 7 N5: `$(...)` is neither a variable nor a literal path."""
        self.assertEqual(
            self.verdict(
                'git -C "$(cat p.txt)" push origin feat/x',
                cwd=self.other_repo("master"),
            ),
            ALLOW,
        )

    def test_bash_bypass_spellings_are_not_honoured_on_powershell(self):
        """Round 6 S1: `export` is not a cmdlet; the push still runs."""
        for cmd in (
            "export PRE_MR_BYPASS=1; " + self.push(),
            "PRE_MR_BYPASS=1 " + self.push(),
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.verdict(cmd, tool_name="PowerShell"), BLOCK)

    def test_an_ambiguous_export_git_dir_is_additive(self):
        """Round 6 B2: an export in a heredoc, a subshell, before an unset, or
        on a PowerShell payload never applies to the push - the cwd does. The
        hook cannot tell those apart from the text, so it judges BOTH the
        exported repo and the walked one."""
        master = self.other_repo("master")
        cases = (
            (f"cat <<'EOF'\nexport GIT_DIR={master}/.git\nEOF\n" + self.push(), "Bash"),
            (f"( export GIT_DIR={master}/.git; true ); " + self.push(), "Bash"),
            (f"export GIT_DIR={master}/.git; unset GIT_DIR; " + self.push(), "Bash"),
            (f"export GIT_DIR={master}/.git; " + self.push(), "PowerShell"),
        )
        for cmd, shell in cases:
            with self.subTest(cmd=cmd, shell=shell):
                self.assertEqual(self.verdict(cmd, tool_name=shell), BLOCK)

    def test_an_exported_git_dir_steers_the_push(self):
        """Round 5 B3: `export GIT_DIR=<review>/.git; git push` landed feat/x
        on the remote from a master cwd, unseen."""
        feat = self.repo.as_posix()
        cmd = f"export GIT_DIR={feat}/.git; git push origin feat/x"
        self.assertEqual(self.feat_from_master(cmd), BLOCK)

    def test_an_unexported_git_dir_statement_is_not_an_env_prefix(self):
        """Round 5 B4/N3: `GIT_DIR=/x; git push` is a separate statement git
        never sees; ENV_PREFIX's `\\S*` crossed the `;` and steered both ways."""
        master = self.other_repo("master")
        self.assertEqual(
            self.verdict(f"GIT_DIR={master}/.git; git push origin feat/x"), BLOCK
        )
        feat = self.repo.as_posix()
        self.assertEqual(
            self.verdict(f"GIT_DIR={feat}/.git; git push origin master", cwd=master),
            ALLOW,
        )

    def test_an_unresolvable_dash_c_judges_the_cwd(self):
        """Round 5 B5: `git -C ""` is a no-op for git - the cwd pushes."""
        self.assertEqual(
            self.verdict('git -C "$NOPE_VAR_FOR_THE_GATE" push origin feat/x'), BLOCK
        )

    def test_a_redirection_ends_the_cd_argument(self):
        feat = self.repo.as_posix()
        for redir in (">log", "<in"):
            with self.subTest(redir=redir):
                cmd = f"cd {feat}{redir}; git push origin feat/x"
                self.assertEqual(self.feat_from_master(cmd), BLOCK)

    def test_a_backslash_escaped_space_in_a_cd_path(self):
        spaced = self.other_repo("feat/x", prefix="fs pace ")
        escaped = spaced.replace(" ", "\\ ")
        self.assertEqual(
            self.verdict(
                f"cd {escaped}; git push origin feat/x", cwd=self.other_repo("master")
            ),
            BLOCK,
        )

    def test_line_continuation_inside_a_word_and_crlf(self):
        """Round 5 S3/S4: the shell JOINS the pieces around a backslash-newline."""
        feat = self.repo.as_posix()
        inside = f"cd {feat[:-3]}\\\n{feat[-3:]}; git push origin feat/x"
        self.assertEqual(self.feat_from_master(inside), BLOCK)
        crlf = f"cd \\\r\n  {feat}\r\ngit push origin feat/x"
        self.assertEqual(self.feat_from_master(crlf), BLOCK)

    def test_percent_variables_are_literal_in_bash(self):
        """Round 5 S5: bash does not expand %USERPROFILE%; the cd fails and
        the push runs from the cwd."""
        self.assertEqual(self.verdict("cd %USERPROFILE%; " + self.push()), BLOCK)

    def test_cd_double_dash_and_line_continuation(self):
        """Round 4 S5."""
        feat = self.repo.as_posix()
        master = self.other_repo("master")
        self.assertEqual(
            self.feat_from_master(f"cd -- {feat}; git push origin feat/x"), BLOCK
        )
        self.assertEqual(
            self.feat_from_master(f"cd \\\n  {feat}\ngit push origin feat/x"), BLOCK
        )
        self.assertEqual(self.verdict(f"cd -- {master}; git push origin master"), ALLOW)

    def test_git_dir_steering_is_seen(self):
        """Round 3 S1: --git-dir / GIT_DIR name the repo as surely as -C."""
        feat = self.repo.as_posix()
        for cmd in (
            f"git --git-dir={feat}/.git --work-tree={feat} push origin feat/x",
            f"git --git-dir {feat}/.git push origin feat/x",
            f"GIT_DIR={feat}/.git git push origin feat/x",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.feat_from_master(cmd), BLOCK)

    def test_pushd_is_a_cd(self):
        master = self.other_repo("master")
        self.assertEqual(self.verdict(f"pushd {master}; git push origin master"), ALLOW)

    def test_powershell_has_a_bypass_spelling(self):
        """Round 3 S2: the hook accepts PowerShell payloads but printed a
        bash-only escape hatch; on PowerShell the gate was unbypassable."""
        cmd = "$env:PRE_MR_BYPASS=1; git push origin feat/x"
        self.assertEqual(self.verdict(cmd, tool_name="PowerShell"), ALLOW)

    def test_a_wrapper_word_at_a_line_start_in_prose_is_not_a_push(self):
        """Round 3 S3: module-wide IGNORECASE made `Time git push` a push."""
        cmd = 'git commit -m "fix\n\nTime git push was measured"'
        self.assertEqual(self.verdict(cmd), ALLOW)

    def test_a_prefix_bypass_after_the_push_does_not_apply(self):
        """Round 3 N1: pins the seg.end() bound of the prefix scan."""
        cmd = "git push origin feat/x; PRE_MR_BYPASS=1 echo done"
        self.assertEqual(self.verdict(cmd), BLOCK)

    def test_pathological_wrapper_options_do_not_hang(self):
        """Round 3 N2: the option loop backtracked exponentially."""
        import time as _time

        opts = " ".join(f"-o{i}" for i in range(40))
        started = _time.monotonic()
        self.assertEqual(self.verdict(f"env {opts} git-thing push_notes"), ALLOW)
        self.assertLess(_time.monotonic() - started, 5.0)

    def test_a_push_on_master_is_allowed(self):
        git(self.repo, "checkout", "-q", "master")
        self.assertEqual(self.verdict("git push origin master"), ALLOW)

    @unittest.skipIf(MARKER is None or not MARKER.is_file(), "digest module absent")
    def test_a_marker_covering_the_tree_lets_the_push_through(self):
        done = subprocess.run(
            [
                sys.executable,
                str(MARKER),
                "--repo",
                str(self.repo),
                "write",
                "--base",
                "master",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.verdict(self.push()), ALLOW)
        (self.repo / "a.txt").write_text("edited after the gate\n", encoding="utf-8")
        self.assertEqual(self.verdict(self.push()), BLOCK)


@unittest.skipIf(shutil.which("git") is None, "git not on PATH")
@unittest.skipIf(HOOK is None, "hook not found in this layout")
class DocsOnlyExemption(GuardCase):
    """Docs-only exemption: a branch whose whole diff against its base is
    `docs/**/*.md` (the default docs-only prefix) pushes
    without a marker. Everything else keeps the gate - including an EMPTY
    diff and a `.md` that lives outside that tree."""

    def branch_from_master(self, name, files):
        git(self.repo, "checkout", "-q", "master")
        git(self.repo, "checkout", "-q", "-b", name)
        for rel, body in files.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        git(self.repo, "add", "-A")
        if files:
            git(self.repo, "commit", "-qm", "docs")

    def push(self, prefix="", suffix=""):
        return f"{prefix}git push origin HEAD{suffix}"

    # --- must NOT fire -------------------------------------------------------

    def test_a_branch_that_only_adds_docs_markdown_is_allowed(self):
        self.branch_from_master("docs/x", {"docs/docs/specs/a.md": "# a\n"})
        self.assertEqual(self.verdict(self.push()), ALLOW)

    def test_a_deleted_mirror_document_is_still_docs_only(self):
        self.branch_from_master("docs/seed", {"docs/old.md": "x\n"})
        git(self.repo, "checkout", "-q", "master")
        git(self.repo, "merge", "-q", "docs/seed")
        git(self.repo, "checkout", "-q", "-b", "docs/drop")
        git(self.repo, "rm", "-q", "docs/old.md")
        git(self.repo, "commit", "-qm", "drop")
        self.assertEqual(self.verdict(self.push()), ALLOW)

    # --- must fire -----------------------------------------------------------

    def test_markdown_plus_anything_else_keeps_the_gate(self):
        self.branch_from_master(
            "docs/mixed",
            {"docs/docs/a.md": "# a\n", "a.txt": "changed\n"},
        )
        self.assertEqual(self.verdict(self.push()), BLOCK)

    def test_markdown_outside_the_docs_prefix_keeps_the_gate(self):
        self.branch_from_master("docs/readme", {"README.md": "# r\n"})
        self.assertEqual(self.verdict(self.push()), BLOCK)

    def test_a_non_markdown_file_under_the_docs_prefix_keeps_the_gate(self):
        self.branch_from_master("docs/py", {"docs/tool.py": "x = 1\n"})
        self.assertEqual(self.verdict(self.push()), BLOCK)

    def test_an_empty_diff_is_not_docs_only(self):
        self.branch_from_master("docs/empty", {})
        self.assertEqual(self.verdict(self.push()), BLOCK)

    def test_the_path_rule_itself(self):
        sys.path.insert(0, str(HOOK.parent))
        import guard_pre_mr as hook

        ok = hook.docs_only_paths
        self.assertTrue(ok(["docs/docs/specs/a.md", "docs/b.md"]))
        self.assertFalse(ok([]))
        self.assertFalse(ok(["docs/a.md", "hooks/x.py"]))
        self.assertFalse(ok(["notes/a.md"]))
        self.assertFalse(ok(["docs/a.md.bak"]))
        self.assertFalse(ok(["docs2/a.md"]))  # a lookalike prefix


if __name__ == "__main__":
    unittest.main()
