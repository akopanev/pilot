Implement the following task.

## Protocol
{{file:protocol.md}}

## Task
{{TASK}}

## Project Knowledge
Read selectively if needed:
- `.pilot/{{artifacts_dir}}/ARCHITECTURE.md` — module structure and patterns
- `.pilot/{{artifacts_dir}}/QA.md` — test patterns and conventions

## Instructions

STEP 1 — UNDERSTAND:
- Read the task's Objective, Files, and Actions sections
- Examine existing code listed in the task's `## Files` section
- If the task has `depends_on`, verify those changes exist
- Identify the minimal set of changes needed

STEP 2 — IMPLEMENT:
- Make the changes described in `## Actions`
- Follow existing code conventions (naming, style, patterns)
- Keep changes focused — do not refactor unrelated code
- Touch only the files listed in `## Files` (unless a new file is clearly needed)

STEP 3 — VERIFY:
- Execute the commands in the task's `## Verify` section
- Run the project's test suite to verify nothing is broken
- Fix any failures before proceeding

STEP 4 — COMMIT:
- Stage only the files you changed
- Commit with message: `feat: <brief task description>`

## Signals

If the task contains a "SKIP_ME" marker or is not applicable:
<pilot:skip>reason</pilot:skip>

When implementation is complete and verification passes:
<pilot:completed>brief summary of what was done</pilot:completed>
