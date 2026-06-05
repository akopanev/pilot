"""Codex executor — streaming JSONL events via --json mode."""

from __future__ import annotations

import json
import subprocess
import threading

from pilot.executors.result import ExecutorResult, kill_process_group, start_cancel_watchdog
from pilot.signals import SignalScanner


def _extract_text(event: dict) -> str | None:
    """Extract agent message text from a codex JSONL event.

    Returns the text for agent_message item.completed events,
    None for everything else.
    """
    if event.get("type") != "item.completed":
        return None
    item_type = event.get("item", {}).get("type")
    if item_type != "agent_message":
        return None
    return event.get("item", {}).get("text", "")


def _extract_progress(event: dict) -> str | None:
    """Extract a human-readable progress line from non-message events."""
    etype = event.get("type", "")
    item = event.get("item", {})
    itype = item.get("type", "")

    if etype == "item.completed" and itype == "command_execution":
        cmd = item.get("command", "")
        status = item.get("status", "")
        code = item.get("exit_code")
        suffix = f" (exit {code})" if code is not None else ""
        return f"$ {cmd} [{status}{suffix}]"

    if etype == "item.completed" and itype == "file_change":
        changes = item.get("changes", [])
        parts = [f"{c.get('kind', '?')} {c.get('path', '?')}" for c in changes]
        return "files: " + ", ".join(parts) if parts else None

    if etype == "item.started" and itype == "command_execution":
        cmd = item.get("command", "")
        return f"$ {cmd}"

    return None


class CodexExecutor:
    """Runs codex CLI with --json mode for structured JSONL output.

    All events arrive on stdout as JSONL. Agent messages contain the
    model's response text (including signals). stderr is only used
    for codex internal logging/errors.
    """

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None,
            cancel=None,
            args: list[str] | None = None) -> ExecutorResult:
        # None → codex наследует model из ~/.codex/config.toml (обычно gpt-5.5).
        # НЕ навязываем "o3": она недоступна для ChatGPT-subscription аккаунта → сервер 400 → exit 1.
        effective_model = model

        # Полный yolo одинаково на host и в docker. Раньше host шёл через --full-auto,
        # а это (а) deprecated в codex >=0.136 ("use --sandbox workspace-write instead"),
        # (б) = --sandbox workspace-write, т.е. codex на host сидел В ПЕСОЧНИЦЕ (нет сети,
        # нет записи вне cwd) — расходясь с docker-веткой (--dangerously-bypass...), где
        # codex развязан. Отсюда "работает только в докере". Единый bypass: без песочницы,
        # без аппрувов — как claude --dangerously-skip-permissions в этом же пуле.
        cmd = ["codex", "exec", "--json",
               "--dangerously-bypass-approvals-and-sandbox",
               "--skip-git-repo-check"]
        if effective_model:
            cmd += ["-c", f'model="{effective_model}"']
        cmd += [
            "-c", "model_reasoning_effort=xhigh",
            "-c", "stream_idle_timeout_ms=3600000",
        ]
        # Raw per-runner args last → автор может переопределить дефолты выше
        # (codex слоит -c по принципу "последний выигрывает").
        if args:
            cmd += args

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        # Send prompt via stdin (avoids shell escaping issues with large prompts)
        if proc.stdin:
            proc.stdin.write(prompt)
            proc.stdin.close()

        start_cancel_watchdog(cancel, proc)

        # Capture stderr tail for error reporting
        stderr_result: dict = {"last_lines": [], "error": None}
        stderr_thread = threading.Thread(
            target=self._capture_stderr,
            args=(proc.stderr, stderr_result),
            daemon=True,
        )
        stderr_thread.start()

        output_parts: list[str] = []
        all_signals = []
        stdout_error = None
        scanner = SignalScanner(known_signals)

        try:
            for line in proc.stdout:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Agent message — extract text, scan for signals
                text = _extract_text(event)
                if text:
                    output_parts.append(text)
                    if on_output:
                        on_output(text)
                    for sig in scanner.feed(text):
                        all_signals.append(sig)
                        if on_signal:
                            on_signal(sig)
                    continue

                # Error / turn.failed — поймать РЕАЛЬНУЮ причину (иначе теряется → "0 вывода, exit 1")
                etype = event.get("type", "")
                if etype in ("error", "turn.failed") or event.get("error"):
                    detail = event.get("message") or event.get("error") or event
                    if isinstance(detail, (dict, list)):
                        detail = json.dumps(detail, ensure_ascii=False)
                    stdout_error = f"codex {etype or 'error'}: {detail}"
                    if on_output:
                        on_output(stdout_error)
                    continue

                # Other events — show progress
                progress = _extract_progress(event)
                if progress and on_output:
                    on_output(progress)

        except KeyboardInterrupt:
            raise
        except Exception as e:
            stdout_error = str(e)
        finally:
            if proc.poll() is None:
                kill_process_group(proc)
            stderr_thread.join(timeout=5)
            proc.wait()

        # Flush remaining buffered signals
        for sig in scanner.flush():
            all_signals.append(sig)
            if on_signal:
                on_signal(sig)

        stdout_content = "".join(output_parts)

        error = None
        if stderr_result["error"]:
            error = stderr_result["error"]
        elif stdout_error:
            error = stdout_error
        elif proc.returncode != 0:
            tail = "\n".join(stderr_result["last_lines"])
            error = f"codex exited with code {proc.returncode}"
            if tail:
                error += f"\nstderr: {tail}"

        return ExecutorResult(
            output=stdout_content,
            exit_code=proc.returncode,
            error=error,
            signals=all_signals,
        )

    @staticmethod
    def _capture_stderr(stream, result: dict) -> None:
        """Capture stderr tail for error reporting."""
        max_tail = 10
        tail: list[str] = []

        try:
            for line in stream:
                stripped = line.strip()
                if not stripped:
                    continue
                stored = stripped[:256] + "..." if len(stripped) > 256 else stripped
                tail.append(stored)
                if len(tail) > max_tail:
                    tail.pop(0)
        except Exception as e:
            result["error"] = str(e)

        result["last_lines"] = tail
