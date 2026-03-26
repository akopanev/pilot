#!/usr/bin/env bash
set -euo pipefail

# Final validation — full build of the Flutter project.
# Emits: <signal:approved>builds OK</signal:approved> or <signal:failed>reason</signal:failed>

FLUTTER_DIR="$PILOT_CONFIG_DIR/../../$PILOT_FLUTTER_DIR"

if [ ! -d "$FLUTTER_DIR" ]; then
  echo "<signal:failed>Flutter project not found at $PILOT_FLUTTER_DIR</signal:failed>"
  exit 0
fi

cd "$FLUTTER_DIR"

echo "<signal:update>running final validation</signal:update>"

# Ensure deps
flutter pub get 2>&1

FAILED=0
FAIL_LOG=$(mktemp)

# Analyze
echo "=== flutter analyze ==="
if ! flutter analyze 2>&1 | tee -a "$FAIL_LOG"; then
  FAILED=1
fi

# Build (iOS if on macOS, otherwise just check analysis)
if [ "$(uname)" = "Darwin" ]; then
  echo "=== flutter build ios (no-codesign) ==="
  if ! flutter build ios --no-codesign 2>&1 | tee -a "$FAIL_LOG"; then
    FAILED=1
  fi
fi

# Tests (if any exist)
TEST_FILES=$(find test -name '*_test.dart' 2>/dev/null | head -1 || true)
if [ -n "$TEST_FILES" ]; then
  echo "=== flutter test ==="
  if ! flutter test 2>&1 | tee -a "$FAIL_LOG"; then
    FAILED=1
  fi
fi

rm -f "$FAIL_LOG"

if [ "$FAILED" -ne 0 ]; then
  echo "<signal:failed>build validation failed</signal:failed>"
else
  echo "<signal:approved>all checks passed</signal:approved>"
fi
