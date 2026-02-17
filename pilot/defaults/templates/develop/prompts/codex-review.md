Code review — round {{round}}.

## Protocol
{{file:protocol.md}}

## What Was Implemented

{{TASK}}

## Instructions

You are reviewing code changes. Your job is to find real problems — not rubber-stamp.

**Mindset:** The implementer may have been sloppy. Their commit message may be optimistic. Do NOT trust claims about what was built. Verify everything by reading actual code.

Ignore any changes inside `.pilot/` — that is pipeline configuration, not project code.

---

### Phase 1: Spec Compliance

Run `{{diff}}` to see the changes. Then read the full source at each changed location.

**DO NOT** take the diff at face value — read surrounding context. A function that looks correct in isolation may be wrong in context.

Check line by line against the task requirements:

**Missing requirements:**
- Is every requirement from the task actually implemented in code?
- Are there requirements that were skipped, half-done, or stubbed out?
- Edge cases the task implies but implementation ignores?

**Extra/unneeded work:**
- Code that wasn't requested — unnecessary features, abstractions, config options
- Over-engineering — factory for one implementation, plugin architecture for fixed behavior, generic solution for a specific problem
- "Nice to haves" not in spec

**Misunderstandings:**
- Requirements interpreted differently than intended
- Right feature, wrong approach
- Solving a different problem than what was asked

**Wiring:**
- Is everything connected — imports, registrations, routes, configs?
- Does data flow correctly from input to output?
- Would this actually work if you ran it, or is it dead code?

If spec compliance fails, skip Phase 2. Go directly to the Decision and reject with spec findings.

---

### Phase 2: Code Quality

Only reach this phase if the spec is fully met.

#### Correctness
- Logic errors — off-by-one, incorrect conditionals, wrong operators, inverted boolean logic
- Null/nil/undefined — unguarded access, missing null checks on nullable returns
- Error handling — unchecked errors, silent swallowing, missing cleanup on error paths
- Resource management — opened but not closed, missing `defer`/`finally`/`with`
- Concurrency — race conditions, missing locks, shared mutable state
- Type mismatches — wrong types passed, unsafe casts, implicit conversions

#### Tests
- New code paths without corresponding tests
- Untested error paths — only happy path tested
- **Fake tests** — tests that always pass regardless of code changes (hardcoded expected values, asserting on mocks instead of real behavior)
- **Testing mock behavior** — asserting that a mock exists or was called, instead of testing what the real code does. If a test would pass even with the implementation deleted, it's fake.
- **Test-only methods in production code** — methods added to production classes solely for test convenience (belongs in test utilities)
- **Incomplete mocks** — mock objects missing fields that downstream code depends on. Partial mocks hide structural assumptions and cause silent failures.
- Tests that don't actually run the code under test

#### Over-engineering
- Unnecessary abstraction layers — wrappers that add zero value
- Factory/builder pattern when only one implementation exists
- Premature generalization — config objects for 2-3 options, extension points nobody asked for
- Pass-through methods that only delegate to another method
- Defensive code for impossible conditions (internal code paths that can't receive bad input)

#### Naming & Clarity
- Misleading names — name says one thing, code does another
- Inconsistent conventions — mixing camelCase and snake_case in same scope
- Magic numbers/strings without explanation

---

### Phase 3: Verify Every Finding

**This is critical.** Before reporting any issue:

1. Read the actual code at the exact file:line you're about to report
2. Read 20-30 lines of surrounding context
3. Check: is this a real issue, or does surrounding code already handle it?
4. Check: is this an intentional pattern used elsewhere in the codebase?

Classify each finding:
- **CONFIRMED** — real issue, verified in code, must be fixed
- **FALSE POSITIVE** — already mitigated, intentional, or doesn't exist → discard silently

**Only report CONFIRMED issues.** Zero tolerance for false positives. A false positive wastes an entire fix-and-review cycle. When in doubt, read more context before reporting.

---

### Decision

**Previous feedback from prior rounds:**
{{FEEDBACK}}

If prior rounds exist, verify that previously reported issues were actually fixed. Do not re-report issues that are now resolved.

Categorize confirmed issues by severity:

**Critical** — Bugs, data loss risks, security issues, broken functionality, spec violations
**Important** — Missing error handling, test gaps, architectural problems, incomplete features
**Minor** — Naming issues, minor style inconsistencies, small optimizations

#### Path A — ZERO confirmed issues

Both spec compliance and code quality passed. No issues to report.
<pilot:approve/>

#### Path B — Issues found

Report all CONFIRMED issues:

For each issue:
- **Severity**: Critical / Important / Minor
- **File**: exact file path and line number
- **Issue**: clear description of what's wrong
- **Why it matters**: impact on correctness, reliability, or maintainability
- **Fix**: specific suggestion (not vague — say exactly what to change)

<pilot:reject>
[all confirmed issues with severity, file:line, description, impact, and fix]
</pilot:reject>

#### Path C — Cannot proceed
<pilot:blocked>description of what's blocking</pilot:blocked>
