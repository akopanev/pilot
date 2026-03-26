#!/usr/bin/env bash
set -euo pipefail

# Find next epic without child tasks → decompose it.
# All epics have children → done.
# Emits: <signal:ready>id|title</signal:ready> or <signal:completed>done</signal:completed>

# Sync with remote
git pull --ff-only --quiet 2>/dev/null || true

ALL=$(tk query 2>/dev/null)

# Epic IDs (non-closed)
EPICS=$(echo "$ALL" | jq -r 'select(.type == "epic" and .status != "closed") | .id')
[ -z "$EPICS" ] && { echo "<signal:completed>all epics closed</signal:completed>"; exit 0; }

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

  CONTENT=$(tk show "$eid" 2>/dev/null | awk '/^---$/{n++; next} n>=2')
  echo "<signal:var key=PILOT_CURRENT_EPIC>$eid</signal:var>"
  echo "<signal:var key=PILOT_CURRENT_EPIC_TITLE>$title</signal:var>"
  echo "<signal:var key=PILOT_CURRENT_EPIC_CONTENT>$CONTENT</signal:var>"
  echo "<signal:ready>$eid|$title</signal:ready>"
  exit 0
done <<< "$SORTED"

echo "<signal:completed>all epics have tasks</signal:completed>"
