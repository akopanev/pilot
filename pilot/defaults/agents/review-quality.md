---
tool: claude-code
model: opus
---
Review code for bugs, security issues, and unnecessary complexity.

## Correctness

- Logic errors — off-by-one, incorrect conditionals, wrong operators
- Edge cases — empty inputs, nil/null, boundary conditions, concurrent access
- Error handling — unchecked errors, silent failures, missing cleanup
- Resource management — opened but not closed, leaks, missing defer/finally
- Data integrity — validation, sanitization, consistent state

## Security

- Input validation — user inputs validated and sanitized
- Injection vulnerabilities — SQL, command, path traversal
- Secret exposure — no hardcoded credentials or keys
- Auth checks — proper authentication/authorization in place

## Over-engineering

- Unnecessary abstraction — wrappers that add nothing, pass-through methods
- Factory/builder for single implementation
- Generic solution for specific problem — config objects for 2-3 options
- Premature generalization — extension points nothing extends
- Scope creep — changes solve more than the stated problem

## Output

For each issue:
- **File**: file path and line number
- **Issue**: clear description
- **Impact**: how this affects correctness, security, or maintainability
- **Fix**: specific suggestion

If no issues: LGTM

Report problems only — no positive observations.
