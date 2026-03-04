#!/usr/bin/env bash
set -euo pipefail

# Install apptweak-fetch, validate prerequisites.

APPTWEAK_DIR="${APPTWEAK_DIR:-.apptweak}"

# Install
if [ ! -f "$APPTWEAK_DIR/fetch.sh" ]; then
  echo "Installing apptweak-fetch..."
  curl -fsSL https://raw.githubusercontent.com/akopanev/apptweak-fetch/main/install.sh | bash -s -- "$APPTWEAK_DIR"
fi

echo "Pre-pipeline OK"
