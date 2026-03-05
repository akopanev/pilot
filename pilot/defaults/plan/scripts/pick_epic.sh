#!/usr/bin/env bash
set -euo pipefail

# Find the next epic ticket that has no child tasks yet.
# Epics are sorted by title (Epic 0, Epic 1, ...) so we process in order.

# Get all epic tickets as JSON, sorted by title
EPICS_JSON=$(tk query '[.[] | select(.type == "epic" and .status != "closed")] | sort_by(.title)')

if [ "$EPICS_JSON" = "[]" ] || [ -z "$EPICS_JSON" ]; then
  echo "<signal:failed>no epic tickets found — run create_epics first</signal:failed>"
  exit 1
fi

# For each epic, check if it has child tasks
EPIC_IDS=$(echo "$EPICS_JSON" | python3 -c "
import json, sys
epics = json.load(sys.stdin)
for e in epics:
    print(e['id'] + '|' + e['title'])
")

while IFS='|' read -r epic_id epic_title; do
  # Check if any tasks have this epic as parent
  CHILD_COUNT=$(tk query "[.[] | select(.parent == \"$epic_id\")] | length")
  if [ "$CHILD_COUNT" = "0" ]; then
    echo "<signal:ready>$epic_id|$epic_title</signal:ready>"
    exit 0
  fi
done <<< "$EPIC_IDS"

# All epics have tasks
echo "<signal:completed>all epics have tasks</signal:completed>"
