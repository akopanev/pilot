#!/usr/bin/env bash
set -euo pipefail

# Find the next epic to decompose:
# 1. Has no child tasks yet (not yet decomposed)
# 2. All dependency epics are already decomposed (have children)
#
# We don't use `tk ready` because epics don't auto-close.
# Instead: an epic's deps are "satisfied" for planning purposes
# when all dependency epics already have tasks created.

ALL_TICKETS=$(tk query 2>/dev/null)

# Get epic IDs sorted by title (Epic 000 < Epic 001 < ...)
EPICS=$(echo "$ALL_TICKETS" | jq -r 'select(.type == "epic" and .status != "closed") | .id')

if [ -z "$EPICS" ]; then
  echo "<signal:failed>no epic tickets found — run create_epics first</signal:failed>"
  exit 1
fi

# Build set of epics that already have child tasks
PARENTS_WITH_TASKS=$(echo "$ALL_TICKETS" | jq -r 'select(.type == "task" and .parent != null) | .parent' | sort -u)

# For each epic, get its title for sorting
EPIC_LIST=""
while read -r eid; do
  [ -z "$eid" ] && continue
  TITLE=$(tk show "$eid" 2>/dev/null | grep -m1 '^# ' | sed 's/^# //')
  EPIC_LIST="${EPIC_LIST}${TITLE}|${eid}\n"
done <<< "$EPICS"

# Sort by title (Epic 000 first) and iterate
while IFS='|' read -r title epic_id; do
  [ -z "$epic_id" ] && continue

  # Skip if already has children (already decomposed)
  if echo "$PARENTS_WITH_TASKS" | grep -qF "$epic_id"; then
    continue
  fi

  # Check if all dep epics are already decomposed (have children)
  DEPS=$(echo "$ALL_TICKETS" | jq -r "select(.id == \"$epic_id\") | .deps[]?" 2>/dev/null)
  ALL_DEPS_READY=true
  for dep_id in $DEPS; do
    [ -z "$dep_id" ] && continue
    if ! echo "$PARENTS_WITH_TASKS" | grep -qF "$dep_id"; then
      ALL_DEPS_READY=false
      break
    fi
  done

  if [ "$ALL_DEPS_READY" = true ]; then
    CONTENT=$(tk show "$epic_id" 2>/dev/null | sed '1,/^---$/d')
    TITLE_CLEAN=$(echo "$CONTENT" | grep -m1 '^# ' | sed 's/^# //')
    echo "<signal:var key=PILOT_CURRENT_EPIC>$epic_id</signal:var>"
    echo "<signal:var key=PILOT_CURRENT_EPIC_TITLE>$TITLE_CLEAN</signal:var>"
    echo "<signal:var key=PILOT_CURRENT_EPIC_CONTENT>$CONTENT</signal:var>"
    echo "<signal:ready>$epic_id|$TITLE_CLEAN</signal:ready>"
    exit 0
  fi
done < <(echo -e "$EPIC_LIST" | sort)

# Check: all decomposed or stuck?
ALL_DONE=true
while read -r eid; do
  [ -z "$eid" ] && continue
  if ! echo "$PARENTS_WITH_TASKS" | grep -qF "$eid"; then
    ALL_DONE=false
    break
  fi
done <<< "$EPICS"

if [ "$ALL_DONE" = true ]; then
  echo "<signal:completed>all epics have tasks</signal:completed>"
else
  echo "<signal:failed>epics without tasks exist but deps are not satisfied — check epic dependencies</signal:failed>"
fi
