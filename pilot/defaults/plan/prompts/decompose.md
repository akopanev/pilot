# Protocol: Epic Decomposition & Ticket Creation

Read the PRD and docs, decompose one epic into tasks, then spawn
parallel agents to create each ticket. Wire dependencies after.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — epic fully ticketed
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
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
2. List `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DOCS_DIR}}/` and read EVERY file.
3. Run `tk list` to see existing epics and tasks from previous rounds.
4. `<signal:update>read PRD + N docs, decomposing {{var:PILOT_CURRENT_EPIC_TITLE}}</signal:update>`

The epic's content is already in the prompt above — no need to read it from tk.

**Do NOT proceed until you have read every file.**

### Step 2: Understand this epic

**If Epic 000: Foundation** — synthesize from the docs. This covers:
- Project scaffolding and tooling
- Core data models / DB schema
- Auth setup (if applicable)
- Base navigation shell
- Only what's needed for Epic 001 to start. Keep it minimal.

**All other epics** — find the epic in the PRD. It has a goal, features,
scope, and user stories. Those are your source of truth.

### Step 3: Decompose into tasks

Break the epic into tasks. For each task, define:

- **Title**: verb-first, specific. "Create water_logs table", not "Database"
- **Outcome**: what is true when done. One sentence, verifiable.
- **Tags**: backend, mobile, db, api, ui, auth, etc.
- **Depends on**: other tasks in this epic (by position: T1, T2...) or
  existing `tk` IDs for cross-epic deps (from `tk list`)
- **Complexity**: S (few hours) / M (1 day) / L (2 days)

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
  -d "[Outcome]" \
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
| Lean tickets | Title + outcome + tags. No long descriptions |
| Reference docs | Outcomes should cite specific paths, schemas, endpoints |
| Follow the PRD | Don't add or remove features. Decompose what's there |
| Use real tk IDs | Cross-epic deps use actual IDs from `tk list` |
| Foundation is minimal | Epic 000: only what Epic 001 needs |
| Vertical slices | End-to-end over layer-by-layer |
| Right-sized | 0.5–2 days per task |
| Parallel agents | Launch ALL ticket-creation agents in ONE message |
| --parent is mandatory | Every task uses `--parent {{var:PILOT_CURRENT_EPIC}}` |
