#!/bin/bash
# Init script for pilot Docker container.
# Runs as root: remaps pilot user UID to match host, copies credentials,
# then drops to pilot via gosu.

# Remap pilot user to match host UID
APP_UID="${APP_UID:-1000}"
if [ "$(id -u pilot)" != "$APP_UID" ]; then
    usermod -u "$APP_UID" pilot 2>/dev/null
fi
chown -R pilot:pilot /home/pilot

export HOME=/home/pilot

# Claude config (settings, agents, etc.)
if [ -d /mnt/claude ]; then
    mkdir -p /home/pilot/.claude
    for f in .credentials.json settings.json settings.local.json CLAUDE.md; do
        [ -e "/mnt/claude/$f" ] && cp -L "/mnt/claude/$f" "/home/pilot/.claude/$f" 2>/dev/null || true
    done
    for d in commands skills hooks agents plugins; do
        [ -d "/mnt/claude/$d" ] && cp -rL "/mnt/claude/$d" "/home/pilot/.claude/" 2>/dev/null || true
    done
    chown -R pilot:pilot /home/pilot/.claude
fi

# Claude credentials extracted from macOS Keychain (mounted separately by pilot-docker)
if [ -f /mnt/claude-credentials.json ]; then
    mkdir -p /home/pilot/.claude
    cp /mnt/claude-credentials.json /home/pilot/.claude/.credentials.json
    chown -R pilot:pilot /home/pilot/.claude
    chmod 600 /home/pilot/.claude/.credentials.json
fi

# Export env vars from claude settings.json (if jq available)
if [ -f /home/pilot/.claude/settings.json ] && command -v jq >/dev/null 2>&1; then
    while IFS='=' read -r key val; do
        [ -n "$key" ] && export "$key=$val"
    done < <(jq -r '.env // {} | to_entries[] | "\(.key)=\(.value)"' /home/pilot/.claude/settings.json 2>/dev/null)
fi

# Codex credentials
if [ -d /mnt/codex ]; then
    mkdir -p /home/pilot/.codex
    cp -rL /mnt/codex/* /home/pilot/.codex/ 2>/dev/null || true
    chown -R pilot:pilot /home/pilot/.codex
fi

# OpenCode auth
if [ -f /mnt/opencode-auth.json ]; then
    mkdir -p /home/pilot/.opencode
    cp /mnt/opencode-auth.json /home/pilot/.opencode/auth.json
    chown -R pilot:pilot /home/pilot/.opencode
    chmod 600 /home/pilot/.opencode/auth.json
fi

exec gosu pilot "$@"
