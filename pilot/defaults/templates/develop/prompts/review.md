Code review — round {{round}}.

## Protocol
{{file:protocol.md}}

## What Was Implemented

The following task was just implemented. Review agents should verify the changes achieve this goal:

{{TASK}}

## Context

Review the implementation for correctness, quality, and completeness.
Run `{{diff}}` to see the changes to review.

## Step 1: Launch ALL 5 Review Agents IN PARALLEL

Launch all agents using the Task tool with run_in_background=true — ALL 5 in one response.
Then immediately call TaskOutput(task_id, block=true) for EACH agent to wait for its completion.
Collect ALL results before proceeding to Step 2.

Each agent should receive:
1. The task description above (so they know the GOAL)
2. The diff command: `{{diff}}`
3. Instruction: "Report problems only — no positive observations."

{{agent:quality}}
{{agent:implementation}}
{{agent:testing}}
{{agent:simplification}}
{{agent:documentation}}

CRITICAL: Do NOT proceed to Step 2 until ALL 5 agents have returned results. Wait for every TaskOutput call to complete. Do not start evaluating findings or deciding on signals based on partial results.

## Step 2: Collect, Verify, and Classify

After ALL agents complete:

### 2.1 Collect and Deduplicate
- Merge findings from all agents
- Same file:line + same issue = merge into one finding
- Cross-agent duplicates = merge, note both sources

### 2.2 Verify EVERY Finding
For EACH issue reported:
1. Read actual code at the reported file:line
2. Check full context (20-30 lines around the location)
3. Verify the issue is real, not a false positive
4. Check for existing mitigations or intentional patterns

Classify each as:
- **CONFIRMED** — real issue, must be fixed
- **FALSE POSITIVE** — doesn't exist, already mitigated, or intentional — discard

### 2.3 Include Pre-existing Issues
Pre-existing issues (linter errors, failing tests) visible in the diff should also be flagged.
Do NOT skip issues just because they existed before — they still need fixing.

## Step 3: Decision

IMPORTANT: Do not decide until Steps 1-2 are complete — all agents finished, all findings verified.

**Previous feedback from prior rounds:**
{{FEEDBACK}}

### Path A — ZERO confirmed issues found
You reviewed the code thoroughly and found nothing to fix.
<pilot:approve/>

### Path B — Issues found that need fixing
List all CONFIRMED issues with:
- **File**: exact file path and line number
- **Issue**: clear description of the problem
- **Impact**: how this affects correctness, security, or quality
- **Fix**: specific suggestion for how to fix it
<pilot:reject>
[list of all confirmed issues with file:line, description, impact, and fix suggestion]
</pilot:reject>

### Path C — Issues found but cannot be fixed
Something prevents progress and requires human intervention.
<pilot:blocked>description of what's blocking</pilot:blocked>
