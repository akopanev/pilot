Analyze the current codebase and produce a structured snapshot for use by all subsequent pipeline stages.

## Protocol
{{file:protocol.md}}

## Instructions

This snapshot runs ONCE at pipeline start. Every stage after this (PRD, planning, implementation, review) will reference your output. Be thorough and precise — downstream quality depends on this.

## Step 1: Quick Scan

Before launching analysts, do a rapid 2-minute scan:
- Read the project root: README, package manifest (package.json, setup.py, Cargo.toml, go.mod, etc.), and top-level directory structure
- Determine: **product type** (CLI, web app, API, library, mobile, desktop)
- Determine: **project stage** (greenfield — empty/minimal, or brownfield — existing code)

If the project is greenfield (no meaningful code yet), skip the full analysis. Emit a minimal snapshot and complete immediately:

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

## Step 2: Launch ALL 5 Analyst Agents IN PARALLEL

Launch all agents using the Task tool with run_in_background=true — ALL 5 in one response.
Then immediately call TaskOutput(task_id, block=true) for EACH agent to wait for its completion.
Collect ALL results before proceeding to Step 3.

CRITICAL: Do NOT proceed to Step 3 until ALL 5 agents have returned results. Wait for every TaskOutput call to complete. Do not start synthesizing based on partial results.

{{agent:analyst-pm}}
{{agent:analyst-architect}}
{{agent:analyst-ux}}
{{agent:analyst-qa}}
{{agent:analyst-devops}}

## Step 3: Collect and Synthesize

After ALL agents complete:

1. Collect all 5 reports
2. Write each report as an individual artifact file:

<pilot:update path=".pilot/{{artifacts_dir}}/PROJECT.md">[PM analyst report]</pilot:update>
<pilot:update path=".pilot/{{artifacts_dir}}/ARCHITECTURE.md">[Architect analyst report]</pilot:update>
<pilot:update path=".pilot/{{artifacts_dir}}/UX.md">[UX analyst report]</pilot:update>
<pilot:update path=".pilot/{{artifacts_dir}}/QA.md">[QA analyst report]</pilot:update>
<pilot:update path=".pilot/{{artifacts_dir}}/OPS.md">[DevOps analyst report]</pilot:update>

3. Synthesize all findings into a single unified snapshot:

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

## User Experience
- **Interfaces**: [list of user touchpoints]
- **Primary flow**: [main user journey]
- **Error experience**: [how errors reach users]

## Health
- **Documentation**: [good/adequate/poor]
- **TODOs/FIXMEs**: [count]
- **Known gaps**: [list of significant gaps across all dimensions]
</pilot:emit>

## Important

- The emitted snapshot is consumed by: PRD generation, task planning, implementation, and review
- Keep the snapshot factual and dense — no filler, no praise, no recommendations
- Individual artifact files in `.pilot/{{artifacts_dir}}/` are for human reference and for direct reads by downstream stages (PRD, planner)

When complete:
<pilot:completed>codebase analysis complete</pilot:completed>
