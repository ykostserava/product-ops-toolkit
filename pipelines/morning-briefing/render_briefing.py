#!/usr/bin/env python3
"""
Render morning Jira briefing from raw Jira JSON into HTML + Markdown.

Pipeline stage: takes raw output of `jira_api.py search` and produces
visual dashboard + plain-text briefing.

Usage:
    python3 render_briefing.py <raw_jira.json> <output_base_path>

Produces:
    <base>.html  - dashboard
    <base>.md    - markdown digest
    <base>.json  - categorized structured data

Environment variables:
    JIRA_BASE_URL         - base URL of your Jira instance (required)
    JIRA_BOARD_URL        - optional link to your kanban board
    PRODUCT_NAME          - name shown in dashboard header (default: "Product")
    TEAM_NAME             - team shown in dashboard footer (default: "Team")
    BRIEFING_EVENT_TIME   - HH:MM for Calendar event (default: "09:15")
    BRIEFING_TZ           - IANA timezone (default: "Europe/Warsaw")
    NO_CALENDAR           - set to skip Google Calendar integration

Optional: if `claude` CLI is on PATH, generates a "Top focus today" blurb
and creates/updates a Google Calendar event via the Google Calendar MCP.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

JIRA_BASE = os.environ.get("JIRA_BASE_URL", "https://jira.example.com")
BOARD_URL = os.environ.get("JIRA_BOARD_URL", JIRA_BASE)
PRODUCT_NAME = os.environ.get("PRODUCT_NAME", "Product")
TEAM_NAME = os.environ.get("TEAM_NAME", "Team")

# ---------- categorization ----------

def parse_jira_date(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def days_ago(dt):
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    return (now - dt).days


def categorize(issues):
    blockers, stuck, new_24h, in_progress = [], [], [], []
    wip_by_assignee = {}

    for issue in issues:
        f = issue.get("fields", {})
        key = issue.get("key", "?")
        summary = f.get("summary", "")
        assignee = (f.get("assignee") or {}).get("displayName") or "unassigned"
        priority = (f.get("priority") or {}).get("name", "")
        labels = f.get("labels", []) or []
        status = (f.get("status") or {}).get("name", "")
        status_cat = ((f.get("status") or {}).get("statusCategory") or {}).get("name", "")
        updated = parse_jira_date(f.get("updated"))
        created = parse_jira_date(f.get("created"))
        d_updated = days_ago(updated)
        d_created = days_ago(created)

        base = {
            "key": key,
            "summary": summary[:110] + ("..." if len(summary) > 110 else ""),
            "assignee": assignee,
            "priority": priority,
            "status": status,
            "days_since_update": d_updated if d_updated is not None else 0,
            "days_since_create": d_created if d_created is not None else 0,
            "url": f"{JIRA_BASE}/browse/{key}",
        }

        is_blocker = priority in ("Highest", "High") or any(
            "block" in l.lower() for l in labels
        )
        if is_blocker:
            blockers.append(base)

        if d_updated is not None and d_updated > 3 and status_cat != "Done":
            stuck.append(base)

        if d_created is not None and d_created < 1:
            new_24h.append(base)

        if status_cat == "In Progress":
            in_progress.append(base)
            wip_by_assignee[assignee] = wip_by_assignee.get(assignee, 0) + 1

    blockers.sort(key=lambda x: -x["days_since_update"])
    stuck.sort(key=lambda x: -x["days_since_update"])
    new_24h.sort(key=lambda x: x["days_since_create"])
    wip_rows = sorted(wip_by_assignee.items(), key=lambda kv: -kv[1])

    return {
        "blockers": blockers,
        "stuck": stuck,
        "new_24h": new_24h,
        "wip": [{"name": n, "count": c} for n, c in wip_rows],
        "total_open": len(issues),
        "total_wip": len(in_progress),
    }


# ---------- Claude: Top focus ----------

def generate_top_focus(data):
    """Optional: ask Claude for a 2-sentence 'Top focus today' recommendation."""
    claude = os.environ.get("CLAUDE_CLI", "claude")
    try:
        summary = json.dumps(
            {
                "blockers": [{"key": b["key"], "summary": b["summary"], "days": b["days_since_update"]} for b in data["blockers"]],
                "stuck": [{"key": s["key"], "days": s["days_since_update"]} for s in data["stuck"]],
                "new_24h_count": len(data["new_24h"]),
                "wip": data["wip"],
            },
            indent=2,
        )
        prompt = (
            f"You are advising the Product Owner of the {PRODUCT_NAME} Jira project. "
            "Below is a categorized summary of today's open tickets. "
            "Respond with exactly 2 short sentences telling the PO what to focus on "
            "in the next 4 hours. No preamble. ASCII only. "
            "Kanban workflow - never mention sprints or velocity.\n\n"
            f"Data:\n{summary}"
        )
        result = subprocess.run(
            [claude, "-p", "--allowedTools", ""],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# ---------- Claude: Google Calendar event ----------

def create_calendar_event(data, top_focus, md_path, html_path, date_str):
    """Create or update today's briefing event via Google Calendar MCP."""
    if os.environ.get("NO_CALENDAR"):
        print("Calendar event: skipped (NO_CALENDAR set)")
        return

    claude = os.environ.get("CLAUDE_CLI", "claude")
    event_time = os.environ.get("BRIEFING_EVENT_TIME", "09:15")
    tz = os.environ.get("BRIEFING_TZ", "Europe/Warsaw")

    title = (
        f"{PRODUCT_NAME} Briefing {date_str} - "
        f"{len(data['blockers'])} blockers / "
        f"{len(data['stuck'])} stuck / "
        f"{len(data['new_24h'])} new"
    )

    description = (
        (f"TOP FOCUS\n{top_focus}\n\n" if top_focus else "")
        + f"STATS\n"
        f"- Blockers: {len(data['blockers'])}\n"
        f"- Stuck >3d: {len(data['stuck'])}\n"
        f"- New 24h: {len(data['new_24h'])}\n"
        f"- WIP total: {data['total_wip']}\n"
        f"- Open total: {data['total_open']}\n\n"
    )

    # top 5 blockers inline for mobile readability
    if data["blockers"]:
        description += "BLOCKERS (top 5)\n"
        for b in data["blockers"][:5]:
            description += f"- {b['key']} {b['summary']} ({b['days_since_update']}d)\n"
        description += "\n"

    if data["stuck"]:
        description += "STUCK (top 5)\n"
        for s in data["stuck"][:5]:
            description += f"- {s['key']} {s['summary']} ({s['days_since_update']}d)\n"
        description += "\n"

    description += f"Full dashboard: file:///{str(html_path).replace(chr(92), '/')}\n"
    description += f"Markdown: file:///{str(md_path).replace(chr(92), '/')}\n"

    prompt = f"""Create or update today's {PRODUCT_NAME} Morning Briefing event in my primary Google Calendar.

Step 1: List today's events on my primary calendar. Look for any event whose title starts with "{PRODUCT_NAME} Briefing".
Step 2: If such an event exists for today, UPDATE it with the new title and description below.
        If not, CREATE a new event.

Event details:
- Calendar: primary
- Title: {title}
- Start: {date_str}T{event_time}:00
- End: {date_str}T{event_time[:2]}:45:00
- Timezone: {tz}
- Reminder: popup 0 minutes before start
- Description:
---
{description}
---

Respond with exactly one short line: "CREATED <id>" or "UPDATED <id>" or "ERROR <reason>".
Do not narrate intermediate steps.
"""

    allowed_tools = (
        "mcp__claude_ai_Google_Calendar__list_events,"
        "mcp__claude_ai_Google_Calendar__list_calendars,"
        "mcp__claude_ai_Google_Calendar__create_event,"
        "mcp__claude_ai_Google_Calendar__update_event"
    )

    try:
        result = subprocess.run(
            [claude, "-p", "--allowedTools", allowed_tools],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=180,
        )
        out = (result.stdout or "").strip().splitlines()
        tail = out[-1] if out else "(empty)"
        if result.returncode == 0:
            print(f"Calendar event: {tail[:150]}")
        else:
            err = (result.stderr or "").strip().splitlines()
            print(f"Calendar event FAILED (exit {result.returncode}): "
                  f"{(err[-1] if err else tail)[:200]}")
    except FileNotFoundError:
        print("Calendar event: skipped (claude CLI not found)")
    except subprocess.TimeoutExpired:
        print("Calendar event: skipped (timeout)")


# ---------- renderers ----------

def render_markdown(data, date_str, top_focus):
    lines = [f"# {PRODUCT_NAME} Morning Briefing - {date_str}", ""]
    lines.append(f"**Open tickets:** {data['total_open']} | **WIP:** {data['total_wip']}")
    lines.append("")

    if top_focus:
        lines += ["## Top focus today", "", top_focus, ""]

    def section(title, items, fmt):
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("- None")
        else:
            for it in items:
                lines.append(fmt(it))
        lines.append("")

    section(
        f"Blockers ({len(data['blockers'])})",
        data["blockers"],
        lambda b: f"- [{b['key']}]({b['url']}) {b['summary']} | {b['assignee']} | {b['priority']} | {b['days_since_update']}d",
    )
    section(
        f"Stuck >3d ({len(data['stuck'])})",
        data["stuck"],
        lambda s: f"- [{s['key']}]({s['url']}) {s['summary']} | {s['status']} | {s['assignee']} | {s['days_since_update']}d",
    )
    section(
        f"New last 24h ({len(data['new_24h'])})",
        data["new_24h"],
        lambda n: f"- [{n['key']}]({n['url']}) {n['summary']} | {n['assignee']} | {n['priority']}",
    )

    lines.append(f"## WIP per assignee ({data['total_wip']} total)")
    lines.append("")
    if not data["wip"]:
        lines.append("- None")
    else:
        for w in data["wip"]:
            lines.append(f"- {w['name']}: {w['count']}")
    lines.append("")

    return "\n".join(lines)


def render_html(data, date_str, top_focus, generated_at):
    def ticket_row(t, extra=""):
        return (
            f'<a class="ticket" href="{t["url"]}" target="_blank">'
            f'<span class="tkey">{t["key"]}</span>'
            f'<span class="tsummary">{html_escape(t["summary"])}</span>'
            f'<span class="tmeta">{html_escape(t.get("assignee",""))} &middot; {extra}</span>'
            f"</a>"
        )

    blockers_html = (
        "\n".join(
            ticket_row(b, f"{html_escape(b['priority'])} &middot; {b['days_since_update']}d")
            for b in data["blockers"]
        )
        or '<div class="empty">No blockers. Nice.</div>'
    )
    stuck_html = (
        "\n".join(
            ticket_row(s, f"{html_escape(s['status'])} &middot; {s['days_since_update']}d stuck")
            for s in data["stuck"]
        )
        or '<div class="empty">Nothing stuck over 3 days.</div>'
    )
    new_html = (
        "\n".join(
            ticket_row(n, f"{html_escape(n['priority'])} &middot; new")
            for n in data["new_24h"]
        )
        or '<div class="empty">No new tickets since yesterday.</div>'
    )

    max_wip = max((w["count"] for w in data["wip"]), default=1)
    wip_html = (
        "\n".join(
            f'<div class="wip-row">'
            f'<div class="wip-name">{html_escape(w["name"])}</div>'
            f'<div class="wip-bar"><div class="wip-fill" style="width:{int(w["count"]/max_wip*100)}%"></div></div>'
            f'<div class="wip-count">{w["count"]}</div>'
            f"</div>"
            for w in data["wip"]
        )
        or '<div class="empty">No WIP.</div>'
    )

    focus_block = (
        f'<div class="focus"><div class="focus-label">Top focus today</div>'
        f'<div class="focus-text">{html_escape(top_focus)}</div></div>'
        if top_focus
        else ""
    )

    return HTML_TEMPLATE.format(
        date=date_str,
        product=PRODUCT_NAME,
        team=TEAM_NAME,
        total_open=data["total_open"],
        total_wip=data["total_wip"],
        blockers_count=len(data["blockers"]),
        stuck_count=len(data["stuck"]),
        new_count=len(data["new_24h"]),
        wip_count=data["total_wip"],
        blockers=blockers_html,
        stuck=stuck_html,
        new=new_html,
        wip=wip_html,
        focus=focus_block,
        board_url=BOARD_URL,
        generated_at=generated_at,
    )


def html_escape(s):
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{product} Morning Briefing - {date}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background:#0a0a0a; color:#e5e5e5;
  font-family:'Segoe UI',-apple-system,system-ui,sans-serif;
  padding:0; min-height:100vh;
}}
.container {{ max-width:1100px; margin:0 auto; padding:40px 32px 64px; }}
.header {{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:32px; padding-bottom:20px; border-bottom:1px solid #1a1a1a; }}
.title {{ font-size:24px; font-weight:600; color:#fff; letter-spacing:-0.3px; }}
.title span {{ color:#f59e0b; }}
.subtitle {{ font-size:12px; color:#666; text-transform:uppercase; letter-spacing:2px; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:32px; }}
.kpi {{ background:#111; border:1px solid #1f1f1f; padding:20px; border-radius:6px; }}
.kpi-label {{ font-size:11px; color:#666; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:8px; }}
.kpi-value {{ font-size:32px; font-weight:600; font-family:Consolas,monospace; }}
.kpi.warn .kpi-value {{ color:#ef4444; }}
.kpi.caution .kpi-value {{ color:#f59e0b; }}
.kpi.info .kpi-value {{ color:#60a5fa; }}
.kpi.neutral .kpi-value {{ color:#4ade80; }}
.focus {{ background:linear-gradient(135deg,#1a1207,#0a0a0a); border:1px solid #3a2a07; border-left:3px solid #f59e0b; padding:20px 24px; border-radius:6px; margin-bottom:32px; }}
.focus-label {{ font-size:10px; color:#f59e0b; text-transform:uppercase; letter-spacing:2.5px; margin-bottom:8px; font-weight:600; }}
.focus-text {{ font-size:15px; color:#e5e5e5; line-height:1.6; }}
.section {{ margin-bottom:32px; }}
.section-head {{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #1a1a1a; }}
.section-title {{ font-size:13px; color:#fff; text-transform:uppercase; letter-spacing:2px; font-weight:600; }}
.section-title.warn {{ color:#ef4444; }}
.section-title.caution {{ color:#f59e0b; }}
.section-title.info {{ color:#60a5fa; }}
.section-count {{ font-size:11px; color:#555; font-family:Consolas,monospace; }}
.ticket {{ display:grid; grid-template-columns:90px 1fr auto; gap:16px; align-items:center; padding:10px 14px; background:#0f0f0f; border:1px solid #1a1a1a; border-radius:4px; margin-bottom:6px; text-decoration:none; color:#ccc; transition:all 0.15s; }}
.ticket:hover {{ background:#141414; border-color:#2a2a2a; }}
.tkey {{ font-family:Consolas,monospace; font-size:13px; color:#f59e0b; font-weight:600; }}
.tsummary {{ font-size:13px; color:#ddd; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.tmeta {{ font-size:11px; color:#666; font-family:Consolas,monospace; }}
.empty {{ padding:14px; color:#555; font-size:13px; font-style:italic; }}
.wip-row {{ display:grid; grid-template-columns:180px 1fr 40px; gap:12px; align-items:center; margin-bottom:8px; }}
.wip-name {{ font-size:13px; color:#ddd; }}
.wip-bar {{ height:8px; background:#1a1a1a; border-radius:4px; overflow:hidden; }}
.wip-fill {{ height:100%; background:linear-gradient(90deg,#4ade80,#22c55e); }}
.wip-count {{ font-family:Consolas,monospace; font-size:13px; color:#4ade80; text-align:right; }}
.footer {{ margin-top:48px; padding-top:20px; border-top:1px solid #1a1a1a; display:flex; justify-content:space-between; color:#555; font-size:11px; }}
.footer a {{ color:#666; text-decoration:none; }}
.footer a:hover {{ color:#f59e0b; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="title">{product} <span>/</span> Morning Briefing</div>
      <div class="subtitle">{date}</div>
    </div>
    <div class="subtitle">{team}</div>
  </div>

  <div class="kpis">
    <div class="kpi warn"><div class="kpi-label">Blockers</div><div class="kpi-value">{blockers_count}</div></div>
    <div class="kpi caution"><div class="kpi-label">Stuck &gt;3d</div><div class="kpi-value">{stuck_count}</div></div>
    <div class="kpi info"><div class="kpi-label">New 24h</div><div class="kpi-value">{new_count}</div></div>
    <div class="kpi neutral"><div class="kpi-label">WIP total</div><div class="kpi-value">{wip_count}</div></div>
  </div>

  {focus}

  <div class="section">
    <div class="section-head"><div class="section-title warn">Blockers</div><div class="section-count">{blockers_count} items</div></div>
    {blockers}
  </div>

  <div class="section">
    <div class="section-head"><div class="section-title caution">Stuck &gt;3 days</div><div class="section-count">{stuck_count} items</div></div>
    {stuck}
  </div>

  <div class="section">
    <div class="section-head"><div class="section-title info">New last 24h</div><div class="section-count">{new_count} items</div></div>
    {new}
  </div>

  <div class="section">
    <div class="section-head"><div class="section-title">WIP per assignee</div><div class="section-count">{wip_count} total</div></div>
    {wip}
  </div>

  <div class="footer">
    <div>Generated {generated_at}</div>
    <div><a href="{board_url}" target="_blank">Open board in Jira</a></div>
  </div>
</div>
</body>
</html>
"""


# ---------- main ----------

def main():
    if len(sys.argv) != 3:
        print("Usage: render_briefing.py <raw_jira.json> <output_base_path>", file=sys.stderr)
        sys.exit(2)

    raw_path = sys.argv[1]
    out_base = Path(sys.argv[2])
    out_base.parent.mkdir(parents=True, exist_ok=True)

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    issues = raw.get("issues") if isinstance(raw, dict) else raw
    if not isinstance(issues, list):
        issues = []

    data = categorize(issues)
    date_str = datetime.now().strftime("%Y-%m-%d")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"Categorized: {len(issues)} issues -> "
          f"{len(data['blockers'])} blockers, "
          f"{len(data['stuck'])} stuck, "
          f"{len(data['new_24h'])} new, "
          f"{data['total_wip']} WIP")

    top_focus = generate_top_focus(data)
    if top_focus:
        print(f"Top focus: {top_focus[:80]}...")
    else:
        print("Top focus: skipped (claude CLI unavailable or failed)")

    html_path = out_base.with_suffix(".html")
    md_path = out_base.with_suffix(".md")
    json_path = out_base.with_suffix(".json")

    html_path.write_text(
        render_html(data, date_str, top_focus, generated_at), encoding="utf-8"
    )
    md_path.write_text(
        render_markdown(data, date_str, top_focus), encoding="utf-8"
    )
    json_path.write_text(
        json.dumps({**data, "top_focus": top_focus, "date": date_str}, indent=2),
        encoding="utf-8",
    )

    print(f"Written: {html_path}")
    print(f"Written: {md_path}")

    create_calendar_event(data, top_focus, md_path, html_path, date_str)


if __name__ == "__main__":
    main()
