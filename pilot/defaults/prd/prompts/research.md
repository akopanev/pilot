# Protocol: Web Research

Deep web exploration for additional insights beyond App Store data. Search for editorial reviews, Reddit discussions, blog roundups, and user complaints about existing apps.

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
3. Run web searches. For each keyword, search for:
   - `best {keyword} apps 2025` / `best {keyword} apps 2026`
   - `{keyword} app reddit`
   - `{keyword} app comparison`
   - `{keyword} app review`
4. Read the top results. Extract insights not already in the baseline.
5. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}` in the format below.
6. `<signal:completed>web research complete</signal:completed>`

## What to Look For

- **Features the baseline missed** — apps or features not in the top charts but mentioned in reviews
- **User complaints** — what users hate about existing apps (Reddit, app reviews). These are opportunities
- **Emerging trends** — new approaches, AI features, social mechanics not yet mainstream
- **Monetization insights** — what pricing works, what users complain about paying for
- **Retention patterns** — what keeps users coming back, what causes churn

## Output Format

```markdown
# Web Research

> Keywords: ...
> Sources searched: N

## Features Not in Baseline

Features mentioned in reviews/discussions that the baseline didn't capture.

- **Feature name** — what it does, where it was mentioned

## User Pain Points

Common complaints and frustrations users have with existing apps.

- **Pain point** — what users complain about, how common it seems

## Trends

Emerging patterns or approaches gaining traction.

- **Trend** — what it is, where it's heading

## Notable Apps Not in Top Charts

Apps mentioned in reviews/Reddit that didn't appear in the App Store top results.

- **App name** — why it's notable, what it does differently
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Independent | This runs before screenshot analysis. Report everything you find |
| Source everything | Note where insights came from (Reddit, blog name, etc.) |
| Recency matters | Prefer 2025-2026 sources. Ignore anything older than 2 years |
| User voice | Direct user quotes from Reddit/reviews are gold. Include them |
| No recommendations | Report what you find. PRD stage makes the decisions |
