Implement the following task.

## Protocol
{{file:protocol.md}}

## Task
{{TASK}}

## Codebase Context

Read the analysis artifacts before starting:
- `.pilot/{{artifacts_dir}}/ARCHITECTURE.md` — codebase structure, patterns, conventions
- `.pilot/{{artifacts_dir}}/QA.md` — test/build commands, coverage map
- `.pilot/{{artifacts_dir}}/PRODUCT.md` — product context, features
- `.pilot/{{artifacts_dir}}/UX.md` — navigation, screens, component patterns

If `.pilot/{{docs_dir}}/` exists, read the project documentation there for additional context.

## Instructions

STEP 1 — UNDERSTAND:
- Read the task carefully — understand what is being asked and why
- Read the artifacts above — understand codebase patterns, conventions, test framework
- If the task references dependencies on other tasks, verify those changes exist
- Identify the minimal set of changes needed

STEP 2 — IMPLEMENT:
- Make exactly the changes the task describes
- Follow existing code conventions (naming, style, patterns)
- Keep changes focused — do not refactor unrelated code
- Write tests for new code paths

STEP 3 — VERIFY:
- Run the test suite: {{emit.test_command}}
- Run the build if available: {{emit.build_command}}
- If the task has a `## Verify` section, run those commands too
- ALL must pass. Fix any failures before proceeding.

STEP 4 — COMMIT:
- Stage only the files you changed
- Commit with message: `feat: <brief task description>`

## Signals

If the task contains a "SKIP_ME" marker or is not applicable:
<pilot:skip>reason</pilot:skip>

When implementation is complete and verification passes:
<pilot:completed>brief summary of what was done</pilot:completed>
