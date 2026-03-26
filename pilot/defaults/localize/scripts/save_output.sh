#!/usr/bin/env bash
set -euo pipefail

CURRENT_INDEX="${CURRENT_INDEX:-0}"

# Advance to next content item
NEXT_INDEX=$((CURRENT_INDEX + 1))
echo "<signal:var key=CURRENT_INDEX>$NEXT_INDEX</signal:var>"
echo "<signal:completed>Item $CURRENT_INDEX localized</signal:completed>"
