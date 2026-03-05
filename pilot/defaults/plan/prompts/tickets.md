# Protocol: Ticket Creation (Single Epic)

Read the decomposed epic and create `tk` tickets — one epic ticket
plus its child tasks with dependencies.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — tickets created
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Decomposed epic**: `{{var:PILOT_CONFIG_DIR}}/data/current-epic.md`

## Execution

### Step 1: Read the epic

Read `{{var:PILOT_CONFIG_DIR}}/data/current-epic.md`. Parse the epic name,
goal, and all tasks.

`<signal:update>creating tickets for [epic name]</signal:update>`

### Step 2: Create the epic ticket

```bash
EPIC_ID=$(tk create "[Epic Name]" \
  -d "[Goal from the decomposed epic]" \
  -t epic \
  -p [priority])
```

Parse the ticket ID from stdout (format: `xx-xxxx`).

**Priority mapping:**
- Epic 0 (Foundation): priority 0
- Epic 1 (Onboarding): priority 0
- Epic 2 (Monetization): priority 1
- Epic 3+: priority 2

### Step 3: Create task tickets

For each task, in order:

```bash
T1=$(tk create "[Task Title]" \
  -d "[Outcome from the decomposed epic]" \
  -t task \
  -p [same as epic priority] \
  --parent $EPIC_ID \
  --tags [tags from decomposition])
```

Capture every task ID.

### Step 4: Link dependencies

Wire up dependencies from the decomposition:

```bash
# Within-epic: T2 depends on T1
tk dep $T2 $T1

# Cross-epic: T1 depends on ticket from previous epic
tk dep $T1 xx-xxxx
```

For cross-epic deps, the decomposition references actual `tk` ticket IDs —
use them directly.

### Step 5: Verify this epic

```bash
tk dep tree --full $EPIC_ID
```

Report what was created.

`<signal:completed>[epic name]: 1 epic + N tasks, D deps</signal:completed>`

---

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Parse IDs carefully | `tk create` prints ID + info — extract only the ID |
| Epic first, then tasks | Create the epic ticket before any child tasks |
| Use --parent | Every task is parented to the epic |
| Sequential creation | Create tasks in order — you need IDs for deps |
| Description = outcome | Task description is just the outcome line. Keep it lean |
| Faithful transcription | Don't add, remove, or reword. Copy from the decomposition |
| Cross-epic deps as-is | Use the tk IDs referenced in the decomposition directly |
