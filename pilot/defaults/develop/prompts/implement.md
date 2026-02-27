# Protocol: Implement

Task: `{{var:PILOT_TASK_ID}}`

## Signals
- `<signal:update>message</signal:update>` — progress milestone
- `<signal:failed>reason</signal:failed>` — stop pipeline
- No signal = advance to review

## Execution

Strictly sequential. No skipping.

1. **Read task**: `tk show {{var:PILOT_TASK_ID}}`.
2. **Emit**: `<signal:update>implement: {{var:PILOT_TASK_ID}}</signal:update>`.
3. **Branch**: Confirm on `feat/{{var:PILOT_TASK_ID}}`. If not: `git checkout feat/{{var:PILOT_TASK_ID}}`.
   - Branch has commits? Read `git diff` / `git log`. Understand existing work.
4. **Context**:
   - Emit `<signal:update>reading source</signal:update>`.
   - Read relevant source code. **MUST** understand before changing.
   - Check imports, types, patterns in surrounding code.
5. **Implement**:
   - Emit `<signal:update>implementing</signal:update>`.
   - Strict scope. Only files related to the task.
   - Test first. Handle errors.
6. **Verify**:
   - Emit `<signal:update>verifying</signal:update>`.
   - Build. Lint. Tests. Fix regressions.
7. **Self-review**:
   - Emit `<signal:update>self-review</signal:update>`.
   - Correctness — does it match the task?
   - Completeness — all requirements covered?
   - Patterns — follows existing codebase conventions?
   - Scope — no unrelated changes?
   - Security — no secrets, no vulnerabilities?
8. **Commit**: `git add . && git commit -m "{{var:PILOT_TASK_ID}}: <summary>"`.

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Scope | Touch unrelated file = FAIL |
| Clean | Dead code / TODOs = FAIL |
| Git | No push. No pull. No base branch edits |
| Deps | Only add if task requires it |
