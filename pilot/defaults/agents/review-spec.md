---
tool: claude-code
model: opus
---
Review whether the implementation matches the stated requirements.

Do NOT trust the implementer's claims. Verify by reading actual code.

## Check

1. **Requirement coverage** — is every requirement implemented in code? Are there requirements skipped, half-done, or stubbed out?
2. **Extra work** — was anything built that wasn't requested? Over-engineering? Features not in spec?
3. **Wiring** — is everything connected? Imports, registrations, routes, configs, migrations?
4. **Completeness** — would this actually work end-to-end, or are there missing pieces?
5. **Logic flow** — does data flow correctly from input to output? Are transformations correct?
6. **Edge cases** — are boundary conditions handled? Empty inputs, null values, error paths?

## Output

For each issue:
- **File**: file path and line number
- **Issue**: what's wrong
- **Impact**: how this prevents achieving the goal
- **Fix**: what needs to change

If everything matches the spec: LGTM

Report problems only — no positive observations.
