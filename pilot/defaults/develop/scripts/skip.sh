#!/usr/bin/env bash
set -euo pipefail

# Skip stuck task — add note, clean up branch, move on.
# Uses: $PILOT_DEFAULT_BRANCH, $PILOT_TASK_ID, $PILOT_WORKING_BRANCH

echo "<signal:update>skipping $PILOT_TASK_ID (stuck)</signal:update>"

git checkout "$PILOT_WORKING_BRANCH" --quiet 2>/dev/null || true

if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "$PILOT_TASK_ID: pre-skip cleanup" --quiet
fi

tk add-note "$PILOT_TASK_ID" "SKIP: stuck in fix/review loop after multiple attempts"
git add .tickets/
git commit -m "$PILOT_TASK_ID: skip (stuck)" --quiet

git checkout "$PILOT_DEFAULT_BRANCH" --quiet
git branch -D "$PILOT_WORKING_BRANCH" 2>/dev/null || true

echo "<signal:update>skipped $PILOT_TASK_ID</signal:update>"
