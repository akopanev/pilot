#!/usr/bin/env bash
set -euo pipefail

# Squash-merge feature branch, close task, clean up.
# Uses: $PILOT_DEFAULT_BRANCH, $PILOT_TASK_ID, $PILOT_WORKING_BRANCH

# Merge
git checkout "$PILOT_DEFAULT_BRANCH" --quiet
git merge --squash "$PILOT_WORKING_BRANCH"
git commit -m "$PILOT_TASK_ID: merge"

# Clean up
git branch -D "$PILOT_WORKING_BRANCH"

# Close task
tk close "$PILOT_TASK_ID"

echo "<signal:update>merged $PILOT_TASK_ID</signal:update>"
