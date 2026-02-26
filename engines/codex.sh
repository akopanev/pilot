#!/usr/bin/env bash
# engine: codex
#
# interface: engine.sh <prompt-file> <model> <logfile>
# env: VERBOSE (0|1), PILOT_DOCKER (0|1)
set -uo pipefail

PROMPT=$(cat "$1")
MODEL="$2"
LOGFILE="$3"

SANDBOX="full-auto"
[ "${PILOT_DOCKER:-}" = "1" ] && SANDBOX="danger-full-access"

if [ "${VERBOSE:-0}" = "1" ]; then
  codex exec \
    --sandbox "$SANDBOX" \
    --skip-git-repo-check \
    -c model="$MODEL" \
    -c model_reasoning_effort=xhigh \
    -c stream_idle_timeout_ms=3600000 \
    "$PROMPT" 2>&1 | tee "$LOGFILE"
else
  codex exec \
    --sandbox "$SANDBOX" \
    --skip-git-repo-check \
    -c model="$MODEL" \
    -c model_reasoning_effort=xhigh \
    -c stream_idle_timeout_ms=3600000 \
    "$PROMPT" > "$LOGFILE" 2>&1
fi
