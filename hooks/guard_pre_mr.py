"""PreToolUse hook: enforce the /pre-mr gate before pushing to an MR branch.

Team ruling (the pre-mr rule): every push to a branch that goes to team
review must be preceded by a /pre-mr run. The skill's final step writes a
JSON marker at <git-dir>/pre-mr-ok holding a digest of the reviewed content;
this hook blocks `git push` on non-master/main branches when that marker is missing or
does not cover the current tree.

Coverage is by CONTENT, not by HEAD: an amend that only rewords a commit keeps
the marker, while applying review findings invalidates it. That is the case
this hook was widened for in an earlier review - findings were applied after the
adversarial pass, the marker was rewritten mechanically because HEAD had
moved, and a regression introduced by the fixes reached the branch with the
gate reporting green. The digest lives in pre_mr_marker.py, installed next to
this hook; if it is missing, fall back to the old HEAD comparison rather than
blocking (fail-open).

Allowed without a marker:
  - pushes on master/main (not MR branches)
  - docs-only branches: every file the branch changes against its base is a
    `.md` under the docs-only prefix (PRE_MR_DOCS_ONLY_PREFIX, default
    `docs/`) - a mirror of product documents, not code. A claims audit of a document its author wrote catches
    nothing; the gate stays for anything executable or outside that tree. An
    EMPTY diff is not docs-only (nothing to exempt - judged as before).
  - dry runs (--dry-run / -n) and remote branch deletions (--delete / -d)
  - explicit bypass: prefix the command with PRE_MR_BYPASS=1 (for branches
    that are not going to team review)

Fail-open by design: any internal error -> exit 0 (never break a push because
the hook itself is broken). Exit 2 = block, stderr shown to the model.

Detection is best-effort text matching. `git` must sit at a command position
(start, or after ; & | ( { newline or a backtick, optional VAR=x prefixes) and
only git options may appear between `git` and `push`, so `echo 'git push'`
does not trigger. The `{` and backtick positions were added for PowerShell's
`if ($?) { ... }` and for backtick continuations, and they do NOT respect
quoting: a string that merely CONTAINS "{ git push }" or a backtick code span
around it will block. So can a heredoc that documents a push. That is the
cheap error - use PRE_MR_BYPASS=1 there.

Known costs, accepted (seven review rounds): an `export GIT_DIR=`
earlier in the line is judged ADDITIVELY (the exported repo and the cwd walk
both), because a heredoc body, a subshell or a later `unset` look identical
in the text - so `export GIT_DIR=<master>/.git; git push origin master` from
a review-branch cwd blocks, and the bypass is the answer there too. Deliberate
evasion (`sh -c '...'`, `xargs git push`, `eval`, a quoted verb `git "push"`,
more than eight wrapper options) is out of scope: this is a gate against an
accidental push, not against an adversary.

"""

import json
import os
import re
import shutil
import subprocess
import sys

QUOTED = r"\"[^\"]+\"|'[^']+'|\S+"
# A path or a value: quoted, or up to whitespace / a shell delimiter. `\S+`
# swallowed the `;` after `R=/x;` and after `cd /x;` (rounds 3-4), so every
# reader of a path uses this class; QUOTED stays only inside PUSH_SEG.
# `<` `>` are redirections, never unquoted path characters (`cd /x>log`);
# a backslash escapes the next character (`fs\ pace`), unescaped in the
# cd walk for Bash payloads (round 5, S1/S2).
TOKEN = r"\"[^\"]*\"|'[^']*'|(?:\\.|[^\s;&|(){}<>`\\])+"
# VAR=x VAR2=y git push - the value is a TOKEN, so the prefix can never cross
# a `;`: `GIT_DIR=/x; git push` is an unexported statement git never sees,
# and `\S*` made it steer the verdict (round 5, B4).
ENV_PREFIX = r"(?:[A-Za-z_]\w*=(?:" + TOKEN + r")?\s+)*"
SHELL = "Bash"  # set from the payload's tool_name in main()
WRAPPER = (
    # `sudo -u me git`, `env FOO=1 git`, `nohup git`: a wrapper word, its
    # own options, then env prefixes again. Repetitions are capped: the
    # option loop backtracked exponentially on `env -o0 ... -o32 git-thing`
    # (6.9 s at n=32 - a hanging hook is worse than either verdict).
    r"(?:(?:sudo|env|time|nohup|command|winpty)"
    r"(?:\s+-{1,2}[\w-]+(?:[= ]\S+)?){0,8}\s+" + ENV_PREFIX + r"){0,3}"
)
GIT_BIN = (
    # Spellings that still run git: a bare `git`, `git.exe` (this machine's
    # own shell), a path prefix, or a quoted path with spaces. Only the
    # binary is case-insensitive (the filesystem is); a module-wide flag made
    # `Time git push` at a line start of a commit body a push (round 3, S3).
    r"(?i:\"[^\"]*[\\/]git(?:\.exe)?\"|'[^']*[\\/]git(?:\.exe)?'"
    r"|(?:[\w.~:\\/-]*[\\/])?git(?:\.exe)?)"
)
PUSH_SEG = re.compile(
    r"(?:^|[;&|({`\n]\s*|\$\(\s*)"
    + ENV_PREFIX
    + WRAPPER
    + GIT_BIN
    # options before the verb, including the ones that steer which repo is
    # pushed: -C <dir>, --git-dir <dir>, --work-tree <dir> (space or `=`)
    + r"(?P<opts>(?:\s+(?:--?[\w-]+(?:=\S+)?|(?:-[Cc]|--git-dir|--work-tree)\s+(?:"
    + QUOTED
    + r")))*)"
    r"(?:\s|`)+push\b(?P<rest>[^|;&\n]*)"
)

# Inside a double-quoted string a `\"` (bash) or a backtick-escaped `"`
# (PowerShell) does not close it. Pairing the escaped quote with the opener
# left the rest of the string outside the blank, and a `;` there was a
# command position (round 6, B1). Single quotes admit no escapes in either
# shell.
# Escapes are per shell: `\"` in bash, a backtick-escaped `"` in
# PowerShell. Applying BOTH to both (round 6) under-closed strings: in bash a
# backtick is a substitution, so `"on `pwd`"` swallowed the closing quote and
# the blank ran over a following `cd`; in PowerShell `\` is not an escape, so
# a Windows path ending in `\"` did the same (round 7).
QUOTE_SPAN_BASH = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'[^']*'")
QUOTE_SPAN_PS = re.compile(r"\"(?:[^\"`]|`.)*\"|'[^']*'")


def blank_quotes(text):
    """Quoted spans replaced by spaces of the same length: offsets survive,
    and a `;`, `cd` or bypass token INSIDE a string is no longer a command
    position (review round 2: `echo "x; PRE_MR_BYPASS=1"` and
    `echo "x; cd <other repo>"` both steered the gate)."""
    rx = QUOTE_SPAN_PS if SHELL == "PowerShell" else QUOTE_SPAN_BASH
    return rx.sub(lambda m: " " * len(m.group()), text)


# The bypass must sit at a command position, and an env-prefix form applies
# to ITS command only (`PRE_MR_BYPASS=1 git push a; git push b` vouches for
# nothing behind the `;`), while `export` persists for the rest of the line.
EXPORT_BYPASS_RX = re.compile(
    r"(?:^|[;&|({`\n])\s*export\s+PRE_MR_BYPASS=1(?=[\s;&|)}]|$)"
)
# PowerShell has no env-prefix form; `$env:PRE_MR_BYPASS = "1"` is how it is
# written, the drive and the name are case-insensitive there, and the value
# may be quoted. Round 4 matched it on the raw text and thereby reopened the
# "token inside a string" class (`"note; $env:PRE_MR_BYPASS=1 applied"`) -
# and honoured it on Bash payloads, where `$env:X=1` is not even a command.
# Now: the quoted VALUE is unquoted first (same length), the rest is blanked
# like every other scan, and the spelling counts only for PowerShell
# payloads (round 5, B1).
# Located on the BLANKED text (so a spelling inside a string is prose), the
# value read from the ORIGINAL at the same offset - the trick the cd walk
# uses. Round 5 rewrote `= "1"` before blanking; deleting two quotes re-paired
# the rest of the line and a backtick-escaped `"` exposed an in-string
# bypass (round 6, B1). `${env:NAME}` is a legal PowerShell spelling too.
PS_BYPASS_RX = re.compile(
    r"(?:^|[;&|({`\n])\s*\$\{?env:PRE_MR_BYPASS\}?\s*=", re.IGNORECASE
)
# Read from the ORIGINAL right after the `=`: whitespace is identical in both
# texts (only quotes are blanked), so the value regex owns the `\s*`.
PS_VALUE_RX = re.compile(r"\s*['\"]?1['\"]?(?=[\s;&|)}]|$)")
PREFIX_BYPASS_RX = re.compile(
    r"(?:^|[;&|({`\n])\s*" + ENV_PREFIX + r"PRE_MR_BYPASS=1(?=\s)"
)


def bypassed(cmd, seg):
    """True when a command-position PRE_MR_BYPASS=1 covers this segment."""
    text = blank_quotes(cmd)
    if SHELL == "PowerShell":
        # Only the PowerShell spelling counts here: `export X=1` is not a
        # cmdlet and `X=1 cmd` is a parse error, yet both used to disarm the
        # gate on PowerShell payloads (round 6, S1).
        for m in PS_BYPASS_RX.finditer(text, 0, seg.start() + 1):
            if PS_VALUE_RX.match(cmd, m.end()):
                return True
        return False
    if EXPORT_BYPASS_RX.search(text, 0, seg.start() + 1):
        return True
    return PREFIX_BYPASS_RX.search(text, seg.start(), seg.end()) is not None


def norm_path(p, base):
    p = p.strip("\"'")
    m = re.match(r"^/([a-zA-Z])(/.*)?$", p)  # git-bash /c/... -> C:/...
    if m:
        p = m.group(1).upper() + ":" + (m.group(2) or "/")
    p = os.path.expanduser(p)
    if not os.path.isabs(p):
        p = os.path.join(base, p)
    return p


ASSIGN_RX = re.compile(r"(?:^|[;&|({\n]\s*)([A-Za-z_]\w*)=(" + TOKEN + ")")
VAR_RX = re.compile(r"\$\{(\w+)\}|\$(\w+)|%(\w+)%")
UNRESOLVED = "\x00?\x00"


def expand_vars(raw, prefix):
    """Expand $VAR / ${VAR} / %VAR% from assignments made earlier in the SAME
    command, then from the environment.

    %TEMP% and friends are ordinary on Windows, so refusing to expand them
    made the gate skip itself on a routine command. What must still fail open
    is a name nothing defines: guessing there makes the hook judge a DIFFERENT
    repository than the one being pushed, in both directions.
    """
    values = {m.group(1): m.group(2).strip("\"'") for m in ASSIGN_RX.finditer(prefix)}

    def one(match):
        if match.group(3) and SHELL != "PowerShell":
            return match.group(0)  # bash does not expand %VAR%: literal (round 5, S5)
        name = match.group(1) or match.group(2) or match.group(3)
        if name in values:
            return values[name]
        return os.environ.get(name) or UNRESOLVED

    out = VAR_RX.sub(one, raw)
    if UNRESOLVED in out or "$(" in out or any(ch in out for ch in (chr(96), "*")):
        return None
    return out


# A cd/pushd argument ends at whitespace OR a shell delimiter: `\S+` used to
# swallow the `;` of `cd repo; ls; git push` and the path never resolved.
CD_ARG = re.compile(TOKEN)
CD_RX = re.compile(r"(?:^|[;&|({`\n]\s*)(?:cd|pushd)(?=[ \t])")
EXPORT_GITDIR_RX = re.compile(r"(?:^|[;&|({`\n])\s*export\s+GIT_DIR=")


def unescape(token):
    r"""An unquoted Bash token: `\x` is `x`. PowerShell keeps backslashes."""
    if SHELL == "PowerShell" or token[:1] in "\"'":
        return token
    return re.sub(r"\\(.)", r"\1", token)


def repo_dir_for(cmd, seg):
    base = os.getcwd()
    prefix = cmd[: seg.start()]
    # Anything that names the repo explicitly wins over the cd walk:
    # -C <dir>, --git-dir <dir> / --git-dir=<dir>, and a GIT_DIR= env prefix
    # (round 3, S1: all three steered the push without being seen).
    opts = seg.group("opts")
    head = seg.group(0)[: seg.end("opts") - seg.start()]  # up to the verb
    blank = blank_quotes(prefix)
    m_c = re.search(r"-C\s+(" + TOKEN + ")", opts)
    m_gd = re.search(r"--git-dir(?:=|\s+)(" + TOKEN + ")", opts)
    m_env = re.search(r"(?:^|[\s;&|({`])GIT_DIR=(" + TOKEN + ")", head)
    # `export GIT_DIR=<dir>; git push` from an earlier statement: located on
    # the blanked prefix, value read from the original (round 5, B3). The
    # LAST export wins, like the shell.
    # git's own precedence: --git-dir, then the GIT_DIR environment prefix,
    # then -C, which only chdirs. The reverse order let `-C <master>
    # --git-dir=<review>` be judged on master (round 4); GIT_DIR after the
    # verb (a trailing comment) steered too, hence `head`.
    for m_named, unresolved in (
        (m_gd, None),  # git fatals on a bad --git-dir: nothing is pushed
        (m_env, None),
        (m_c, base),  # `-C ""` is a no-op for git: the cwd is what pushes
    ):
        if m_named:
            expanded = expand_vars(m_named.group(m_named.re.groups), prefix)
            if expanded is None:
                return None if unresolved is None else [unresolved]
            return [norm_path(expanded, base)]
    cur = base
    # Locate `cd` on the quote-blanked text (a cd inside a string is prose)
    # and read its argument from the ORIGINAL at the same offset - skipping
    # whitespace on the original, never on the blanked copy, where a quoted
    # argument is all spaces and a greedy `\s+` ran straight past it
    # (round 3). Always blanked: a raw-text fallback for an odd quote count
    # (round 3) was a bypass - an apostrophe INSIDE double quotes made the
    # count odd and a `cd` inside that string relocated the judged repo
    # (round 4). An unbalanced quote is a shell syntax error - nothing runs.
    # The delimiter class includes newline and backtick: `cd` on its own
    # line is the Bash tool's normal shape.
    for m_cd in CD_RX.finditer(blank):
        # A backslash-newline (LF or CRLF) continues the line INSIDE a word:
        # the shell joins the pieces, so the pair is removed, not spaced
        # (round 5, S3/S4). Offsets are not indexed back into prefix after
        # this point. `cd -- path` is valid.
        rest = prefix[m_cd.end() :]
        rest = rest.replace("\\\r\n", "").replace("\\\n", "").lstrip(" \t")
        if rest.startswith("--") and rest[2:3] in (" ", "\t"):
            rest = rest[2:].lstrip(" \t")
        m_arg = CD_ARG.match(rest)
        if not m_arg:
            continue
        expanded = expand_vars(unescape(m_arg.group(0)), prefix)
        if expanded is None:
            # `cd $UNDEFINED` expands to `cd ""` / bare `cd` - the shell stays
            # put or goes HOME, neither of which is a repo the push can land
            # in. Judging the current directory is right; failing open was a
            # free bypass (review round 2, finding 4).
            continue
        cur = norm_path(expanded, cur)
    repos = [cur]
    # `export GIT_DIR=<dir>` in an earlier statement (Bash only - PowerShell
    # has no `export`). Whether it applies to the push is not decidable from
    # the text: a heredoc body, a subshell, a later `unset`, an `if false`
    # branch all contain one that does not (round 6, B2). So the export is
    # ADDITIVE: the exported repo and the walked one are both judged, and the
    # segment blocks if either does. The last export wins, like the shell.
    if SHELL != "PowerShell":
        for m_x in EXPORT_GITDIR_RX.finditer(blank):
            m_arg = CD_ARG.match(prefix[m_x.end() :])
            if not m_arg:
                continue
            expanded = expand_vars(m_arg.group(0), prefix)
            if expanded is not None:
                exported = norm_path(expanded, base)
                repos = [exported, cur] if exported != cur else [cur]
    return repos


# Documents-only exemption: a branch that changes nothing but `.md` files
# under this prefix pushes without a marker (a claims audit of a document its
# author wrote catches nothing). Point it at your docs mirror; an empty value
# disables the exemption.
DOCS_ONLY_PREFIX = os.environ.get("PRE_MR_DOCS_ONLY_PREFIX", "docs/")
DOCS_ONLY_SUFFIX = ".md"
BASE_REFS = ("origin/master", "origin/main", "master", "main")


def docs_only_paths(paths):
    """True when EVERY changed path is a `.md` under the docs-only prefix and
    there is at least one. Pure: the decision lives here so it is testable
    without a repo. Paths are git's own output: forward slashes, repo-relative."""
    paths = [p for p in paths if p]
    if not DOCS_ONLY_PREFIX:
        return False
    return bool(paths) and all(
        p.startswith(DOCS_ONLY_PREFIX) and p.endswith(DOCS_ONLY_SUFFIX) for p in paths
    )


def docs_only(repo):
    """The branch's diff against its base touches only <prefix>/**/*.md.

    Base = the first of BASE_REFS that resolves (a clone usually tracks
    origin/master or origin/main; the test repo has only master). No base -> not docs-only:
    an unknown diff keeps the gate. Renames are listed by their new path
    (--no-renames), deletions by the deleted path - a deleted .md is still
    a docs-only change."""
    for ref in BASE_REFS:
        rc, base = git(repo, "merge-base", "HEAD", ref)
        if rc == 0 and base:
            break
    else:
        return False
    rc, out = git(repo, "diff", "--name-only", "--no-renames", base, "HEAD")
    if rc != 0:
        return False
    return docs_only_paths(out.splitlines())


def load_checker():
    """pre_mr_marker installed next to this hook - one digest, one copy."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import pre_mr_marker

        return pre_mr_marker
    except Exception:
        return None


_GIT_MEMO = {}


def git(repo, *args):
    key = (repo, args)
    if key not in _GIT_MEMO:
        r = subprocess.run(
            ["git", "-C", repo, *args], capture_output=True, text=True, timeout=10
        )
        _GIT_MEMO[key] = (r.returncode, r.stdout.strip())
    return _GIT_MEMO[key]


def main():
    data = json.load(sys.stdin)
    if data.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    cmd = data.get("tool_input", {}).get("command", "") or ""
    global SHELL
    SHELL = data.get("tool_name") or "Bash"
    # Cheap pre-filter, case-insensitive like the regex: an upper-case
    # spelling is the same binary on this filesystem (review r2).
    low = cmd.lower()
    if "git" not in low or "push" not in low:
        return 0

    # EVERY push segment, not just the first: "git push --dry-run && git push"
    # used to be waved through on the strength of the dry run, and that is a
    # sequence an agent writes unprompted.
    # A `# --dry-run` trailing comment is not a dry run (round 5, B2): the
    # flag scan stops at the first ` #`.
    def flags_of(rest):
        # up to the first ` #` outside quotes (round 6, S2: a `#` inside a
        # quoted -o value used to cut before a real --dry-run)
        # and flags inside a quoted value (`-o "fix -n flag"`) are not flags:
        # the blanked slice is what gets scanned (round 7, S2)
        blanked = blank_quotes(rest)
        cut = len(re.split(r"\s#", blanked)[0])
        return blanked[:cut]

    real = [
        m
        for m in PUSH_SEG.finditer(cmd)
        if not re.search(r"\s(--dry-run|-n|--delete|-d)\b", flags_of(m.group("rest")))
    ]
    if not real:
        return 0
    if shutil.which("git") is None:
        return 0
    # Every real segment is judged on its own repo and branch. Judging only
    # the first one let `git -C <repo-on-master> push; git push` through on
    # the strength of the harmless first push (review, B2).
    for seg in real:
        try:
            if bypassed(cmd, seg):
                continue
            blocked, branch, detail = judge(cmd, seg)
        except Exception:
            continue  # fail-open for THIS segment only, never for the line
        if blocked:
            explain(branch, detail)
            return 2
    return 0


def judge(cmd, seg):
    """One push segment -> (blocked, branch, detail). Fail-open stays: any
    situation the hook cannot read returns (False, ...). A segment may name
    more than one candidate repo (an ambiguous export); it blocks if any does."""
    repos = repo_dir_for(cmd, seg)
    if repos is None:
        return False, None, None  # cannot tell which repo - do not guess
    verdict = (False, None, None)
    for repo in repos:
        try:
            verdict = judge_repo(repo)
        except Exception:
            continue  # one unreadable candidate must not silence the other
        if verdict[0]:
            return verdict
    return verdict


def judge_repo(repo):
    if not os.path.isdir(repo):
        repo = os.getcwd()
    rc, branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if rc != 0 or branch in ("master", "main", "HEAD"):
        return False, branch, None
    rc, head = git(repo, "rev-parse", "HEAD")
    if rc != 0:
        return False, branch, None
    rc, git_dir = git(repo, "rev-parse", "--git-dir")
    if rc != 0:
        return False, branch, None
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(repo, git_dir)
    if docs_only(repo):
        return False, branch, f"docs-only branch ({DOCS_ONLY_PREFIX}**/*.md)"
    marker = os.path.join(git_dir, "pre-mr-ok")
    detail = "no marker covering the current tree"
    checker = load_checker()
    if checker is not None:
        try:
            ok, detail = checker.check(repo)
            if ok:
                return False, branch, detail
        except Exception:
            return False, branch, None  # fail-open: never block on our own error
    else:
        # Legacy path: the digest module is not installed. A JSON marker still
        # names the head it covered - compare that, or a modern marker never
        # matches the raw text and this fallback always BLOCKS, which is the
        # opposite of falling back.
        try:
            with open(marker, encoding="utf-8") as f:
                raw = f.read().strip()
            try:
                data = json.loads(raw)
                # A non-object (`0`, `[]`) is not a marker - same as B1 in
                # pre_mr_marker; raising here read as ALLOW.
                recorded = data.get("head") if isinstance(data, dict) else raw
            except ValueError:
                recorded = raw
            if recorded == head:
                return False, branch, None
            detail = "marker does not cover this HEAD (digest module missing)"
        except (OSError, UnicodeDecodeError):
            # UnicodeDecodeError comes from f.read(), OUTSIDE the json try, so
            # the inner `except ValueError` never saw it: undecodable bytes in
            # the marker raised out of judge() and the per-segment fail-open
            # skipped the segment - ALLOW. read_marker got this fix in round 2
            # and this second reader did not (review round 3).
            pass
    return True, branch, detail


def explain(branch, detail):
    sys.stderr.write(
        "PRE-MR GATE: push to branch '"
        + str(branch)
        + "' blocked - "
        + str(detail)
        + ".\n"
        "Team ruling: run the /pre-mr gate before any push that goes to review.\n"
        "If the diff changed after the gate ran, re-run the adversarial pass on\n"
        "the CURRENT diff first - applying findings and re-marking without it is\n"
        "how a regression introduced by the fixes reaches review. Then:\n"
        "  python ~/.claude/hooks/pre_mr_marker.py write --base origin/master\n"
        "If this branch is NOT going to team review, bypass explicitly:\n"
        "  PRE_MR_BYPASS=1 git push ...        (bash)\n"
        "  $env:PRE_MR_BYPASS=1; git push ...   (PowerShell)\n"
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open
