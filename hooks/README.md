# Hooks

Hooks are **hard guarantees** enforced by the Claude Code harness — unlike rules and
CLAUDE.md, which are guidance the model can (rarely) miss under pressure. Use hooks for
the things that must never slip.

| Hook | Event | What it guarantees |
|------|-------|--------------------|
| `secret_scan.py` | PreToolUse (Bash/PowerShell) | `git commit` is blocked when [gitleaks](https://github.com/gitleaks/gitleaks) finds a secret in the staged diff. Fails open if gitleaks isn't installed. |
| `guard_env.py` | PreToolUse (Write/Edit) | Claude cannot write or edit `.env*` files — credentials are edited by humans only. |
| `guard_pre_mr.py` + `pre_mr_marker.py` | PreToolUse (Bash/PowerShell) | `git push` to a non-master/main branch is blocked unless the `/pre-mr` gate marker covers the CURRENT tree (a content digest, not a HEAD sha: an amend keeps it, applying review findings invalidates it). Dry runs, deletions, docs-only branches (`PRE_MR_DOCS_ONLY_PREFIX`, default `docs/`) and an explicit `PRE_MR_BYPASS=1` pass. Fails open on its own errors. Both files must sit side by side. 60+ must-fire / must-not-fire cases in `tests/test_guard_pre_mr.py`. |
| `model_staleness.py` | SessionStart | Adds a one-paragraph reminder to the session context: verify model ids, API shapes, library versions and CLI flags against current docs or code instead of asserting them from training data. |
| `guard_jira_ascii.py` | PreToolUse (Bash/PowerShell) | A shell command that actually SENDS a request to a Jira/Confluence host (curl, Invoke-RestMethod, python requests/urllib, node fetch, `jira_api.py add-comment`, ...) is denied when it contains a non-ASCII character. Local work that merely mentions the host (notes, greps, commits) stays untouched. Hosts: anything matching `jira.` / `confluence.` / `atlassian.`, plus `GUARD_JIRA_HOSTS=host1,host2`. Tested by `tests/test_guard_jira_ascii.py` with the inputs it must fire on and the ones it must not. |

## Install

1. Copy the hook files somewhere stable, e.g. `~/.claude/hooks/`:

   ```bash
   mkdir -p ~/.claude/hooks
   cp hooks/*.py ~/.claude/hooks/
   ```

2. Wire them in `~/.claude/settings.json` (user-wide) or `.claude/settings.json`
   (per project):

   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Bash|PowerShell",
           "hooks": [
             { "type": "command", "command": "python ~/.claude/hooks/secret_scan.py", "timeout": 60 },
             { "type": "command", "command": "python ~/.claude/hooks/guard_jira_ascii.py", "timeout": 10 },
             { "type": "command", "command": "python ~/.claude/hooks/guard_pre_mr.py", "timeout": 20 }
           ]
         },
         {
           "matcher": "Write|Edit",
           "hooks": [
             { "type": "command", "command": "python ~/.claude/hooks/guard_env.py", "timeout": 10 }
           ]
         }
       ],
       "SessionStart": [
         {
           "hooks": [
             { "type": "command", "command": "python ~/.claude/hooks/model_staleness.py", "timeout": 15 }
           ]
         }
       ]
     }
   }
   ```

   On Windows, use a full path to the script in double quotes
   (`"command": "python \"C:\\Users\\you\\.claude\\hooks\\secret_scan.py\""`).

3. For `secret_scan.py`, install gitleaks and make sure it is on `PATH`. The hook
   fails open without it — arm it by installing the binary.

## Design notes

- Both hooks **fail open** on their own errors: a broken hook must never lock a
  developer out of committing. The deny path fires only on a *confirmed* finding.
- False positives in gitleaks are handled with an allowlist entry in `.gitleaks.toml`,
  never by disabling the hook.
