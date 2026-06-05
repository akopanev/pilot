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
# Global gitignore (copied from host)
if [ -f /mnt/gitignore_global ]; then
    mkdir -p /home/pilot/.config/git
    cp /mnt/gitignore_global /home/pilot/.config/git/ignore
    chown -R pilot:pilot /home/pilot/.config/git
fi
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

# ~/.gemini config — home of Antigravity (agy): oauth token, settings, and
# trustedWorkspaces live under ~/.gemini/antigravity-cli/ (gemini-cli itself is
# no longer installed; agy is its successor).
if [ -d /mnt/gemini ]; then
    mkdir -p /home/pilot/.gemini
    cp -rL /mnt/gemini/* /home/pilot/.gemini/ 2>/dev/null || true
    chown -R pilot:pilot /home/pilot/.gemini
fi

# Antigravity (agy): trust the container workspace. The host's trustedWorkspaces
# (copied above under .gemini/antigravity-cli/) point at host paths, but the
# container cwd is /workspace — without it `agy --dangerously-skip-permissions`
# HANGS on the interactive trust prompt. Add /workspace (create settings if absent).
AGY_SETTINGS=/home/pilot/.gemini/antigravity-cli/settings.json
if command -v jq >/dev/null 2>&1; then
    mkdir -p /home/pilot/.gemini/antigravity-cli
    if [ -f "$AGY_SETTINGS" ]; then
        jq '.trustedWorkspaces = ((.trustedWorkspaces // []) + ["/workspace"] | unique)' \
            "$AGY_SETTINGS" > "${AGY_SETTINGS}.tmp" && mv "${AGY_SETTINGS}.tmp" "$AGY_SETTINGS"
    else
        echo '{"trustedWorkspaces":["/workspace"]}' > "$AGY_SETTINGS"
    fi
    chown -R pilot:pilot /home/pilot/.gemini
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
