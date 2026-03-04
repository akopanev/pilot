# Protocol: Feature Baseline

Merge per-app feature extractions into a unified competitive baseline.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — baseline written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Per-app features**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/*/features.md`
- **App metadata**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`

## Execution

1. Read `apps.json` for the app list.
2. Read every `features.md` file (one per app folder).
3. `<signal:update>building baseline from N apps</signal:update>`
4. Normalize feature names across apps — same concept = same name.
5. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}` in the format below.
6. `<signal:completed>baseline: X features across N apps</signal:completed>`

## Output Format

```markdown
# Feature Baseline

> N competitors analyzed for keywords: ...

## Feature Matrix

| Feature | App1 | App2 | App3 | ... |
|:--------|:----:|:----:|:----:|:---:|
| Feature X | ✓ | ✓ | — | ... |
| Feature Y | — | ✓ | ✓ | ... |

Every unique feature across all apps gets a row.
Group rows by category (Tracking, Social, Gamification, etc.).

## Common Features
Features present in majority of apps. One line each.

## Differentiators
Features unique to one app. Format: **Feature** — App Name.

## Gaps
Notable features missing across all or most apps.
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Normalize names | "Streak tracking" not "streaks" vs "streak counter" — same concept, same row |
| No opinions | Matrix is factual. Present/absent, nothing else |
| No recommendations | This is a map of what exists, not what to build |
| Concise | Feature matrix is the core deliverable. Keep text sections brief |
