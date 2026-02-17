---
tool: claude-code
model: opus
---
Analyze the codebase architecture and write a detailed reference document.

Do NOT rely on README files — they are often stale. Read actual code.

## How to Analyze

- Read directory structure first
- Read key config files: package.json, pyproject.toml, Cargo.toml, go.mod, Makefile, etc.
- Read entry points (main, index, app, cmd/)
- Read 3-5 representative source files to understand patterns
- Do NOT read every file — map the structure, sample the patterns

## What to Map

1. **Tech stack** — languages, frameworks, key dependencies with versions
2. **Project structure** — directory layout, what lives where, entry points
3. **Module boundaries** — how the code is organized, what depends on what
4. **Key patterns** — naming conventions, error handling style, logging, config management, file organization
5. **Data flow** — how data moves through the system (API → service → DB, etc.)
6. **Build system** — how the project builds, compiles, bundles

## Output

Write the analysis to the artifacts path specified in your dispatch instructions, using this structure:

```markdown
# Architecture

## Stack
- **Language**: [lang + version]
- **Framework**: [framework + version]
- **Key dependencies**: [list with versions]

## Structure
[directory tree with brief descriptions of what each dir contains]

## Modules
[key modules, their responsibilities, dependencies between them]

## Patterns
- **Naming**: [conventions found in code]
- **Error handling**: [approach — try/catch, Result types, error codes, etc.]
- **Config**: [how configuration is managed]
- **Logging**: [approach if any]
- **File organization**: [how files are laid out within modules]

## Entry Points
[main entry points and how the app starts/runs]

## Data Flow
[how data moves through the system — request/response, event-driven, etc.]
```

Be factual and dense — no filler, no praise, no recommendations. This document is consumed by implementation and review agents who need to understand where to put code and how to write it.
