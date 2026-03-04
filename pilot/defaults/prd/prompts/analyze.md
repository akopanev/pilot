# Protocol: Competitor Analysis

Analyze competitor apps — screenshots and metadata — to build a feature baseline.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — findings written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Config dir**: `{{var:PILOT_CONFIG_DIR}}`
- **Competitor data**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json`
- **Screenshots**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/<app-slug>/screenshot_*.jpg`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`

## Execution

1. Read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json`. Parse the app list.
2. `<signal:update>analyzing N competitors in parallel</signal:update>`
3. **For each app, launch a Task agent in parallel.** Use the Task tool — one call per app, all in a single message so they run concurrently. Each agent receives:
   - The app's metadata (title, subtitle, description, rating, categories, features)
   - Instruction to open EVERY screenshot listed in `screenshots_local` using the Read tool (Read can display images)
   - Instruction to return a structured analysis (see format below)

4. Collect all agent results.
5. Synthesize into `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}` (see output format below).
6. `<signal:completed>N competitors analyzed, findings written</signal:completed>`

## Per-App Agent Prompt

Give each Task agent a prompt like this (fill in the actual data):

```
Analyze this competitor app. You MUST open and examine EVERY screenshot.

App: {title}
Rating: {rating} | Categories: {categories}
Subtitle: {subtitle}
Description: {description}
Listed features: {features}

Screenshots (open ALL of them with the Read tool):
{list each path from screenshots_local}

After examining every screenshot, return your analysis in this exact format:

## {title}

**Overview**: One sentence — what this app does and who it's for.
**Rating**: {rating} | **Category position**: {categories}

### Features Observed
For each distinct feature you can identify from screenshots + metadata:
- **Feature name** — what it does. (Source: screenshot N / metadata / description)

### UI/UX Patterns
- Navigation pattern (tab bar, sidebar, etc.)
- Visual style (minimal, colorful, dark, etc.)
- Key interactions visible in screenshots

### Strengths
Bullet list — what this app does well.

### Weaknesses
Bullet list — gaps, missing features, or poor UX visible in screenshots.
```

## Output Format for {{var:PILOT_FINDINGS}}

```markdown
# Competitor Analysis Findings

> N competitors analyzed for keywords: ...

## Per-App Analysis

{paste each agent's analysis here, in order}

## Feature Matrix

| Feature | App1 | App2 | App3 | ... |
|:--------|:----:|:----:|:----:|:---:|
| Feature X | ✓ | ✓ | — | ... |
| Feature Y | — | ✓ | ✓ | ... |

Build this matrix from the per-app feature lists. Every unique feature
observed across all apps gets a row.

## Key Patterns

- Common features (present in 3+ apps)
- Differentiators (unique to one app)
- Gaps (missing across all or most apps)
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Every screenshot matters | Agents MUST open every image. Features are in the screenshots, not just metadata |
| Parallel execution | Launch ALL app agents in a single message — do not analyze sequentially |
| Observable features only | Only list features you can see in screenshots or read in metadata. No guessing |
| Consistent naming | Use the same feature name across apps (e.g. "streak tracking", not "streaks" vs "streak counter") |
| No recommendations | This is analysis, not prescription. Report what exists. Do not suggest what to build |
