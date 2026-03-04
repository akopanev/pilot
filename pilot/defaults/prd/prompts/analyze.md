# Protocol: PRD Generation

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — PRD written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

1. **User brief**: `{{var:PILOT_BRIEF}}`
2. **Competitor data**: `data/competitors/apps.json` + screenshot images in subdirectories
3. **Output path**: `{{var:PILOT_PRD_OUTPUT}}`

## Steps

1. Read the user brief: `cat {{var:PILOT_BRIEF}}`
2. Read competitor data: `cat data/competitors/apps.json`
3. Look at competitor screenshots in `data/competitors/*/` — open each image.
   Note UI patterns, features, design language.
4. `<signal:update>analyzing competitors and brief</signal:update>`
5. **Write the PRD** to `{{var:PILOT_PRD_OUTPUT}}`. Structure:

```
# PRD: <Product Name>

## Vision
One paragraph. What is this product and why does it exist.

## Target User
Who. Be specific — demographics, behavior, pain points.

## Competitive Landscape
For each competitor analyzed:
- Name, app store position, rating
- Key features (what they do well)
- Gaps (what they miss or do poorly)
- UI/UX observations from screenshots

## Feature List
Numbered list. Each feature:
- **F1: Feature Name** — one-line description
  - Priority: must-have | should-have | nice-to-have
  - Rationale: why this feature (from brief, competitive gap, or user need)

## Non-Goals
What this product explicitly does NOT do in v1.

## Open Questions
Decisions the user needs to make before planning begins.
```

6. `<signal:completed>PRD written to {{var:PILOT_PRD_OUTPUT}}</signal:completed>`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Brief is truth | The user brief defines the product. Competitors inform, not dictate |
| No scope creep | Don't add features just because competitors have them. Only if it serves the brief |
| Be specific | "Good UX" is not a feature. "Swipe to complete habit with haptic feedback" is |
| Prioritize | Must-have = launch blocker. Should-have = v1.1. Nice-to-have = backlog |
| Screenshots matter | Note specific UI patterns worth adopting or avoiding. Reference by competitor name |
