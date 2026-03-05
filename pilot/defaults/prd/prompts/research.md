# Protocol: Web Research

Demand-side research — understand what users WANT, what jobs they're hiring
apps for, what's broken, what works. Competitor features are evidence of
demand, not the goal. Organize findings by user need, not by app.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — research written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Keywords**: `{{var:PILOT_KEYWORDS}}`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}`

## Execution

1. `<signal:update>researching demand: {{var:PILOT_KEYWORDS}}</signal:update>`
2. **Search for user voice first.** For each keyword:
   - `{keyword} app reddit` — what real users say
   - `{keyword} frustrated reddit` / `"switched from" {keyword} app`
   - `{keyword} app comparison` — what people weigh when choosing
   - `best {keyword} apps 2025` / `best {keyword} apps 2026`
   - `{keyword} app review`
3. **Read results with a demand lens.** For every source, extract:
   - What users say they WANT (explicit demand)
   - What users complain about (unmet demand)
   - What users praise (met demand — validated use case)
   - Why users switch apps (demand the old app failed to meet)
4. **For notable apps discovered** — research them, but through the demand
   lens. Don't just list features. Ask: what demand does this app serve
   that others don't? What do its users specifically love/hate?
5. **Group everything by demand signal**, not by app. See output format.
6. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}` in the format below.
7. `<signal:completed>web research complete</signal:completed>`

## What to Look For

- **What users want** — "I wish an app would...", "I need...", "looking for..."
- **What's broken** — "I hate that...", "why can't any app...", "I switched because..."
- **What works** — "I love that...", "finally an app that...", "this is why I pay for..."
- **What competitors ship** — features across the category, as evidence of validated demand
- **What makes users stay** — retention signals, the moments that hook people
- **What makes users leave** — churn triggers, deal-breakers

## Output Format

```markdown
# Web Research

> Keywords: ...
> Sources searched: N

## Demand Signals

Group findings by what users want — each signal is a user need or job-to-be-done.
Order by strength of signal (how many sources, how passionately expressed).

### [User Need / Job-to-be-Done]

**What users say**: direct quotes from Reddit, reviews, forums.
Include 3-5 representative quotes that capture the demand.

**Evidence from competitors**: which apps address this need and how.
Brief — app name + approach, not full feature lists.

**Unmet demand**: what's still broken or missing. What users wish was better.

### [Next User Need]
...

## Pain Points

Frustrations that cut across the category. These aren't tied to one need —
they're universal complaints.

- **Pain point** — what users hate, direct quotes, how widespread

## What Works

The moments users love. Evidence for what a good app in this category
feels like.

- **What works** — direct user language, which apps nail this

## Notable Apps

Apps discovered outside the top charts that are worth knowing about.
Keep this brief — the demand signals above are the primary output.

### [App Name]
**What it is**: one sentence.
**Why it's notable**: what demand it serves differently.
**Key features**: only the ones relevant to demands identified above.

## Trends

Emerging patterns. New approaches gaining traction.

- **Trend** — what it is, what demand it responds to
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Demand first | Organize by user need, not by app. Apps are evidence |
| User voice | Direct quotes are the most valuable data. Collect as many as possible |
| Competitor features = demand signal | "5/5 apps have X" means the market validated demand for X. Note it as evidence |
| Source everything | Note where insights came from |
| Recency matters | Prefer 2025-2026 sources. Ignore anything older than 2 years |
| Go deep on new apps | When you find a notable app, research it — but through the demand lens |
| No recommendations | Report demand signals. Downstream stages make the decisions |
