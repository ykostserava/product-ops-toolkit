# Hooks

Hooks are **hard guarantees** enforced by the Claude Code harness — unlike rules and
CLAUDE.md, which are guidance the model can (rarely) miss under pressure. Use hooks for
the things that must never slip.

| Hook | Event | What it guarantees |
|------|-------|--------------------|
| `secret_scan.py` | PreToolUse (Bash/PowerShell) | `git commit` is blocked when [gitleaks](https://github.com/gitleaks/gitleaks) finds a secret in the staged diff. Fails open if gitleaks isn't installed. |
| `guard_env.py` | PreToolUse (Write/Edit) | Claude cannot write or edit `.env*` files — credentials are edited by humans only. |

## Install

1. Copy the hook files somewhere stable, e.g. `~/.claude/hooks/`:

   ```bash
   mkdir -p ~/.claude/hooks
   cp hooks/secret_scan.py hooks/guard_env.py ~/.claude/hooks/
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
             { "type": "command", "command": "python ~/.claude/hooks/secret_scan.py", "timeout": 60 }
           ]
         },
         {
           "matcher": "Write|Edit",
           "hooks": [
             { "type": "command", "command": "python ~/.claude/hooks/guard_env.py", "timeout": 10 }
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
