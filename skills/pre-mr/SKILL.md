---
name: pre-mr
description: Pre-review gate - run BEFORE pushing any commit that goes to team review (MR/PR create or update). Deterministic checks, boundary tables for pure functions, a constant-mutation sweep, adversarial fresh-context review of the diff, and a claims audit of the MR text. Triggers on "pre-mr", "gate before the MR", or any push to a branch with an open/planned MR.
---

# /pre-mr — gate before anything goes to review

The author is anchored on their own solution. This gate is mechanized fresh eyes,
built from the four error classes that team review actually caught (the first two merge requests this gate was built from - two review rounds each, both found defects the author walked past):

| # | Class | Example caught in review |
|---|-------|--------------------------|
| 1 | Unhandled failure paths | `agent()` returns null -> `.then` dereferences -> whole platform audit lost |
| 2 | Boundary behavior | verdict cliff: refuted=1 -> `unreliable` at 4 claims, `minor-issues` at 5 |
| 3 | Unverified claims | "CLAUDE_HOME is honoured" - asserted, never executed in the target runtime |
| 4 | Information loss in aggregates | `unevidenced` as a count -> coordinator cannot attribute; "unaccounted claim" placeholders |

## Steps (all BEFORE the push, in order)

1. **Deterministic checks.** Syntax for every changed file type (`node --check`,
   `python -m py_compile`, `bash -n`, `python -m json.tool`); repo lint if available
   (shellcheck, ruff); byte-identity (sha1) of any shared fragment touched.
   **Agent-eval gate:** if the diff touches a judgment-agent definition
   (`agents/project-manager.md`, `agents/po-prioritizer.md`), run its eval
   (`scripts/eval_board_sync.py` / `scripts/eval_prioritize.py`, `--runs 3`)
   before pushing and keep the report next to the MR. A red eval means the doc
   change regressed judgment - fix the doc, not the golden set.

2. **Boundary tables, then the constant sweep.** For every NEW or MODIFIED pure
   function: actually execute it over a printed input/output table covering
   0 / 1 / boundary / just-past-boundary / large. Eyeball for cliffs and
   non-monotonicity. Ten lines of throwaway code — this is the cheapest step and
   the one most often skipped.

   Then let the machine pick the constants, because judgement picks one and
   misses its neighbour:

   ```bash
   python skills/pre-mr/scripts/mutate_constants.py --target <file under test> \
       --from "<first line of the region>" --to "<last line>" \
       --test "<command that must go red>"
   ```

   It changes every numeric literal one at a time and reports the ones the suite
   does not notice. A SURVIVED line means that constant is unpinned: the code
   can drift there and nothing says so. Pin it or state why it does not matter.

   > Why: in one real case three models reviewed a test guarding two thresholds,
   > mutated one, and called the test real. The other was unpinned — loosening
   > it passed green, and a human reviewer found it a day later. The sweep finds
   > it in seconds, without judgement.

3. **Adversarial fresh-context pass.** Spawn a reviewer agent (no shared context with
   the authoring conversation) on the full diff, prompted to REFUTE, with explicit
   lenses:
   - *Failure paths:* for every external call in the diff that can return null / throw /
     time out — trace what happens next. "It won't happen" is not an answer.
   - *Boundaries:* re-derive step 2 independently; check small-N vs large-N fairness.
   - *Aggregation:* does any count/summary destroy information someone downstream is
     told to use?
   - *Incentives:* does the change make a lazy path cheaper than a diligent one?
   Findings come back as blocking / should-fix / nit; each one is fixed or explicitly
   accepted with a reason before pushing.

4. **Smoke run for behavior changes.** Static checks and simulations verify the logic
   you thought of; a real run catches what you didn't. If the diff changes a workflow,
   skill, or hook: execute its cheapest real invocation (workflow `dryRun`, hook
   pipe-test with synthetic stdin, skill on a toy input). For workflow logic changes,
   schedule one REAL end-to-end run before merge — note it in the MR description if
   it hasn't happened yet, so the reviewer knows.

5. **Claims audit.** Every behavioral assertion in the MR title, description, code
   comments, and prepared thread replies: name the command or test that proved it.
   No proof -> run one now, or soften the text to "untested" / remove the claim.
   Special case: never assert what a mechanism "will catch/enforce" unless that
   mechanism demonstrably contains the check.

6. **Write the gate marker, only then push.** After every step above passes,
   record the reviewed CONTENT so the enforcement hook lets the push through:

   ```bash
   python hooks/pre_mr_marker.py write --base origin/master
   ```

   The marker holds a digest of the diff the pass actually read (tracked changes
   against the base plus untracked files), not just a HEAD sha. So an amend that
   only rewords a commit keeps it, while **applying review findings invalidates
   it** — which is the point. Re-marking a changed diff requires
   `--reason "<what you re-verified>"`, and the reason is stored in the marker.

   > Why: in one real case findings were applied AFTER the adversarial pass, the
   > marker was rewritten as a mechanical step because HEAD had moved, and a
   > regression introduced by the fixes reached the branch with the gate green.
   > Re-running step 3 on the diff you are about to push is not optional.

   The PreToolUse hook `hooks/guard_pre_mr.py` blocks any
   `git push` on a non-master/main branch unless the marker covers the current
   tree (bypass for non-review branches: `PRE_MR_BYPASS=1 git push ...`; a branch that changes only `.md` files under
   the docs-only prefix, `PRE_MR_DOCS_ONLY_PREFIX`, default `docs/`, is exempt).
   Write the marker and push in SEPARATE commands: the hook evaluates the whole
   command BEFORE it runs, so a combined `write-marker && git push` blocks itself.
   

   **Turning the hook on (per person, once).** It ships installed but unwired,
   because a gate is a team decision. Add to your `~/.claude/settings.json`:

   ```json
   { "hooks": { "PreToolUse": [ { "matcher": "Bash",
       "hooks": [ { "type": "command",
                    "command": "python3 ~/.claude/hooks/guard_pre_mr.py" } ] } ] } }
   ```

   On Windows use `python` and an absolute path in double quotes. Copy
   `hooks/guard_pre_mr.py` AND `hooks/pre_mr_marker.py` side by side - the hook
   imports the marker module from its own directory (without it, it falls
   back to a HEAD-only comparison).

   If a reviewer later finds something this gate missed — add the
   miss as a new lens in step 3 (this file is a living checklist).

## Scope

Applies to: every push to a branch with an open MR, and the initial push before
MR creation. Does NOT replace CI or team review — it exists so team review spends
time on design, not on nulls and cliffs.
