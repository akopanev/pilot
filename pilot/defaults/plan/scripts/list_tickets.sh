#!/usr/bin/env bash
set -euo pipefail

# List tickets by type with status, parent epic, and title.
# Usage: ./list_tickets.sh [type]
#   type: epic, task, bug, feature, chore (default: all)

TYPE="${1:-}"

ALL=$(tk query 2>/dev/null)
[ -z "$ALL" ] && { echo "No tickets found."; exit 0; }

FILTER='.'
[ -n "$TYPE" ] && FILTER="select(.type == \"$TYPE\")"

echo "$ALL" | jq -rs --arg filter "$FILTER" '
  def pad(n): tostring | . + (" " * (n - length)) | .[:n];

  # Task counts per parent (for epics)
  (map(select(.parent != null) | .parent) | group_by(.) | map({(.[0]): length}) | add // {}) as $task_counts |

  map('"$FILTER"') | sort_by(.title // .id) |

  if length == 0 then "No tickets found." else
    (["ID", "TYPE", "STATUS", "EPIC", "TASKS", "TITLE"] | @tsv),
    (.[] |
      [
        .id,
        .type,
        .status,
        (.parent // "-"),
        ($task_counts[.id] // 0 | tostring),
        .title
      ] | @tsv
    )
  end
' | column -t -s $'\t'
