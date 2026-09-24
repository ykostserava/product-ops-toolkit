---
name: dup-check
description: Check whether a ticket or a described feature already exists on the board (or another JQL scope) - deterministic TF-IDF shortlist from scripts/duplicate_scan.py plus a judged verdict per match (duplicate / overlaps / distinct) with evidence. Read-only, zero Jira writes. Triggers on "is this a duplicate?", "duplicate check", "do we already have this?", "was this already filed?", "check for duplicates".
---

# /dup-check

Answer "do we already have this?" with evidence instead of memory. Thin
orchestrator: deterministic shortlist (`scripts/duplicate_scan.py`, TF-IDF
over summary+description, closed issues included - duplicates usually hide
in done scope) -> judged verdict per match. **Read-only: never writes to
Jira, never closes or links anything** - acting on a confirmed duplicate
(Duplicate-close, Relate link) is the user's follow-up call, through
`/jira-package` and its gates.

Corpus default: `project = <project_key>` from `scripts/jira-config.json`.
Extra stopwords for your domain: `extra_stopwords` in the same file.

## Usage

```
/dup-check EXT-15021              # a ticket against the board
/dup-check "round-up savings"     # free text against the board
/dup-check PROJ-457 --corpus "project = DSGN"   # another corpus
```

## Flow

1. **Gate 0:** `python scripts/jira_api.py search "project = PROJ" --max=1 --format=brief`;
   on failure STOP ("Jira unreachable - check network/VPN and JIRA_API_TOKEN").
   Read mechanics (batch fetch, exit codes): `patterns/jira-read-protocol.md`.
2. **Shortlist:** `python scripts/duplicate_scan.py --query <KEY>` (or
   `--text "..."`), `--corpus-jql` when the user names another scope. Exit 1
   AUTH = stop; exit 2 = score what arrived, say what failed.
3. **Judge every match >= 0.12** (do not trust scores as verdicts - they only
   rank): read the match summaries (fetch full descriptions via
   `python scripts/jira_api.py get <key>` only for the top candidates where
   the summary is not conclusive) and label each:
   - **duplicate** - same ask; name which side supersedes which (an existing
     result means the newcomer closes as Done/Duplicate, not Won't Do);
   - **overlaps** - shared scope, different ask (say what differs);
   - **distinct** - lexical coincidence; drop from the answer unless top-3.
4. **Think outside the corpus:** if the query smells like scope known to
   live in another project or team, say so and offer ONE targeted re-run
   with a narrower `--corpus-jql` - never a fishing expedition over a whole
   big project.
5. **Answer:** verdict first ("duplicate of PROJ-x", "overlaps PROJ-y", "no
   match"), then the evidence table `key | status | score | shared / differs`.
   If nothing survives judgment, say plainly that the scan found no duplicate
   - and name the corpus it checked.

## What this is NOT

- Not a closer/linker - it only reports; Duplicate-closes and Relate links
  are separate, user-approved actions.
- Not semantic search magic - TF-IDF misses reworded twins; a "no duplicate"
  answer is evidence of absence in WORDING, and the answer must carry that
  caveat when the score table is thin.
