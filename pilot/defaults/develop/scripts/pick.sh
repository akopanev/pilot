#!/usr/bin/env bash
set -euo pipefail

# Pick next ready task, create feature branch.
# Emits: <signal:ready>id</signal:ready> or <signal:completed>no tasks</signal:completed>
# Uses: $PILOT_DEFAULT_BRANCH

if ! command -v tk &>/dev/null; then
  echo "<signal:failed>tk command not found — install ticket (https://github.com/wedow/ticket) or edit scripts/pick.sh</signal:failed>"
  exit 0
fi

# Clean slate
git checkout "$PILOT_DEFAULT_BRANCH" --quiet 2>/dev/null || true
git pull --ff-only --quiet 2>/dev/null || true

# Pick
TASK=$(tk ready | head -n 1 || true)

if [ -z "$TASK" ]; then
  echo "<signal:completed>no tasks</signal:completed>"
  exit 0
fi

# Claim and branch
tk start "$TASK"
BRANCH="feat/$TASK"
git checkout -B "$BRANCH"

echo "<signal:var key=PILOT_TASK_ID>$TASK</signal:var>"
echo "<signal:var key=PILOT_WORKING_BRANCH>$BRANCH</signal:var>"
echo "<signal:ready>$TASK</signal:ready>"
