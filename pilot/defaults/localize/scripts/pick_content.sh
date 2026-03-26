#!/usr/bin/env bash
set -euo pipefail

# Paths are relative to project root (shell stages run from there)
INPUT_FILE="${INPUT_FILE:?INPUT_FILE is required — set it in pipeline.yaml vars}"
OUTPUT_DIR="${OUTPUT_DIR:?OUTPUT_DIR is required — set it in pipeline.yaml vars}"
CURRENT_INDEX="${CURRENT_INDEX:-0}"

if [ ! -f "$INPUT_FILE" ]; then
  echo "INPUT_FILE not found: $INPUT_FILE (cwd: $(pwd))"
  exit 1
fi

mkdir -p "${PILOT_CONFIG_DIR}/data" "$OUTPUT_DIR"

TOTAL=$(jq 'length' "$INPUT_FILE")

if [ "$CURRENT_INDEX" -ge "$TOTAL" ]; then
  echo "<signal:completed>All $TOTAL content items processed</signal:completed>"
  exit 0
fi

# Extract current item to working file
jq ".[$CURRENT_INDEX]" "$INPUT_FILE" > "${PILOT_CONFIG_DIR}/data/current_content.json"

ITEM_ID=$(jq -r '.id' "${PILOT_CONFIG_DIR}/data/current_content.json")
ITEM_TITLE=$(jq -r '.title' "${PILOT_CONFIG_DIR}/data/current_content.json")

echo "Item $((CURRENT_INDEX + 1))/$TOTAL: $ITEM_TITLE"
echo "  id: $ITEM_ID"

# Create en output — reshape to target format (no LLM needed)
mkdir -p "${OUTPUT_DIR}/en"
jq '{
  type: "article",
  locale: "en",
  canonicalId: .id,
  meta: { status: "published" },
  data: {
    title: .title,
    card_title: .card_title,
    markdown: .article_markdown,
    imageUrl: .image_url,
    sources: .grounding_sources
  }
}' "${PILOT_CONFIG_DIR}/data/current_content.json" > "${OUTPUT_DIR}/en/${ITEM_ID}.json"

echo "  en: ${OUTPUT_DIR}/en/${ITEM_ID}.json"

echo "<signal:var key=CURRENT_ID>$ITEM_ID</signal:var>"
echo "<signal:ready>$CURRENT_INDEX</signal:ready>"
