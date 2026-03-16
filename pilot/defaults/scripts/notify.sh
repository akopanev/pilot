#!/usr/bin/env bash
# notify.sh — Send pipeline completion notification
#
# Env vars set automatically by pilot:
#   PILOT_EXIT_STATUS    "success" or "failed"
#   PILOT_PIPELINE_NAME  pipeline name (e.g. "dev", "prd")
#   PILOT_DURATION       total duration (e.g. "2m30s")
#   PILOT_ROUNDS         number of rounds completed
#   PILOT_LAST_STAGE     last stage executed
#   PILOT_CONFIG_DIR     absolute path to config directory
#
# Required:
#   NOTIFIER_API_KEY     API key for the notifier service
#
# Optional overrides:
#   NOTIFIER_URL         notification endpoint
#   NOTIFIER_CHANNEL     channel name (default: "pilot-pipelines")

set -euo pipefail

NOTIFIER_URL="${NOTIFIER_URL:-https://notifier-server-production.up.railway.app/send}"
NOTIFIER_CHANNEL="${NOTIFIER_CHANNEL:-pilot-pipelines}"

if [ -z "${NOTIFIER_API_KEY:-}" ]; then
  echo "NOTIFIER_API_KEY not set — skipping notification"
  exit 0
fi

# Pipeline metadata (set by pilot engine)
STATUS="${PILOT_EXIT_STATUS:-unknown}"
PIPELINE="${PILOT_PIPELINE_NAME:-unknown}"
DURATION="${PILOT_DURATION:-?}"
ROUNDS="${PILOT_ROUNDS:-?}"
LAST_STAGE="${PILOT_LAST_STAGE:-?}"

# System context
COMPUTER="$(hostname -s 2>/dev/null || echo unknown)"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo n/a)"
PROJECT="$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo unknown)"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M')"

if [ "$STATUS" = "success" ]; then
  ICON="✅"; LABEL="SUCCESS"
else
  ICON="❌"; LABEL="FAILED"
fi

# Telegram-compatible HTML (only <b>, <i>, <code>, <pre>, <u>, <s> allowed)
MESSAGE="${ICON} <b>Pipeline ${LABEL}</b>

<b>Pipeline:</b> ${PIPELINE}
<b>Computer:</b> ${COMPUTER}
<b>Project:</b> ${PROJECT}
<b>Branch:</b> <code>${GIT_BRANCH}</code>
<b>Duration:</b> ${DURATION}
<b>Rounds:</b> ${ROUNDS}
<b>Last stage:</b> ${LAST_STAGE}
<b>Time:</b> ${TIMESTAMP}"

# Use python3 for safe JSON encoding
JSON_PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({
    'channel': sys.argv[1],
    'message': sys.argv[2],
    'content_type': 'html'
}))
" "$NOTIFIER_CHANNEL" "$MESSAGE")

curl -sf -X POST "$NOTIFIER_URL" \
  -H "Authorization: Bearer $NOTIFIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD"

echo "Notification sent (${STATUS})"
