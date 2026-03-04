#!/usr/bin/env bash
set -euo pipefail

# Verify gate — run automated checks based on what changed.
# Uses: $PILOT_DEFAULT_BRANCH, $PILOT_WORKING_BRANCH, $PILOT_TASK_ID

git checkout "$PILOT_WORKING_BRANCH" --quiet 2>/dev/null || true

echo "<signal:update>verify: $PILOT_TASK_ID</signal:update>"

CHANGED=$(git diff --name-only "$PILOT_DEFAULT_BRANCH"...HEAD)
ERRORS=""

# --- Mobile (React Native / Expo) ---
if echo "$CHANGED" | grep -q "^mobile/"; then
  echo "=== mobile: typecheck ==="
  if ! (cd mobile && pnpm typecheck 2>&1); then
    ERRORS="${ERRORS}mobile typecheck failed\n"
  fi

  echo "=== mobile: lint ==="
  if ! (cd mobile && pnpm lint 2>&1); then
    ERRORS="${ERRORS}mobile lint failed\n"
  fi

  echo "=== mobile: test ==="
  if ! (cd mobile && pnpm test --passWithNoTests 2>&1); then
    ERRORS="${ERRORS}mobile tests failed\n"
  fi
fi

# --- Backend ---
if echo "$CHANGED" | grep -q "^backend/"; then
  echo "=== backend: typecheck ==="
  if ! (cd backend && npm run typecheck 2>&1); then
    ERRORS="${ERRORS}backend typecheck failed\n"
  fi

  echo "=== backend: test ==="
  if ! (cd backend && npm test 2>&1); then
    ERRORS="${ERRORS}backend tests failed\n"
  fi
fi

# --- Result ---
if [ -n "$ERRORS" ]; then
  SUMMARY=$(echo -e "$ERRORS" | head -5)
  tk add-note "$PILOT_TASK_ID" "VERIFY FAIL:\n$SUMMARY"
  git add .tickets/
  git commit -m "$PILOT_TASK_ID: verify fail" --quiet

  echo "<signal:rejected>verify failed</signal:rejected>"
else
  tk add-note "$PILOT_TASK_ID" "VERIFY PASS: typecheck, lint, tests OK"
  git add .tickets/
  git commit -m "$PILOT_TASK_ID: verify pass" --quiet

  echo "<signal:approved>verify passed</signal:approved>"
fi
