#!/usr/bin/env bash
set -euo pipefail

# Install apptweak-fetch if not present.
# PILOT_CONFIG_DIR is set by the engine (absolute path to pipeline dir).

APPTWEAK_DIR="$PILOT_CONFIG_DIR/.apptweak"

if [ ! -f "$APPTWEAK_DIR/fetch.sh" ]; then
  echo "Installing apptweak-fetch..."
  curl -fsSL https://raw.githubusercontent.com/akopanev/apptweak-fetch/master/install.sh | bash -s -- "$APPTWEAK_DIR"
fi

echo "Pre-pipeline OK"
