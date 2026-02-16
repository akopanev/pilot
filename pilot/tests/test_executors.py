"""Tests for executors."""

import json

from pilot.executors.claude import (
    ClaudeExecutor,
    check_error_patterns,
    extract_text,
)
from pilot.executors.codex import CodexExecutor, strip_bold
from pilot.executors.custom import CustomExecutor
from pilot.executors.generic import GenericExecutor
from pilot.executors.shell import ShellExecutor
from pilot.executors import ExecutorPool


# ── Shell executor ──────────────────────────────────────────

def test_shell_executor_success():
    executor = ShellExecutor()
    result = executor.run("echo hello world")
    assert result.exit_code == 0
    assert "hello world" in result.output
    assert result.error is None


def test_shell_executor_failure():
    executor = ShellExecutor()
    result = executor.run("exit 42")
    assert result.exit_code == 42
    assert result.error is not None


# ── Error pattern detection ─────────────────────────────────

def test_check_error_patterns_match():
    output = "Error: Rate limit exceeded, please try again"
    patterns = ["rate limit"]
    assert check_error_patterns(output, patterns) == "rate limit"


def test_check_error_patterns_no_match():
    output = "Everything is fine"
    patterns = ["rate limit", "quota exceeded"]
    assert check_error_patterns(output, patterns) is None


def test_check_error_patterns_case_insensitive():
    output = "RATE LIMIT EXCEEDED"
    patterns = ["rate limit"]
    assert check_error_patterns(output, patterns) == "rate limit"


def test_check_error_patterns_empty():
    assert check_error_patterns("any output", []) is None
    assert check_error_patterns("any output", ["  "]) is None


# ── Claude JSON stream event extraction ─────────────────────

def test_extract_text_assistant():
    event = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "Hello "},
                {"type": "text", "text": "world"},
            ]
        },
    }
    assert extract_text(event) == "Hello world"


def test_extract_text_assistant_no_text():
    event = {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "text": ""}]},
    }
    assert extract_text(event) == ""


def test_extract_text_content_block_delta():
    event = {
        "type": "content_block_delta",
        "delta": {"type": "text_delta", "text": "chunk"},
    }
    assert extract_text(event) == "chunk"


def test_extract_text_content_block_delta_non_text():
    event = {
        "type": "content_block_delta",
        "delta": {"type": "input_json_delta", "text": "{}"},
    }
    assert extract_text(event) == ""


def test_extract_text_message_stop():
    event = {
        "type": "message_stop",
        "message": {"content": [{"type": "text", "text": "final"}]},
    }
    assert extract_text(event) == "final"


def test_extract_text_result_string():
    # String result = session summary, should be skipped
    event = {"type": "result", "result": "session summary text"}
    assert extract_text(event) == ""


def test_extract_text_result_object():
    event = {"type": "result", "result": {"output": "the answer"}}
    assert extract_text(event) == "the answer"


def test_extract_text_result_none():
    event = {"type": "result", "result": None}
    assert extract_text(event) == ""


def test_extract_text_unknown_type():
    event = {"type": "content_block_start"}
    assert extract_text(event) == ""


# ── Claude command building ─────────────────────────────────

def test_claude_build_command():
    executor = ClaudeExecutor()
    cmd = executor._build_command("do something", "claude-sonnet-4")
    assert cmd[0] == "claude"
    assert "--dangerously-skip-permissions" in cmd
    assert "--output-format" in cmd
    assert "stream-json" in cmd
    assert "--model" in cmd
    assert "claude-sonnet-4" in cmd
    assert cmd[-2:] == ["-p", "do something"]


def test_claude_build_command_no_model():
    executor = ClaudeExecutor()
    cmd = executor._build_command("prompt", None)
    assert "--model" not in cmd
    assert cmd[-2:] == ["-p", "prompt"]


# ── Codex command building ──────────────────────────────────

def test_codex_build_command():
    executor = CodexExecutor()
    cmd = executor._build_command("do something", None)
    assert cmd[0] == "codex"
    assert "exec" in cmd
    assert "--sandbox" in cmd
    assert "full-auto" in cmd
    assert any("gpt-5.3-codex" in arg for arg in cmd)
    assert any("model_reasoning_effort=xhigh" in arg for arg in cmd)
    assert any("stream_idle_timeout_ms=3600000" in arg for arg in cmd)
    assert "do something" in cmd


def test_codex_build_command_with_model():
    executor = CodexExecutor()
    cmd = executor._build_command("prompt", "gpt-4o")
    assert any("gpt-4o" in arg for arg in cmd)


# ── Codex strip_bold ────────────────────────────────────────

def test_strip_bold_simple():
    assert strip_bold("**hello** world") == "hello world"


def test_strip_bold_multiple():
    assert strip_bold("**a** and **b**") == "a and b"


def test_strip_bold_no_bold():
    assert strip_bold("no bold here") == "no bold here"


def test_strip_bold_unclosed():
    assert strip_bold("**unclosed marker") == "**unclosed marker"


# ── Generic executor command building ───────────────────────

def test_generic_build_command():
    executor = GenericExecutor("opencode")
    cmd = executor._build_command("prompt text", "gemini-2.5-pro")
    assert cmd[0] == "opencode"
    assert "--model" in cmd
    assert "gemini-2.5-pro" in cmd
    assert cmd[-2:] == ["-p", "prompt text"]


def test_generic_build_command_no_model():
    executor = GenericExecutor("aider")
    cmd = executor._build_command("prompt", None)
    assert cmd == ["aider", "-p", "prompt"]


# ── Executor pool routing ──────────────────────────────────

def test_pool_routes_claude():
    pool = ExecutorPool()
    executor = pool.get("claude-code")
    assert isinstance(executor, ClaudeExecutor)


def test_pool_routes_codex():
    pool = ExecutorPool()
    executor = pool.get("codex")
    assert isinstance(executor, CodexExecutor)


def test_pool_routes_shell():
    pool = ExecutorPool()
    executor = pool.get("shell")
    assert isinstance(executor, ShellExecutor)


def test_pool_routes_generic():
    pool = ExecutorPool()
    executor = pool.get("opencode")
    assert isinstance(executor, GenericExecutor)
    assert executor.tool == "opencode"


def test_pool_caches_executors():
    pool = ExecutorPool()
    a = pool.get("claude-code")
    b = pool.get("claude-code")
    assert a is b


def test_pool_does_not_cache_shell():
    pool = ExecutorPool()
    a = pool.get("shell")
    b = pool.get("shell")
    assert a is not b  # ShellExecutor is stateless, new each time


# ── Change 6: Custom executor routing ──────────────────────

def test_pool_routes_custom_with_script():
    pool = ExecutorPool()
    executor = pool.get("custom", script="./scripts/review.sh")
    assert isinstance(executor, CustomExecutor)
    assert executor.script == "./scripts/review.sh"


def test_pool_caches_custom_by_script():
    pool = ExecutorPool()
    a = pool.get("custom", script="./scripts/a.sh")
    b = pool.get("custom", script="./scripts/a.sh")
    c = pool.get("custom", script="./scripts/b.sh")
    assert a is b  # same script = same instance
    assert a is not c  # different script = different instance


# ── Change 8: Signals list in ExecutorResult ────────────────

def test_shell_executor_has_signals_list():
    executor = ShellExecutor()
    result = executor.run("echo hello")
    assert isinstance(result.signals, list)
    assert result.signals == []


def test_pool_custom_without_script_raises():
    import pytest
    pool = ExecutorPool()
    with pytest.raises(ValueError, match="requires a 'script' path"):
        pool.get("custom")


# ── Args in command building ─────────────────────────────────

def test_claude_build_command_with_args():
    executor = ClaudeExecutor()
    cmd = executor._build_command("prompt", "claude-sonnet-4", args=["--flag", "value"])
    # args should appear before -p prompt
    p_idx = cmd.index("-p")
    assert "--flag" in cmd
    assert cmd.index("--flag") < p_idx
    assert cmd[-2:] == ["-p", "prompt"]


def test_codex_build_command_with_args():
    executor = CodexExecutor()
    cmd = executor._build_command("prompt", None, args=["--sandbox", "read-only"])
    # args should appear before the positional prompt (last element)
    assert cmd[-1] == "prompt"
    assert "--sandbox" in cmd
    # There should be two --sandbox entries: the default full-auto and the args override
    sandbox_indices = [i for i, x in enumerate(cmd) if x == "--sandbox"]
    assert len(sandbox_indices) == 2


def test_generic_build_command_with_args():
    executor = GenericExecutor("opencode")
    cmd = executor._build_command("prompt", None, args=["--extra"])
    p_idx = cmd.index("-p")
    assert "--extra" in cmd
    assert cmd.index("--extra") < p_idx
    assert cmd[-2:] == ["-p", "prompt"]


def test_custom_execute_with_args():
    executor = CustomExecutor("./my-script.sh")
    # We can't run the script, but we can test that _execute builds the right command
    # by checking the Popen call. Instead, just verify the method signature accepts args.
    import inspect
    sig = inspect.signature(executor._execute)
    assert "args" in sig.parameters


def test_claude_build_command_with_empty_args():
    executor = ClaudeExecutor()
    cmd_no_args = executor._build_command("prompt", None, args=[])
    cmd_none_args = executor._build_command("prompt", None, args=None)
    assert cmd_no_args == cmd_none_args
