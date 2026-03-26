#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:?OUTPUT_DIR not set}"
CURRENT_INDEX="${CURRENT_INDEX:-0}"

TRANSLATIONS_FILE="${PILOT_CONFIG_DIR}/data/translations.json"

if [ ! -f "$TRANSLATIONS_FILE" ]; then
  echo "ERROR: Translations file not found at $TRANSLATIONS_FILE"
  exit 1
fi

if ! jq empty "$TRANSLATIONS_FILE" 2>/dev/null; then
  echo "ERROR: Invalid JSON in translations file"
  exit 1
fi

# Write each locale to its subfolder
for LOCALE in $(jq -r 'keys[]' "$TRANSLATIONS_FILE"); do
  LOCALE_DIR="${OUTPUT_DIR}/${LOCALE}"
  mkdir -p "$LOCALE_DIR"

  ITEM_ID=$(jq -r ".\"${LOCALE}\".canonicalId" "$TRANSLATIONS_FILE")
  OUTPUT_FILE="${LOCALE_DIR}/${ITEM_ID}.json"

  jq ".\"${LOCALE}\"" "$TRANSLATIONS_FILE" > "$OUTPUT_FILE"
  echo "  ${LOCALE}: $OUTPUT_FILE"
done

# Advance to next content item
NEXT_INDEX=$((CURRENT_INDEX + 1))
echo "<signal:var key=CURRENT_INDEX>$NEXT_INDEX</signal:var>"
echo "<signal:completed>Item $CURRENT_INDEX localized</signal:completed>"
