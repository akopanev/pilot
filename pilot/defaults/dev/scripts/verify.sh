#!/usr/bin/env bash
set -euo pipefail

# Verify gate — run automated checks based on what changed.
# Uses: $PILOT_DEFAULT_BRANCH, $PILOT_WORKING_BRANCH, $PILOT_TASK_ID

git checkout "$PILOT_WORKING_BRANCH" --quiet 2>/dev/null || true

echo "<signal:update>verify: $PILOT_TASK_ID</signal:update>"

CHANGED=$(git diff --name-only "$PILOT_DEFAULT_BRANCH"...HEAD)
FAIL_LOG=$(mktemp)
FAILED=0

# Run a check: label, working dir, command...
run_check() {
  local label="$1" dir="$2"; shift 2
  echo "=== $label ==="
  local out
  if out=$( cd "$dir" && "$@" 2>&1 ); then
    echo "$out"
  else
    echo "$out"
    FAILED=1
    printf "\n### %s\n%s\n" "$label" "$out" >> "$FAIL_LOG"
  fi
}

# --- Mobile (React Native / Expo) ---
if echo "$CHANGED" | grep -q "^mobile/"; then
  if [ ! -d "mobile/node_modules" ]; then
    echo "=== mobile: install ==="
    (cd mobile && pnpm install --frozen-lockfile 2>&1) || true
  fi

  run_check "mobile: typecheck" mobile pnpm typecheck
  run_check "mobile: lint" mobile pnpm lint
  run_check "mobile: test" mobile pnpm test --passWithNoTests
fi

# --- Backend ---
if echo "$CHANGED" | grep -q "^backend/"; then
  if [ ! -d "backend/node_modules" ]; then
    echo "=== backend: install ==="
    (cd backend && npm ci 2>&1) || true
  fi

  run_check "backend: typecheck" backend npm run typecheck
  run_check "backend: test" backend npm test
fi

# --- Result ---
if [ "$FAILED" -ne 0 ]; then
  # Pipe via stdin to avoid shell-quoting issues with compiler output.
  # Truncate to first 120 lines so notes stay actionable.
  { echo "VERIFY FAIL:"; head -120 "$FAIL_LOG"; } | tk add-note "$PILOT_TASK_ID"
  rm -f "$FAIL_LOG"
  git add .tickets/
  git commit -m "$PILOT_TASK_ID: verify fail" --quiet

  echo "<signal:rejected>verify failed</signal:rejected>"
else
  rm -f "$FAIL_LOG"
  tk add-note "$PILOT_TASK_ID" "VERIFY PASS: typecheck, lint, tests OK"
  git add .tickets/
  git commit -m "$PILOT_TASK_ID: verify pass" --quiet

  echo "<signal:approved>verify passed</signal:approved>"
fi
