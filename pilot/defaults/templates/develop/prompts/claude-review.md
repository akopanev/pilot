Code review — round {{round}}.

## Protocol
{{file:protocol.md}}

## What Was Implemented

{{TASK}}

## Instructions

Two-stage review. Dispatch a sub-agent for each stage using the Task tool. Ignore any changes inside `.pilot/` — that is pipeline configuration, not project code.

### Stage 1: Spec Compliance

Use the Task tool to launch a spec compliance reviewer:

"You are reviewing whether an implementation matches its specification.

## What Was Requested

{{TASK}}

## CRITICAL: Verify by Reading Code

The implementer may have been sloppy. Their commit message and comments may be optimistic or incomplete. You MUST verify everything independently by reading the actual code.

DO NOT trust assumptions about what was implemented. DO read the actual source files changed.

Run `{{diff}}` to see the changes, then read the full code at each changed location.

## Check

**Missing requirements:**
- Did they implement everything that was requested?
- Are there requirements they skipped or only partially implemented?
- Edge cases not handled?

**Extra/unneeded work:**
- Did they build things that weren't requested?
- Over-engineering? Unnecessary features? 'Nice to haves' not in spec?

**Misunderstandings:**
- Did they interpret requirements differently than intended?
- Did they solve the wrong problem?

Report:
- PASS — all requirements met, nothing extra, nothing missing
- FAIL — list specifically what is missing, extra, or wrong (with file:line references)"

If the spec reviewer reports FAIL, skip Stage 2. Go directly to the Decision and reject with the spec findings.

### Stage 2: Code Quality (only after spec PASS)

Use the Task tool to launch a code quality reviewer:

"Review the code changes for quality. Run `{{diff}}` to see the diff.

Check:
**Correctness** — logic errors, off-by-one, wrong operators, unhandled edge cases, missing error handling, resource leaks
**Tests** — missing tests for new code paths, untested error paths, fake tests (always pass regardless of code), tests checking hardcoded values instead of real output
**Over-engineering** — unnecessary abstraction layers, factory for single implementation, generic solution for specific problem, pass-through wrappers
**Naming & clarity** — unclear names, misleading names, inconsistent conventions

For each issue: file:line, what's wrong, how to fix it.
If no issues: APPROVED"

### Merge and Decide

Collect findings from both stages.

**Previous feedback from prior rounds:**
{{FEEDBACK}}

#### Path A — Both stages passed, ZERO issues
<pilot:approve/>

#### Path B — Issues found
List all confirmed issues with:
- **Stage**: spec compliance or code quality
- **File**: exact file path and line number
- **Issue**: clear description
- **Fix**: specific suggestion
<pilot:reject>
[all confirmed issues with stage, file:line, description, and fix suggestion]
</pilot:reject>

#### Path C — Cannot proceed
<pilot:blocked>description of what's blocking</pilot:blocked>
