# Protocol: Create Epic Tickets

Read the PRD and create one `tk` epic ticket per epic. This is a one-time
setup step — subsequent stages will fill each epic with tasks.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — all epics created
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`

## Execution

1. Read the PRD.
2. Extract all epics (headings matching `## Epic N: ...`).
3. Renumber with zero-padded 3-digit IDs: Epic 1 → Epic 001, Epic 2 → Epic 002, etc.
4. Prepend **Epic 000: Foundation** — always first, not in the PRD.
   Foundation covers project scaffolding, core models, and base setup
   that all other epics depend on.
5. `<signal:update>creating N epic tickets</signal:update>`
6. For each epic, create a ticket:

```bash
tk create "Epic 000: Foundation" \
  -d "Project scaffolding, core data models, and base setup needed before feature work begins." \
  -t epic

tk create "Epic 001: [Name from PRD]" \
  -d "[full epic content — see format below]" \
  -t epic

# ... repeat for all epics
```

**Description format**: the epic ticket must be self-contained. Include
the full epic section from the PRD:

- **Goal** — the outcome line
- **Feature list** — every feature with its What, Scope, and User stories
- **Any epic-specific details** (onboarding flow steps, paywall rules, etc.)

The ticket description IS the PRD epic section. Copy it faithfully.
The decompose stage will read this ticket and break features into tasks —
it needs the full scope, not a summary.

7. `<signal:completed>N epics created</signal:completed>`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Epic 000 is synthetic | Always create it. Derive description from what the PRD implies |
| Everything else from PRD | Epic names, goals, features, ordering — all come from the PRD. Don't invent |
| Full content in ticket | Copy the entire epic section from PRD into the ticket description. Features, scope, user stories — all of it |
| Ticket = PRD section | The decompose stage reads the ticket, not the PRD. The ticket must have everything |
| 3-digit numbering | Always zero-pad: Epic 000, Epic 001, ..., Epic 099. Ensures correct sort |
| All at once | Create every epic in this stage. Don't leave any for later |
| No tasks | Only create epic tickets. Tasks come in the decompose stage |
| Order matters | Create in order: 000, 001, 002, ... N |
