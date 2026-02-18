#!/usr/bin/env bash
# pilot — fresh context loop for AI-driven development
set -uo pipefail

# ── defaults ──────────────────────────────────────────────────────────
EXECUTOR="claude-code"
MODEL=""
PROMPTS=()
MAX=50  # safety default — pass --max-rounds 0 for unlimited
VERBOSE=0

# ── parse args ────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      echo "usage: pilot.sh <model> <prompts...> [options]"
      echo ""
      echo "options:"
      echo "  --executor <tool>    claude-code (default), codex"
      echo "  --max-rounds <n>     max loop iterations (default: 50, 0=unlimited)"
      echo "  --verbose            stream agent output live"
      echo ""
      echo "examples:"
      echo "  .pilot/pilot.sh opus PROMPT.md"
      echo "  .pilot/pilot.sh opus gsd.md brief.md context.md"
      echo '  .pilot/pilot.sh opus gsd.md "also fix the login bug"'
      echo "  .pilot/pilot.sh o3 PROMPT.md --executor codex"
      echo "  .pilot/pilot.sh opus PROMPT.md --max-rounds 20"
      exit 0
      ;;
    --executor) EXECUTOR="$2"; shift 2 ;;
    --max-rounds) MAX="$2"; shift 2 ;;
    --verbose) VERBOSE=1; shift ;;
    *)
      if [ -z "$MODEL" ]; then
        MODEL="$1"
      else
        PROMPTS+=("$1")
      fi
      shift
      ;;
  esac
done

# ── validate ──────────────────────────────────────────────────────────
if [ -z "$MODEL" ]; then
  echo "error: no model given"
  echo "usage: pilot.sh <model> <prompts...> [options]"
  exit 1
fi

if [ ${#PROMPTS[@]} -eq 0 ]; then
  echo "error: no prompt given"
  echo ""
  echo "usage: pilot.sh <model> <prompts...> [options]"
  echo ""
  echo "  .pilot/pilot.sh opus PROMPT.md"
  echo "  .pilot/pilot.sh opus gsd.md brief.md context.md"
  echo "  .pilot/pilot.sh --help"
  exit 1
fi

case "$EXECUTOR" in
  claude-code|codex) ;;
  *)
    echo "error: unknown executor '$EXECUTOR'"
    echo "supported: claude-code, codex"
    exit 1
    ;;
esac

# ── prompt display ────────────────────────────────────────────────────
PROMPT_DISPLAY=""
for p in "${PROMPTS[@]}"; do
  if [ -f "$p" ]; then
    PROMPT_DISPLAY="${PROMPT_DISPLAY:+$PROMPT_DISPLAY + }$p"
  else
    SHORT="${p:0:40}$([ ${#p} -gt 40 ] && echo '...')"
    PROMPT_DISPLAY="${PROMPT_DISPLAY:+$PROMPT_DISPLAY + }\"$SHORT\""
  fi
done

# ── signals appended to every prompt ──────────────────────────────────
SIGNALS='

---
# Loop Signals

You are running inside a loop. Each round is a fresh context — you have NO memory of previous rounds. All state must be read from files on disk.

Emit these XML signals during your work:

- <loop:update>short status update</loop:update>
  Emit freely as you hit milestones — starting a task, completed something, passed tests, found an issue, made a decision.

- <loop:done>summary of completed work</loop:done>
  ONLY when ALL work is fully complete. The loop will exit.

- <loop:failed>reason</loop:failed>
  When you are stuck, blocked, or cannot proceed. The loop will stop.

Rules:
- Emit <loop:update> on meaningful progress so the operator can follow along
- <loop:done> means everything is finished, not just this round
- <loop:failed> means you cannot continue — unrecoverable error, missing dependency, conflicting requirements
- If you do not emit <loop:done> or <loop:failed>, the loop continues automatically

# Scope

Do ONE step only. Read your state, figure out what the single next step is in your methodology, execute it, and stop. Do not try to do everything in one round — you will be restarted with fresh context for the next step. One step, done well, then exit.
'

# ── portable signal extraction (no grep -P, works on macOS) ──────────
extract_signals() {
  local tag="$1" input="$2"
  echo "$input" | sed -n "s/.*<loop:${tag}>\(.*\)<\/loop:${tag}>.*/\1/p"
}

# ── build prompt ──────────────────────────────────────────────────────
build_prompt() {
  local result=""
  for p in "${PROMPTS[@]}"; do
    if [ -f "$p" ]; then
      result="${result}$(cat "$p")"$'\n\n'
    else
      result="${result}${p}"$'\n\n'
    fi
  done
  result="${result}${SIGNALS}"
  echo "$result"
}

# ── jq filter for extracting text from claude stream-json ─────────────
# handles all 4 event types: assistant, content_block_delta, message_stop, result
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

# ── executor functions ────────────────────────────────────────────────

run_claude() {
  local prompt="$1" model="$2" tmpfile="$3"
  local streamfile
  streamfile=$(mktemp)

  # always use stream-json for proper event parsing
  if [ "$VERBOSE" = "1" ]; then
    claude -p --dangerously-skip-permissions \
      --model "$model" --verbose \
      --output-format stream-json \
      "$prompt" 2>&1 | tee "$streamfile" | \
      jq --unbuffered -rj "$JQ_STREAM" 2>/dev/null
    echo ""
  else
    claude -p --dangerously-skip-permissions \
      --model "$model" --verbose \
      --output-format stream-json \
      "$prompt" > "$streamfile" 2>&1
  fi

  # extract plain text from NDJSON for signal parsing
  jq -rj "$JQ_STREAM" < "$streamfile" > "$tmpfile" 2>/dev/null
  rm -f "$streamfile"
}

run_codex() {
  local prompt="$1" model="$2" tmpfile="$3"

  # codex needs prompt as positional arg, not via -p
  # Docker: full access; bare metal: full-auto sandbox
  local sandbox="full-auto"
  [ "${PILOT_DOCKER:-}" = "1" ] && sandbox="danger-full-access"

  if [ "$VERBOSE" = "1" ]; then
    codex exec \
      --sandbox "$sandbox" \
      --skip-git-repo-check \
      -c model="$model" \
      -c model_reasoning_effort=xhigh \
      -c stream_idle_timeout_ms=3600000 \
      "$prompt" 2>&1 | tee "$tmpfile"
  else
    codex exec \
      --sandbox "$sandbox" \
      --skip-git-repo-check \
      -c model="$model" \
      -c model_reasoning_effort=xhigh \
      -c stream_idle_timeout_ms=3600000 \
      "$prompt" > "$tmpfile" 2>&1
  fi
}

# ── banner ────────────────────────────────────────────────────────────
echo ""
echo "  pilot"
echo "  executor: $EXECUTOR"
echo "  model:    $MODEL"
echo "  prompt:   $PROMPT_DISPLAY"
echo "  max:      $([ "$MAX" -gt 0 ] 2>/dev/null && echo "$MAX" || echo "unlimited")"
echo ""

# ── main loop ─────────────────────────────────────────────────────────
ROUND=0
FAILURES=0
while true; do
  ROUND=$((ROUND + 1))
  [ "$MAX" -gt 0 ] 2>/dev/null && [ "$ROUND" -gt "$MAX" ] && echo "max rounds ($MAX) reached." && break

  echo "━━━ round $ROUND ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  START=$(date +%s)

  # build prompt fresh each round (re-reads files, allows mid-loop edits)
  FULL_PROMPT=$(build_prompt)

  TMPFILE=$(mktemp)

  # dispatch to executor
  case "$EXECUTOR" in
    claude-code) run_claude "$FULL_PROMPT" "$MODEL" "$TMPFILE" ;;
    codex)       run_codex  "$FULL_PROMPT" "$MODEL" "$TMPFILE" ;;
  esac

  EXIT_CODE=$?
  OUTPUT=$(cat "$TMPFILE")
  rm -f "$TMPFILE"

  ELAPSED=$(( $(date +%s) - START ))

  # ── handle agent failures ───────────────────────────────────────────
  if [ "$EXIT_CODE" -ne 0 ]; then
    FAILURES=$((FAILURES + 1))
    echo ""
    echo "  ⚠ agent exited $EXIT_CODE ($FAILURES/3 consecutive failures)"
    if [ "$FAILURES" -ge 3 ]; then
      echo "  ✗ 3 consecutive failures, stopping."
      exit 1
    fi
    sleep 5
    continue
  fi
  FAILURES=0

  # ── short round detection ───────────────────────────────────────────
  if [ "$ELAPSED" -lt 5 ]; then
    echo ""
    echo "  ⚠ round too short (${ELAPSED}s) — agent may be stuck"
  fi

  # ── extract signals ─────────────────────────────────────────────────
  UPDATES=$(extract_signals "update" "$OUTPUT")

  echo ""
  echo "  round $ROUND · ${ELAPSED}s"
  while IFS= read -r line; do
    [ -n "$line" ] && echo "  ▸ $line"
  done <<< "$UPDATES"

  # check <loop:done> — matches <loop:done>, <loop:done/>, <loop:done />
  if echo "$OUTPUT" | grep -q "<loop:done"; then
    SUMMARY=$(extract_signals "done" "$OUTPUT" | tail -1)
    echo ""
    echo "  ✓ done in $ROUND round(s)"
    [ -n "$SUMMARY" ] && echo "  ↳ $SUMMARY"
    echo ""
    break
  fi

  # check <loop:failed>
  if echo "$OUTPUT" | grep -q "<loop:failed"; then
    REASON=$(extract_signals "failed" "$OUTPUT" | tail -1)
    echo ""
    echo "  ✗ agent reported failure at round $ROUND"
    [ -n "$REASON" ] && echo "  ↳ $REASON"
    echo ""
    exit 1
  fi

  sleep 2
done
