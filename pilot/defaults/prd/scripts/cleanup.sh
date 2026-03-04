#!/usr/bin/env bash
set -euo pipefail

# Clean up apptweak-fetch installation after successful pipeline run.

APPTWEAK_DIR="$PILOT_CONFIG_DIR/.apptweak"

if [ -d "$APPTWEAK_DIR" ]; then
  rm -rf "$APPTWEAK_DIR"
  echo "Removed $APPTWEAK_DIR"
fi
