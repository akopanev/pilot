#!/bin/bash
# Selective copy of credentials from read-only mounts into container home.
# Mounts at /mnt/claude and /mnt/codex are read-only — we copy only
# essential files to avoid the multi-GB claude cache.

# Claude config (settings, agents, etc.)
if [ -d /mnt/claude ]; then
    mkdir -p "$HOME/.claude"
    for f in .credentials.json settings.json settings.local.json CLAUDE.md; do
        [ -e "/mnt/claude/$f" ] && cp -L "/mnt/claude/$f" "$HOME/.claude/$f" 2>/dev/null || true
    done
    for d in commands skills hooks agents plugins; do
        [ -d "/mnt/claude/$d" ] && cp -rL "/mnt/claude/$d" "$HOME/.claude/" 2>/dev/null || true
    done
fi

# Claude credentials extracted from macOS Keychain (mounted separately by pilot-docker)
if [ -f /mnt/claude-credentials.json ]; then
    mkdir -p "$HOME/.claude"
    cp /mnt/claude-credentials.json "$HOME/.claude/.credentials.json"
    chmod 600 "$HOME/.claude/.credentials.json"
fi

# Export env vars from claude settings.json (if jq available)
if [ -f "$HOME/.claude/settings.json" ] && command -v jq >/dev/null 2>&1; then
    while IFS='=' read -r key val; do
        [ -n "$key" ] && export "$key=$val"
    done < <(jq -r '.env // {} | to_entries[] | "\(.key)=\(.value)"' "$HOME/.claude/settings.json" 2>/dev/null)
fi

# Codex credentials
if [ -d /mnt/codex ]; then
    mkdir -p "$HOME/.codex"
    cp -rL /mnt/codex/* "$HOME/.codex/" 2>/dev/null || true
fi

# OpenCode auth
if [ -f /mnt/opencode-auth.json ]; then
    mkdir -p "$HOME/.opencode"
    cp /mnt/opencode-auth.json "$HOME/.opencode/auth.json"
    chmod 600 "$HOME/.opencode/auth.json"
fi

# Git safe.directory — host-mounted workspace ownership won't match container user
git config --global safe.directory /workspace

exec "$@"
