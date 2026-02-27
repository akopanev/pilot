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

# Dirty working tree = trouble
if [ -n "$(git status --porcelain)" ]; then
  echo "<signal:failed>uncommitted changes — commit or stash before running pilot</signal:failed>"
  exit 0
fi

# Clean slate
git checkout "$PILOT_DEFAULT_BRANCH" --quiet 2>/dev/null || true
git pull --ff-only --quiet 2>/dev/null || true

# Pick
TASK=$(tk ready 2>/dev/null | awk 'NR==1{print $1}' || true)

if [ -z "$TASK" ]; then
  echo "<signal:completed>no tasks</signal:completed>"
  exit 0
fi

# Claim on default branch (visible to other agents, survives crashes)
tk start "$TASK"
git add .tickets/
git commit -m "$TASK: start" --quiet

# Feature branch
BRANCH="feat/$TASK"
git checkout -B "$BRANCH"

REMAINING=$(tk ls 2>/dev/null | wc -l | tr -d ' ')
echo "<signal:update>$REMAINING task(s) remaining</signal:update>"
echo "<signal:var key=PILOT_TASK_ID>$TASK</signal:var>"
echo "<signal:var key=PILOT_WORKING_BRANCH>$BRANCH</signal:var>"
echo "<signal:ready>$TASK</signal:ready>"
