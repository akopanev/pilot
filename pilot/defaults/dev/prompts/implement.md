# Protocol: Implement

Task: `{{var:PILOT_TASK_ID}}`

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:failed>reason</signal:failed>` — fatal only: can't checkout, missing tool,
  broken environment. Never for typecheck/lint/test failures
- No signal = advance to verify

## Steps

1. **Read task**: `tk show {{var:PILOT_TASK_ID}}`. The ticket contains:
   - What to build (files, components, endpoints)
   - How it fits (connections to other tasks/epics, patterns to follow)
   - Acceptance criteria with exact check commands
   - Out of scope (what NOT to touch)
2. **Checkout**: `git checkout {{var:PILOT_WORKING_BRANCH}}`.
3. **Read context**:
   - Prior work on branch? `git log --oneline -5` and `git diff` — understand before
     changing.
   - Open files referenced in the ticket description.
   - Read source files in scope and their surroundings — imports, types, tests,
     related components. Understand existing patterns.
4. `<signal:update>implement: {{var:PILOT_TASK_ID}}</signal:update>`
5. **Implement**: Write the code. Stay on task — every change must be necessary
   for this task to work. Don't refactor or improve unrelated code.
6. **Verify**: Run the check commands listed in the ticket's acceptance criteria.
   If anything fails — read the error, fix the code, re-run.
   Repeat until clean. Up to 3 fix cycles. Then commit regardless.
7. **Commit**: `git add . && git commit -m "{{var:PILOT_TASK_ID}}: <summary>"`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Read first | Understand existing code before writing. Check imports, types, conventions in surrounding files |
| Stay on task | Every change must serve this task. Don't refactor, clean up, or improve unrelated code |
| Git | No push. No pull. No base branch edits |
| Deps | Only add if the task requires it |
| Fixable ≠ fatal | Build/lint/test failures are fixable. Read the error, fix, re-run. Never emit `failed` for these |
