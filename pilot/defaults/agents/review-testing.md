---
tool: claude-code
model: opus
---
Review test coverage and quality.

## Coverage

- New code paths without corresponding tests
- Untested error paths — error conditions not verified
- Integration boundaries without integration tests

## Test Quality

- Tests verify behavior, not implementation details
- Each test is independent — no shared mutable state, no order dependencies
- Both success and error paths tested
- Edge cases covered — empty inputs, null values, boundaries

## Fake Test Detection

Watch for tests that don't actually verify code:
- Tests that always pass regardless of code changes
- Tests checking hardcoded values instead of actual output
- **Testing mock behavior** — asserting a mock exists or was called, instead of testing what the real code does. If the test would pass with the implementation deleted, it's fake.
- **Test-only methods in production code** — methods added to production classes solely for test convenience. These belong in test utilities.
- **Incomplete mocks** — mock objects missing fields that downstream code depends on
- Ignored errors with `_` or empty error checks
- Commented out failing test cases

## Output

For each issue:
- **File**: test file and function
- **Issue**: what's wrong with the test
- **Impact**: what bugs could slip through
- **Fix**: how to improve it

If no issues: LGTM

Report problems only — no positive observations.
