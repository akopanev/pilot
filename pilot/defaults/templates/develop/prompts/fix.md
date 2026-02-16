Fix the issues identified in the code review.

## Protocol
{{file:protocol.md}}

## Original Task
{{TASK}}

## Review Feedback
{{FEEDBACK}}

## Instructions

1. Read each issue in the feedback carefully — note the file, line, and suggested fix
2. For each issue:
   - Read the actual code at the specified location
   - Understand the context (what the code does, why it's there)
   - Apply the fix or an equivalent correction
   - Verify the fix doesn't break surrounding code
3. After all issues are fixed:
   - Run the project's test suite — ALL tests must pass
   - Run the linter if configured — ALL issues must be resolved
   - Fix any failures caused by your changes
4. Commit all fixes: `git commit -m "fix: address code review findings"`

## Rules

- Fix ONLY what the feedback asks for — do not refactor or improve unrelated code
- If a suggested fix would break something else, fix it differently but explain why
- If an issue cannot be fixed (missing context, external dependency), note it clearly
- Follow existing code conventions (naming, style, patterns)
- Every fix must leave the codebase in a working state

When all fixes are applied and tests pass:
<pilot:completed>summary of fixes applied</pilot:completed>

If fixes cannot be applied:
<pilot:blocked>what's preventing the fix and why</pilot:blocked>
