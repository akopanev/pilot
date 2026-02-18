#!/usr/bin/env python3
"""pilot-docker.py — run pilot.sh in Docker with credential forwarding.

Handles macOS Keychain extraction so subscription-based Claude Code auth
works inside the container.

Usage:
    pilot-docker.py opus PROMPT.md --max-rounds 10
    pilot-docker.py --build opus PROMPT.md        # force rebuild image

Run from your project directory — mounts $(pwd) as /workspace.
"""

import hashlib
import os
import platform
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_IMAGE = "pilot:latest"
SCRIPT_DIR = Path(os.path.realpath(__file__)).parent
PROJECT_ROOT = SCRIPT_DIR.parent


# --- image ---

def ensure_image(image: str, build: bool) -> int:
    if not build:
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True, check=False,
        )
        if result.returncode == 0:
            return 0
        print(f"image '{image}' not found, building...", file=sys.stderr)

    print(f"building image '{image}' from {PROJECT_ROOT}...", file=sys.stderr)
    cmd = ["docker", "build",
           "--build-arg", f"USER_UID={os.getuid()}",
           "-t", image]
    if build:
        cmd.append("--no-cache")
    cmd.append(str(PROJECT_ROOT))
    rc = subprocess.run(cmd, check=False).returncode
    if rc != 0:
        print("docker build failed", file=sys.stderr)
    return rc


# --- credential extraction ---

def keychain_service_name(claude_home: Path) -> str:
    resolved = claude_home.expanduser().resolve()
    default = Path.home() / ".claude"
    if resolved == default or resolved == default.resolve():
        return "Claude Code-credentials"
    digest = hashlib.sha256(str(resolved).encode()).hexdigest()[:8]
    return f"Claude Code-credentials-{digest}"


def extract_macos_credentials(claude_home: Path):
    if platform.system() != "Darwin":
        return None
    if (claude_home / ".credentials.json").exists():
        return None

    service = keychain_service_name(claude_home)

    def _find():
        try:
            r = subprocess.run(
                ["security", "find-generic-password", "-s", service, "-w"],
                capture_output=True, text=True, check=False,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except OSError:
            pass
        return None

    creds = _find()
    if not creds:
        print("unlocking macOS Keychain for Claude credentials...", file=sys.stderr)
        subprocess.run(["security", "unlock-keychain"], capture_output=True, check=False)
        creds = _find()

    if not creds:
        return None

    fd, tmp_path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w") as f:
            f.write(creds + "\n")
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return None
    return Path(tmp_path)


# --- volumes ---

def build_volumes(creds_temp, claude_home):
    home = Path.home()
    pwd_env = os.environ.get("PWD")
    cwd = Path(pwd_env) if pwd_env else Path(os.getcwd())
    vols = []

    def add(src, dst, ro=False):
        suffix = ":ro" if ro else ""
        vols.extend(["-v", f"{src}:{dst}{suffix}"])

    # claude config (read-only — init-docker.sh copies what's needed)
    if claude_home.is_dir():
        add(claude_home.resolve(), "/mnt/claude", ro=True)

    # workspace (read-write)
    add(cwd, "/workspace")

    # macOS keychain credentials
    if creds_temp:
        add(creds_temp, "/mnt/claude-credentials.json", ro=True)

    # codex config (read-only)
    codex_dir = home / ".codex"
    if codex_dir.is_dir():
        add(codex_dir.resolve(), "/mnt/codex", ro=True)

    # .gitconfig
    gitconfig = home / ".gitconfig"
    if gitconfig.exists():
        add(gitconfig.resolve(), "/home/pilot/.gitconfig", ro=True)

    return vols


# --- run ---

def run_docker(image, volumes, args):
    cmd = ["docker", "run", "-t"]
    if sys.stdin.isatty():
        cmd.append("-i")
    cmd.append("--rm")

    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        val = os.environ.get(key)
        if val:
            cmd.extend(["-e", f"{key}={val}"])

    cmd.extend(volumes)
    cmd.extend(["-w", "/workspace"])
    cmd.extend([image, "pilot"])
    cmd.extend(args)

    proc = subprocess.Popen(cmd)
    try:
        proc.wait()
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
        proc.wait()
    return proc.returncode


# --- main ---

def main():
    image = os.environ.get("PILOT_IMAGE", DEFAULT_IMAGE)
    args = sys.argv[1:]

    build = "--build" in args
    if build:
        args = [a for a in args if a != "--build"]

    rc = ensure_image(image, build)
    if rc != 0:
        return rc

    claude_config = os.environ.get("CLAUDE_CONFIG_DIR")
    claude_home = Path(claude_config).expanduser().resolve() if claude_config else Path.home() / ".claude"

    creds_temp = extract_macos_credentials(claude_home)
    if creds_temp:
        print("extracted Claude credentials from macOS Keychain", file=sys.stderr)

    def cleanup():
        if creds_temp:
            try:
                creds_temp.unlink(missing_ok=True)
            except OSError:
                pass

    def term_handler(signum, frame):
        cleanup()
        sys.exit(128 + signum)

    signal.signal(signal.SIGTERM, term_handler)

    try:
        volumes = build_volumes(creds_temp, claude_home)
        return run_docker(image, volumes, args)
    finally:
        cleanup()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
