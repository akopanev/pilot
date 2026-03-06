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

# Collect rows as tab-separated, then sort and format
ROWS=""
while read -r tid; do
  [ -z "$tid" ] && continue

  META=$(echo "$ALL" | jq -r --arg id "$tid" 'select(.id == $id) | [.type, .status, (.parent // "-")] | @tsv')
  TTYPE=$(echo "$META" | cut -f1)
  STATUS=$(echo "$META" | cut -f2)
  PARENT=$(echo "$META" | cut -f3)

  TITLE=$(tk show "$tid" 2>/dev/null | awk '/^---$/{n++; next} n>=2' | grep -m1 '^# ' | sed 's/^# //')

  COUNT=$(echo "$TASK_COUNTS" | grep "^${tid}	" | cut -f2 || true)
  [ -z "$COUNT" ] && COUNT=0

  ROWS+="${TITLE}	${tid}	${TTYPE}	${STATUS}	${PARENT}	${COUNT}
"
done <<< "$IDS"

# Header + sorted rows (sorted by title via first column, then reformatted)
{
  printf "%s\t%s\t%s\t%s\t%s\t%s\n" "ID" "TYPE" "STATUS" "EPIC" "TASKS" "TITLE"
  echo "$ROWS" | sort | while IFS=$'\t' read -r title tid ttype status parent count; do
    [ -z "$tid" ] && continue
    printf "%s\t%s\t%s\t%s\t%s\t%s\n" "$tid" "$ttype" "$status" "$parent" "$count" "$title"
  done
} | column -t -s $'\t'
