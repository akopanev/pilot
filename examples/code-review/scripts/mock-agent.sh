#!/usr/bin/env bash
# mock-agent.sh — custom executor that simulates LLM signals.
#
# Receives the expanded prompt as a temp file argument ($1).
# Inspects the prompt content to decide which signals to emit.

set -euo pipefail

PROMPT_FILE="$1"
PROMPT=$(cat "$PROMPT_FILE")

# ── Setup step: emit api_url + completed ─────────────────
# Detects setup by checking if TASK placeholder is still unexpanded
if echo "$PROMPT" | grep -q '{{TASK}}'; then
    echo "Setting up project environment..."
    echo '<pilot:emit key="api_url">https://api.example.com/v1</pilot:emit>'
    echo '<pilot:completed>project setup complete</pilot:completed>'
    exit 0
fi

# ── Implementation step: check for SKIP_ME ───────────────
if echo "$PROMPT" | grep -q 'SKIP_ME'; then
    echo "Task marked for skipping."
    echo '<pilot:skip>task contains SKIP_ME marker</pilot:skip>'
    exit 0
fi

# ── Review step: reject round 1, approve round 2+ ────────
if echo "$PROMPT" | grep -q 'Review round'; then
    ROUND=$(echo "$PROMPT" | grep -oE 'Review round [0-9]+' | grep -oE '[0-9]+')
    if [ "${ROUND:-1}" = "1" ]; then
        echo "Found issues in implementation."
        echo '<pilot:reject>Missing error handling in edge cases</pilot:reject>'
    else
        echo "Implementation looks good."
        echo '<pilot:approve/>'
    fi
    exit 0
fi

# ── Default: implementation step — emit completed ────────
echo "Implementing the task..."
echo '<pilot:emit key="last_impl">done</pilot:emit>'
echo '<pilot:completed>implementation finished</pilot:completed>'
exit 0
