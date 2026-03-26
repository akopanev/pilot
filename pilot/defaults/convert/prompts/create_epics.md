# Protocol: Create Conversion Epics

Read the analysis and codebook. Think about how to break this conversion
into epics. You've seen the code (via the analysis) — use that knowledge
to make smart grouping decisions.

The conversion must go **layer-first**: data models and pure business logic
before UI. But within that constraint, you decide the exact breakdown.
Group things that belong together. Split things that are too big.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — all epics created
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Analysis**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_ANALYSIS}}`
- **Codebook**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK}}`
- **Inventory**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_INVENTORY}}`
- **iOS source**: `{{var:PILOT_IOS_DIR}}/` (read files as needed to verify your understanding)

## Execution

1. Read the analysis and codebook thoroughly.
2. `<signal:update>planning conversion epics</signal:update>`
3. **Think about the breakdown.** The analysis tells you what's in the app
   and how it's structured. The codebook tells you the conversion order.
   Now decide: how many epics? What goes in each? Consider:
   - The layer-first order: models → networking → services → persistence
     → state management → UI → integration
   - Natural groupings in the code (domain boundaries, feature modules)
   - Size — each epic should decompose into 3-10 tasks
   - Dependencies — can epic N start without epic N-1 being done?
   - The analysis's complexity ratings — keep complex stuff in focused epics

   **Typical structure** (adapt to what you see in the code):
   - Epic 001: Foundation — Flutter project setup, deps, theme, routing skeleton
   - Epic 002+: Data layer epics (models, DTOs, enums — pure Dart)
   - Epic N: Networking / API layer
   - Epic N+1: Services & business logic
   - Epic N+2: Persistence
   - Epic N+3: State management
   - Epic N+4+: UI epics (one per feature area or screen group)
   - Final epic: Integration & wiring

   But don't follow this blindly. If the app has 5 models, one epic is
   fine. If it has 200 models across 8 domains, split into multiple epics.
   Look at the code and decide.

4. For each epic, read the relevant iOS source files if you need to
   verify your understanding. Don't create an epic based on file names
   alone — understand what the code does.

5. Create tickets:

```bash
tk create "Epic 001: [Name]" \
  -d "[description]" \
  -t epic
```

6. **Epic description format** — the decompose stage reads ONLY this
   ticket, so it must be self-contained:

   - **Goal** — what this epic converts, why it's at this position in
     the order
   - **iOS source files** — the specific files to convert (paths)
   - **Target location** — where Dart files go (from codebook structure)
   - **Relevant codebook sections** — which mappings and patterns apply
   - **Dependencies** — what from prior epics this epic builds on
   - **Complexity notes** — what's straightforward, what needs care.
     Include your observations from reading the code
   - **What to skip** — deprecated code, test files, platform-specific
     features that need platform channels

   Don't just copy the analysis into the ticket. Synthesize — the
   decompose agent needs actionable context, not a data dump.

7. Wire build dependencies:

```bash
tk dep [epic-002-id] [epic-001-id]    # everything needs foundation
tk dep [epic-003-id] [epic-002-id]    # later layers need earlier ones
# ... wire the chain
```

8. Push to remote (this pipeline runs remotely):
   ```bash
   git add .tickets/ && git commit -m "convert: epic tickets created" --quiet
   git push
   ```
9. `<signal:completed>N epics created, deps wired</signal:completed>`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Layer-first always | Models → services → UI. Business logic before pixels. This is non-negotiable |
| Read before creating | If unsure about a grouping, read the source files. Verify your understanding |
| Think about size | Each epic = 3-10 tasks. Too big → split. Too small → merge |
| Self-contained tickets | Decompose stage reads ONLY the ticket. Include everything it needs |
| Specific file lists | Every epic must list the iOS source files it covers |
| 3-digit numbering | Epic 001, Epic 002, ... |
| Wire deps | Foundation first. Each layer depends on the one before it |
| Pure Dart first | Early epics should produce pure Dart with no Flutter dependency |
| No invention | Convert what exists in the iOS app |
| Use your judgment | The analysis gives you context. The codebook gives you patterns. YOU decide the plan |
