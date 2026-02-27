#!/usr/bin/env bash
set -euo pipefail

# PILOT v2 installer
# Usage:
#   curl -sSL <url>/install.sh | bash
#   bash install.sh
#   PILOT_REPO=/path/to/local install.sh

INSTALL_DIR="$HOME/.pilot"
VENV_DIR="$INSTALL_DIR/.venv"
BIN_DIR="$HOME/.local/bin"
WRAPPER="$BIN_DIR/pilot"
REPO_URL="${PILOT_REPO_URL:-https://github.com/akopanev/pilot.git}"

info()  { printf '\033[1;34m=>\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m!!\033[0m %s\n' "$*" >&2; exit 1; }

# --- Find Python 3.11+ ---
find_python() {
    for candidate in python3.13 python3.12 python3.11 python3; do
        if command -v "$candidate" &>/dev/null; then
            local ver major
            ver=$("$candidate" -c "import sys; print(sys.version_info.minor)" 2>/dev/null) || continue
            major=$("$candidate" -c "import sys; print(sys.version_info.major)" 2>/dev/null) || continue
            if [[ "$major" -eq 3 && "$ver" -ge 11 ]]; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python) || error "Python 3.11+ not found. Install it first."
PY_VERSION=$("$PYTHON" --version)
info "Using $PY_VERSION ($PYTHON)"

# --- Get source code ---
if [[ -n "${PILOT_REPO:-}" ]]; then
    info "Copying from local repo: $PILOT_REPO"
    rm -rf "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='*.egg-info' \
        "$PILOT_REPO/" "$INSTALL_DIR/"
elif [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Updating existing install..."
    git -C "$INSTALL_DIR" fetch --quiet
    git -C "$INSTALL_DIR" reset --hard origin/master
    git -C "$INSTALL_DIR" clean -fdx --exclude='.venv'
else
    info "Cloning PILOT..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# --- Create / refresh venv ---
if [[ -d "$VENV_DIR" ]] && ! "$VENV_DIR/bin/python" --version &>/dev/null; then
    warn "Existing virtualenv is broken, recreating..."
    rm -rf "$VENV_DIR"
fi

if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtualenv..."
    "$PYTHON" -m venv "$VENV_DIR"
else
    info "Virtualenv exists, upgrading..."
fi

info "Installing PILOT into venv..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet "$INSTALL_DIR"

# --- Write wrapper scripts ---
mkdir -p "$BIN_DIR"

# pilot — native CLI
cat > "$WRAPPER" <<'WRAPPER_EOF'
#!/usr/bin/env bash
exec "$HOME/.pilot/.venv/bin/python" -m pilot "$@"
WRAPPER_EOF
chmod +x "$WRAPPER"
info "Wrapper installed at $WRAPPER"

# pilot-docker — Docker runner with credential forwarding
DOCKER_WRAPPER="$BIN_DIR/pilot-docker"
cp "$INSTALL_DIR/scripts/pilot-docker" "$DOCKER_WRAPPER"
chmod +x "$DOCKER_WRAPPER"
info "Docker wrapper installed at $DOCKER_WRAPPER"

# --- PATH check ---
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        warn "$BIN_DIR is not in your PATH."
        warn "Add this to your shell profile:"
        warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        ;;
esac

info "Done! Run: pilot --version"
