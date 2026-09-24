"""Mutate every numeric constant in a file and demand the tests notice.

Written after a review in which three models reviewed a test that guards two
thresholds, mutated one of them, and pronounced the test real. The other
threshold was not pinned at all: loosening it passed green. Judgement picked a
constant; this walks all of them.

    python skills/pre-mr/scripts/mutate_constants.py --target src/thresholds.py \
        --test "python -m pytest tests/test_thresholds.py -q"

Every literal is changed one at a time, the test command is run, and the file
is restored. A literal whose mutation leaves the suite green is UNGUARDED: the
code could drift there and nothing would say so. Exit 1 if any survived.

The target is edited in place and restored from a byte copy in a finally, and
the run refuses to start unless the baseline is green - a red baseline makes
every mutant look caught.
"""

import argparse
import re
import importlib.util
import os
import subprocess
import sys
import tokenize
from io import BytesIO
from pathlib import Path

# Numbers that carry no threshold meaning; mutating them is noise.
TRIVIAL = {0, 1, -1}


def python_literals(source):
    """(start, end, text) for every numeric token - tokenize skips strings."""
    out = []
    # Split on newline ONLY. str.splitlines also breaks on form feed, -,
    #  and the unicode separators, which tokenize does not - one form feed
    # in the file and every offset after it points at the wrong bytes, so the
    # sweep mutates an identifier, the suite goes red on a SyntaxError, and the
    # constant is reported "caught" while nothing tests it.
    offsets, run = [], 0
    for line in source.split(chr(10)):
        offsets.append(run)
        run += len(line) + 1
    for tok in tokenize.tokenize(BytesIO(source.encode("utf-8")).readline):
        if tok.type == tokenize.NUMBER:
            start = offsets[tok.start[0] - 1] + tok.start[1]
            out.append((start, start + len(tok.string), tok.string))
    return out


JS_SKIP = re.compile(
    r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`",
    re.S,
)
# Hex, exponent and leading-dot forms count: a threshold written 0x10 or 1e3
# is still a threshold. Regex literals are NOT excluded - / is ambiguous with
# division, so a pattern like /d{3}/ can be mutated; the report names every
# literal it touched, so that shows up rather than hiding.
JS_NUMBER = re.compile(
    r"(?<![\w.$])(?:0[xX][0-9a-fA-F]+|\d*\.?\d+(?:[eE][+-]?\d+)?)(?![\w.])"
)


def js_literals(source):
    """Same, minus comments and string literals (blanked, offsets preserved)."""
    scan = JS_SKIP.sub(lambda m: " " * len(m.group(0)), source)
    return [(m.start(), m.end(), m.group()) for m in JS_NUMBER.finditer(scan)]


def literals_for(path, source):
    if path.suffix == ".py":
        return python_literals(source)
    return js_literals(source)


def mutants_of(text):
    """Values a reviewer would try: one step, and a coarse move."""
    try:
        if text[:2].lower() == "0x":
            value = int(text, 16)
        elif "." in text or "e" in text.lower():
            value = float(text)
        else:
            value = int(text)
    except ValueError:
        return []
    if value in TRIVIAL:
        return []
    if isinstance(value, int):
        return [str(value + 1), str(value - 1)]
    fine = max(abs(value) * 0.002, 1e-9)
    coarse = abs(value) * 0.2
    seen, out = {text}, []
    for delta in (fine, coarse):
        for candidate in (value + delta, value - delta):
            rendered = f"{candidate:.10g}"
            if rendered not in seen:
                seen.add(rendered)
                out.append(rendered)
    return out


def drop_bytecode(path):
    """Delete cached bytecode for a Python target so no run reads a stale .pyc.

    Found in a real run: the sweep mutated `2 -> 1`, the test run compiled that
    mutant to __pycache__, and the restore wrote the original back within the
    same second and at the same size - the only two things the import system
    checks. The mutant's bytecode then validated for the ORIGINAL source, and
    the next (unrelated) test run reported the mutant's behaviour as the code's.
    The same collision between two consecutive mutants would misreport a
    survivor as caught, which is the dangerous direction for this tool.
    """
    path = Path(path)
    if path.suffix != ".py":
        return
    try:
        # Ask the import system where it would put the cache: this follows
        # PYTHONPYCACHEPREFIX, a sibling __pycache__ guess does not.
        cache = Path(importlib.util.cache_from_source(str(path))).parent
        if not cache.is_dir():
            return
        for pyc in cache.glob(path.stem + ".*.pyc"):
            pyc.unlink()
    except OSError:
        # Best effort only: a cache we cannot touch must never be reported
        # as a failed source restore by the caller.
        pass


def run(command, cwd, timeout=300):
    # No bytecode from any run: see drop_bytecode. Set here, not left to the
    # caller's shell, so the guarantee travels with the tool.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run(
        command, shell=True, cwd=cwd, capture_output=True, timeout=timeout, env=env
    )
    return done.returncode


def region_bounds(source, region=None, start_text=None, end_text=None):
    """Byte range to mutate: a whole snippet, or a from/to pair of anchors."""
    if region:
        lo = source.find(region)
        if lo == -1:
            raise SystemExit("--region text not found")
        return lo, lo + len(region)
    if start_text:
        lo = source.find(start_text)
        if lo == -1:
            raise SystemExit(f"--from text not found: {start_text!r}")
        if not end_text:
            return lo, len(source)
        hi = source.find(end_text, lo)
        if hi == -1:
            raise SystemExit(f"--to text not found after --from: {end_text!r}")
        return lo, hi + len(end_text)
    return None


def sweep(
    target, command, cwd=".", region=None, start_text=None, end_text=None, timeout=300
):
    path = Path(target)
    backup = path.with_name(path.name + ".premr-backup")
    if backup.exists():
        raise SystemExit(
            f"{backup} exists - a previous sweep was killed. Compare it with "
            f"{path.name}, restore it, and delete the backup before re-running."
        )
    original = path.read_bytes()
    source = original.decode("utf-8")
    drop_bytecode(path)  # a stale .pyc from an earlier run must not vote
    if run(command, cwd, timeout=timeout) != 0:
        raise SystemExit(
            "baseline is RED - fix the suite first, or every mutant looks caught"
        )
    found = literals_for(path, source)
    bounds = region_bounds(source, region, start_text, end_text)
    if bounds:
        lo, hi = bounds
        found = [item for item in found if lo <= item[0] < hi]
    results = []
    backup.write_bytes(original)
    try:
        for start, end, text in found:
            candidates = mutants_of(text)
            if not candidates and text not in {"0", "1", "-1"}:
                # A literal the sweep cannot mutate (BigInt, complex, a form
                # this parser does not know) must be visible, or a threshold
                # written that way disappears into a clean report.
                results.append((source.count(chr(10), 0, start) + 1, text, None, True))
            for replacement in candidates:
                path.write_bytes(
                    (source[:start] + replacement + source[end:]).encode("utf-8")
                )
                caught = run(command, cwd, timeout=timeout) != 0
                line = source.count("\n", 0, start) + 1
                results.append((line, text, replacement, caught))
    finally:
        try:
            if path.read_bytes() != original:
                path.write_bytes(original)
            restored = path.read_bytes() == original
        except OSError:
            restored = False
        drop_bytecode(path)  # never leave a mutant's bytecode behind
        if restored:
            backup.unlink()
        else:
            # Keep the backup and say so. A read-only target used to raise from
            # the restore itself, masking the real cause and leaving a stale
            # backup that then refused every later run.
            raise SystemExit(
                f"could not restore {target} - the original is in {backup}, "
                f"put it back by hand and delete the backup"
            )
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mutate_constants.py", description=__doc__)
    ap.add_argument("--target", required=True, help="file whose constants to mutate")
    ap.add_argument("--test", required=True, help="command that must go red")
    ap.add_argument("--cwd", default=".", help="where to run the test command")
    ap.add_argument("--region", help="only mutate inside this literal snippet")
    ap.add_argument(
        "--from", dest="start_text", help="anchor: first line of the region"
    )
    ap.add_argument("--to", dest="end_text", help="anchor: last line of the region")
    args = ap.parse_args(argv)

    results = sweep(
        args.target,
        args.test,
        cwd=args.cwd,
        region=args.region,
        start_text=args.start_text,
        end_text=args.end_text,
    )
    if not results:
        print("no non-trivial numeric constants found - nothing to sweep")
        return 0
    mutations = [r for r in results if r[2] is not None]
    survived = [r for r in mutations if not r[3]]
    for line, text in sorted({(r[0], r[1]) for r in results if r[2] is None}):
        print(f"  skipped   line {line}: {text} (no mutation this tool can make)")
    for line, text, replacement, caught in mutations:
        mark = "caught   " if caught else "SURVIVED "
        print(f"  {mark} line {line}: {text} -> {replacement}")
    print(
        f"{chr(10)}{len(mutations) - len(survived)}/{len(mutations)} mutations caught."
    )
    if survived:
        print("UNGUARDED constants (the tests do not pin these):")
        for line, text, replacement, _ in survived:
            print(f"  line {line}: {text} survives becoming {replacement}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
