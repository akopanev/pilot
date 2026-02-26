#!/usr/bin/env bash
# engine: claude-code
#
# interface: engine.sh <prompt-file> <model> <logfile>
# env: VERBOSE (0|1)
set -uo pipefail

PROMPT=$(cat "$1")
MODEL="$2"
LOGFILE="$3"

JQ_STREAM='
  if .type == "content_block_delta" and .delta?.type == "text_delta" then
    .delta.text // empty
  elif .type == "assistant" then
    ([.message?.content[]? | select(.type == "text") | .text] | join(""))
  elif .type == "message_stop" then
    ([.message?.content[]? | select(.type == "text") | .text] | join(""))
  elif .type == "result" and (.result?.output | type) == "object" then
    ([.result.output.content[]? | select(.type == "text") | .text] | join(""))
  else empty end
'

if [ "${VERBOSE:-0}" = "1" ]; then
  echo "  ┄┄┄"
  claude -p --dangerously-skip-permissions \
    --model "$MODEL" --verbose \
    --output-format stream-json \
    "$PROMPT" 2>&1 | \
    jq --unbuffered -r "$JQ_STREAM" 2>/dev/null | \
    tee -a "$LOGFILE" | cat -s
  echo "  ┄┄┄"
else
  claude -p --dangerously-skip-permissions \
    --model "$MODEL" --verbose \
    --output-format stream-json \
    "$PROMPT" 2>&1 | \
    jq --unbuffered -r "$JQ_STREAM" 2>/dev/null | \
    tee -a "$LOGFILE" | \
    sed -nu 's/.*<loop:update>\(.*\)<\/loop:update>.*/  ▸ \1/p'
fi

# clean up blank lines in log
grep '.' "$LOGFILE" > "$LOGFILE.tmp" 2>/dev/null && mv "$LOGFILE.tmp" "$LOGFILE" || true
