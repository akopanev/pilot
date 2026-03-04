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
   - Receives the app metadata and screenshot paths
   - MUST open every screenshot with the Read tool
   - Writes `features.md` into the app's folder
   - Returns confirmation

4. Verify each `features.md` was written.
5. `<signal:completed>N apps analyzed</signal:completed>`

## Per-App Agent Prompt

Give each Task agent a prompt like this (fill in the actual data):

```
Extract features from this app by examining its screenshots and metadata. Research task only — do NOT edit or create any files other than the output file specified below.

App: {title}
Subtitle: {subtitle}
Description: {description}

Screenshots (open EVERY one with the Read tool — do not skip any):
{list each absolute path from screenshots_local}

First, read the title, subtitle, and description — note any features mentioned.
Then open each screenshot. For each one, describe what screen it shows and
list every feature visible. Then write the results to:
{app_folder}/features.md

Use this exact format:

# {title}

## Screen-by-Screen

For each screenshot, in order:

### Screenshot N
- **Screen**: what this screen is (e.g., "Main dashboard", "Settings", "Workout in progress")
- **Features visible**:
  - Feature name — what it does, what UI element represents it
  - Feature name — ...

### Screenshot N+1
...

## Features

Deduplicated list of all features found across screenshots, title, subtitle, and description.
Group by category (e.g., Tracking, Social, Gamification, Settings).

- **Feature name** — one sentence description (source: screenshot N / description / subtitle)
- **Feature name** — one sentence description (source: screenshots N, M)

## Navigation
- Primary navigation pattern (tab bar, sidebar, hamburger, etc.)
- Tab/section names and count
- Secondary navigation (segmented controls, drill-down, etc.)

## Onboarding
If any screenshot shows onboarding, first-run, or welcome screens:
- What steps are shown
- What information is collected
- What choices the user makes

If no onboarding screens are visible, write: "No onboarding screens visible."
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Every screenshot | Agents MUST open every image. Do not skip. Do not summarize without looking |
| All parallel | Launch ALL agents in one message |
| Screen-by-screen first | Describe each screenshot individually before deduplicating into the features list |
| Facts only | Report what you see. No opinions, no judgments, no recommendations |
| Cite screenshots | Every feature must reference which screenshot(s) it appears in |
| Write to file | Each agent writes `features.md` in the app's folder |
