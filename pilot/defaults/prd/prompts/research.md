# Protocol: Market Research

## Output Principles

This document will be consumed by an AI agent in the next pipeline stage, not a human.
Write for an agent that has zero prior context about this market or category.

- **Maximum detail.** Never abbreviate, never summarize to save tokens. Include
  every finding, every quote, every data point you discover. More detail is
  always better — downstream agents cannot ask follow-up questions.
- **Structured and navigable.** Use consistent headings, bullet formatting, and
  clear section boundaries. Every section must stand alone as a complete reference.
- **No implicit knowledge.** State everything explicitly. If a term has domain
  meaning, define it. If a conclusion follows from evidence, show the chain.
  Nothing is "obvious."
- **Source everything.** For every claim, note where it came from (subreddit,
  review, article, forum). The downstream agent needs to assess credibility.

Two-lens research: **demand-side** (what users want) and **supply-side** (what
competitors actually ship). Both are required. The goal is to shadow existing
apps — we need to understand demand AND know exactly what the market delivers.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — research written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Keywords**: `{{var:PILOT_KEYWORDS}}`
- **Competitor data** (if available): `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}`

## Execution

1. `<signal:update>researching market: {{var:PILOT_KEYWORDS}}</signal:update>`

2. **Read competitor data.** If `apps.json` exists, read it. Extract app names,
   IDs, descriptions, and `app_details.json` from each app folder (contains
   releaseNotes, pricing, version history). These are the top competitors —
   research them by name in addition to keyword searches.

3. **Demand-side research.** For each keyword:
   - `{keyword} app reddit` — what real users say
   - `{keyword} frustrated reddit` / `"switched from" {keyword} app`
   - `{keyword} app comparison` — what people weigh when choosing
   - `best {keyword} apps 2025` / `best {keyword} apps 2026`
   - `{keyword} app review`

4. **Read results with a demand lens.** For every source, extract:
   - What users say they WANT (explicit demand)
   - What users complain about (unmet demand)
   - What users praise (met demand — validated use case)
   - Why users switch apps (demand the old app failed to meet)

5. **Supply-side research.** For each top competitor (from apps.json + discovered):
   - `"{app name}" app features` — what the app ships
   - `"{app name}" app review` — detailed reviews from blogs/sites
   - `"{app name}" pricing` / `"{app name}" subscription` — exact pricing
   - `"{app name}" app update` / `"{app name}" what's new` — recent changes
   - Note their App Store description and releaseNotes from app_details.json

6. **For each competitor, build a supply-side profile:**
   - What they ship (feature inventory from reviews, articles, store description)
   - Navigation structure (tabs, flows) if reviewers or articles describe it
   - Pricing model: free tier, subscription tiers, exact prices, trial length
   - Recent updates: what they've been investing in (from What's New / articles)
   - What power users say about workflow and daily usage patterns

7. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}` in the format below.
8. `<signal:completed>web research complete</signal:completed>`

## What to Look For

**Demand side:**
- **What users want** — "I wish an app would...", "I need...", "looking for..."
- **What's broken** — "I hate that...", "why can't any app...", "I switched because..."
- **What works** — "I love that...", "finally an app that...", "this is why I pay for..."
- **What makes users stay** — retention signals, the moments that hook people
- **What makes users leave** — churn triggers, deal-breakers

**Supply side:**
- **What competitors ship** — complete feature sets, not just highlights
- **How competitors monetize** — exact pricing, trial lengths, what's free vs paid
- **What competitors invest in** — recent updates, new features, direction
- **How competitors structure** — navigation, flows, screens described by users/reviewers

## Output Format

```markdown
# Market Research

> Keywords: ...
> Sources searched: N
> Competitors profiled: N

## Part 1: Demand Signals

Group findings by what users want — each signal is a user need or job-to-be-done.
Order by strength of signal (how many sources, how passionately expressed).

### [User Need / Job-to-be-Done]

**What users say**: direct quotes from Reddit, reviews, forums.
Include 3-5 representative quotes that capture the demand.

**Evidence from competitors**: which apps address this need and how.

**Unmet demand**: what's still broken or missing. What users wish was better.

### [Next User Need]
...

## Part 2: Competitor Profiles

One section per top competitor. This is supply-side intelligence.

### [App Name]

**Positioning**: what the App Store description says (summarize key claims).

**Feature inventory**: every feature discoverable from reviews, articles, store
description, and user discussions. Group by category.

**Pricing**:
- Free tier: what's included
- Subscription: exact price(s), billing period(s), trial length
- What unlocks on subscribe
- Source of pricing info

**Recent updates** (from What's New / releaseNotes / articles):
- Version X.Y: what changed
- Version X.Z: what changed
- Direction: what are they investing in

**Navigation / structure**: how users describe the app's layout (tabs, screens,
flows) from reviews and articles. Include direct quotes if available.

**User verdict**: what loyal users say about daily usage patterns, workflow,
what keeps them. What churned users cite as reasons for leaving.

### [Next Competitor]
...

## Part 3: Pain Points

Frustrations that cut across the category. These aren't tied to one need —
they're universal complaints.

- **Pain point** — what users hate, direct quotes, how widespread

## Part 4: What Works

The moments users love. Evidence for what a good app in this category
feels like.

- **What works** — direct user language, which apps nail this

## Part 5: Pricing Landscape

Summary across all competitors:
- Dominant model (subscription / freemium / one-time)
- Price range
- Trial norms (length, with/without payment method)
- What's typically free vs. paid
- Any outlier approaches

## Part 6: Trends

Emerging patterns. New approaches gaining traction.

- **Trend** — what it is, what demand it responds to
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Two lenses | Both demand-side AND supply-side research are required |
| User voice | Direct quotes are the most valuable data. Collect ALL relevant quotes |
| Per-competitor profiles | Every top competitor gets a dedicated supply-side section |
| Pricing must be concrete | Exact numbers. "Premium subscription available" is not enough — find the price |
| Recent updates required | For each competitor, find What's New / changelog / recent articles |
| Source everything | Note where insights came from |
| Recency matters | Prefer 2025-2026 sources. Ignore anything older than 2 years |
| No recommendations | Report signals and facts. Downstream stages make the decisions |
