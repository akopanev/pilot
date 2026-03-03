# Protocol: Fix

Task: `{{var:PILOT_TASK_ID}}`

## Signals
- `<signal:update>message</signal:update>` — progress milestone
- `<signal:stuck>description</signal:stuck>` — contradictions in review notes, cannot fix
- `<signal:failed>reason</signal:failed>` — stop pipeline
- No signal = advance to review

## Execution

Strictly sequential. No skipping.

1. **Read task and notes**: `tk show {{var:PILOT_TASK_ID}}`. Find the FAIL reasons.
2. **Emit**: `<signal:update>fix: {{var:PILOT_TASK_ID}}</signal:update>`.
3. **Checkout**: `git checkout {{var:PILOT_WORKING_BRANCH}}`.
4. **Fix**:
   - Emit `<signal:update>fixing</signal:update>`.
   - **Surgical.** Fix ONLY the reported issues.
   - Verify each fix locally.
5. **Verify**:
   - Emit `<signal:update>verifying</signal:update>`.
   - Build. Lint. Tests. Fix regressions.
6. **Commit**: `git add . && git commit -m "{{var:PILOT_TASK_ID}}: fix review issues"`.

## Rules

| Rule | Constraint |
|:-----|:-----------|
| No arguments | Fix what was reported |
| No scope creep | Touch unrelated file = FAIL |
| Git | No push. No pull. No base branch edits |
| Detect contradictions | Read ALL prior notes. If note A says "revert X" and note B says "X is needed for build", that's a Catch-22. Emit `<signal:stuck>` with description |
