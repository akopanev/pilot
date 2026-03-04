#!/usr/bin/env bash
set -euo pipefail

# Clean up apptweak-fetch installation.
# Only remove on success — on failure, keep for debugging.

if [ "${PILOT_EXIT_STATUS:-}" != "success" ]; then
  echo "Pipeline failed — keeping .apptweak for debugging"
  exit 0
fi

APPTWEAK_DIR="$PILOT_CONFIG_DIR/.apptweak"

if [ -d "$APPTWEAK_DIR" ]; then
  rm -rf "$APPTWEAK_DIR"
  echo "Removed $APPTWEAK_DIR"
fi
