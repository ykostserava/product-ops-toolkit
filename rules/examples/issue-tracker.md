# Issue Tracker Rules

Example of an **unconditional rule**: API hygiene + defaults + a confirm-before-create
gate for whatever tracker your team uses (Jira shown). Edit to match yours.

- **ASCII only in API calls** — no Unicode arrows, currency signs, or special symbols
  in text sent to the tracker API (older instances corrupt or reject them)
- **Default priority: High** — never invent an urgency level the workflow doesn't have
- **Always confirm scope before creating issues** — e.g. don't create web stories if
  the feature already exists on web; list the planned issues and get user approval first

## Issue output format
- Clear, actionable descriptions
- Acceptance criteria as a checklist
- Explicit priority and dependencies
- Estimate when possible
