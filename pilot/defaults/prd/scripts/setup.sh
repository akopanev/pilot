#!/usr/bin/env bash
set -euo pipefail

# Install apptweak-fetch if not present, verify API key.

APPTWEAK_DIR="${APPTWEAK_DIR:-.apptweak}"

if [ ! -f "$APPTWEAK_DIR/fetch.sh" ]; then
  echo "Installing apptweak-fetch..."
  curl -fsSL https://raw.githubusercontent.com/akopanev/apptweak-fetch/main/install.sh | bash -s -- "$APPTWEAK_DIR"
fi

# Check API key — env takes priority, fall back to .env file
if [ -z "${APPTWEAK_API_KEY:-}" ]; then
  if [ -f "$APPTWEAK_DIR/.env" ]; then
    set -a
    source "$APPTWEAK_DIR/.env" 2>/dev/null || true
    set +a
  fi
fi

if [ -z "${APPTWEAK_API_KEY:-}" ]; then
  echo "<signal:failed>APPTWEAK_API_KEY not set. Export it or add to $APPTWEAK_DIR/.env</signal:failed>"
  exit 1
fi

# Check keywords are configured
if [ -z "${PILOT_KEYWORDS:-}" ]; then
  echo "<signal:failed>PILOT_KEYWORDS not set. Edit pipeline.yaml vars section</signal:failed>"
  exit 1
fi

# Check brief exists
if [ ! -f "${PILOT_BRIEF:-brief.md}" ]; then
  echo "<signal:failed>Brief not found: ${PILOT_BRIEF:-brief.md}. Create it first</signal:failed>"
  exit 1
fi

echo "<signal:ready>setup complete</signal:ready>"
