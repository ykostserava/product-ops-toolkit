---
name: Jira API Best Practices
description: ASCII-only safety rule for Jira API calls, default priority, scope confirmation
type: pattern
---

# Jira API Best Practices

## Rule 1: ASCII-Only in API Calls

When creating or updating Jira issues programmatically, all text sent to the Jira API (summaries, descriptions, comments) should be ASCII-only.

**Why:** Some Jira Server instances and older plugins return encoding errors or store garbled bytes when non-ASCII characters land in issue fields. The safest default is ASCII (bytes 0-127) for anything written through the REST API.

**How to apply:** Before creating a Jira issue, scan all text fields (summary, description) for non-ASCII characters. Either transliterate or substitute with ASCII equivalents.

### Characters to Avoid

| Character | Unicode | Reason | ASCII Substitute |
|-----------|---------|--------|------------------|
| -> (arrow) | U+2192 | Often added by auto-format | `->` (dash-greater) |
| <- (arrow) | U+2190 | Same | `<-` |
| EUR sign | U+20AC | Currency symbol | `EUR` |
| GBP sign | U+00A3 | Currency symbol | `GBP` |
| Non-Latin scripts | U+0400+ | Server encoding | Transliterate or translate |
| Checkmark | U+2713 | Visual marker | `[x]` or `Done` |
| Cross mark | U+2717 | Visual marker | `[ ]` or `Failed` |
| Bullet | U+2022 | List marker | `-` or `*` |
| Ellipsis | U+2026 | Auto-replace | `...` |
| En dash | U+2013 | Auto-replace | `-` |
| Em dash | U+2014 | Auto-replace | `--` |
| Smart quotes | U+201C-F | Auto-replace | `"` or `'` |

### Common Sources of Unicode Contamination

1. **Copy-paste** from Confluence, Word, Slack, or browser rich-text editors -- smart quotes and em dashes get inserted silently.
2. **Auto-replacements** in editors -- `->` becomes arrow, `...` becomes ellipsis, straight quotes become smart quotes.
3. **Language-specific content** -- Cyrillic, Arabic, CJK scripts should be transliterated or translated before hitting the Jira API (unless you've confirmed your instance handles them).

### Detection

**Quick check via grep:**
```bash
# Show lines with non-ASCII bytes
grep -P '[^\x00-\x7F]' file.md
grep -n -P '[^\x00-\x7F]' file.md
```

**Python one-liner:**
```bash
python -c "c=open('file.md','rb').read(); print('Unicode found' if any(b>127 for b in c) else 'ASCII only')"
```

**Automated check via hook:**
Add a PostToolUse hook to `.claude/settings.json` that runs after every `.md` edit. Example that prints a system message when non-ASCII is detected:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python -c \"import json,sys,os;d=json.load(sys.stdin);fp=d.get('tool_input',{}).get('file_path') or d.get('tool_response',{}).get('filePath','');(fp and fp.endswith('.md') and os.path.exists(fp) and any(b>127 for b in open(fp,'rb').read())) and print(json.dumps({'systemMessage':f'WARNING: Non-ASCII characters in {fp}. Jira API may reject.'}))\""
          }
        ]
      }
    ]
  }
}
```

## Rule 2: Default Priority "High"

When creating Jira issues programmatically without an explicit priority, default to `High`.

**Why:** Jira requires the priority field on most issue types. `High` is a safe default that avoids workflow rule violations (e.g. some projects forbid "Highest" unless an incident is declared).

**Never use:** `ASAP` as a priority -- it's not a standard Jira value and usually isn't in the priority scheme.

## Rule 3: Confirm Scope Before Creating

Before creating a batch of issues in Jira, list them and get user approval.

**Why:** Prevents creating duplicate work (e.g. web stories when the feature already exists on web), and catches scope misunderstanding before it becomes cleanup work.

**How to apply:**
1. Generate the breakdown (markdown) with all stories
2. Show user: "I will create these N stories in project X: [list with titles]"
3. User confirms, adjusts scope, or rejects
4. Only then call Jira create API

## Rule 4: Separate Initiative and Delivery Projects

Many Jira setups split planning (initiative-level) and delivery (epic/story-level) into separate projects. If yours does:

- Create the **initiative** in the planning / support project
- Create **epics, stories, tasks** in the delivery project
- Link: epic -> initiative via "Relates To"; story/task -> epic via "Epic Link" custom field

The epic link custom field ID varies per Jira instance (`customfield_10091`, `customfield_10014`, etc.). Put it in your `config.yml` under `jira.epic_link_field`.

## Rule 5: Be Careful With Batch Deletes

When cleaning up issues you just created (e.g. after realizing the breakdown needs revision):

- Prefer **moving to a "trash" status** over hard delete, if your workflow allows
- Keep a record of deleted keys before destroying
- Never batch-delete without verbose confirmation -- Jira rarely lets you undo

## Common Pitfalls

1. **Pasting from Confluence** drops em dashes into Jira -> encoding errors
2. **Copying from Slack** drops smart quotes -> garbled descriptions
3. **Scraping from the web** drops arrows and bullets -> API rejection
4. **Using unicode emoji in titles** -> breaks Jira mobile apps on older clients
5. **Using HTML in description** when field expects Jira wiki markup -> malformed rendering

## Related

- `initiative-breakdown-pattern.md` - how breakdown uses these rules
- `.claude/settings.json` -> hooks section - where to configure ASCII guard
