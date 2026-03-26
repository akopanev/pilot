#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:?OUTPUT_DIR not set}"

echo "Merging locale files into content.json..."

COUNT=0
for DIR in "$OUTPUT_DIR"/*/; do
  [ -d "$DIR" ] || continue
  LOCALE=$(basename "$DIR")

  # Collect all {id}.json files, skip content.json itself
  FILES=()
  for F in "$DIR"*.json; do
    [ -f "$F" ] || continue
    [ "$(basename "$F")" = "content.json" ] && continue
    FILES+=("$F")
  done

  if [ ${#FILES[@]} -eq 0 ]; then
    echo "  $LOCALE: no files, skipping"
    continue
  fi

  jq -s '.' "${FILES[@]}" > "${DIR}content.json"
  echo "  $LOCALE: ${#FILES[@]} items → ${DIR}content.json"
  COUNT=$((COUNT + 1))
done

echo "<signal:completed>Merged $COUNT locales</signal:completed>"
