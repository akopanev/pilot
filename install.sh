#!/usr/bin/env bash
set -euo pipefail

REPO="https://raw.githubusercontent.com/akopanev/pilot/master"
INSTALL_DIR="${PILOT_INSTALL_DIR:-.pilot}"

echo "installing pilot to $INSTALL_DIR..."

mkdir -p "$INSTALL_DIR/scripts"

curl -fsSL "$REPO/pilot.sh" -o "$INSTALL_DIR/pilot.sh"
curl -fsSL "$REPO/Dockerfile" -o "$INSTALL_DIR/Dockerfile"
curl -fsSL "$REPO/.dockerignore" -o "$INSTALL_DIR/.dockerignore"
curl -fsSL "$REPO/scripts/init-docker.sh" -o "$INSTALL_DIR/scripts/init-docker.sh"
curl -fsSL "$REPO/scripts/pilot-docker.sh" -o "$INSTALL_DIR/scripts/pilot-docker.sh"
chmod +x "$INSTALL_DIR/pilot.sh" "$INSTALL_DIR/scripts/"*.sh

echo "done."
echo ""
echo "  ./$INSTALL_DIR/pilot.sh --help"
