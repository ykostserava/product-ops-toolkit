#!/bin/bash
# Morning Briefing - daily Jira digest for Product Owners / Delivery Managers.
#
# Pipeline:
#   1. jira_api.py -> raw JSON (all open tickets in your project)
#   2. render_briefing.py -> categorizes + asks Claude for "Top focus today"
#                         -> writes .html (dashboard) + .md (digest) + .json
#   3. auto-opens latest.html in browser (unless NO_OPEN=1)
#
# Configure via environment variables (see README-briefing.md):
#   JIRA_API_TOKEN       - required
#   JIRA_BASE_URL        - required (e.g. https://jira.example.com)
#   JIRA_PROJECT         - required (e.g. PROJ)
#   JIRA_API_SCRIPT      - path to jira_api.py script
#   PYTHON_BIN           - path to real Python (not MS Store stub on Windows)
#   CLAUDE_CLI           - path to claude CLI
#   OUTPUT_DIR           - where briefings are written (default: ./briefings)
#   BRIEFING_EVENT_TIME  - HH:MM of Calendar event (default: 09:15)
#   BRIEFING_TZ          - IANA timezone (default: Europe/Warsaw)
#
# Run manually:  bash pipelines/morning-briefing/morning-briefing.sh
# Schedule:      see README-briefing.md
# Skip browser:  NO_OPEN=1 bash pipelines/morning-briefing/morning-briefing.sh

set -euo pipefail

# --- Required config ---
if [[ -z "${JIRA_API_TOKEN:-}" ]]; then
  echo "ERROR: JIRA_API_TOKEN not set" >&2
  exit 1
fi
if [[ -z "${JIRA_BASE_URL:-}" ]]; then
  echo "ERROR: JIRA_BASE_URL not set (e.g. https://jira.example.com)" >&2
  exit 1
fi
if [[ -z "${JIRA_PROJECT:-}" ]]; then
  echo "ERROR: JIRA_PROJECT not set (e.g. PROJ)" >&2
  exit 1
fi
if [[ -z "${JIRA_API_SCRIPT:-}" ]]; then
  echo "ERROR: JIRA_API_SCRIPT not set (path to jira_api.py)" >&2
  exit 1
fi

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDER_SCRIPT="$SCRIPT_DIR/render_briefing.py"
OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)/briefings}"
LOG_FILE="$OUTPUT_DIR/briefing.log"

mkdir -p "$OUTPUT_DIR"

# --- Resolve Python interpreter ---
# On Windows Git Bash, `python3` may be the MS Store stub that hangs in Task Scheduler.
# Try venv python first, then fall back to PATH python.
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in \
    "$(pwd)/venv/Scripts/python.exe" \
    "$(pwd)/venv/bin/python" \
    "/c/Program Files/Python312/python.exe" \
    "/usr/bin/python3" \
    "/usr/local/bin/python3" \
    "python3"; do
    if command -v "$candidate" >/dev/null 2>&1 || [[ -x "$candidate" ]]; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi
if [[ -z "$PYTHON_BIN" ]]; then
  echo "ERROR: Could not locate a Python interpreter." >&2
  exit 1
fi

# --- Pin claude CLI for subprocess ---
export CLAUDE_CLI="${CLAUDE_CLI:-claude}"
if ! command -v "$CLAUDE_CLI" >/dev/null 2>&1 && [[ ! -x "$CLAUDE_CLI" ]]; then
  echo "WARNING: claude CLI not found at $CLAUDE_CLI - Top focus and Calendar event will be skipped." >&2
fi

TODAY=$(date +%F)
NOW=$(date +"%F %H:%M:%S")
OUT_BASE="$OUTPUT_DIR/briefing-$TODAY"

echo "[$NOW] Starting briefing" | tee -a "$LOG_FILE"

# --- Stage 1: fetch raw Jira data ---
JQL="project = ${JIRA_PROJECT} AND statusCategory != Done ORDER BY updated DESC"

RAW=$(mktemp)
trap 'rm -f "$RAW"' EXIT

echo "[$NOW] Fetching JQL: $JQL" | tee -a "$LOG_FILE"
"$PYTHON_BIN" "$JIRA_API_SCRIPT" search "$JQL" --max=100 --format=json > "$RAW" 2>> "$LOG_FILE" || {
  echo "[$NOW] ERROR: Jira fetch failed. See $LOG_FILE" | tee -a "$LOG_FILE"
  exit 1
}

# --- Stage 2: categorize + render (Python calls Claude for Top focus internally) ---
"$PYTHON_BIN" "$RENDER_SCRIPT" "$RAW" "$OUT_BASE" 2>&1 | tee -a "$LOG_FILE"

# --- Update latest.* shortcuts ---
cp "$OUT_BASE.html" "$OUTPUT_DIR/latest.html"
cp "$OUT_BASE.md" "$OUTPUT_DIR/latest.md"

END_TIME=$(date +"%F %H:%M:%S")
echo "[$END_TIME] Briefing ready: $OUT_BASE.html" | tee -a "$LOG_FILE"

# --- Stage 3: open in browser (unless disabled) ---
if [[ -z "${NO_OPEN:-}" ]]; then
  if command -v start >/dev/null 2>&1; then
    start "" "$(cygpath -w "$OUT_BASE.html" 2>/dev/null || echo "$OUT_BASE.html")"
  elif command -v open >/dev/null 2>&1; then
    open "$OUT_BASE.html"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$OUT_BASE.html"
  fi
fi
