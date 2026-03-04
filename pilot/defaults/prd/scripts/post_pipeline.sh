#!/usr/bin/env bash
set -euo pipefail

# Clean up apptweak-fetch installation.

APPTWEAK_DIR="${APPTWEAK_DIR:-.apptweak}"

if [ -d "$APPTWEAK_DIR" ]; then
  rm -rf "$APPTWEAK_DIR"
  echo "Removed $APPTWEAK_DIR"
fi
