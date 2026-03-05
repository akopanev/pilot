#!/usr/bin/env bash
set -euo pipefail

# Find the next epic ticket that has no child tasks yet.
# tk query outputs JSONL (one JSON object per line).
# Title lives in the markdown body, not in JSON — we use tk show to get it.

# Get all open epic IDs, sorted by ID (creation order)
EPIC_IDS=$(tk query 2>/dev/null | jq -r 'select(.type == "epic" and .status != "closed") | .id' | sort)

if [ -z "$EPIC_IDS" ]; then
  echo "<signal:failed>no epic tickets found — run create_epics first</signal:failed>"
  exit 1
fi

# Get all task parent IDs (epics that already have children)
PARENTS_WITH_TASKS=$(tk query 2>/dev/null | jq -r 'select(.type == "task" and .parent != null) | .parent' | sort -u)

# Find the first epic that has no child tasks
while read -r epic_id; do
  if ! echo "$PARENTS_WITH_TASKS" | grep -qF "$epic_id"; then
    # Get full ticket content
    CONTENT=$(tk show "$epic_id" 2>/dev/null | sed '1,/^---$/d')
    TITLE=$(echo "$CONTENT" | grep -m1 '^# ' | sed 's/^# //')
    echo "<signal:var key=PILOT_CURRENT_EPIC>$epic_id</signal:var>"
    echo "<signal:var key=PILOT_CURRENT_EPIC_TITLE>$TITLE</signal:var>"
    echo "<signal:var key=PILOT_CURRENT_EPIC_CONTENT>$CONTENT</signal:var>"
    echo "<signal:ready>$epic_id|$TITLE</signal:ready>"
    exit 0
  fi
done <<< "$EPIC_IDS"

# All epics have tasks
echo "<signal:completed>all epics have tasks</signal:completed>"
