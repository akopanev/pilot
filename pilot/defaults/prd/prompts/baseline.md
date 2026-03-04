# Protocol: Feature Baseline

Merge per-app feature extractions into a unified feature baseline for a PM writing a PRD.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — baseline written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Per-app features**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/*/features.md`
- **Web research**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}`
- **App metadata**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`

## Execution

1. Read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json` for the app list.
2. Read every `features.md` file (one per app folder).
3. Read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}` — includes features from apps not in top charts.
4. `<signal:update>building baseline from N apps + web research</signal:update>`
5. Merge ALL features — from screenshot analysis AND web research — into one deduplicated list. Same concept = one entry.
5. Order by how common the feature is — universal features first, niche features last.
6. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}` in the format below.
7. `<signal:completed>baseline: X features from N apps</signal:completed>`

## Output Format

```markdown
# Feature Baseline

> Based on N competitor apps in [category].

## Features

Unified, deduplicated feature list across all analyzed competitors.
Ordered by prevalence — features found in most apps first.

### [Category]

- **Feature name** — what it does, how the user interacts with it. 2-3 sentences with enough detail for a PM to understand scope and expected behavior.

- **Feature name** — ...

### [Category]

- ...

## Navigation Patterns

Common navigation and information architecture patterns observed across apps.

## Onboarding Patterns

Common onboarding flows observed. What information is typically collected,
what choices users make on first run.

## User Sentiment

Common themes from user reviews across all apps.
- What users consistently love (top 3-5 themes)
- What users consistently hate (top 3-5 themes)

Use actual user language where possible. No app names.
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| No app names | This is a category baseline, not a comparison. Don't mention which app has what |
| Normalize | Same concept = one entry. "Streak tracking" not "streaks" vs "streak counter" |
| Describe, don't prescribe | Describe what the feature does. Don't recommend whether to build it |
| Enough detail | A PM reading this should understand the feature's scope without seeing the apps |
| Order by prevalence | Universal features first, rare/niche features last within each category |
