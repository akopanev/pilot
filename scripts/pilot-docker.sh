#!/usr/bin/env python3
"""pilot-docker.sh - run pilot in a docker container with credential forwarding.

Handles macOS Keychain extraction so subscription-based Claude Code auth
works inside the container. Modeled after ralphex's ralphex-dk.sh.

Usage:
    pilot-docker.sh [pilot-args]
    pilot-docker.sh run --dry-run
    pilot-docker.sh run --config my-pipeline.yaml
    pilot-docker.sh --build run          # force rebuild image

Run from any directory — mounts $(pwd) as /workspace.
Image is auto-built on first use from the pilot source directory.
"""

import hashlib
import os
import platform
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional

DEFAULT_IMAGE = "pilot:latest"
SCRIPT_DIR = Path(os.path.realpath(__file__)).parent
# pilot source: either scripts/../ (dev) or ~/.pilot/ (installed)
_dev_src = SCRIPT_DIR.parent
_installed_src = Path.home() / ".pilot"
PILOT_SRC = _dev_src if (_dev_src / "Dockerfile").exists() else _installed_src


def ensure_image(image: str, build: bool) -> int:
    """Build the Docker image if --build requested or image doesn't exist."""
    if not build:
        # check if image exists
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True, check=False,
        )
        if result.returncode == 0:
            return 0
        print(f"image '{image}' not found, building from {PILOT_SRC}...", file=sys.stderr)

    print(f"building image '{image}' from {PILOT_SRC}...", file=sys.stderr)
    uid_arg = str(os.getuid())
    rc = subprocess.run(
        ["docker", "build", "--build-arg", f"USER_UID={uid_arg}", "-t", image, str(PILOT_SRC)],
        check=False,
    ).returncode
    if rc != 0:
        print("docker build failed", file=sys.stderr)
    return rc


# --- credential extraction ---

def keychain_service_name(claude_home: Path) -> str:
    """Derive macOS Keychain service name from claude config directory.

    Default ~/.claude uses "Claude Code-credentials" (no suffix).
    Custom paths use "Claude Code-credentials-{sha256(absolute_path)[:8]}".
    """
    resolved = claude_home.expanduser().resolve()
    default = Path.home() / ".claude"
    if resolved == default or resolved == default.resolve():
        return "Claude Code-credentials"
    digest = hashlib.sha256(str(resolved).encode()).hexdigest()[:8]
    return f"Claude Code-credentials-{digest}"


def _security_find_credentials(service_name: str) -> Optional[str]:
    """Try to read Claude Code credentials from macOS Keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service_name, "-w"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except OSError:
        pass
    return None


def extract_macos_credentials(claude_home: Path) -> Optional[Path]:
    """On macOS, extract claude credentials from Keychain if not already on disk."""
    if platform.system() != "Darwin":
        return None
    if (claude_home / ".credentials.json").exists():
        return None

    service = keychain_service_name(claude_home)

    # try to read credentials (works if keychain already unlocked)
    creds_json = _security_find_credentials(service)
    if not creds_json:
        # keychain locked - unlock and retry
        print("unlocking macOS Keychain to extract Claude credentials (enter login password)...",
              file=sys.stderr)
        subprocess.run(["security", "unlock-keychain"], capture_output=True, check=False)
        creds_json = _security_find_credentials(service)

    if not creds_json:
        return None

    fd, tmp_path = tempfile.mkstemp()
    fd_closed = False
    try:
        with os.fdopen(fd, "w") as f:
            fd_closed = True
            f.write(creds_json + "\n")
    except OSError:
        if not fd_closed:
            os.close(fd)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return None
    return Path(tmp_path)


# --- symlink resolution ---

def symlink_target_dirs(src: Path, maxdepth: int = 2) -> list[Path]:
    """Collect unique parent directories of symlink targets inside a directory, limited to maxdepth."""
    if not src.is_dir():
        return []
    dirs: set[Path] = set()
    src_str = str(src)
    for root, dirnames, filenames in os.walk(src):
        depth = root[len(src_str):].count(os.sep)
        if depth >= maxdepth:
            dirnames.clear()
            continue
        if depth >= maxdepth - 1:
            entries = list(dirnames) + filenames
            dirnames.clear()
        else:
            entries = list(dirnames) + filenames
        root_path = Path(root)
        for name in entries:
            entry = root_path / name
            if entry.is_symlink():
                try:
                    target = entry.resolve()
                    dirs.add(target.parent)
                except (OSError, RuntimeError):
                    continue
    return sorted(dirs)


# --- volume building ---

def build_volumes(creds_temp: Optional[Path], claude_home: Optional[Path] = None) -> list[str]:
    """Build docker volume mount arguments."""
    home = Path.home()
    pwd_env = os.environ.get("PWD")
    cwd = Path(pwd_env) if pwd_env else Path(os.getcwd())
    if claude_home is None:
        claude_home = home / ".claude"
    vols: list[str] = []

    def add(src: Path, dst: str, ro: bool = False) -> None:
        suffix = ":ro" if ro else ""
        vols.extend(["-v", f"{src}:{dst}{suffix}"])

    def add_symlink_targets(src: Path) -> None:
        """Mount read-only symlink target directories that live under $HOME."""
        for target in symlink_target_dirs(src):
            if target.is_dir() and target.is_relative_to(home):
                add(target, str(target), ro=True)

    # 1. claude config -> /mnt/claude:ro + symlink targets
    if claude_home.is_dir():
        add(claude_home.resolve(), "/mnt/claude", ro=True)
        add_symlink_targets(claude_home)

    # 2. workspace
    add(cwd, "/workspace")

    # 3. macOS credentials temp file
    if creds_temp:
        add(creds_temp, "/mnt/claude-credentials.json", ro=True)

    # 4. codex config -> /mnt/codex:ro + symlink targets
    codex_dir = home / ".codex"
    if codex_dir.is_dir():
        add(codex_dir.resolve(), "/mnt/codex", ro=True)
        add_symlink_targets(codex_dir)

    # 5. .gitconfig -> /home/pilot/.gitconfig:ro (same as ralphex)
    gitconfig = home / ".gitconfig"
    if gitconfig.exists():
        add(gitconfig.resolve(), "/home/pilot/.gitconfig", ro=True)

    # 6. global gitignore -> same path in container:ro
    global_gitignore = _get_global_gitignore()
    if global_gitignore:
        add(global_gitignore.resolve(), str(global_gitignore), ro=True)

    return vols


def _get_global_gitignore() -> Optional[Path]:
    """Get global gitignore path if configured and exists."""
    try:
        result = subprocess.run(
            ["git", "config", "--global", "core.excludesFile"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            p = Path(result.stdout.strip()).expanduser()
            if p.exists():
                return p
    except OSError:
        pass
    return None


# --- cleanup ---

def schedule_cleanup(creds_temp: Optional[Path]) -> None:
    """Schedule credentials temp file deletion after a delay."""
    if not creds_temp:
        return

    def _remove() -> None:
        try:
            creds_temp.unlink(missing_ok=True)
        except OSError:
            pass

    t = threading.Timer(10.0, _remove)
    t.daemon = True
    t.start()


# --- docker execution ---

def run_docker(image: str, volumes: list[str], args: list[str]) -> int:
    """Build and execute docker run command."""
    cmd = ["docker", "run"]

    interactive = sys.stdin.isatty()
    if interactive:
        cmd.append("-it")
    cmd.append("--rm")

    cmd.extend(["-e", f"APP_UID={os.getuid()}"])

    # pass through API keys and pilot config if set
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PILOT_DEBUG", "PILOT_NO_COLOR"):
        val = os.environ.get(key)
        if val:
            cmd.extend(["-e", f"{key}={val}"])

    cmd.extend(volumes)
    cmd.extend(["-w", "/workspace"])
    cmd.extend([image, "pilot"])
    cmd.extend(args)

    # defer SIGTERM during Popen to prevent race condition
    _pending: list[tuple[int, object]] = []

    def _deferred_term(signum: int, frame: object) -> None:
        _pending.append((signum, frame))

    old_handler = signal.signal(signal.SIGTERM, _deferred_term)
    try:
        proc = subprocess.Popen(cmd)
        run_docker._active_proc = proc  # type: ignore[attr-defined]
    finally:
        signal.signal(signal.SIGTERM, old_handler)
    if _pending and callable(old_handler):
        old_handler(*_pending[0])

    try:
        proc.wait()
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
        proc.wait()
    finally:
        run_docker._active_proc = None  # type: ignore[attr-defined]
    return proc.returncode


# --- main ---

def main() -> int:
    image = os.environ.get("PILOT_IMAGE", DEFAULT_IMAGE)
    args = sys.argv[1:]

    # handle --build flag
    build = "--build" in args
    if build:
        args = [a for a in args if a != "--build"]

    # ensure image exists (auto-build if missing)
    rc = ensure_image(image, build)
    if rc != 0:
        return rc

    # resolve claude config directory
    claude_config_env = os.environ.get("CLAUDE_CONFIG_DIR", "")
    if claude_config_env:
        claude_home = Path(claude_config_env).expanduser().resolve()
    else:
        claude_home = Path.home() / ".claude"

    # extract macOS credentials from Keychain
    creds_temp = extract_macos_credentials(claude_home)
    if creds_temp:
        print("extracted Claude credentials from macOS Keychain", file=sys.stderr)

    def _cleanup_creds() -> None:
        if creds_temp:
            try:
                creds_temp.unlink(missing_ok=True)
            except OSError:
                pass

    # SIGTERM handler: terminate docker child and clean up
    def _term_handler(signum: int, frame: object) -> None:
        proc = getattr(run_docker, "_active_proc", None)
        if proc is not None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
        _cleanup_creds()
        sys.exit(128 + signum)

    signal.signal(signal.SIGTERM, _term_handler)

    try:
        volumes = build_volumes(creds_temp, claude_home)
        print(f"using image: {image}", file=sys.stderr)
        schedule_cleanup(creds_temp)
        return run_docker(image, volumes, args)
    finally:
        _cleanup_creds()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
