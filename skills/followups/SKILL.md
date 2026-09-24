---
name: followups
description: Track open follow-ups (who you are waiting on, since when) in the canonical registry scripts/followups.json - view the aging list, sync candidates from your notes/memory with per-item approval, add/close/snooze entries, and draft per-person ping messages for items waiting too long (nudge mode - drafts only, never sends; sent pings are recorded so nobody gets nagged twice). Triggers on "followups", "follow-ups", "who are we waiting on", "open questions", "what did I forget to ask", "who to ping", "nudge".
---

# /followups

Canonical tracker for dated, person-addressed follow-ups ("ask Alex about
PROJ-328", "waiting on the payments team re prod access"). It complements -
does NOT replace - a product-scope backlog or radar document: that holds
scope gaps with scope-triggers; this registry holds follow-ups with a date
and a person. If a candidate has a scope-trigger instead of a person+date,
propose a radar row instead of a registry entry.

Engine: `scripts/followups.py` (stdlib only, tested in
`tests/test_followups.py`). Registry path override: `FOLLOWUPS_REGISTRY`.
Your own aliases (entries that are never nudge targets):
`FOLLOWUPS_SELF_ALIASES`, default `self,me`.

## Hard rules

- **Every registry write goes through `python scripts/followups.py ...`** -
  never edit `scripts/followups.json` with Edit/Write.
- **Sync writes only after per-item approval in THIS conversation.**
  Headless/non-interactive runs never write - view only.
- Zero issue-tracker writes. This skill touches only the local registry.
- Non-ASCII content in the registry is fine (local file; an ASCII-only rule,
  if your tracker has one, applies to API payloads only).

## Modes

### `/followups` (default - view)

Run `python scripts/followups.py list` and present open items sorted by age
(oldest first); flag items aged >= 5 working days. Mention the snoozed count.
`python scripts/followups.py stats` gives the triage view: age buckets
(over 30d / 15-30d / under 15d) and a per-person "worth a ping" summary.
Read-only.

### `/followups sync`

1. Scan for candidates (read-only):
   - your notes / auto-memory index and the files it points to, looking for
     markers such as "ask", "waiting on", "follow-up", "remind", "clarify
     with";
   - the backlog radar document, if you keep one (a status column may hide a
     dated follow-up);
   - recorded meetings newer than the last sync (default window: 7 days).
     Summarized meetings have an action-items section - take items owned by
     or requiring input from you. A meeting note that is only a raw transcript
     still counts: extract the action items addressed to you via a subagent,
     mark them with confidence, and say that the summary was missing. Source
     format: `meeting:<folder-name>`. Convert relative dates ("today", "by
     Friday") against the meeting date.
2. Load the current registry (`python scripts/followups.py list --all`) and
   dedupe candidates SEMANTICALLY against existing entries (same
   person+topic = same follow-up, wording may differ). Also collect open
   entries that the notes now show as resolved -> close candidates with a
   proposed outcome.
3. Present ONE table: `# | action (add/close) | what | who | source |
   evidence quote`. No candidate without an evidence quote.
4. **Gate (per item):** ask which numbers to apply. For each approved item
   run `python scripts/followups.py add "<what>" --who <X> --source <S>` or
   `... close <id> --outcome "<text>"`. Report each command's output.
   Anything not approved is dropped - do not stash it anywhere.

### `/followups nudge` (ping drafts - NEVER sends)

1. `python scripts/followups.py nudge-candidates` - JSON of open items
   waiting on someone else: overdue, or older than 7 days, and not pinged in
   the last 5 (`last_nudged` cooldown). Empty -> say so and stop.
2. Group by person and compose ONE ping draft per person, ready to paste
   into your chat tool: greeting, one bullet per item (what you are waiting
   for + since when + short context from the source), no bureaucratic tone,
   no registry ids inside the message text. Multi-item pings stay ONE
   message. Teams get a draft addressed to the team channel. Show each draft
   under a header `-> <who> (<items>)`.
3. This skill NEVER posts anywhere - the user copies and sends themselves.
4. **Gate (after the user says which pings they actually sent):** for each
   item covered by a sent ping run `python scripts/followups.py nudge <id>`
   (records `last_nudged`, keeps the cooldown honest). Unsent drafts are
   dropped - never record a nudge that did not happen.

### `/followups add | close | snooze` (manual passthrough)

Map the user's words onto the CLI and run it:
- `python scripts/followups.py add "<what>" --who <who> [--due YYYY-MM-DD] [--source <src>] [--opened YYYY-MM-DD]`
- `python scripts/followups.py close <id> --outcome "<what happened>"` (outcome is mandatory - the CLI rejects blank)
- `python scripts/followups.py snooze <id> --until YYYY-MM-DD`

On `ERROR:` output, relay the message verbatim and stop - do not retry with
guessed arguments.

## Registry shape

One JSON array; every entry: `id` (`fu-YYYY-MM-DD-NN`), `what`, `who`,
`opened`, `status` (`open|snoozed|closed`), plus nullable `due`,
`snoozed_until`, `source`, `closed`, `outcome`, `last_nudged`. A snooze that
has expired counts as open again (nothing flips the status automatically, so
consumers must use the module's `effectively_open`, not the raw status).
