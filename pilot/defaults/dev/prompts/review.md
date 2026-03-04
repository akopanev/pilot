# Protocol: Review

Task: `{{var:PILOT_TASK_ID}}`

Automated checks (typecheck, lint, tests) have already been verified before
this stage. Your job is to review the code — not re-run the checks.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:approved>summary</signal:approved>` — ship it
- `<signal:rejected>issues</signal:rejected>` — send to fix
- `<signal:stuck>description</signal:stuck>` — loop detected, escalate
- `<signal:failed>reason</signal:failed>` — fatal only
- No signal = retry review

## Steps

1. `tk show {{var:PILOT_TASK_ID}}` — read task, acceptance criteria, and ALL prior notes.
2. `<signal:update>review: {{var:PILOT_TASK_ID}}</signal:update>`
3. `git checkout {{var:PILOT_WORKING_BRANCH}}`
4. `git diff {{var:PILOT_DEFAULT_BRANCH}}...HEAD` — read the diff.
5. Read every changed file in full. Not just the diff — the whole file.
6. **Judge**:
   - **Task match**: Does the code do what the ticket says? Check every
     acceptance criterion.
   - **Logic**: Will it work at runtime? Off-by-one, null refs, race conditions,
     edge cases — the bugs that tests don't catch.
   - **Regressions**: Did it break existing functionality? Removed code, broken
     imports, changed behavior of unrelated features.
   - **Scope**: Every changed file must be necessary for this task. Unrelated
     refactors, style changes, "improvements" = FAIL.

## PASS

1. `tk add-note {{var:PILOT_TASK_ID}} "PASS: <summary>"`
2. `git add .tickets/ && git commit -m "{{var:PILOT_TASK_ID}}: review pass" --quiet`
3. Emit `<signal:approved>summary</signal:approved>`. **STOP.**

## FAIL

1. Find ALL issues in one pass. No incremental reviews — don't make the fix
   agent play whack-a-mole.
2. `tk add-note {{var:PILOT_TASK_ID}} "FAIL:\n- <file:line> <issue>\nFIX: <concrete fix>"`
3. `git add .tickets/ && git commit -m "{{var:PILOT_TASK_ID}}: review fail" --quiet`
4. Emit `<signal:rejected>issues found</signal:rejected>`. **STOP.**

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Build > scope | If a change is needed for the build to pass, it's in-scope. Never reject a build-fixing change as "out of scope" |
| Every FAIL = concrete FIX | If you can't describe a fix that works without breaking something else, the issue isn't actionable — skip it |
| No nitpicking | Style, naming, comments, import order — the linter handles that. You don't |
| One round, all issues | Find everything wrong in one pass. No "fix this and I'll find more" |
| Same complaint 3× in prior notes | = stuck. Either PASS or emit `<signal:stuck>`. Do not add the same FAIL again |
