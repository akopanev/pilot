#!/usr/bin/env bash
set -euo pipefail

# Fetch competitor data from App Store via apptweak-fetch.

APPTWEAK_DIR="${APPTWEAK_DIR:-.apptweak}"
OUTPUT_DIR="data/competitors"

echo "<signal:update>fetching competitors: $PILOT_KEYWORDS</signal:update>"

"$APPTWEAK_DIR/fetch.sh" "$PILOT_KEYWORDS" "$OUTPUT_DIR"

if [ ! -f "$OUTPUT_DIR/apps.json" ]; then
  echo "<signal:failed>fetch produced no data</signal:failed>"
  exit 1
fi

APP_COUNT=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_DIR/apps.json'))))" 2>/dev/null || echo "?")
echo "<signal:ready>$APP_COUNT competitors fetched</signal:ready>"
