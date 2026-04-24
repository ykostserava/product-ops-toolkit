# Morning Briefing Pipeline

Automated daily Jira digest for Product Owners and Delivery Managers.

**What it does:**
1. Fetches open tickets from your Jira project (via any REST client that takes a JQL query and outputs JSON)
2. Categorizes them: blockers, stuck >3 days, new last 24h, WIP per assignee
3. Asks Claude to write a 2-sentence "Top focus today"
4. Renders an HTML dashboard + markdown digest + structured JSON
5. Creates or updates a Google Calendar event so you get a phone + laptop notification each morning

**End result:** open your phone at 09:15 and see the title "Product Briefing - 3 blockers / 4 stuck / 2 new" with top focus in the description. Open `latest.html` on your laptop for the full dashboard.

---

## Architecture

```
jira_api.py (Python, direct Jira API)
      |
      v  raw JSON
render_briefing.py
      |
      +-- categorizes (Python, deterministic)
      +-- claude -p "Top focus today" (2-sentence AI synthesis)
      +-- claude -p "Update Calendar event" (Google Calendar MCP)
      |
      v
briefings/briefing-YYYY-MM-DD.{html,md,json}
briefings/latest.{html,md}
```

**Why this split:** Python handles the mechanical work (fetch, categorize, render) deterministically. Claude handles only the part that needs intelligence (the "Top focus" recommendation + Calendar orchestration). Faster, cheaper, more reliable than asking Claude to do the whole pipeline.

---

## Requirements

1. **Jira API script** - a CLI that takes `search "<JQL>" --max=N --format=json` and outputs Jira issues as JSON. Many Claude Code plugin suites ship one; if yours doesn't, a 50-line Python script using `requests` + Jira REST API does the job. Point `JIRA_API_SCRIPT` at it.
2. **Python 3.10+** - any Python with stdlib is enough. The render script has no third-party dependencies.
3. **`claude` CLI** - [Claude Code](https://docs.claude.com/claude-code) installed and on PATH (optional - if missing, Top focus and Calendar event are skipped gracefully).
4. **Google Calendar MCP** - configured in your Claude Code setup (optional - set `NO_CALENDAR=1` to disable).

---

## Configuration

Set these environment variables (or export them in the shell script):

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `JIRA_API_TOKEN` | yes | Personal access token for Jira | `NTU0NDYzM...` |
| `JIRA_BASE_URL` | yes | Base URL of your Jira instance | `https://jira.example.com` |
| `JIRA_PROJECT` | yes | Project key to query | `PROJ` |
| `JIRA_API_SCRIPT` | yes | Path to the Jira REST CLI | `/path/to/jira_api.py` |
| `PYTHON_BIN` | no | Path to real Python (avoids MS Store stub on Windows) | `./venv/Scripts/python.exe` |
| `CLAUDE_CLI` | no | Path to claude CLI | `/usr/local/bin/claude` |
| `PRODUCT_NAME` | no | Shown in dashboard header and event title | `Acme Wallet` |
| `TEAM_NAME` | no | Shown in dashboard footer | `Wallet Team` |
| `OUTPUT_DIR` | no | Where briefings are written | `./briefings` |
| `BRIEFING_EVENT_TIME` | no | HH:MM for Calendar event (default: 09:15) | `08:30` |
| `BRIEFING_TZ` | no | IANA timezone (default: Europe/Warsaw) | `America/New_York` |
| `JIRA_BOARD_URL` | no | Link shown in dashboard footer | `https://jira.example.com/secure/RapidBoard.jspa?rapidView=123` |
| `NO_OPEN` | no | Set to skip opening HTML in browser | `1` |
| `NO_CALENDAR` | no | Set to skip Google Calendar integration | `1` |

---

## Test Manually

```bash
export JIRA_API_TOKEN=your-token
export JIRA_BASE_URL=https://jira.example.com
export JIRA_PROJECT=PROJ
export JIRA_API_SCRIPT=/path/to/jira_api.py
export PRODUCT_NAME="Acme Wallet"
export TEAM_NAME="Wallet Team"

bash pipelines/morning-briefing/morning-briefing.sh
```

Expected: one file per day in `briefings/`, plus `latest.html` and `latest.md`. Logs go to `briefings/briefing.log`.

---

## Schedule on Windows (Task Scheduler)

Create a task via Task Scheduler GUI or PowerShell:

```powershell
$action = New-ScheduledTaskAction `
  -Execute 'C:\Program Files\Git\bin\bash.exe' `
  -Argument '-lc "NO_OPEN=1 /path/to/pipelines/morning-briefing/morning-briefing.sh"' `
  -WorkingDirectory 'C:\path\to\your\workspace'

$trigger = New-ScheduledTaskTrigger `
  -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
  -At '08:00'

$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
  -TaskName "Morning Briefing" `
  -Description "Daily Jira briefing pipeline" `
  -Action $action -Trigger $trigger -Settings $settings -Force
```

`-StartWhenAvailable` catches up if the laptop was off at 08:00 - task fires as soon as you log in.

---

## Schedule on macOS / Linux (cron)

```cron
# m h dom mon dow command
0 8 * * 1-5 cd /path/to/workspace && NO_OPEN=1 bash pipelines/morning-briefing/morning-briefing.sh >> briefings/cron.log 2>&1
```

---

## Schedule on macOS (launchd)

More reliable than cron for long-running Macs. Create `~/Library/LaunchAgents/com.you.morning-briefing.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.you.morning-briefing</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>cd /path/to/workspace &amp;&amp; NO_OPEN=1 bash pipelines/morning-briefing/morning-briefing.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
  </array>
</dict>
</plist>
```

Load with `launchctl load ~/Library/LaunchAgents/com.you.morning-briefing.plist`.

---

## Google Calendar Recurring Event (Optional)

For notifications to fire even on days the script didn't run, create a **recurring master event** in Google Calendar once:

- Title: "{Product} Briefing (auto-updated)"
- When: every weekday at your target time (e.g. 09:15)
- Duration: 15 minutes
- Reminder: popup 0 minutes before
- Description: placeholder with troubleshooting instructions

Each morning the pipeline will find today's instance of this recurring event and update it with the actual briefing data. On days the pipeline doesn't run, you still see the placeholder reminder to investigate.

You can create the recurring event via an interactive Claude Code session that has the Google Calendar MCP enabled.

---

## Troubleshooting

**"JIRA_API_TOKEN not set"** - export it or regenerate from your Jira profile.

**Script hangs at "Fetching JQL"** - on Windows, `python3` may resolve to the Microsoft Store stub. Set `PYTHON_BIN=/path/to/venv/Scripts/python.exe` explicitly.

**Empty briefing** - no matching tickets. Adjust the JQL in `morning-briefing.sh` or check that `JIRA_PROJECT` is right.

**"claude CLI not found"** - Top focus and Calendar event skipped. Install Claude Code or set `CLAUDE_CLI` to the absolute path.

**Calendar event not updating** - verify Google Calendar MCP is configured in your Claude Code setup. Run `claude -p "list today's calendar events"` interactively to confirm auth.

**Unicode warning in Jira** - the PostToolUse hook from `.claude/settings.json` can catch non-ASCII in .md files before they hit Jira. See `patterns/jira-api-best-practices.md`.

---

## Customizing

Edit `render_briefing.py`:
- Change categorization thresholds in `categorize()` (e.g. "stuck" = >5 days instead of >3)
- Change Top focus prompt in `generate_top_focus()`
- Change dashboard visual in `HTML_TEMPLATE` (CSS + layout)
- Add new sections (e.g. "Ready for review") by adding to `categorize()` + template

Edit `morning-briefing.sh`:
- Change the JQL if you want a different scope than "all non-Done in project"
- Add additional environment variables
