Break the PRD into iterations of atomic, executable tasks.

## Protocol
{{file:protocol.md}}

## Inputs

### PRD
{{file:{{prd_file}}}}

### Project Knowledge
Read selectively — only what's needed for decomposition:
- `.pilot/{{artifacts_dir}}/ARCHITECTURE.md` — module boundaries, dependency graph
- `.pilot/{{artifacts_dir}}/QA.md` — test patterns (if tasks involve testing)
- `.pilot/{{artifacts_dir}}/UX.md` — UI patterns (if tasks involve UI)
- `.pilot/{{artifacts_dir}}/OPS.md` — deploy patterns (if tasks involve infra)

The PRD already contains Technical Context from artifacts. Read artifacts directly only if you need more detail to decompose properly.

## Read Discipline

- Do NOT probe the filesystem (no `ls`, no directory checks)
- Do NOT read source code unless the PRD is missing a critical boundary
- If you must read code, justify it and read the minimum (1-2 files)
- The PRD is your contract — work from it, not from the codebase

## Process

1. Read PRD — this is your contract
2. Read relevant artifacts if PRD lacks detail for decomposition
3. Decompose into atomic tasks
4. Group tasks into iterations based on dependencies and complexity
5. Identify parallel groups where safe
6. Define verification criteria per task AND per iteration
7. Write roadmap and task files

## Task Decomposition Rules

Each task must be:
- **Atomic** — one task = one logical unit of work
- **Clear** — single objective, no ambiguity
- **Scoped** — specific files listed
- **Verifiable** — concrete done criteria (executable commands, not "make sure it works")
- **Ordered** — respect dependency sequence via `depends_on`

## Task ID Pattern

`i{NN}-{descriptive-name}`

Examples: `i01-user-model`, `i02-auth-routes`, `i03-refresh-token`

## Task Kinds

- `IMPLEMENT` — changes production code. Must list all touched files in `## Files`
- `ANALYZE` / `RESEARCH` / `DOC` — read-only on production code. Allowed writes: `.pilot/**` only

## Iteration Sizing

- Aim for <500 lines of code changes per iteration
- Each iteration should be independently meaningful (not "part 1 of 3")
- Each iteration leaves the project in a working state

## Parallel Groups

Tasks marked with `parallel_group` run simultaneously. A task qualifies ONLY if ALL of:
1. `depends_on` is empty (or all deps complete before the group starts)
2. `## Files` do NOT overlap with other tasks in the group
3. Tasks don't share mutable state (config, test fixtures, DB schemas)

When unsure, omit — tasks default to sequential. Safety first.

## Scope Check

| PRD says | Expected tasks |
|----------|----------------|
| small | 1-6 |
| medium | 7-20 |
| large | 20+ |

If your count doesn't match the PRD's scope estimate — re-evaluate.

## Output

### 1. Roadmap

<pilot:update path=".pilot/roadmap.md">
# Roadmap

## Iterations

### Iteration 1 — {Theme}
- i01-{name} (depends: none) [parallel: A]
- i02-{name} (depends: i01)
- i03-{name} (depends: none) [parallel: A]

### Iteration 2 — {Theme}
- i04-{name} (depends: i01, i02)
- ...

## Iteration Review Criteria

### Iteration 1
- Build passes
- Tests pass for: {specific test files}
- Integration check: {what to verify across tasks}

### Iteration 2
- ...

## Total
- Iterations: N
- Tasks: N
- Estimated scope: {small|medium|large}
</pilot:update>

### 2. Task Files

Write each task to `.pilot/{{tasks_dir}}/`:

<pilot:update path=".pilot/{{tasks_dir}}/i01-description.md">
---
id: i01-{descriptive-name}
iteration: 1
kind: IMPLEMENT
depends_on: []
parallel_group: null
status: pending
attempt: 1
---

## Objective

{Single clear goal — one sentence}

## Files

- {file paths to create or modify}

## Actions

- {Specific action 1}
- {Specific action 2}

## Verify

- {Exact commands to run or checks to perform}
</pilot:update>

Create as many task files as needed.

## Rules

1. The PRD is your contract — do NOT reinterpret the user's intent
2. Do NOT invent tasks beyond what the PRD requires
3. One task = one logical unit of work
4. Every `## Verify` section must be executable and explicit
5. All task files go to `.pilot/{{tasks_dir}}/`
6. Consider iteration size — keep PRs reviewable (<500 lines)
7. Read artifacts only if PRD doesn't have enough detail

When all task files and roadmap are written:
<pilot:completed>created N tasks in M iterations</pilot:completed>
