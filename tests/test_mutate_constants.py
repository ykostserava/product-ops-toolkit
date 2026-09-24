"""Tests for mutate_constants.py.

The sweep exists because judgement picks a constant and misses its neighbour.
So these cases check the two things that make it trustworthy: it finds the
constants that matter (and only those), and it puts the file back.

stdlib unittest on purpose: runs under `unittest discover` and under pytest.
"""

import contextlib
import io
import subprocess
import py_compile
import os
import importlib.util
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (
    ROOT / "skills" / "pre-mr" / "scripts",
    ROOT / "scripts",
):
    if candidate.is_dir():
        sys.path.insert(0, str(candidate))

import mutate_constants as mc  # noqa: E402


class LiteralDetection(unittest.TestCase):
    def test_js_literals_skip_comments_and_strings(self):
        src = (
            "// x = 42 comment\n"
            "const a = 5.5\n"
            'const s = "text 99 here"\n'
            "const t = 'more 77'\n"
            "/* block 88 */\n"
            "const b = 16\n"
        )
        self.assertEqual([t for _, _, t in mc.js_literals(src)], ["5.5", "16"])

    def test_python_literals_skip_strings_and_comments(self):
        src = 'X = 5\nS = "not 99"\n# also not 88\nY = 0.25\n'
        self.assertEqual([t for _, _, t in mc.python_literals(src)], ["5", "0.25"])


class MutantChoice(unittest.TestCase):
    def test_trivial_constants_are_not_mutated(self):
        for trivial in ("0", "1"):
            with self.subTest(value=trivial):
                self.assertEqual(mc.mutants_of(trivial), [])

    def test_int_mutants_step_by_one(self):
        self.assertEqual(mc.mutants_of("16"), ["17", "15"])

    def test_float_mutants_include_a_fine_and_a_coarse_step(self):
        got = mc.mutants_of("0.5")
        self.assertIn("0.501", got)  # fine: catches a hair's move
        self.assertIn("0.499", got)
        self.assertIn("0.6", got)  # coarse: catches a real change
        self.assertIn("0.4", got)


class Sweep(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def fixture(self, guarded_only):
        """Two constants, and a checker that pins only the first."""
        target = self.dir / "code.py"
        target.write_text("THRESHOLD = 10\nSPARE = 20\n", encoding="utf-8")
        checker = self.dir / "check.py"
        condition = "'THRESHOLD = 10' in s"
        if not guarded_only:
            condition += " and 'SPARE = 20' in s"
        checker.write_text(
            "import sys\n"
            f"s = open(r'{target}', encoding='utf-8').read()\n"
            f"sys.exit(0 if {condition} else 1)\n",
            encoding="utf-8",
        )
        return target, f'"{sys.executable}" "{checker}"'

    def test_reports_the_unguarded_constant_and_restores_the_file(self):
        target, command = self.fixture(guarded_only=True)
        before = target.read_bytes()
        results = mc.sweep(str(target), command, cwd=str(self.dir))
        survived = {(text, repl) for _, text, repl, caught in results if not caught}
        self.assertIn(("20", "21"), survived, "SPARE is unguarded, must be reported")
        self.assertFalse(
            [1 for _, text, _, caught in results if text == "10" and not caught]
        )
        self.assertEqual(target.read_bytes(), before, "target must be restored")

    def test_everything_caught_when_the_tests_pin_both(self):
        target, command = self.fixture(guarded_only=False)
        results = mc.sweep(str(target), command, cwd=str(self.dir))
        self.assertTrue(results)
        self.assertTrue(all(caught for *_, caught in results))

    def test_a_red_baseline_aborts_instead_of_calling_every_mutant_caught(self):
        target = self.dir / "code.py"
        target.write_text("THRESHOLD = 10\n", encoding="utf-8")
        failing = f'"{sys.executable}" -c "raise SystemExit(1)"'
        with self.assertRaises(SystemExit) as caught:
            mc.sweep(str(target), failing, cwd=str(self.dir))
        self.assertIn("baseline is RED", str(caught.exception))
        self.assertEqual(target.read_text(encoding="utf-8"), "THRESHOLD = 10\n")

    def test_the_file_is_restored_even_when_the_test_command_explodes(self):
        target = self.dir / "code.py"
        target.write_text("THRESHOLD = 10\n", encoding="utf-8")
        before = target.read_bytes()
        calls = {"n": 0}
        real_run = mc.run

        def flaky(command, cwd, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return 0  # baseline green
            raise RuntimeError("test runner died")

        mc.run = flaky
        self.addCleanup(setattr, mc, "run", real_run)
        with self.assertRaises(RuntimeError):
            mc.sweep(str(target), "irrelevant", cwd=str(self.dir))
        self.assertEqual(target.read_bytes(), before)

    def test_cli_exit_code_is_nonzero_when_a_constant_survives(self):
        target, command = self.fixture(guarded_only=True)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = mc.main(
                ["--target", str(target), "--test", command, "--cwd", str(self.dir)]
            )
        self.assertEqual(code, 1)
        self.assertIn("UNGUARDED", out.getvalue())


class OffsetsMatchTheTokenizer(unittest.TestCase):
    def test_a_form_feed_does_not_shift_every_later_offset(self):
        # str.splitlines breaks on form feed and friends; tokenize does not.
        # One page separator and the sweep mutated an identifier, the suite
        # went red on a SyntaxError, and the constant was reported guarded.
        src = "A = 1\n" + chr(12) + "\nTHRESHOLD = 10\nSPARE = 20\n"
        for start, end, text in mc.python_literals(src):
            self.assertEqual(src[start:end], text)

    def test_offsets_hold_for_crlf_and_a_missing_final_newline(self):
        for src in ("A = 1\r\nT = 10\r\n", "A = 1\nT = 10"):
            with self.subTest(src=repr(src)):
                for start, end, text in mc.python_literals(src):
                    self.assertEqual(src[start:end], text)


class BackupSurvivesAKill(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_a_leftover_backup_stops_the_next_run(self):
        # The in-memory original dies with the process, so a killed sweep used
        # to leave the developer's file holding a mutant with no way back.
        target = self.dir / "code.py"
        target.write_text("T = 10\n", encoding="utf-8")
        target.with_name(target.name + ".premr-backup").write_bytes(b"T = 10\n")
        with self.assertRaises(SystemExit) as caught:
            mc.sweep(str(target), "echo x", cwd=str(self.dir))
        self.assertIn("previous sweep was killed", str(caught.exception))

    def test_the_backup_exists_during_the_sweep_and_is_gone_after(self):
        target = self.dir / "code.py"
        target.write_text("T = 10\n", encoding="utf-8")
        original = target.read_bytes()  # text mode may have written CRLF
        backup = target.with_name(target.name + ".premr-backup")
        seen = {}
        real_run = mc.run

        def watch(command, cwd, timeout=None):
            seen["backup_present"] = backup.exists()
            seen["backup_bytes"] = backup.read_bytes() if backup.exists() else None
            return 0

        mc.run = watch
        self.addCleanup(setattr, mc, "run", real_run)
        mc.sweep(str(target), "irrelevant", cwd=str(self.dir))
        self.assertTrue(seen["backup_present"], "no backup while the file is mutated")
        self.assertEqual(seen["backup_bytes"], original)
        self.assertFalse(backup.exists(), "backup left behind after a clean run")


class RegionAnchors(unittest.TestCase):
    def test_anchors_narrow_the_sweep(self):
        src = "A = 5\nB = 7\nC = 9\n"
        lo, hi = mc.region_bounds(src, start_text="B = ", end_text="7")
        self.assertEqual(src[lo:hi], "B = 7")

    def test_a_missing_anchor_is_an_error_not_a_silent_full_sweep(self):
        with self.assertRaises(SystemExit) as caught:
            mc.region_bounds("A = 5\n", start_text="ZZZ")
        self.assertIn("--from text not found", str(caught.exception))


if __name__ == "__main__":
    unittest.main()


class Bytecode(unittest.TestCase):
    """A Python target's __pycache__ must never carry a mutant's bytecode.

    Real case: mutant `2 -> 1` compiled to .pyc, the restore landed
    in the same second at the same size, and the next test run executed the
    mutant while the source read as the original. The import system checks
    only mtime and size, so the tool has to clear the cache itself.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        # Not "code.py": that name shadows the stdlib module when imported.
        self.target = self.dir / "guarded_mod.py"
        # Bytes, not write_text: on Windows the latter writes CRLF and the
        # planted .pyc could never match the size of the real source.
        self.target.write_bytes(b"THRESHOLD = 10\n")
        self.cache = self.dir / "__pycache__"
        self.cache.mkdir()
        self.other = self.cache / "unrelated.cpython-312.pyc"
        self.other.write_bytes(b"keep")

    def plant_colliding_bytecode(self):
        """A REAL .pyc of a different source that the import system accepts
        for the target: same size, same mtime - exactly the real case."""
        real = self.target.read_bytes()
        stale_src = b"THRESHOLD = 99\n"
        assert len(stale_src) == len(real), "collision needs equal size"
        self.target.write_bytes(stale_src)
        pyc = Path(importlib.util.cache_from_source(str(self.target)))
        py_compile.compile(str(self.target), cfile=str(pyc), doraise=True)
        st = self.target.stat()
        self.target.write_bytes(real)
        os.utime(self.target, ns=(st.st_atime_ns, st.st_mtime_ns))
        return pyc

    def importing_checker(self):
        """Exit 0 only if the IMPORTED module (bytecode and all) says 10."""
        checker = self.dir / "check.py"
        checker.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(self.dir)!r})\n"
            "import guarded_mod\n"
            "sys.exit(0 if guarded_mod.THRESHOLD == 10 else 1)\n",
            encoding="utf-8",
        )
        return f"{sys.executable} {checker}"

    def test_the_collision_is_real(self):
        """Sanity: without any cleanup, Python runs the stale bytecode."""
        self.plant_colliding_bytecode()
        env = dict(os.environ)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        rc = subprocess.run(
            self.importing_checker(), shell=True, cwd=str(self.dir), env=env
        ).returncode
        self.assertEqual(rc, 1, "expected the stale .pyc (THRESHOLD=99) to win")

    def test_sweep_drops_stale_bytecode_before_the_baseline(self):
        """The BEFORE half: with a colliding .pyc in place, the baseline must
        see the real source (green), not the stale bytecode (red -> abort).
        Removing the pre-baseline drop_bytecode() call turns this test red."""
        self.plant_colliding_bytecode()
        results = mc.sweep(
            str(self.target), self.importing_checker(), cwd=str(self.dir)
        )
        self.assertTrue(results, "sweep did not run")
        self.assertTrue(all(caught for _, _, _, caught in results))

    def compiling_checker(self):
        """A test command that writes bytecode itself, ignoring the env var -
        the case the post-sweep cleanup exists for."""
        checker = self.dir / "check_compile.py"
        checker.write_text(
            "import py_compile, sys\n"
            f"py_compile.compile({str(self.target)!r}, doraise=True)\n"
            f"sys.path.insert(0, {str(self.dir)!r})\n"
            "import guarded_mod\n"
            "sys.exit(0 if guarded_mod.THRESHOLD == 10 else 1)\n",
            encoding="utf-8",
        )
        return f"{sys.executable} {checker}"

    def test_sweep_leaves_no_bytecode_behind(self):
        """The AFTER half: a test command that compiles the target itself
        leaves a mutant's .pyc that the sweep must remove. Removing the
        post-restore drop_bytecode() call turns this test red."""
        mc.sweep(str(self.target), self.compiling_checker(), cwd=str(self.dir))
        self.assertFalse(list(self.cache.glob("guarded_mod.*.pyc")))
        self.assertTrue(self.other.exists())

    def test_drop_bytecode_follows_pycache_prefix(self):
        """PYTHONPYCACHEPREFIX moves the cache away from the sibling
        __pycache__; the sweep must clear the cache where Python reads it."""
        prefix = self.dir / "central-cache"
        with mock.patch.dict(os.environ, {"PYTHONPYCACHEPREFIX": str(prefix)}):
            with mock.patch.object(sys, "pycache_prefix", str(prefix)):
                pyc = Path(importlib.util.cache_from_source(str(self.target)))
                pyc.parent.mkdir(parents=True, exist_ok=True)
                pyc.write_bytes(b"stale")
                self.assertTrue(str(pyc).startswith(str(prefix)))
                mc.drop_bytecode(self.target)
                self.assertFalse(pyc.exists())

    def test_drop_bytecode_removes_only_the_targets_cache(self):
        stale = self.plant_colliding_bytecode()
        mc.drop_bytecode(self.target)
        self.assertFalse(stale.exists())
        self.assertTrue(self.other.exists())

    def test_drop_bytecode_ignores_non_python_targets(self):
        stale = self.plant_colliding_bytecode()
        js = self.dir / "code.js"
        js.write_text("const a = 1\n", encoding="utf-8")
        mc.drop_bytecode(js)
        self.assertTrue(stale.exists())

    def test_run_disables_bytecode_for_the_test_process(self):
        """Pinned even when the ambient shell already sets the variable."""
        probe = self.dir / "probe.py"
        probe.write_text(
            "import os, sys\n"
            "sys.exit(0 if os.environ.get('PYTHONDONTWRITEBYTECODE') == '1' else 1)\n",
            encoding="utf-8",
        )
        with mock.patch.dict(os.environ):
            os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            self.assertEqual(mc.run(f"{sys.executable} {probe}", cwd=str(self.dir)), 0)
