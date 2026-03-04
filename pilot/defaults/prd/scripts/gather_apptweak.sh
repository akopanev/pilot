#!/usr/bin/env bash
set -euo pipefail

# Fetch competitor data from App Store via apptweak-fetch.
# PILOT_CONFIG_DIR is set by the engine (absolute path to pipeline dir).

APPTWEAK_DIR="$PILOT_CONFIG_DIR/.apptweak"
OUTPUT_DIR="$PILOT_CONFIG_DIR/$PILOT_APPTWEAK_OUTPUT_DIR"

if [ -f "$OUTPUT_DIR/apps.json" ]; then
  APP_COUNT=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_DIR/apps.json'))))" 2>/dev/null || echo "?")
  echo "<signal:ready>$APP_COUNT competitors (cached)</signal:ready>"
  exit 0
fi

echo "<signal:update>fetching competitors: $PILOT_KEYWORDS</signal:update>"

"$APPTWEAK_DIR/fetch.sh" "$PILOT_KEYWORDS" "$OUTPUT_DIR" "$PILOT_NUM_TOP_APPS"

if [ ! -f "$OUTPUT_DIR/apps.json" ]; then
  echo "<signal:failed>fetch produced no data</signal:failed>"
  exit 1
fi

APP_COUNT=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_DIR/apps.json'))))" 2>/dev/null || echo "?")
echo "<signal:ready>$APP_COUNT competitors fetched</signal:ready>"
