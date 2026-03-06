#!/usr/bin/env bash
set -euo pipefail

# List tickets by type with status, parent epic, task count, and title.
# Usage: ./list_tickets.sh [type]
#   type: epic, task, bug, feature, chore (default: all)

TYPE="${1:-}"

ALL=$(tk query 2>/dev/null)
[ -z "$ALL" ] && { echo "No tickets found."; exit 0; }

# Filter by type if specified
if [ -n "$TYPE" ]; then
  IDS=$(echo "$ALL" | jq -r "select(.type == \"$TYPE\") | .id")
else
  IDS=$(echo "$ALL" | jq -r '.id')
fi
[ -z "$IDS" ] && { echo "No ${TYPE:-tickets} found."; exit 0; }

# Task counts per parent
TASK_COUNTS=$(echo "$ALL" | jq -rs '
  map(select(.parent != null) | .parent) | group_by(.) |
  map(.[0] + "\t" + (length | tostring)) | .[]
')

# Print header
printf "%-10s  %-6s  %-8s  %-10s  %5s  %s\n" "ID" "TYPE" "STATUS" "EPIC" "TASKS" "TITLE"
printf "%-10s  %-6s  %-8s  %-10s  %5s  %s\n" "----------" "------" "--------" "----------" "-----" "------------------------------------"

# For each ticket: get title from tk show (first # heading after frontmatter)
while read -r tid; do
  [ -z "$tid" ] && continue

  # Get metadata from JSON
  META=$(echo "$ALL" | jq -r --arg id "$tid" 'select(.id == $id) | [.type, .status, (.parent // "-")] | @tsv')
  TTYPE=$(echo "$META" | cut -f1)
  STATUS=$(echo "$META" | cut -f2)
  PARENT=$(echo "$META" | cut -f3)

  # Get title from markdown (first # heading after ---)
  TITLE=$(tk show "$tid" 2>/dev/null | sed '1,/^---$/d' | grep -m1 '^# ' | sed 's/^# //')

  # Task count
  COUNT=$(echo "$TASK_COUNTS" | grep "^${tid}	" | cut -f2)
  [ -z "$COUNT" ] && COUNT=0

  printf "%-10s  %-6s  %-8s  %-10s  %5s  %s\n" "$tid" "$TTYPE" "$STATUS" "$PARENT" "$COUNT" "$TITLE"
done <<< "$IDS" | sort -k7
