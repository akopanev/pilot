#!/usr/bin/env bash
set -euo pipefail

# Squash-merge feature branch, close task, clean up.
# Uses: $PILOT_DEFAULT_BRANCH, $PILOT_TASK_ID, $PILOT_WORKING_BRANCH

# Ensure we're on the feature branch
git checkout "$PILOT_WORKING_BRANCH" --quiet 2>/dev/null || true

# Commit any uncommitted changes (reviewer notes, leftover work)
if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -m "$PILOT_TASK_ID: pre-merge cleanup" --quiet
fi

# Squash-merge into default branch
git checkout "$PILOT_DEFAULT_BRANCH" --quiet
git merge --squash "$PILOT_WORKING_BRANCH"
git commit -m "$PILOT_TASK_ID: merge"

# Clean up feature branch
git branch -D "$PILOT_WORKING_BRANCH"

# Close task
tk close "$PILOT_TASK_ID"
git add .tickets/
git commit -m "$PILOT_TASK_ID: close" --quiet

echo "<signal:update>merged $PILOT_TASK_ID</signal:update>"
