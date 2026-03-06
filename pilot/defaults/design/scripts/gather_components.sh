#!/usr/bin/env bash
set -euo pipefail

# Install @gluestack-ui/themed so claude-code can read the actual
# TypeScript types and build a component catalog.

GLUESTACK_DIR="$PILOT_CONFIG_DIR/.gluestack"
CATALOG="$PILOT_CONFIG_DIR/data"

mkdir -p "$CATALOG"

# Skip if already installed (re-run tolerance)
if [ -d "$GLUESTACK_DIR/node_modules/@gluestack-ui" ]; then
  echo "gluestack already installed at $GLUESTACK_DIR"
  exit 0
fi

echo "Installing @gluestack-ui/themed..."
mkdir -p "$GLUESTACK_DIR"
cd "$GLUESTACK_DIR"
npm init -y --silent 2>/dev/null
npm install @gluestack-ui/themed @gluestack-style/react react react-native --silent 2>/dev/null

echo "gluestack installed at $GLUESTACK_DIR"
