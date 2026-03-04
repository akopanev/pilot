# Protocol: Fix

Task: `{{var:PILOT_TASK_ID}}`

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:stuck>description</signal:stuck>` — contradictions in notes, cannot fix
- `<signal:failed>reason</signal:failed>` — fatal only
- No signal = advance to verify

## Steps

1. `tk show {{var:PILOT_TASK_ID}}` — read ALL notes. Find the FAIL and VERIFY FAIL reasons.
2. `<signal:update>fix: {{var:PILOT_TASK_ID}}</signal:update>`
3. `git checkout {{var:PILOT_WORKING_BRANCH}}`
4. **Detect contradictions**: Read notes chronologically. If note A says "revert X" and
   note B says "X is needed for build" — that's a Catch-22. Emit `<signal:stuck>` with
   description. Do not attempt to fix.
5. **Fix**: Address every reported issue. Surgical — fix what was reported, nothing else.
   Run typecheck after fixing to catch regressions.
6. `git add . && git commit -m "{{var:PILOT_TASK_ID}}: fix review issues"`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Fix what was reported | Don't argue with the reviewer. Don't add improvements. Fix the listed issues |
| Stay surgical | Every change must address a reported issue. Don't refactor or clean up unrelated code |
| Git | No push. No pull. No base branch edits |
| Fixable ≠ fatal | Typecheck/test failures are fixable. Never emit `failed` for these |
