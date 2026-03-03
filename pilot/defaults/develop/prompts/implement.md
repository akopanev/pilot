# Protocol: Implement

Task: `{{var:PILOT_TASK_ID}}`

## Signals
- `<signal:update>message</signal:update>` — progress milestone
- `<signal:failed>reason</signal:failed>` — **fatal only** (missing tool, wrong branch, unreachable repo). Stops the entire pipeline
- No signal = advance to review

## Execution

Strictly sequential. No skipping.

1. **Read task**: `tk show {{var:PILOT_TASK_ID}}`.
2. **Emit**: `<signal:update>implement: {{var:PILOT_TASK_ID}}</signal:update>`.
3. **Branch**: Confirm on `{{var:PILOT_WORKING_BRANCH}}`. If not: `git checkout {{var:PILOT_WORKING_BRANCH}}`.
   - Branch has commits? Read `git diff` / `git log`. Understand existing work.
4. **Context**:
   - Emit `<signal:update>reading source</signal:update>`.
   - Read relevant source code. **MUST** understand before changing.
   - Check imports, types, patterns in surrounding code.
5. **Implement**:
   - Emit `<signal:update>implementing {{var:PILOT_TASK_ID}}</signal:update>`.
   - Strict scope. Only files related to the task.
   - Test first. Handle errors.
6. **Verify**:
   - Emit `<signal:update>verifying {{var:PILOT_TASK_ID}}</signal:update>`.
   - Build. Lint. Tests. Fix regressions.
7. **Self-review**:
   - Emit `<signal:update>self-review {{var:PILOT_TASK_ID}}</signal:update>`.
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
| Never emit `failed` for fixable errors | Typecheck, lint, test failures are **fixable** — read the error, fix the code, re-run. Only emit `failed` for truly fatal problems (missing tools, can't checkout branch, environment broken) |
| Keep going | If verify fails, go back to step 5 and fix. Do not give up. Do not emit `failed` |
