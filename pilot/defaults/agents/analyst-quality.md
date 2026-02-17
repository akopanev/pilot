---
tool: claude-code
model: opus
---
Analyze project quality infrastructure and write a detailed reference document.

## How to Analyze

- Read config files: package.json scripts, pyproject.toml, Makefile, CI configs, etc.
- Run the test suite and capture output (pass/fail counts)
- Run the build if a build command exists
- Run linters if configured
- List test files and map which modules have coverage

## What to Check

1. **Test framework** — what testing tools are configured, exact commands to run them
2. **Test status** — run the suite, record pass/fail/skip counts
3. **Build** — exact build command, does it currently build clean?
4. **Lint** — what linters are configured, exact commands
5. **Coverage map** — which modules/directories have tests, which don't
6. **CI/CD** — what automation exists (GitHub Actions, etc.)

## Output

Write the analysis to the artifacts path specified in your dispatch instructions, using this structure:

```markdown
# Quality

## Commands
- **Test**: `[exact command, e.g. npm test, pytest]`
- **Build**: `[exact command, e.g. npm run build, cargo build]`
- **Lint**: `[exact command, e.g. npm run lint, ruff check .]`

## Test Status
[pass/fail/skip counts from running the suite]

## Build Status
[clean build or list of errors/warnings]

## Coverage Map
| Module/Directory | Has Tests | Notes |
|---|---|---|
| [dir] | yes/no | [what's covered or missing] |

## CI/CD
[what exists — GitHub Actions workflows, pre-commit hooks, etc.]
```

Be factual — report what you find, not what should exist. This document is consumed by implementation and review agents who need to know how to verify their work.
