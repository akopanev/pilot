# Protocol: PRD Generation

Write a PRD based on the feature baseline and user brief. Shadow strategy — replicate what top competitors ship.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — PRD written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Feature baseline**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`
- **User brief**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_BRIEF}}`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`

## Execution

1. Read the feature baseline.
2. Read the user brief.
3. `<signal:update>writing PRD</signal:update>`
4. Write the PRD to `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}` in the format below.
5. `<signal:completed>PRD written</signal:completed>`

## Output Format

```markdown
# PRD: [Product Name]

## Overview
One paragraph. What this app is, who it's for, what it does.
Derived from the brief.

## Strategy
Shadow — replicate proven features from top competitors. Ship fast,
validate CAC. Differentiate later if unit economics work.

## MVP Features

Features for v1. If most competitors have it — it's in.

For each feature:

### F[N]: Feature Name
- **What**: what it does from the user's perspective. 2-3 sentences.
- **Why MVP**: why this is in v1 (e.g., "all competitors have it",
  "core to the value proposition", "needed for retention loop")
- **Scope**: concrete boundaries — what's included, what's explicitly not.
  Enough detail for an engineer to estimate and build.

## Deferred (v1.1+)

Features from the baseline that are NOT in MVP, with reason.

- **Feature name** — reason for deferral (e.g., "only 1 of 5 competitors
  has it", "requires watch app extension", "nice-to-have, not core")

## Navigation
Recommended app structure based on competitor patterns from the baseline.
Tab bar layout, main sections, key user flows.

## Open Questions
Decisions that need human input before development starts.
```

## Decision Rules for MVP Cut

| Rule | Guidance |
|:-----|:---------|
| Most competitors have it | MVP — this is table stakes |
| Half have it | MVP if it's simple, defer if it requires a separate target (watch, widget) |
| Few competitors have it | Defer unless the brief explicitly calls for it |
| Brief explicitly wants it | MVP regardless of competitor prevalence |
| Requires separate build target | Defer (watch app, widgets, extensions) unless ALL competitors have it |
| Core retention loop | MVP — daily engagement features (streaks, goals, progress) are critical for CAC |

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Brief is truth | If brief and baseline conflict, brief wins |
| Shadow, don't innovate | Don't invent new features. Replicate what's proven |
| Scope each feature | Every MVP feature needs concrete scope. "Add social features" is not scope |
| Be decisive | Make the call on every feature. In or out, with rationale |
| Human reviews | This PRD will be reviewed and edited. Make it easy to move features between MVP and deferred |
