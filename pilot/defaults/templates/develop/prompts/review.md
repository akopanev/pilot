Code review — round {{round}}.

## Protocol
{{file:protocol.md}}

## What Was Implemented

The following task was just implemented. Verify the changes achieve this goal:

{{TASK}}

## Instructions

Review the implementation by reading the diff and checking against the checklist below. Do the review yourself directly — do NOT use the Task tool or launch sub-agents. Ignore any changes inside `.pilot/` — that is pipeline configuration, not project code.

### Step 1: Read the Diff

Run `{{diff}}` to see the changes to review. Read the full diff carefully.

### Step 2: Check Against Checklist

#### Correctness
- Logic errors — off-by-one, incorrect conditionals, wrong operators
- Edge cases — empty inputs, nil/null values, boundary conditions
- Error handling — all errors checked, no silent failures
- Resource management — proper cleanup, no leaks

#### Goal Achieved
- Does the implementation address all aspects of the task?
- Is everything wired correctly — imports, registrations, routes, configs?
- Are there missing pieces that would prevent the feature from working?
- Does data flow correctly from input to output?

#### Tests
- New code paths without corresponding tests
- Untested error paths
- Fake tests — tests that always pass regardless of code changes
- Tests checking hardcoded values instead of actual output
- Tests verifying mock behavior instead of real code

#### Over-engineering
- Unnecessary abstraction layers — wrappers that add nothing
- Factory pattern when only one implementation exists
- Generic solution for a specific problem
- Premature generalization — config objects for 2-3 options, plugin architecture for fixed functionality
- Pass-through methods that only delegate

### Step 3: Verify Every Finding

For EACH issue you identify:
1. Read actual code at the reported file:line
2. Check full context (20-30 lines around the location)
3. Verify the issue is real, not a false positive
4. Check for existing mitigations or intentional patterns

Classify each as:
- **CONFIRMED** — real issue, must be fixed
- **FALSE POSITIVE** — doesn't exist, already mitigated, or intentional — discard

### Step 4: Decision

**Previous feedback from prior rounds:**
{{FEEDBACK}}

#### Path A — ZERO confirmed issues found
You reviewed the code thoroughly and found nothing to fix.
<pilot:approve/>

#### Path B — Issues found that need fixing
List all CONFIRMED issues with:
- **File**: exact file path and line number
- **Issue**: clear description of the problem
- **Impact**: how this affects correctness or quality
- **Fix**: specific suggestion for how to fix it
<pilot:reject>
[list of all confirmed issues with file:line, description, impact, and fix suggestion]
</pilot:reject>

#### Path C — Cannot proceed
Something prevents progress and requires human intervention.
<pilot:blocked>description of what's blocking</pilot:blocked>
