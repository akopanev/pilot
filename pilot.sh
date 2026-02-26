#!/usr/bin/env bash
# pilot — fresh context loop for AI-driven development
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── defaults ──────────────────────────────────────────────────────────
ENGINE=""
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
      echo "  -m, --model <name>        model to use (e.g. opus, o3)"
      echo "  -p, --prompt <file|text>  prompt file or inline text (repeatable)"
      echo "  -e, --engine <name|path>  engine script (e.g. claude-code, codex, ./my-engine.sh)"
      echo "  -n, --max-rounds <n>      max loop iterations (0 = unlimited)"
      echo ""
      echo "options:"
      echo "  -v, --verbose            stream agent output live"
      echo "  --human-block            stop loop on <loop:human> signals"
      echo ""
      echo "engines:"
      echo "  built-in: claude-code, codex"
      echo "  custom:   any executable — receives <prompt-file> <model> <logfile>"
      echo ""
      echo "examples:"
      echo "  pilot.sh -m opus -p prompts/signals.md -p prompts/gsd.md -p BRIEF.md -e claude-code -n 20"
      echo "  pilot.sh -m o3 -p PROMPT.md -e codex -n 10"
      echo "  pilot.sh -m opus -p PROMPT.md -e ./my-engine.sh -n 10"
      exit 0
      ;;
    -m|--model) MODEL="$2"; shift 2 ;;
    -p|--prompt) PROMPTS+=("$2"); shift 2 ;;
    -e|--engine) ENGINE="$2"; shift 2 ;;
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
[ -z "$ENGINE" ] && MISSING+=("--engine (-e)")
[ -z "$MAX" ] && MISSING+=("--max-rounds (-n)")

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "error: missing required params: ${MISSING[*]}"
  echo ""
  echo "usage: pilot.sh -m <model> -p <prompt> -e <engine> -n <max-rounds>"
  echo ""
  echo "  pilot.sh -m opus -p prompts/signals.md -p prompts/gsd.md -p BRIEF.md -e claude-code -n 20"
  echo "  pilot.sh --help"
  exit 1
fi

# ── resolve engine ────────────────────────────────────────────────────
if [ -x "$ENGINE" ]; then
  ENGINE_PATH="$ENGINE"
elif [ -x "$SCRIPT_DIR/engines/${ENGINE}.sh" ]; then
  ENGINE_PATH="$SCRIPT_DIR/engines/${ENGINE}.sh"
else
  echo "error: engine '$ENGINE' not found"
  echo "looked in: $ENGINE, $SCRIPT_DIR/engines/${ENGINE}.sh"
  exit 1
fi

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

  echo "$result"
}

# ── session logs ─────────────────────────────────────────────────────
SESSION_ID=$(date +%Y-%m-%d_%H%M%S)
LOG_DIR=".pilot/logs/$SESSION_ID"
mkdir -p "$LOG_DIR"

# ── banner ────────────────────────────────────────────────────────────
echo ""
echo "  pilot"
echo "  engine:   $(basename "$ENGINE_PATH" .sh)"
echo "  model:    $MODEL"
echo "  prompt:   $PROMPT_DISPLAY"
echo "  max:      $([ "$MAX" -gt 0 ] 2>/dev/null && echo "$MAX" || echo "unlimited")"
echo "  human:    $([ "$HUMAN_BLOCK" = "1" ] && echo "block" || echo "defer")"
echo "  logs:     $LOG_DIR/"
echo ""

# ── export env for engines ───────────────────────────────────────────
export VERBOSE

# ── main loop ─────────────────────────────────────────────────────────
ROUND=0
FAILURES=0
PROMPT_FILE=$(mktemp)
trap 'rm -f "$PROMPT_FILE"' EXIT

while true; do
  ROUND=$((ROUND + 1))
  [ "$MAX" -gt 0 ] 2>/dev/null && [ "$ROUND" -gt "$MAX" ] && echo "max rounds ($MAX) reached." && break

  echo "━━━ round $ROUND ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  START=$(date +%s)

  # build prompt fresh each round (re-reads files, allows mid-loop edits)
  build_prompt > "$PROMPT_FILE"

  # log file created before engine — tail -f to watch live
  LOG_FILE=$(printf "%s/round-%03d.log" "$LOG_DIR" "$ROUND")
  > "$LOG_FILE"

  # dispatch to engine
  "$ENGINE_PATH" "$PROMPT_FILE" "$MODEL" "$LOG_FILE"
  EXIT_CODE=$?

  OUTPUT=$(cat "$LOG_FILE")
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
    rm -f "$LOG_FILE"
    sleep 2
    continue
  fi

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
