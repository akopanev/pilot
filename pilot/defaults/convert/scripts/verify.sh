#!/usr/bin/env bash
set -euo pipefail

# Verify gate — run flutter analyze and dart format check.
# Uses: $PILOT_DEFAULT_BRANCH, $PILOT_WORKING_BRANCH, $PILOT_TASK_ID, $PILOT_FLUTTER_DIR

git checkout "$PILOT_WORKING_BRANCH" --quiet 2>/dev/null || true

echo "<signal:update>verify: $PILOT_TASK_ID</signal:update>"

FLUTTER_DIR="$PILOT_CONFIG_DIR/../../$PILOT_FLUTTER_DIR"
FAIL_LOG=$(mktemp)
FAILED=0

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

if [ -d "$FLUTTER_DIR" ]; then
  # Ensure deps are fetched
  if [ ! -d "$FLUTTER_DIR/.dart_tool" ]; then
    echo "=== flutter pub get ==="
    (cd "$FLUTTER_DIR" && flutter pub get 2>&1) || true
  fi

  run_check "flutter analyze" "$FLUTTER_DIR" flutter analyze --no-fatal-infos
  run_check "dart format check" "$FLUTTER_DIR" dart format --set-exit-if-changed --output=none lib/
fi

# --- Result ---
if [ "$FAILED" -ne 0 ]; then
  { echo "VERIFY FAIL:"; head -120 "$FAIL_LOG"; } | tk add-note "$PILOT_TASK_ID"
  rm -f "$FAIL_LOG"
  git add .tickets/
  git commit -m "$PILOT_TASK_ID: verify fail" --quiet

  echo "<signal:rejected>verify failed</signal:rejected>"
else
  rm -f "$FAIL_LOG"
  tk add-note "$PILOT_TASK_ID" "VERIFY PASS: flutter analyze, dart format OK"
  git add .tickets/
  git commit -m "$PILOT_TASK_ID: verify pass" --quiet

  echo "<signal:approved>verify passed</signal:approved>"
fi
