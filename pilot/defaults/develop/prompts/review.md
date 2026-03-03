# Protocol: Review

Task: `{{var:PILOT_TASK_ID}}`

## Signals
- `<signal:update>message</signal:update>` — progress milestone
- `<signal:approved>summary</signal:approved>` — pass review, advance to merge
- `<signal:rejected>issues</signal:rejected>` — fail review, send to fix
- `<signal:failed>reason</signal:failed>` — stop pipeline
- No signal = retry review

## Execution

Strictly sequential. No skipping.

1. **Read task**: `tk show {{var:PILOT_TASK_ID}}`.
2. **Emit**: `<signal:update>review: {{var:PILOT_TASK_ID}}</signal:update>`.
3. **Read notes**: `tk show {{var:PILOT_TASK_ID}}` — check existing notes.
4. **Checkout**: `git checkout {{var:PILOT_WORKING_BRANCH}}`.
5. **Diff**: `git diff {{var:PILOT_DEFAULT_BRANCH}}...HEAD`. No changes? PASS.
6. **Read code**: Open and read every changed file. Understand the full context — not just the diff.
7. **Verify**:
   - Emit `<signal:update>verifying</signal:update>`.
   - **Build**: Run build command. Fail? FAIL.
   - **Lint**: Run linter. Fail? FAIL.
   - **Tests**: Run tests. Fail? FAIL.
   - **Manual check**:
     - Correct? Changes match task requirements.
     - Complete? All requirements addressed.
     - Clean? No dead code, no TODOs.
     - Safe? No secrets, no vulnerabilities.
     - Scoped? No unrelated files changed.

## Rules
- **Build > scope.** If a file change is needed for build/typecheck/lint to pass, it is in-scope. Never reject a change that fixes a build error as "out of scope" — that creates an impossible loop.
- **Consistent feedback.** Read existing notes before writing new ones. Never contradict a previous review. If a prior review said "revert file X" but reverting breaks the build, the correct action is PASS (the fix agent resolved the conflict), not another rejection.
- **Actionable fixes only.** Every FAIL note must have a concrete FIX that the fix agent can apply without creating new failures. If you cannot describe a fix that passes all checks, the issue is not actionable — skip it.

## Result: PASS

1. `tk add-note {{var:PILOT_TASK_ID}} "PASS: <summary>"`.
2. `git add .tickets/ && git commit -m "{{var:PILOT_TASK_ID}}: review pass" --quiet`.
3. Emit `<signal:approved>summary</signal:approved>`. **STOP.**

## Result: FAIL

1. **One pass.** Find ALL issues at once. No incremental reviews.
2. `tk add-note {{var:PILOT_TASK_ID}} "FAIL:\n- <file:line> <issue>\nFIX: <concrete steps>"`.
3. `git add .tickets/ && git commit -m "{{var:PILOT_TASK_ID}}: review fail" --quiet`.
4. Emit `<signal:rejected>issues found</signal:rejected>`. **STOP.**
