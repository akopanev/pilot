#!/usr/bin/env bash
set -euo pipefail

# List all epics, sort by title (Epic 000, 001, ...).
# First one without child tasks → decompose it.
# All have children → done.

ALL=$(tk query 2>/dev/null)

# Epic IDs
EPICS=$(echo "$ALL" | jq -r 'select(.type == "epic" and .status != "closed") | .id')
[ -z "$EPICS" ] && { echo "<signal:failed>no epics found</signal:failed>"; exit 1; }

# Parents that already have tasks
HAS_TASKS=$(echo "$ALL" | jq -r 'select(.parent != null) | .parent' | sort -u)

# Build sorted list: "title|id" per line
SORTED=$(while read -r eid; do
  [ -z "$eid" ] && continue
  title=$(tk show "$eid" 2>/dev/null | grep -m1 '^# ' | sed 's/^# //')
  printf '%s|%s\n' "$title" "$eid"
done <<< "$EPICS" | sort)

# Find first epic without children
while IFS='|' read -r title eid; do
  [ -z "$eid" ] && continue
  echo "$HAS_TASKS" | grep -qF "$eid" && continue

  CONTENT=$(tk show "$eid" 2>/dev/null | sed '1,/^---$/d')
  echo "<signal:var key=PILOT_CURRENT_EPIC>$eid</signal:var>"
  echo "<signal:var key=PILOT_CURRENT_EPIC_TITLE>$title</signal:var>"
  echo "<signal:var key=PILOT_CURRENT_EPIC_CONTENT>$CONTENT</signal:var>"
  echo "<signal:ready>$eid|$title</signal:ready>"
  exit 0
done <<< "$SORTED"

echo "<signal:completed>all epics have tasks</signal:completed>"
