# Protocol: Feature Extraction

Extract features from competitor app screenshots. One agent per app, all in parallel.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — extraction done
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Competitor data**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json`

## Output

Per-app files: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/<app-slug>/features.md`

## Execution

1. Read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json`. Parse the app list.
2. `<signal:update>extracting features from N apps</signal:update>`
3. **For each app, launch a Task agent in parallel.** Use the Task tool — one call per app, ALL in a single message so they run concurrently. Each agent:
   - Receives the app metadata (title, subtitle, description) and screenshot paths
   - Receives the path to `reviews.json` in the app's folder (if it exists)
   - MUST open every screenshot with the Read tool
   - MUST read reviews.json for user sentiment
   - Writes `features.md` into the app's folder
   - Returns confirmation

4. Verify each `features.md` was written.
5. `<signal:completed>N apps analyzed</signal:completed>`

## Per-App Agent Prompt

Give each Task agent a prompt like this (fill in the actual data):

```
Extract features from this app. Research task only — write ONLY the output file specified below.

App: {title}
Subtitle: {subtitle}
Description: {description}

Screenshots (open EVERY one with the Read tool — do not skip any):
{list each absolute path from screenshots_local}

Reviews: {app_folder}/reviews.json
(Read this file — it contains recent user reviews with ratings and text.)

## Process

1. Read the title, subtitle, and description. Note features mentioned.
2. Open EVERY screenshot. Study each one carefully.
3. Read reviews.json. Note what users praise and complain about.
4. Build a complete feature list from everything you observed.
5. Order features by importance — core features first, secondary features after.
6. Write the result to: {app_folder}/features.md

## Output format

# {title}

## Features

Ordered by importance. Core value proposition first, then supporting features.

- **Feature name** — what it does, how the user interacts with it
- **Feature name** — ...
- ...

Group under subheadings only if there are natural categories
(e.g., ## Tracking, ## Social). Do not force categories.

## Navigation

- Primary navigation (tab bar, sidebar, etc.) — list tab/section names
- Secondary navigation (segmented controls, drill-down, swipe, etc.)

## Onboarding

If onboarding/welcome/first-run screens are visible:
- Steps shown and information collected

If none visible, write: "Not visible in screenshots."

## User Sentiment

From reviews — what do users love and hate about this app?
Top 3-5 praises and top 3-5 complaints. Use actual user language.
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Every screenshot | Agents MUST open every image. Do not skip any |
| All parallel | Launch ALL agents in one message |
| Facts only | What the app does. No opinions, no strengths/weaknesses |
| Prioritize | Order features by importance, not by screenshot order |
| Concise | One line per feature. Name + what it does. No source citations needed |
| Write to file | Each agent writes `features.md` in the app's folder |
