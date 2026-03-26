#!/usr/bin/env bash
set -euo pipefail

# Create Flutter project if it doesn't exist.
# Emits: <signal:ready>path</signal:ready>

FLUTTER_DIR="$PILOT_CONFIG_DIR/../../$PILOT_FLUTTER_DIR"

if [ -d "$FLUTTER_DIR" ] && [ -f "$FLUTTER_DIR/pubspec.yaml" ]; then
  echo "Flutter project already exists at $PILOT_FLUTTER_DIR/"
  echo "<signal:ready>$PILOT_FLUTTER_DIR</signal:ready>"
  exit 0
fi

echo "<signal:update>creating Flutter project at $PILOT_FLUTTER_DIR</signal:update>"

cd "$PILOT_CONFIG_DIR/../.."
flutter create --org com.example "$PILOT_FLUTTER_DIR" 2>&1

# Commit and push scaffold
git add "$PILOT_FLUTTER_DIR/"
git commit -m "convert: scaffold Flutter project" --quiet
git push --quiet

echo "<signal:ready>$PILOT_FLUTTER_DIR</signal:ready>"
