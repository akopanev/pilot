# Protocol: Competitor Evidence Extraction

Extract the most complete app-level evidence possible from competitor screenshots,
metadata, and reviews. Your job is not to write a category synthesis yet. Preserve
what is clearly observed, what is strongly inferred, and what is only a standard
supporting assumption.

## Output Principles

Each `features.md` file will be consumed by downstream agents building a parity-first
PRD. Write for an agent with zero prior context about this app.

- **Preserve evidence tiers.** Separate `observed`, `supported inference`, and
  `default assumption`. Do not collapse them into one confident feature list.
- **Maximum detail.** Describe every visible screen, feature, state, CTA, metric,
  navigation clue, and monetization clue. Never skip something because it seems minor.
- **Include production-grade support flows.** If a feature implies create/edit/delete,
  settings, restore purchases, retry, empty/loading/error states, or permissions,
  call that out explicitly as observed, inferred, or assumed.
- **Be concrete.** Name tabs, labels, visible data, actions, and state transitions.
- **Be honest about uncertainty.** If screenshots are incomplete, say exactly what is
  missing and what fallback assumption a downstream PRD agent should use.

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
2. `<signal:update>extracting evidence from N apps</signal:update>`
3. **For each app, launch a Task agent in parallel.** Use the Task tool — one call per app, ALL in a single message so they run concurrently. Each agent:
   - Receives the app metadata (title, subtitle, description) and screenshot paths
   - Receives the path to `reviews.json` in the app's folder (if it exists)
   - Receives the path to `app_details.json` in the app's folder (if it exists) — contains What's New (releaseNotes), pricing, version, rating
   - MUST open every screenshot
   - MUST read reviews.json for user sentiment
   - MUST read app_details.json for pricing, What's New, and version data
   - Writes `features.md` into the app's folder
   - Returns confirmation
4. Verify each `features.md` was written.
5. `<signal:completed>N apps analyzed</signal:completed>`

## Per-App Agent Prompt

Give each Task agent a prompt like this (fill in the actual data):

```text
Extract competitor evidence from this app. Research task only — write ONLY the output file specified below.

App: {title}
Subtitle: {subtitle}
Description: {description}

Screenshots (open EVERY one — do not skip any):
{list each absolute path from screenshots_local}

Reviews: {app_folder}/reviews.json
(Read this file — it contains recent user reviews with ratings and text.)

App Details: {app_folder}/app_details.json
(Read this file — it contains What's New / releaseNotes, pricing, version, ratings.)

## Process

1. Read the title, subtitle, and description. Note promised features and positioning.
2. Open EVERY screenshot. Study each one carefully.
3. Read reviews.json. Note what users praise, complain about, and mention repeatedly.
4. Read app_details.json. Extract: releaseNotes (What's New), pricing (price, formattedPrice),
   version, averageUserRating, userRatingCount. This is hard data — use it.
5. Build an evidence file that separates:
   - what is directly visible or explicit
   - what is strongly implied by the visible evidence
   - what is a standard supporting assumption needed to make the visible product work
5. Write the result to: {app_folder}/features.md

## Output format

# {title}

## App Snapshot

- **Store positioning** — what the app claims to do in subtitle/description
- **Business model** — free / freemium / subscription, with concrete pricing from app_details.json
- **Rating** — averageUserRating and userRatingCount from app_details.json
- **Evidence completeness** — high / medium / low with one-sentence reason

## Observed Screens And Flows

List each clearly visible screen or major UI state.

- **[Screen or flow name]** — what is visible, what the user can do, what data or controls appear, and what this implies about the flow direction. Include tab bars, headers, segmented controls, CTAs, progress indicators, cards, list items, badges, metrics, charts, and visible state transitions.

## Observed Features

- **Feature name** — directly visible behavior or explicit store claim. Include interaction details, visible states, and any monetization, notification, or personalization clues.

## Supported Inferences

- **Feature or supporting flow** — not directly shown end-to-end, but strongly implied by screenshots, reviews, or store copy. Explain the evidence chain.

Examples:
- edit/delete for visible list items
- detail screens behind visible cards
- notification scheduling behind reminder toggles
- restore purchases for subscription products
- account/settings surfaces for personalization-heavy apps

## Default Assumptions For Parity

- **Assumption** — a standard production behavior likely needed if someone clones this app from the available evidence. Explain why it is assumed and what confidence level to use.

Only include assumptions that materially help downstream implementation:
- loading/empty/error states
- retry and offline fallback where data is fetched
- settings and preference management for visible personalization
- permission prompts for visible reminder/health/location features
- paywall support flows such as restore purchases / manage subscription

## Navigation Evidence

- **Primary navigation** — observed tabs/sections if visible
- **Secondary navigation** — drill-down, segmented control, modals, sheets, swipe, wizard flow
- **Likely app structure** — tab bar / stack only / mixed, with confidence and evidence

## Pricing And Monetization Evidence

- **App Store price** — from app_details.json: formattedPrice, price, currency
- **Business model** — free with IAP / subscription / one-time purchase / freemium, with evidence
- **Subscription tiers** — if discoverable from screenshots, reviews, or store description: tier names, prices, billing periods
- **Trial** — length, with/without payment method required, evidence source
- **What's free** — which features work without paying
- **What's paywalled** — which features require subscription
- **Paywall placement** — where/when the paywall appears (onboarding, feature gate, usage limit)
- **Paywall UX** — offer framing, skip/close visibility, restore purchases
- **Onboarding observed** — steps shown, questions asked, progression style
- **Permissions observed or implied** — notifications, health, camera, location, etc.

## What's New / Recent Investment

From app_details.json releaseNotes and version data:
- **Current version** — version number and release date
- **What's New text** — full releaseNotes content
- **Investment signals** — what the team is actively working on based on release notes

## User Sentiment

- **What users love** — top themes, using actual user language where possible
- **What users hate** — top themes, using actual user language where possible
- **Why users churn or switch** — if visible from reviews

## Missing Evidence And Fallbacks

- **Unknown** — what cannot be determined from available inputs
- **Best fallback assumption** — what a parity-first PRD writer should assume unless human input says otherwise
- **Materiality** — high / medium / low impact on build scope
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Every screenshot | Agents MUST open every image. Do not skip any |
| All parallel | Launch ALL agents in one message |
| Preserve uncertainty | Separate observed, inferred, and assumed. Never blur them |
| Parity-first | Fill implementation-critical gaps with standard competitor defaults, but label them honestly |
| Facts first | Do not recommend what to build yet. Preserve evidence for downstream stages |
| Write to file | Each agent writes `features.md` in the app's folder |
