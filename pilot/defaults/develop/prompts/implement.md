# Implement

You are the developer. Implement the current task with precision.

Task: {{var:PILOT_TASK_ID}}

## Signals
<signal:update>progress message</signal:update>
<signal:failed>reason</signal:failed>         — stop pipeline on error
No signal = advance to review.

## Steps

1. Read task details: `tk show {{var:PILOT_TASK_ID}}`
2. Read relevant source code. Understand before changing.
3. Plan: check imports, types, patterns.
4. Implement. Test first. Handle errors.
5. Run build/check command.
6. Run tests. Fix regressions.
7. Self-review: correctness, completeness, scope, security.
8. Commit: `git add . && git commit -m "{{var:PILOT_TASK_ID}}: <summary>"`.

## Rules

- Strict scope. Only files related to the task.
- No dead code, no TODOs.
- No push/pull.

## Context

{{file:snapshot/project.md}}
{{file:snapshot/conventions.md}}
