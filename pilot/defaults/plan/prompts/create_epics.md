# Protocol: Create Epic Tickets

Read the PRD and supporting docs. For each epic, synthesize the PRD
content with relevant context from the docs, then create a self-contained
`tk` epic ticket. Subsequent stages will decompose each epic into tasks.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — all epics created
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- **Screen index**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}`
  (navigation structure, screen IDs, epic ownership, transitions)
- **Screen details**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS_DIR}}/`
  (per-screen files: `{screen_id}.yaml` with layout, blocks, states, interactions)
- **Theme**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_THEME}}`
- **Supporting docs**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DOCS_DIR}}/`

## Execution

1. Read the PRD.
2. Read the screen index (screens.yaml). Each screen has an `epic` field —
   this tells you which screens belong to which epic.
3. For each epic, read the per-screen detail files from
   `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS_DIR}}/` — only the files
   for screens belonging to that epic (matched by the `epic` field in the index).
4. Read the theme (theme.yaml). Cross-cutting context for all epics.
5. List `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DOCS_DIR}}/` and read EVERY file.
   These docs contain architecture decisions, design specs, API contracts,
   tech stack details — context that the PRD alone doesn't have.
6. Extract all epics (headings matching `## Epic N: ...`).
7. Renumber with zero-padded 3-digit IDs: Epic 1 → Epic 001, Epic 2 → Epic 002, etc.
8. `<signal:update>creating N epic tickets</signal:update>`
9. For each epic, create a ticket:

```bash
tk create "Epic 001: [Name from PRD]" \
  -d "[synthesized epic content — see format below]" \
  -t epic

# ... repeat for all epics
```

**Description format**: the epic ticket must be self-contained — a
downstream agent will read ONLY this ticket to decompose it into tasks.
It must have everything that agent needs:

- **Goal** — the outcome line from the PRD
- **Context** — relevant cross-cutting info from the PRD (core use cases,
  target user, navigation structure) and from the docs (architecture
  decisions, tech stack, API contracts) that affect this epic
- **Screens** — the per-screen detail files for screens belonging to
  this epic. Include layout, blocks, states, interactions — everything
  the decomposer needs to create screen-level tasks
- **Theme excerpt** — relevant theme tokens (colors, spacing, component
  defaults) that affect this epic's screens
- **Feature list** — every feature with its What, Scope, and User stories
  as written in the PRD
- **Epic-specific details** — onboarding flow steps, paywall rules, etc.
- **Technical references** — which docs are relevant, which patterns or
  APIs from the docs this epic should use

Don't just copy the PRD section verbatim. Enrich it: connect the PRD's
product requirements with the technical context from the docs. The
decomposer needs to understand BOTH what to build and how it fits into
the overall architecture.

10. **Wire epic-level build dependencies.** The PRD orders epics in build
   order: feature epics first, onboarding second-to-last, paywall last.
   Wire dependencies to match this natural order:

   - Epic 001 (Foundation) has no deps — everything depends on it
   - Each feature epic depends on Foundation (and on prior feature epics
     if there's a real dependency)
   - Onboarding depends on the core feature epic(s) it onboards into
   - Paywall depends on Onboarding

   Use `tk dep` to wire these:
   ```bash
   tk dep [every-epic-id] [foundation-id]      # everything needs foundation
   tk dep [onboarding-id] [core-feature-id]    # can't onboard into what doesn't exist
   tk dep [paywall-id] [onboarding-id]         # paywall shows after onboarding
   ```

11. `<signal:completed>N epics created, deps wired</signal:completed>`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Read everything first | PRD + every doc. Don't create tickets until you've read all inputs |
| Synthesize, don't copy | Combine PRD content with doc context. The ticket should be richer than the PRD section alone |
| Self-contained tickets | The decompose stage reads the ticket, not the PRD or docs. The ticket must have everything |
| Features from PRD | Don't invent features. Don't remove features. Enrich them with technical context |
| 3-digit numbering | Always zero-pad: Epic 001, Epic 002, ..., Epic 099. Ensures correct sort |
| All at once | Create every epic in this stage. Don't leave any for later |
| No tasks | Only create epic tickets. Tasks come in the decompose stage |
| Order matters | Create in order: 001, 002, ... N |
| Build deps are mandatory | Wire `tk dep` between epics. PRD order = build order |
| Think about what wraps what | Onboarding wraps core features → depends on them. Paywall wraps onboarding → depends on it |
| Foundation is root | Every epic depends on Foundation |
