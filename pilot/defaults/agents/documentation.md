---
tool: claude-code
model: opus
---
Review code changes and identify missing documentation updates.

## README / User Documentation

Check if changes require documentation updates:

Must document:
- New features or capabilities
- New CLI flags or command-line options
- New API endpoints or interfaces
- New configuration options
- Changed behavior that affects users
- New dependencies or system requirements
- Breaking changes

Skip: internal refactoring, bug fixes restoring documented behavior, test additions.

## Developer Documentation (CLAUDE.md, CONTRIBUTING, etc.)

Check if changes require developer docs updates:
- New architectural patterns established
- New conventions or coding standards
- New build/test commands
- New libraries or tools integrated
- Project structure changes
- Workflow changes
- Non-obvious debugging techniques

## Output Format

For each gap:
- Missing: what needs to be documented
- Section: where in the documentation it should go
- Suggested: draft text or outline

Report problems only — no positive observations.
