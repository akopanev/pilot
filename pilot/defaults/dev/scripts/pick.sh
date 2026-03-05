#!/usr/bin/env bash
set -euo pipefail

# Pick next ready task, create feature branch.
# Emits: <signal:ready>id</signal:ready> or <signal:completed>no tasks</signal:completed>
# Uses: $PILOT_DEFAULT_BRANCH

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "<signal:failed>not a git repository</signal:failed>"
  exit 0
fi

if ! command -v tk &>/dev/null; then
  echo "<signal:failed>tk not found — install ticket (https://github.com/wedow/ticket)</signal:failed>"
  exit 0
fi

if ! tk ls &>/dev/null; then
  echo "<signal:failed>no .tickets/ directory — run 'tk create' to initialize</signal:failed>"
  exit 0
fi

# Commit any leftover changes (agent crash, reviewer notes, etc.)
if [ -n "$(git status --porcelain)" ]; then
  echo "<signal:update>committing leftover changes</signal:update>"
  git add -A
  git commit -m "pilot: auto-commit leftover changes" --quiet
fi

# Clean slate
git checkout "$PILOT_DEFAULT_BRANCH" --quiet 2>/dev/null || true
git pull --ff-only --quiet 2>/dev/null || true

# Pick — scoped to epic if PILOT_EPIC is set
if [ -n "${PILOT_EPIC:-}" ]; then
  # Get ready task IDs, then find the first one parented to this epic
  TASK=""
  while read -r line; do
    TID=$(echo "$line" | awk '{print $1}')
    [ -z "$TID" ] && continue
    PARENT=$(tk query "[.[] | select(.id == \"$TID\")][0].parent // empty" 2>/dev/null || true)
    if [ "$PARENT" = "$PILOT_EPIC" ]; then
      TASK="$TID"
      break
    fi
  done < <(tk ready 2>/dev/null)
else
  TASK=$(tk ready 2>/dev/null | awk 'NR==1{print $1}' || true)
fi

if [ -z "$TASK" ]; then
  if [ -n "${PILOT_EPIC:-}" ]; then
    # Check if all epic tasks are closed (done) vs blocked (stuck)
    OPEN=$(tk query "[.[] | select(.parent == \"$PILOT_EPIC\" and .status != \"closed\")] | length" 2>/dev/null || echo "0")
    if [ "$OPEN" = "0" ]; then
      echo "<signal:completed>epic done</signal:completed>"
    else
      echo "<signal:completed>no ready tasks in epic (${OPEN} blocked)</signal:completed>"
    fi
  else
    echo "<signal:completed>no tasks</signal:completed>"
  fi
  exit 0
fi

# Claim on default branch (visible to other agents, survives crashes)
tk start "$TASK"
git add .tickets/
git commit -m "$TASK: start" --quiet

# Feature branch
BRANCH="feat/$TASK"
git checkout -B "$BRANCH"

if [ -n "${PILOT_EPIC:-}" ]; then
  TOTAL=$(tk query "[.[] | select(.parent == \"$PILOT_EPIC\")] | length" 2>/dev/null || echo "0")
  CLOSED=$(tk query "[.[] | select(.parent == \"$PILOT_EPIC\" and .status == \"closed\")] | length" 2>/dev/null || echo "0")
else
  TOTAL=$(tk ls 2>/dev/null | wc -l | tr -d ' ')
  CLOSED=$(tk ls --status closed 2>/dev/null | wc -l | tr -d ' ')
fi
REMAINING=$((TOTAL - CLOSED))
echo "<signal:update>$REMAINING / $TOTAL tasks remaining</signal:update>"
echo "<signal:var key=PILOT_TASK_ID>$TASK</signal:var>"
echo "<signal:var key=PILOT_WORKING_BRANCH>$BRANCH</signal:var>"
echo "<signal:ready>$TASK</signal:ready>"
