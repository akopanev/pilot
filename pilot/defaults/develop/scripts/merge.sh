#!/usr/bin/env bash
set -euo pipefail

# Squash-merge feature branch, close task, clean up.
# Uses: $PILOT_DEFAULT_BRANCH, $PILOT_TASK_ID

BRANCH="$PILOT_DEFAULT_BRANCH"
TASK="$PILOT_TASK_ID"

# Merge
git checkout "$BRANCH" --quiet
git merge --squash "feat/$TASK"
git commit -m "$TASK: merge"

# Clean up
git branch -D "feat/$TASK"

# Close task
tk close "$TASK"

echo "<signal:update>merged $TASK</signal:update>"
