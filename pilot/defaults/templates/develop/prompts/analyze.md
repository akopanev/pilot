Analyze the current codebase and produce a structured snapshot for use by all subsequent pipeline stages.

## Protocol
{{file:protocol.md}}

## Rules

- **Read-only** — do NOT modify, create, or delete any files. Do NOT run git checkout, git restore, git clean, or any command that changes the working tree. You are here to observe, not to fix.
- **Ignore `.pilot/`** — the `.pilot/` directory is pipeline configuration, not project code. Do not read, analyze, or reference anything in it.
- **Working tree is truth** — analyze only files that exist on disk right now. If files are deleted in the working tree but tracked in git, they are deleted. Do not recover them, do not read them from git history.
- Do NOT use the Task tool or launch sub-agents — do the analysis yourself directly.

## Instructions

This snapshot runs ONCE at pipeline start. Every stage after this (implementation, review) will reference your output. Be thorough and precise — downstream quality depends on this.

### Quick Scan

Start with a rapid scan:
- Read the project root: README, package manifest (package.json, setup.py, Cargo.toml, go.mod, etc.), and top-level directory structure
- Determine: **product type** (CLI, web app, API, library, mobile, desktop)
- Determine: **project stage** (greenfield — empty/minimal, or brownfield — existing code)

If the project is greenfield (no meaningful source code on disk), emit a minimal snapshot and complete immediately:

<pilot:emit key="snapshot">
# Codebase Snapshot

## Product
- **Type**: [detected type or "unknown"]
- **Stage**: greenfield
- **Purpose**: [from README or "new project"]

## Tech Stack
- **Language**: [detected from package manifest or "not yet determined"]
- **Build**: [detected or "none"]

## Patterns & Conventions
- No established patterns yet — new project

## Quality
- No tests yet

## Health
- Greenfield — no existing code to assess
</pilot:emit>

<pilot:completed>greenfield project — minimal snapshot</pilot:completed>

### Full Analysis (brownfield)

For existing projects, scan the codebase directly. Cover each area below:

1. **Project identity** — purpose, target user, product type
2. **Architecture** — language, framework, module structure, entry points, key modules, data flow
3. **Tech stack** — build system, dependencies, infrastructure, deployment
4. **Patterns & conventions** — code organization, naming, error handling, config management
5. **Quality** — test framework, test status (run the tests), coverage, linting, CI/CD
6. **Health** — documentation quality, TODOs/FIXMEs count, known gaps

Keep the scan focused — read only what you need to fill in the snapshot. Do not read every file. Prioritize: README, package manifests, entry points, config files, test runner output, and a representative sample of source files.

### Emit Snapshot

Synthesize all findings into a single unified snapshot:

<pilot:emit key="snapshot">
# Codebase Snapshot

## Product
- **Type**: [CLI / web app / API / library / etc.]
- **Stage**: [greenfield / brownfield]
- **Purpose**: [one sentence]
- **Target user**: [who]

## Architecture
- **Language**: [lang + version]
- **Framework**: [framework + version]
- **Structure**: [organization principle]
- **Entry points**: [list]
- **Key modules**: [list with responsibilities]
- **Data flow**: [how data moves through the system]

## Tech Stack
- **Build**: [build system]
- **Dependencies**: [key deps, pinned/unpinned]
- **Infrastructure**: [databases, services, cloud]
- **Deployment**: [Docker / none / other]

## Patterns & Conventions
- **Code organization**: [pattern or "ad hoc"]
- **Naming**: [conventions]
- **Error handling**: [approach]
- **Config management**: [approach]

## Quality
- **Test framework**: [name]
- **Test status**: [pass/fail count]
- **Coverage**: [tested vs untested modules]
- **Linting/formatting**: [tools in use]
- **CI/CD**: [what exists]

## Health
- **Documentation**: [good/adequate/poor]
- **TODOs/FIXMEs**: [count]
- **Known gaps**: [list of significant gaps]
</pilot:emit>

## Important

- The emitted snapshot is consumed by: implementation and review steps
- Keep the snapshot factual and dense — no filler, no praise, no recommendations

When complete:
<pilot:completed>codebase analysis complete</pilot:completed>
