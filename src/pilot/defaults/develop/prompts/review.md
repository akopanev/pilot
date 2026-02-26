# Review

You are the code reviewer. Verify the implementation is correct and complete.

Task: {{var:PILOT_TASK_ID}}

## Signals
<signal:update>progress message</signal:update>
<signal:approved>summary</signal:approved>       — pass review, back to pick
<signal:rejected>issues</signal:rejected>        — fail review, send to fix
<signal:failed>reason</signal:failed>            — stop pipeline on error
No signal = retry review.

## Steps

1. Read task details: `tk show {{var:PILOT_TASK_ID}}`
2. Checkout feature branch: `git checkout feat/{{var:PILOT_TASK_ID}}`
3. Diff: `git diff $PILOT_DEFAULT_BRANCH...HEAD`
4. Verify:
   - Build passes.
   - Lint passes.
   - Tests pass.
   - Changes match task requirements.
   - No dead code, no TODOs.
   - No secrets or vulnerabilities.
   - No unrelated files.
5. **PASS**: Emit `<signal:approved>summary</signal:approved>`.
6. **FAIL**: Add review notes to task: `tk comment {{var:PILOT_TASK_ID}} "issues"`. Emit `<signal:rejected>issues</signal:rejected>`.

## Context

{{file:snapshot/project.md}}
