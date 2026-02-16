"""Tests for XML signal parsing."""

from pilot.signals import Signal, parse_signals


def test_approve_signal():
    signals = parse_signals("some text <pilot:approve/> more text")
    assert len(signals) == 1
    assert signals[0].type == "approve"


def test_approve_with_whitespace():
    signals = parse_signals("<pilot:approve />")
    assert len(signals) == 1
    assert signals[0].type == "approve"


def test_reject_signal():
    signals = parse_signals("<pilot:reject>Missing error handling in auth module</pilot:reject>")
    assert len(signals) == 1
    assert signals[0].type == "reject"
    assert signals[0].payload == "Missing error handling in auth module"


def test_reject_multiline():
    output = """<pilot:reject>
Line 1 issue
Line 2 issue
</pilot:reject>"""
    signals = parse_signals(output)
    assert len(signals) == 1
    assert signals[0].type == "reject"
    assert "Line 1 issue" in signals[0].payload
    assert "Line 2 issue" in signals[0].payload


def test_blocked_signal():
    signals = parse_signals("<pilot:blocked>Cannot find database config</pilot:blocked>")
    assert len(signals) == 1
    assert signals[0].type == "blocked"
    assert signals[0].payload == "Cannot find database config"


def test_question_signal():
    signals = parse_signals('<pilot:question>{"question": "Which DB?"}</pilot:question>')
    assert len(signals) == 1
    assert signals[0].type == "question"
    assert '"question"' in signals[0].payload


def test_update_signal():
    signals = parse_signals('<pilot:update path=".pilot/plan.md">new plan content</pilot:update>')
    assert len(signals) == 1
    assert signals[0].type == "update"
    assert signals[0].path == ".pilot/plan.md"
    assert signals[0].payload == "new plan content"


def test_draft_signal():
    signals = parse_signals('<pilot:draft label="prd">Draft PRD here</pilot:draft>')
    assert len(signals) == 1
    assert signals[0].type == "draft"
    assert signals[0].label == "prd"
    assert signals[0].payload == "Draft PRD here"


def test_no_signals():
    signals = parse_signals("regular output with no signals")
    assert signals == []


def test_multiple_signals():
    output = """
<pilot:update path=".pilot/state.md">state</pilot:update>
Some text in between.
<pilot:approve/>
"""
    signals = parse_signals(output)
    assert len(signals) == 2
    types = {s.type for s in signals}
    assert types == {"approve", "update"}


# ── Completed signal ──────────────────────────────────────

def test_completed_self_closing():
    signals = parse_signals("done <pilot:completed/> ok")
    assert len(signals) == 1
    assert signals[0].type == "completed"
    assert signals[0].payload is None


def test_completed_with_whitespace():
    signals = parse_signals("<pilot:completed />")
    assert len(signals) == 1
    assert signals[0].type == "completed"
    assert signals[0].payload is None


def test_completed_with_payload():
    signals = parse_signals("<pilot:completed>all tests passing</pilot:completed>")
    assert len(signals) == 1
    assert signals[0].type == "completed"
    assert signals[0].payload == "all tests passing"


def test_completed_multiline_payload():
    output = """<pilot:completed>
Step 1 done
Step 2 done
</pilot:completed>"""
    signals = parse_signals(output)
    assert len(signals) == 1
    assert signals[0].type == "completed"
    assert "Step 1 done" in signals[0].payload
    assert "Step 2 done" in signals[0].payload


# ── Skip signal ───────────────────────────────────────────

def test_skip_self_closing():
    signals = parse_signals("<pilot:skip/>")
    assert len(signals) == 1
    assert signals[0].type == "skip"
    assert signals[0].payload is None


def test_skip_with_reason():
    signals = parse_signals("<pilot:skip>not applicable to this task</pilot:skip>")
    assert len(signals) == 1
    assert signals[0].type == "skip"
    assert signals[0].payload == "not applicable to this task"


def test_skip_with_whitespace():
    signals = parse_signals("<pilot:skip />")
    assert len(signals) == 1
    assert signals[0].type == "skip"
    assert signals[0].payload is None


# ── Emit signal ───────────────────────────────────────────

def test_emit_basic():
    signals = parse_signals('<pilot:emit key="api_url">https://api.example.com</pilot:emit>')
    assert len(signals) == 1
    assert signals[0].type == "emit"
    assert signals[0].key == "api_url"
    assert signals[0].payload == "https://api.example.com"


def test_emit_multiline_value():
    output = '''<pilot:emit key="config">line1
line2
line3</pilot:emit>'''
    signals = parse_signals(output)
    assert len(signals) == 1
    assert signals[0].type == "emit"
    assert signals[0].key == "config"
    assert "line1" in signals[0].payload
    assert "line3" in signals[0].payload


def test_emit_multiple_keys():
    output = """
<pilot:emit key="url">https://example.com</pilot:emit>
<pilot:emit key="token">abc123</pilot:emit>
"""
    signals = parse_signals(output)
    emits = [s for s in signals if s.type == "emit"]
    assert len(emits) == 2
    keys = {s.key for s in emits}
    assert keys == {"url", "token"}


def test_emit_duplicate_keys():
    output = """
<pilot:emit key="val">first</pilot:emit>
<pilot:emit key="val">second</pilot:emit>
"""
    signals = parse_signals(output)
    emits = [s for s in signals if s.type == "emit"]
    assert len(emits) == 2
    assert emits[0].payload == "first"
    assert emits[1].payload == "second"


# ── Mixed signals ─────────────────────────────────────────

def test_completed_and_approve():
    output = "<pilot:completed>done</pilot:completed> <pilot:approve/>"
    signals = parse_signals(output)
    types = {s.type for s in signals}
    assert "completed" in types
    assert "approve" in types


def test_skip_and_emit():
    output = '<pilot:emit key="reason">not needed</pilot:emit> <pilot:skip/>'
    signals = parse_signals(output)
    types = {s.type for s in signals}
    assert "skip" in types
    assert "emit" in types
