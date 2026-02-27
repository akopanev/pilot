#!/bin/bash
# Init script for pilot Docker container.
# Runs as root: remaps pilot user UID to match host, copies credentials,
# then drops to pilot via gosu.

# Remap pilot user to match host UID
PILOT_UID="${PILOT_UID:-1000}"
if [ "$(id -u pilot)" != "$PILOT_UID" ]; then
    usermod -u "$PILOT_UID" pilot 2>/dev/null
fi
chown -R pilot:pilot /home/pilot 2>/dev/null || true

export HOME=/home/pilot

# Git config (mounted read-only at /mnt, copied so we can add safe.directory)
if [ -f /mnt/gitconfig ]; then
    cp /mnt/gitconfig /home/pilot/.gitconfig
fi
git config -f /home/pilot/.gitconfig safe.directory /workspace
chown pilot:pilot /home/pilot/.gitconfig 2>/dev/null || true

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

# OpenCode config (from host ~/.config/opencode/)
if [ -d /mnt/opencode-config ]; then
    mkdir -p /home/pilot/.config/opencode
    cp -rL /mnt/opencode-config/* /home/pilot/.config/opencode/ 2>/dev/null || true
fi
# OpenCode auth
if [ -f /mnt/opencode-auth.json ]; then
    mkdir -p /home/pilot/.local/share/opencode
    cp /mnt/opencode-auth.json /home/pilot/.local/share/opencode/auth.json
    chmod 600 /home/pilot/.local/share/opencode/auth.json
fi
# OpenCode: ensure all permissions allowed (no interactive prompts)
mkdir -p /home/pilot/.config/opencode
OCFILE=/home/pilot/.config/opencode/opencode.json
if [ -f "$OCFILE" ] && command -v jq >/dev/null 2>&1; then
    # merge permission into existing config
    jq '. + {"permission":{"*":"allow"}}' "$OCFILE" > "${OCFILE}.tmp" && mv "${OCFILE}.tmp" "$OCFILE"
else
    cat > "$OCFILE" <<'OCEOF'
{"permission":{"*":"allow"}}
OCEOF
fi
# Ensure pilot owns all config/local dirs (opencode needs .local/state/ too)
chown -R pilot:pilot /home/pilot/.config /home/pilot/.local 2>/dev/null || true

exec gosu pilot "$@"
