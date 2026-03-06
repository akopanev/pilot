#!/usr/bin/env bash
set -euo pipefail

# Install gluestack agent-skills — provides component patterns, styling
# rules, and validation checklists as markdown files for AI agents.

if command -v npx &>/dev/null; then
  echo "Installing gluestack agent-skills..."
  npx skills add gluestack/agent-skills 2>&1 || {
    echo "Warning: failed to install agent-skills, continuing without them"
  }
else
  echo "Warning: npx not found, skipping agent-skills install"
fi

echo "Pre-pipeline OK"
