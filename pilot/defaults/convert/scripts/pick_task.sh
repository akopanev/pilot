#!/usr/bin/env bash
set -euo pipefail

# Pick next ready task in current epic, create feature branch.
# Emits: <signal:ready>id</signal:ready> or <signal:epic_done>summary</signal:epic_done>
# Uses: $PILOT_DEFAULT_BRANCH, $PILOT_CURRENT_EPIC

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "<signal:failed>not a git repository</signal:failed>"
  exit 0
fi

# Commit any leftover changes (agent crash, reviewer notes, etc.)
if [ -n "$(git status --porcelain)" ]; then
  echo "<signal:update>committing leftover changes</signal:update>"
  git add -A
  git commit -m "convert: auto-commit leftover changes" --quiet
fi

# Clean slate
git checkout "$PILOT_DEFAULT_BRANCH" --quiet 2>/dev/null || true
git pull --ff-only --quiet 2>/dev/null || true

# Find ready task scoped to current epic
TASK=""
while read -r line; do
  TID=$(echo "$line" | awk '{print $1}')
  [ -z "$TID" ] && continue
  PARENT=$(tk query 2>/dev/null | jq -r "select(.id == \"$TID\") | .parent // empty" || true)
  if [ "$PARENT" = "$PILOT_CURRENT_EPIC" ]; then
    TASK="$TID"
    break
  fi
done < <(tk ready 2>/dev/null)

if [ -z "$TASK" ]; then
  # Check if all epic tasks are closed vs some are blocked
  TOTAL=$(tk query 2>/dev/null | jq -r "select(.parent == \"$PILOT_CURRENT_EPIC\")" | wc -l | tr -d ' ')
  CLOSED=$(tk query 2>/dev/null | jq -r "select(.parent == \"$PILOT_CURRENT_EPIC\" and .status == \"closed\")" | wc -l | tr -d ' ')
  REMAINING=$((TOTAL - CLOSED))

  if [ "$REMAINING" = "0" ]; then
    echo "<signal:epic_done>$PILOT_CURRENT_EPIC: all $TOTAL tasks closed</signal:epic_done>"
  else
    echo "<signal:epic_done>$PILOT_CURRENT_EPIC: $REMAINING of $TOTAL tasks blocked, moving on</signal:epic_done>"
  fi
  exit 0
fi

# Claim on default branch and push (visible to remote)
tk start "$TASK"
git add .tickets/
git commit -m "$TASK: start" --quiet
git push --quiet

# Feature branch
BRANCH="feat/$TASK"
git checkout -B "$BRANCH"

TOTAL=$(tk query 2>/dev/null | jq -r "select(.parent == \"$PILOT_CURRENT_EPIC\")" | wc -l | tr -d ' ')
CLOSED=$(tk query 2>/dev/null | jq -r "select(.parent == \"$PILOT_CURRENT_EPIC\" and .status == \"closed\")" | wc -l | tr -d ' ')
REMAINING=$((TOTAL - CLOSED))
echo "<signal:update>$REMAINING / $TOTAL tasks remaining in epic</signal:update>"
echo "<signal:var key=PILOT_TASK_ID>$TASK</signal:var>"
echo "<signal:var key=PILOT_WORKING_BRANCH>$BRANCH</signal:var>"
echo "<signal:ready>$TASK</signal:ready>"
