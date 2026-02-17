Analyze the current codebase and produce detailed artifacts for use by all subsequent pipeline stages.

## Protocol
{{file:protocol.md}}

## Rules

- **Ignore `.pilot/`** — the `.pilot/` directory is pipeline configuration, not project code. Do not analyze or reference anything in it.
- **Working tree is truth** — analyze only files that exist on disk right now.

## Instructions

This analysis runs ONCE at pipeline start. Every stage after this (implementation, review, fix) will read the artifacts you produce. Quality here determines quality everywhere downstream.

### Quick Scan

Start with a rapid check:
- Read the project root: package manifest (package.json, setup.py, Cargo.toml, go.mod, etc.) and top-level directory listing
- Determine: is this **greenfield** (empty/minimal — no meaningful source code) or **brownfield** (existing code)?

If greenfield, create minimal artifacts in `.pilot/{{artifacts_dir}}/` and complete:
- `ARCHITECTURE.md` — just the detected language/framework
- `QA.md` — "No tests yet"
- `PRODUCT.md` — product type and purpose from README or manifest
- `UX.md` — "No UI yet" (or minimal if scaffolded)
<pilot:completed>greenfield project — minimal artifacts</pilot:completed>

### Full Analysis (brownfield)

Create the artifacts directory: `.pilot/{{artifacts_dir}}/`

Dispatch four analyst sub-agents in parallel using the Task tool. Send all four in a single message so they run concurrently.

**Architecture analyst:**
{{agent:analyst-architecture}}

Write your analysis to `.pilot/{{artifacts_dir}}/ARCHITECTURE.md`

**Quality analyst:**
{{agent:analyst-quality}}

Write your analysis to `.pilot/{{artifacts_dir}}/QA.md`

**Product analyst:**
{{agent:analyst-product}}

Write your analysis to `.pilot/{{artifacts_dir}}/PRODUCT.md`

**UX analyst:**
{{agent:analyst-ux}}

Write your analysis to `.pilot/{{artifacts_dir}}/UX.md`

Wait for all four to complete.

### Emit Verification Commands

After all analysts finish, read `.pilot/{{artifacts_dir}}/QA.md` and extract the exact commands. Emit each one separately so downstream steps can reference them directly:

<pilot:emit key="test_command">[the test command from QA.md, e.g. npm test]</pilot:emit>
<pilot:emit key="build_command">[the build command from QA.md, e.g. npm run build]</pilot:emit>
<pilot:emit key="lint_command">[the lint command from QA.md, e.g. ruff check .]</pilot:emit>

Only emit commands that actually exist in QA.md. If a command wasn't found, do NOT emit it.

When complete:
<pilot:completed>codebase analysis complete</pilot:completed>
