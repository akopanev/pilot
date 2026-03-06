# Protocol: Epic Decomposition & Ticket Creation

Read the PRD and docs, decompose one epic into tasks, then spawn
parallel agents to create each ticket. Wire dependencies after.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — epic fully ticketed
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- **Screen specs**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}`
- **Theme**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_THEME}}`
- **Supporting docs**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DOCS_DIR}}/`
- **Current epic ID**: `{{var:PILOT_CURRENT_EPIC}}`
- **Current epic title**: `{{var:PILOT_CURRENT_EPIC_TITLE}}`
- **Current epic content**:
{{var:PILOT_CURRENT_EPIC_CONTENT}}
- **Existing tickets**: `tk list` for cross-epic dependencies

---

## Execution

### Step 1: Read everything

1. Read the PRD.
2. Read screens.yaml — find screens belonging to this epic. These define
   exactly what UI to build: layout, blocks, components, states.
3. Read theme.yaml — colors, spacing, typography for implementation.
4. List `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DOCS_DIR}}/` and read EVERY file.
5. Run `tk list` to see existing epics and tasks from previous rounds.
4. `<signal:update>read PRD + N docs, decomposing {{var:PILOT_CURRENT_EPIC_TITLE}}</signal:update>`

The epic's content is already in the prompt above — no need to read it from tk.

**Do NOT proceed until you have read every file.**

### Step 2: Understand this epic

The epic's content is your source of truth — it contains the goal,
features, scope, and user stories. Decompose what's there. Don't add
features, don't remove features, don't reinterpret scope.

Use the PRD and docs for context: architecture patterns, tech stack,
API contracts, navigation structure. This context informs HOW to
decompose, not WHAT to decompose.

### Step 3: Decompose into tasks

Break the epic into tasks. Each task must be **comprehensive** — an AI
agent will implement it with NO context beyond the ticket itself. For
each task, define:

- **Title**: verb-first, specific. "Create water_logs table and API
  endpoints", not "Database"
- **Description**: a complete implementation brief:
  - **What to build** — specific files to create/modify, components,
    endpoints, schemas. Reference concrete paths from the docs and
    existing codebase where applicable.
  - **Screen spec** (for UI tasks) — copy the relevant screen's blocks,
    components, and states from screens.yaml. Include theme tokens the
    screen uses. The implement agent builds exactly what's specified here.
  - **How it fits** — which other tasks/epics this connects to, what
    data flows in and out, what existing patterns to follow (from docs).
  - **Acceptance criteria** — numbered list of verifiable conditions.
    Each criterion must be testable. Include the exact commands to run:
    ```
    AC1: Water log entries persist to SQLite — `pnpm test -- --grep "water_log"` passes
    AC2: POST /api/logs returns 201 with valid payload — `pnpm typecheck` passes
    AC3: No lint errors — `pnpm lint` passes
    ```
  - **Out of scope** — what NOT to touch. Prevents scope creep.
- **Tags**: backend, mobile, db, api, ui, auth, etc.
- **Depends on**: other tasks in this epic (by position: T1, T2...) or
  existing `tk` IDs for cross-epic deps (from `tk list`)

**Sizing**: 0.5–2 days each. Split if bigger, merge if trivial.

**Vertical slices**: "User can log water (API + screen)" beats separate
"Build API" + "Build screen" — unless genuinely independent.

**Sequential**: tasks form a dependency chain for a solo developer.
Internal order: data models → API → UI → integration → polish.

### Step 4: Create tickets in parallel

Launch one Agent per task — ALL in a single message so they run
concurrently. Each agent runs `tk create` and returns the ticket ID.

Give each agent this prompt (fill in the actual values):

```
Create a ticket using tk. Run this command and return ONLY the ticket ID:

tk create "[Task Title]" \
  -d "[Full description — what to build, how it fits, acceptance criteria, out of scope]" \
  -t task \
  --parent {{var:PILOT_CURRENT_EPIC}} \
  --tags [tags]

Return the ticket ID printed by tk (format: xx-xxxx). Nothing else.
```

Collect all returned ticket IDs.

### Step 5: Wire dependencies

After all agents return, link dependencies sequentially:

```bash
tk dep [T2_ID] [T1_ID]      # T2 depends on T1
tk dep [T3_ID] [T2_ID]      # T3 depends on T2
tk dep [T1_ID] [cross-epic-id]  # cross-epic dep if any
```

Use the IDs returned by the agents + any existing `tk` IDs for
cross-epic dependencies.

### Step 6: Verify

```bash
tk dep tree --full {{var:PILOT_CURRENT_EPIC}}
```

`<signal:completed>{{var:PILOT_CURRENT_EPIC_TITLE}}: N tasks, D deps</signal:completed>`

---

## Task Decomposition Rules

| Rule | Constraint |
|:-----|:-----------|
| One epic only | Decompose `{{var:PILOT_CURRENT_EPIC_TITLE}}`, nothing else |
| Self-contained tickets | Every ticket must have enough detail for an AI agent to implement it with NO other context |
| Acceptance criteria required | Every task needs numbered, testable criteria with exact check commands |
| Reference concrete paths | File paths, API endpoints, schema names — not vague descriptions |
| Follow the PRD | Don't add or remove features. Decompose what's there |
| Use real tk IDs | Cross-epic deps use actual IDs from `tk list` |
| Decompose, don't invent | Break down what the epic says. Don't add scope |
| Vertical slices | End-to-end over layer-by-layer |
| Right-sized | 0.5–2 days per task |
| Parallel agents | Launch ALL ticket-creation agents in ONE message |
| --parent is mandatory | Every task uses `--parent {{var:PILOT_CURRENT_EPIC}}` |
