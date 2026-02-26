#!/usr/bin/env bash
set -euo pipefail

# Pick next ready task, create branch, hand off to implement.
# Emits: <signal:ready>task-id</signal:ready>  or  <signal:completed>no tasks</signal:completed>
# Uses: $PILOT_DEFAULT_BRANCH (from pipeline.yaml vars)

# Start from clean default branch
git checkout "$PILOT_DEFAULT_BRANCH" --quiet 2>/dev/null || true

TASK=$(tk ready | head -n 1 || true)

if [ -z "$TASK" ]; then
  echo "<signal:completed>no tasks</signal:completed>"
  exit 0
fi

# Claim it and create feature branch
tk start "$TASK"
git checkout -B "feat/$TASK"

echo "<signal:var key=PILOT_TASK_ID>$TASK</signal:var>"
echo "<signal:ready>$TASK</signal:ready>"
