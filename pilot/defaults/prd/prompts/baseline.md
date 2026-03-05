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
5. **Identify core use cases first.** Before listing features, study the user
   sentiment (what users love and hate) and the feature landscape. Ask:
   "Why do people download apps in this category? What job are they hiring
   the app to do?" Distill this into 1-3 core use cases. These are the
   reasons the category exists — derived from user behavior, not feature counts.
6. Merge ALL features — from screenshot analysis AND web research — into one deduplicated list. Same concept = one entry.
7. **Tag every feature** as either `core` (directly serves a core use case)
   or `nice-to-have` (doesn't directly serve one). Base this on user sentiment,
   not prevalence. A feature in 5/5 apps that no user mentions caring about
   is still a nice-to-have.
8. Within each tag, order by prevalence — universal features first, niche last.
9. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}` in the format below.
10. `<signal:completed>baseline: X features (Y core, Z nice-to-have) from N apps</signal:completed>`

## Output Format

```markdown
# Feature Baseline

> Based on N competitor apps in [category].

## Core Use Cases

Why people download apps in this category. Derived from user sentiment
and behavior patterns — what users actually care about, not what
competitors decided to build.

1. **[Use case]** — one sentence. What job the user is hiring the app to do.
2. **[Use case]** — ...
3. **[Use case]** — ... (if applicable)

## Core Features

Features that directly serve the core use cases above.
Each feature is tagged with which use case it serves.
Ordered by prevalence within this group.

### [Category]

- **Feature name** `→ use case N` — what it does, how the user interacts with it. 2-3 sentences with enough detail for a PM to understand scope and expected behavior.

- **Feature name** `→ use case N` — ...

### [Category]

- ...

## Nice-to-Have Features

Features that exist across competitors but don't directly serve a core
use case. Common ≠ essential. Ordered by prevalence.

### [Category]

- **Feature name** — what it does. Why it's nice-to-have (e.g., "no user
  sentiment supports this", "engagement mechanic, not core job").

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
| Use cases from sentiment | Core use cases come from what users say, not from feature prevalence |
| Tag honestly | A feature in every app is still nice-to-have if no user cares about it |
| Describe, don't prescribe | Describe what the feature does. Don't recommend whether to build it |
| Enough detail | A PM reading this should understand the feature's scope without seeing the apps |
| Order by prevalence | Universal features first, rare/niche features last within each category |
