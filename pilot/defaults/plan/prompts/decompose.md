# Protocol: Epic Decomposition

Decompose ONE epic into concrete tasks. The pipeline tells you which
epic to process (ID + title from the pick_epic signal).

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — epic decomposed
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- **Supporting docs**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DOCS_DIR}}/`
- **Current epic**: ID and title from the pipeline signal
- **Existing tickets**: `tk list` for context on what's already planned

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/data/current-epic.md`

(Overwritten each round — handoff to the tickets stage.)

---

## Execution

### Step 1: Read everything

1. Read the PRD.
2. List `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DOCS_DIR}}/` and read EVERY file.
   Architecture, design system, API specs, data models, tech stack — all of it.
3. Run `tk list` to see existing epics and tasks from previous rounds.
4. `<signal:update>read PRD + N docs, decomposing [epic title]</signal:update>`

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

Break the epic into tasks. Each task:

- **Title**: verb-first, specific. "Create water_logs table", not "Database"
- **Outcome**: what is true when done. One sentence, verifiable.
- **Tags**: backend, mobile, db, api, ui, auth, etc.
- **Depends on**: other tasks in this epic (T1, T2...) or `tk` IDs from
  previous epics (check `tk list`)
- **Complexity**: S (few hours) / M (1 day) / L (2 days)

**Sizing**: 0.5–2 days each. Split if bigger, merge if trivial.

**Vertical slices**: "User can log water (API + screen)" beats separate
"Build API" + "Build screen" — unless genuinely independent.

**Sequential**: tasks form a dependency chain for a solo developer.
Internal order: data models → API → UI → integration → polish.

**Cross-epic deps**: reference actual `tk` ticket IDs from `tk list`.

### Step 4: Write the output

```markdown
# [Epic Title]

**Epic ID**: [tk ID from signal]
**Goal**: [from PRD or synthesized for Epic 0]

## Tasks

### T1: [Task Title]
- **Outcome**: [one sentence]
- **Tags**: [comma-separated]
- **Depends on**: —
- **Complexity**: M

### T2: [Task Title]
- **Outcome**: [one sentence]
- **Tags**: [comma-separated]
- **Depends on**: T1
- **Complexity**: S

### T3: [Task Title]
- **Outcome**: [...]
- **Tags**: [...]
- **Depends on**: T2, xx-xxxx *(cross-epic)*
- **Complexity**: L
```

Write to `{{var:PILOT_CONFIG_DIR}}/data/current-epic.md`.

`<signal:completed>[epic title]: N tasks</signal:completed>`

---

## Rules

| Rule | Constraint |
|:-----|:-----------|
| One epic only | Decompose the epic from the signal, nothing else |
| Lean output | Title + outcome + tags + deps + complexity. No long descriptions |
| Reference docs | Outcomes should cite specific paths, schemas, endpoints |
| Follow the PRD | Don't add or remove features. Decompose what's there |
| Use real tk IDs | Cross-epic deps use actual IDs from `tk list` |
| Foundation is minimal | Epic 000: only what Epic 001 needs |
| Vertical slices | End-to-end over layer-by-layer |
| Right-sized | 0.5–2 days per task |
