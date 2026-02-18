#!/usr/bin/env bash
# pilot — fresh context loop for AI-driven development
set -uo pipefail

# ── defaults ──────────────────────────────────────────────────────────
EXECUTOR=""
MODEL=""
PROMPTS=()
MAX=""
VERBOSE=0
HUMAN_BLOCK=0

# ── parse args ────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      echo "usage: pilot.sh -m <model> -p <prompt> [-p <prompt>...] [options]"
      echo ""
      echo "required:"
      echo "  -m, --model <name>       model to use (e.g. opus, o3)"
      echo "  -p, --prompt <file|text>  prompt file or inline text (repeatable)"
      echo ""
      echo "options:"
      echo "  -e, --executor <tool>    claude-code, codex"
      echo "  -n, --max-rounds <n>     max loop iterations (0 = unlimited)"
      echo "  -v, --verbose            stream agent output live"
      echo "  --human-block            stop loop on <loop:human> signals"
      echo ""
      echo "examples:"
      echo "  pilot.sh -m opus -p gsd.md -p BRIEF.md -e claude-code -n 20"
      echo "  pilot.sh -m opus -p gsd.md -p BRIEF.md -p \"skip research\""
      echo "  pilot.sh -m o3 -p PROMPT.md -e codex -n 10"
      exit 0
      ;;
    -m|--model) MODEL="$2"; shift 2 ;;
    -p|--prompt) PROMPTS+=("$2"); shift 2 ;;
    -e|--executor) EXECUTOR="$2"; shift 2 ;;
    -n|--max-rounds) MAX="$2"; shift 2 ;;
    -v|--verbose) VERBOSE=1; shift ;;
    --human-block) HUMAN_BLOCK=1; shift ;;
    *)
      echo "error: unknown option '$1'"
      echo "run pilot.sh --help for usage"
      exit 1
      ;;
  esac
done

# ── validate ──────────────────────────────────────────────────────────
MISSING=()
[ -z "$MODEL" ] && MISSING+=("--model (-m)")
[ ${#PROMPTS[@]} -eq 0 ] && MISSING+=("--prompt (-p)")
[ -z "$EXECUTOR" ] && MISSING+=("--executor (-e)")
[ -z "$MAX" ] && MISSING+=("--max-rounds (-n)")

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "error: missing required params: ${MISSING[*]}"
  echo ""
  echo "usage: pilot.sh -m <model> -p <prompt> -e <executor> -n <max-rounds>"
  echo ""
  echo "  pilot.sh -m opus -p gsd.md -p BRIEF.md -e claude-code -n 20"
  echo "  pilot.sh --help"
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

- <loop:human>question or action needed</loop:human>
  When you need human input — credentials, decisions, approvals, manual steps. Describe what you need clearly. The question will be logged and the human will answer. Previous Q&A history (if any) is included in your prompt.

Rules:
- Emit <loop:update> on meaningful progress so the operator can follow along
- <loop:done> means everything is finished, not just this round
- <loop:failed> means you cannot continue — unrecoverable error, missing dependency, conflicting requirements
- <loop:human> means you need human input — the loop may continue or pause depending on configuration
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
HUMAN_FILE=".pilot/human.md"

build_prompt() {
  local result=""
  for p in "${PROMPTS[@]}"; do
    if [ -f "$p" ]; then
      result="${result}$(cat "$p")"$'\n\n'
    else
      result="${result}${p}"$'\n\n'
    fi
  done

  # auto-inject human Q&A history if it exists
  if [ -f "$HUMAN_FILE" ]; then
    result="${result}# Human Q&A History"$'\n'
    result="${result}$(cat "$HUMAN_FILE")"$'\n\n'
  fi

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
    echo "  ┄┄┄"
    claude -p --dangerously-skip-permissions \
      --model "$model" --verbose \
      --output-format stream-json \
      "$prompt" 2>&1 | tee "$streamfile" | \
      jq --unbuffered -r "$JQ_STREAM" 2>/dev/null
    echo ""
    echo "  ┄┄┄"
  else
    claude -p --dangerously-skip-permissions \
      --model "$model" --verbose \
      --output-format stream-json \
      "$prompt" 2>&1 | tee "$streamfile" | \
      jq --unbuffered -r "$JQ_STREAM" 2>/dev/null | \
      sed -nu 's/.*<loop:update>\(.*\)<\/loop:update>.*/  ▸ \1/p'
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
echo "  human:    $([ "$HUMAN_BLOCK" = "1" ] && echo "block" || echo "defer")"
echo ""

# ── session logs ─────────────────────────────────────────────────────
SESSION_ID=$(date +%Y-%m-%d_%H%M%S)
LOG_DIR=".pilot/logs/$SESSION_ID"
mkdir -p "$LOG_DIR"

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
    echo "  ⚠ agent exited $EXIT_CODE ($FAILURES/3 consecutive failures)"
    if [ "$FAILURES" -ge 3 ]; then
      echo "  ✗ 3 consecutive failures, stopping."
      exit 1
    fi
    sleep 5
    continue
  fi
  FAILURES=0

  # skip empty responses
  if [ -z "$OUTPUT" ]; then
    echo "  ⚠ empty response (${ELAPSED}s) — agent produced no output"
    sleep 2
    continue
  fi

  # save log
  LOG_FILE=$(printf "%s/round-%03d.log" "$LOG_DIR" "$ROUND")
  echo "$OUTPUT" > "$LOG_FILE"

  # ── short round detection ───────────────────────────────────────────
  if [ "$ELAPSED" -lt 5 ]; then
    echo "  ⚠ round too short (${ELAPSED}s) — agent may be stuck"
  fi

  # ── extract signals ─────────────────────────────────────────────────
  UPDATES=$(extract_signals "update" "$OUTPUT")

  echo "  round $ROUND · ${ELAPSED}s"
  while IFS= read -r line; do
    [ -n "$line" ] && echo "  ▸ $line"
  done <<< "$UPDATES"

  # check <loop:done>
  if echo "$OUTPUT" | grep -q "<loop:done"; then
    SUMMARY=$(extract_signals "done" "$OUTPUT" | tail -1)
    echo "  ✓ done in $ROUND round(s)"
    [ -n "$SUMMARY" ] && echo "  ↳ $SUMMARY"
    break
  fi

  # check <loop:failed>
  if echo "$OUTPUT" | grep -q "<loop:failed"; then
    REASON=$(extract_signals "failed" "$OUTPUT" | tail -1)
    echo "  ✗ agent reported failure at round $ROUND"
    [ -n "$REASON" ] && echo "  ↳ $REASON"
    exit 1
  fi

  # check <loop:human> — always log, optionally stop
  if echo "$OUTPUT" | grep -q "<loop:human"; then
    QUESTION=$(extract_signals "human" "$OUTPUT" | tail -1)
    if [ -n "$QUESTION" ]; then
      mkdir -p .pilot
      echo "" >> "$HUMAN_FILE"
      echo "## Round $ROUND" >> "$HUMAN_FILE"
      echo "Q: $QUESTION" >> "$HUMAN_FILE"
      echo "A: " >> "$HUMAN_FILE"
      echo "  ? human input needed → $HUMAN_FILE"
      echo "  ↳ $QUESTION"
      if [ "$HUMAN_BLOCK" = "1" ]; then
        echo "  ⏸ stopped (--human-block). Answer in $HUMAN_FILE and re-run."
        exit 0
      fi
    fi
  fi

  sleep 2
done
