# Protocol: Web Research

Deep web exploration — editorial reviews, Reddit, blog roundups, user complaints. When you find notable apps not in the top charts, research them in depth.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — research written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Keywords**: `{{var:PILOT_KEYWORDS}}`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}`

## Execution

1. `<signal:update>researching: {{var:PILOT_KEYWORDS}}</signal:update>`
2. Run web searches. For each keyword, search for:
   - `best {keyword} apps 2025` / `best {keyword} apps 2026`
   - `{keyword} app reddit`
   - `{keyword} app comparison`
   - `{keyword} app review`
3. Read the top results. Collect features, pain points, trends.
4. **For each notable app you discover** — go deep:
   - Search for `"{app name}" app review`
   - Read the app's website or App Store page if available
   - Extract a full feature list — same detail level as if you'd seen the screenshots
   - Note what makes it different from mainstream competitors
5. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}` in the format below.
6. `<signal:completed>web research complete</signal:completed>`

## What to Look For

- **Apps not in top charts** — the most valuable find. Research each one in depth
- **Features across the category** — what do blogs/reviewers highlight as important?
- **User complaints** — what users hate (Reddit, app reviews). Direct quotes
- **Emerging trends** — new approaches, AI features, social mechanics
- **Retention patterns** — what keeps users, what causes churn

## Output Format

```markdown
# Web Research

> Keywords: ...
> Sources searched: N

## Notable Apps

For each app discovered that wasn't in the App Store top charts,
write a full profile:

### [App Name]

**What it is**: one sentence.
**Rating**: if known | **Notable**: why it stood out

**Features**:
- **Feature name** — what it does, how the user interacts with it
- **Feature name** — ...

**What makes it different**: 1-2 sentences on unique angle.

### [Next App]
...

## Additional Features

Features mentioned across reviews/blogs that aren't tied to one specific app.
Category-wide capabilities worth noting.

- **Feature name** — what it does, where it was mentioned

## User Pain Points

Common complaints across the category. Direct user quotes where possible.

- **Pain point** — what users complain about, how widespread

## Trends

Emerging patterns gaining traction in the category.

- **Trend** — what it is, where it's heading
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Go deep on new apps | Don't just list app names. Research each one — extract features with the same detail you'd want from screenshots |
| Source everything | Note where insights came from |
| Recency matters | Prefer 2025-2026 sources. Ignore anything older than 2 years |
| User voice | Direct user quotes from Reddit/reviews are valuable. Include them |
| No recommendations | Report what you find. PRD stage makes the decisions |
