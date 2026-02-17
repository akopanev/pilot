Implement the following task.

## Protocol
{{file:protocol.md}}

## Task
{{TASK}}

## Codebase Context
{{emit.snapshot}}

## Instructions

STEP 1 — UNDERSTAND:
- Read the task carefully — understand what is being asked and why
- Examine the relevant existing code in the codebase
- If the task references dependencies on other tasks, verify those changes exist
- If anything is unclear — requirements, approach, dependencies — stop and note it in your report. Do not guess.
- Identify the minimal set of changes needed

STEP 2 — IMPLEMENT:
- Make exactly the changes the task describes
- Follow existing code conventions (naming, style, patterns)
- Keep changes focused — do not refactor unrelated code
- Write tests for new code paths

STEP 3 — VERIFY:
- If the task specifies verification commands, run them
- Run the project's test suite to verify nothing is broken
- Fix any failures before proceeding

STEP 4 — SELF-REVIEW:
Before committing, review your own work. Use the Task tool to launch a self-review sub-agent with this prompt:

"Review the uncommitted changes in this repository (`git diff`) against the task spec below. Check:

**Completeness** — did the implementation cover every requirement? Are there requirements that were skipped or half-done? Edge cases not handled?

**Discipline** — was only what was requested built? Any over-engineering, unnecessary abstractions, premature generalization, or 'nice to haves' that weren't in spec?

**Testing** — do tests verify actual behavior (not just mock behavior)? Are tests comprehensive? Do all tests pass?

**Quality** — are names clear and accurate? Is the code clean? Does it follow existing codebase patterns?

Report issues found. If no issues, say LGTM.

Task spec:
{{TASK}}"

If the self-review finds issues, fix them now — before committing.

STEP 5 — COMMIT:
- Stage only the files you changed
- Commit with message: `feat: <brief task description>`

## Signals

If the task contains a "SKIP_ME" marker or is not applicable:
<pilot:skip>reason</pilot:skip>

When implementation is complete and verification passes:
<pilot:completed>brief summary of what was done</pilot:completed>
