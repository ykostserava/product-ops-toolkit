---
name: handoff
description: Compact the current session into a handoff document so a fresh session can pick the work up without re-reading this one. User-invoked only.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

# /handoff

Write a handoff document summarising the current conversation so a fresh
agent can continue the work. This is the mechanism behind the discipline that
**plan, audit and execution are different sessions**: the next session starts
from this file, not from a re-read of this one.

Adapted from `handoff` in [mattpocock/skills](https://github.com/mattpocock/skills)
(MIT, see `NOTICE.md` next to this file).

## Usage

```
/handoff                                  # generic continuation
/handoff "execute the breakdown of <initiative>"   # tailor to the next session's job
/handoff "audit docs/specs/x.md"          # an audit session must read the doc itself - hand over the PATH, not a retelling
```

## Where it goes

`briefings/handoffs/handoff-<YYYY-MM-DD>-<slug>.md` in the repo (create the
directory if missing), or whichever gitignored output directory your project
keeps - the file must survive the session without polluting git. Never the
session scratchpad (it dies with the session) and never `/tmp`. If the user
wants it reviewable by others, a tracked planning-docs folder is the home.
Print the absolute path at the end.

## What goes in

- **Goal** of the work in one line, and what the next session is for (from
  the argument, if given).
- **Where the work is**: repo and branch, worktree path if not the main one,
  what is committed / staged / unstaged / untracked, MR and ticket keys, the
  commands that produce the current state (test, lint, gate).
- **State**: what is done and verified, what is done but unverified, what is
  not started. Verified means a test, a command output or a source was seen -
  say which.
- **Decisions and rulings** made in this session, each with who made it
  (user / model / external person by role) and the one-line why. Keep the
  `[user]` / `[as recommended]` tag if the decision came out of `/grill-me`.
  A user ruling that reversed a model proposal is worth a line of its own.
- **Tried and rejected**: dead ends walked this session and why they are
  dead, so the next session does not walk them again.
- **Open questions** and who they wait on. Propose (do not apply) follow-up
  entries for anything waiting on a person outside the repo.
- **Dangers**: one-way actions ahead (tracker transitions that cannot be
  undone, closed resolutions, external posts), permission or environment
  traps hit this session.
- **Suggested skills** the next session should call, in order, with the
  argument each needs, and the first command to run.

## What stays out

- Content already captured elsewhere - specs, ADRs, initiative docs, tickets,
  commits, diffs, memory files. Reference by path, key or URL instead.
- For an audit handoff: no retelling of the scheme. The auditors must read
  the document itself; the handoff carries the path and the open questions
  only.
- Secrets and PII: redact API keys, tokens, emails, customer data. Refer to
  people by role where the name is not needed.

Auto-memory is not replaced by this file: rulings and facts every future
session needs still go to your memory system as usual. The handoff carries
only the next session's working state.

## Done

The file exists at the printed path, and a reader with no other context can
locate the working tree, run the first named command, and see the same
state this session sees. "Suggested skills" is non-empty and the first
command is named.
