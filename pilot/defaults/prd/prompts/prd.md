# Protocol: PRD Generation

Write a PRD based on the feature baseline, web research, and optionally a user brief.
Shadow strategy — replicate what top competitors ship. Structure output as plannable epics.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — PRD written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Feature baseline**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`
- **Web research**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}`
- **User brief** (optional): `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_BRIEF}}`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`

## Execution

1. Read the feature baseline.
2. Read the web research.
3. Try to read the user brief. If the file doesn't exist or is empty, proceed
   without it — derive product context from the baseline and research instead.
4. `<signal:update>writing PRD</signal:update>`
5. Write the PRD to `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}` in the format below.
6. `<signal:completed>PRD written</signal:completed>`

---

## Hard Constraints

These are non-negotiable structural requirements. Every PRD must have them,
in this order:

1. **Epic 1 is always Foundation.** Project scaffolding, core data models,
   base navigation shell, localization infrastructure, and any setup that
   all feature epics depend on. This is a **technical-only** epic — no
   user-facing screens, no UI features, no settings editors, no forms.
   Just the skeleton: project init, shared types/models, empty navigation
   tabs, i18n wiring, auth skeleton. If a user can interact with it
   beyond navigating between empty tabs, it belongs in a feature epic.
   Derive its scope from what the feature epics need.

2. **Feature epics come next.** All product features are grouped into
   epics ordered by impact on the core use cases. Each epic is a plannable
   unit — a set of related features that ship together. No flat feature
   lists. Every feature belongs to exactly one epic.

3. **Second-to-last epic is always Onboarding.** The first 30 seconds of
   the product are the primary driver for retention and word-of-mouth.
   Design the product from the onboarding experience outward. Onboarding
   comes after feature epics because you build the product first, then the
   entrance into it. See [Onboarding Principles](#onboarding-principles).

4. **Last epic is always Monetization Gate (Paywall).** Immediately after
   onboarding, present a paywall with a prominent skip button. The user has
   just experienced the aha moment — this is the highest-intent conversion
   point. The skip button is mandatory: never block users from entering the
   product. Paywall is last because it wraps onboarding.

5. **App only. No extensions.** The PRD covers the main app and nothing
   else. Automatically defer any feature that requires a separate build
   target: Apple Watch apps, widgets, iMessage extensions, Siri intents,
   Safari extensions, App Clips, or any other extension point. These are
   out of scope for MVP — no exceptions, even if every competitor has them.

6. **React Native, cross-platform.** The app is built with React Native
   targeting both iOS and Android from a single codebase. All features must
   be designed for cross-platform compatibility. No platform-specific APIs
   unless wrapped with a cross-platform abstraction. Native modules are
   acceptable only when no React Native equivalent exists.

7. **Localization from day one.** All user-facing strings must be
   localizable from the start. MVP ships with: {{var:PILOT_LANGUAGES}}.
   This is a hard requirement — not a v1.1 item. The PRD should note
   this in the Overview or as a cross-cutting concern so engineers build
   with localization infrastructure from the first commit.

---

## Onboarding Principles

Apply these when writing the Onboarding epic. They are not optional.

- **Make the first 30 seconds magical.** Invest disproportionately in the
  first moments. This is the primary driver for word-of-mouth growth.
- **Action, not explanation.** Users learn by doing. No carousels, no
  tooltip tours, no "welcome to the app" screens. Get users into the core
  experience immediately.
- **Remove every blocker to the aha moment.** Every screen between signup
  and value is a potential drop-off. Cut steps that don't earn their place.
  But note: more screens is not the problem — friction is. **10+ onboarding
  screens is totally fine** as long as each one is fast, purposeful, and
  moves the user forward. Short, focused screens (one question each, big
  tap targets) convert better than fewer screens crammed with fields.
  Focus your detail on the KEY screens — the ones that deliver aha moments
  or collect inputs critical to personalization.
- **Design like a game tutorial.** Progressive disclosure — teach by letting
  the user do, not by telling. Reward early actions.
- **Request permissions in context.** Never ask for notifications, health,
  or location on a cold screen. Ask when the user does something that needs it.
- **Time to value < 30 seconds.** The user must do something meaningful
  (not just view something) within the first 30 seconds.

---

## Output Format

```markdown
# PRD: [Product Name]

## Overview
One paragraph. What this app is, who it's for, what it does.
Derived from the brief if available, otherwise from baseline + research.

**Core use cases** (1-3):
1. [The primary thing users come to this app to do]
2. [The second thing, if any]
3. [The third thing, if any]

Every MVP feature must trace back to one of these. If it doesn't, defer it.

## Strategy
Shadow — replicate proven features from top competitors. Ship fast,
validate CAC. Differentiate later if unit economics work.

## Target User
Who this is for. Demographics, behavior, motivation.
Keep it concrete — one paragraph.

---

## Epic 1: Foundation

**Goal**: Technical scaffolding only. No user-facing features.

- **Project setup**: tooling, directory structure, CI/CD skeleton.
  pnpm with `node-linker=hoisted` in `.npmrc` (required for React Native
  + CocoaPods compatibility)
- **Core data models**: shared types and entities (TypeScript types, DB schema)
- **Base navigation**: tab bar / router shell with **empty placeholder screens**
- **Localization infrastructure**: i18n setup, string extraction pipeline,
  Foundation-only strings (tab labels, common actions)
- **Auth skeleton**: sign-up / sign-in flow if applicable
- **Theme setup**: design tokens, provider, light/dark mode

**NOT in Foundation**: settings UI, profile editors, forms, toggles,
pickers, save flows, or any screen where a user does something beyond
seeing a placeholder. Those belong in feature epics.

Keep this minimal — only what's needed for the first feature epic to start.

---

## Epic 2: [Epic Name]

**Goal**: what user outcome this epic delivers AND why it matters for
retention or the core use case. Not "add history" — instead "Users
understand whether they're on track, and the streak mechanic creates
a daily reason to return."

### Features

#### F1: Feature Name
- **What**: what it does from the user's perspective. 2-3 sentences.
- **Why MVP**: why this is in v1 (e.g., "all competitors have it",
  "core to the value proposition", "needed for retention loop")
- **Scope**: concrete boundaries — included vs. explicitly excluded.
  Enough detail for an engineer to estimate.
- **User stories**: 1-3 key user stories in "As a [user], I want [action]
  so that [outcome]" format.

#### F2: Feature Name
- ...

#### Localization (if epic adds user-facing strings)
- Update/add localized strings for all features in this epic across all
  supported languages ({{var:PILOT_LANGUAGES}}).

---

## Epic N: [Epic Name]
(repeat feature epic structure)

---

## Epic N+1: Onboarding

**Goal**: Get the user to the aha moment in under 30 seconds.

### First-Run Flow
Step-by-step screens the user sees on first launch. For each step:
- **Screen**: what the user sees
- **Action**: what the user does (not reads — does)
- **Why**: what this step accomplishes toward the aha moment

Design principles: action-first, no carousels, no explanation screens.
Every step must earn its place — if removing it doesn't hurt, remove it.

### Data Collection
What we ask (name, goal, preferences) and WHY each field exists.
Only collect what the product needs in the first session.

### Permissions
Which system permissions, and the exact moment they're requested.
Each permission must be triggered by a user action that makes the ask obvious.

### Aha Moment
Define the specific moment the user first experiences core value.
What they see, what they feel, how quickly it happens.

### Activation Hooks
3-5 moments in the first session that reinforce engagement:
- **Hook**: what happens
- **Trigger**: when it fires
- **Reinforces**: what behavior this builds

---

## Epic N+2: Monetization Gate

**Goal**: Convert high-intent users immediately after the aha moment.

- **Placement**: shown immediately after onboarding completes
- **What the user sees**: pricing, value props, social proof if available
- **Skip button**: always visible, prominent, no dark patterns.
  Label: "Continue for free" or similar — never hide it
- **What happens on skip**: user enters the full product with free-tier
  limitations (define what's limited)
- **What happens on subscribe**: user enters the full product unlocked

---

## Navigation & Screens

The user journey mapped to named screens. No visual details — just what
exists, why, and how users move between them.

### Tabs
| Tab | Label | Root Screen |
|:----|:------|:------------|
| 1 | Home | home_dashboard |
| 2 | ... | ... |

### Key Flows
Main user journeys as screen sequences:
- **First launch**: onboarding_welcome → ... → paywall → home_dashboard
- **Core action**: home_dashboard → [screen] → home_dashboard
- **Settings**: settings → [sub-screen] → settings

### Screen Inventory

| Screen ID | Epic | What the user does here | Comes from | Goes to |
|:----------|:-----|:------------------------|:-----------|:--------|
| onboarding_welcome | onboarding | Sees app promise, taps continue | app launch (first time) | onboarding_goal |
| onboarding_goal | onboarding | Picks their goal | onboarding_welcome | onboarding_prefs |
| paywall | paywall | Decides to subscribe or skip | onboarding complete | home_dashboard |
| home_dashboard | [epic] | Sees today's progress, takes core action | paywall, tab bar | log_entry |
| ... | ... | ... | ... | ... |

Rules:
- One row per screen. Every screen belongs to one epic.
- Screen IDs are snake_case — they become identifiers downstream.
- Every user story must map to at least one screen.
- Include settings, profile, edit screens — not just the happy path.
- No layout, no visuals, no components. Just the journey.

## Deferred (v1.1+)

Features from the baseline that are NOT in MVP, with reason.

- **Feature name** — reason for deferral (e.g., "only 1 of 5 competitors
  has it", "requires watch app extension", "nice-to-have, not core")

## Design Direction

Before running the design pipeline, prepare a design brief with visual
references. This section tells the human WHAT to collect.

**Mood**: 3-5 adjectives describing the desired feel (e.g., calm, minimal,
premium, playful, bold). Derived from the app category and target user.

**Reference areas**: List the 2-4 screen types that benefit most from
visual references. For each, suggest what to look for:
- e.g., "Dashboard — look for apps with clean progress visualization"
- e.g., "Onboarding — look for apps with minimal, one-thing-per-screen flows"

**Notes**: Any aesthetic observations from the competitor research —
common visual patterns, color tendencies in the category, density norms.

_The human places screenshots and notes in `.pilot/design/brief.md`
before running the design pipeline. This section helps them know what
to look for._

## Open Questions
Decisions that need human input before development starts.
```

## Epic Grouping Rules

Group features into epics by user outcome, not by technical similarity.

| Guideline | Example |
|:----------|:--------|
| One epic = one plannable unit | An epic should be shippable on its own |
| 2-5 features per epic | Smaller = easier to plan and ship |
| Name by user outcome | "Daily Tracking", not "Database Features" |
| Order by priority | Feature epics ordered by impact on retention, then Onboarding (second-to-last), then Paywall (last) |
| Each feature in exactly one epic | No duplicates across epics |

## MVP Cut Line

Before writing features, stop and think:

**What are the 1-3 core use cases this product solves?** Write them down.
Then for every feature, ask: "Does this directly serve one of those core
use cases?" If no — defer it. Competitor prevalence alone is not enough
to justify inclusion.

The goal is the smallest possible app that solves the core use cases well.
Not the app with the most features. Not parity with competitors. The
leanest thing that delivers value and lets you validate CAC.

Think of it as a filter chain — a feature must pass ALL of these:

1. **Does it serve a core use case?** If no → defer.
2. **Can the app function without it?** If yes → probably defer.
3. **Is it table stakes for the category?** Even table-stakes features
   get deferred if they don't serve the core use cases.
4. **Is it simple to build?** Complexity tips borderline features to deferred.

Write the core use cases explicitly in the PRD (in the Overview section)
so the cut decisions are traceable.

## Decision Rules

| Rule | Guidance |
|:-----|:---------|
| Serves core use case | MVP — this is why the app exists |
| Table stakes + core use case | MVP |
| Table stakes but NOT core | Defer — prevalence alone doesn't justify inclusion |
| Half have it | Defer unless it directly serves a core use case |
| Few competitors have it | Defer unless the brief explicitly calls for it |
| Brief explicitly wants it | MVP regardless of competitor prevalence |
| Requires separate build target | Always defer. Watch, widgets, extensions are out of scope — no exceptions |
| Core retention loop | MVP only if it serves a core use case. Streaks/goals for the sake of engagement are not enough |

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Brief is optional | If no brief, derive everything from baseline + research |
| Brief is truth | If brief exists and conflicts with baseline, brief wins |
| Cut ruthlessly | When in doubt, defer. A smaller MVP that ships is better than a complete one that doesn't |
| Shadow, don't innovate | Don't invent new features. Replicate what's proven |
| Scope each feature | Every MVP feature needs concrete scope. "Add social features" is not scope |
| Be decisive | Make the call on every feature. In or out, with rationale |
| Foundation is Epic 1 | Always. Technical scaffolding, no user-facing features |
| Onboarding is second-to-last | Always. Non-negotiable. Apply the onboarding principles |
| Paywall is last | Always. Immediately after onboarding. Always has a skip button |
| App only | No watch apps, widgets, extensions, App Clips, or any other separate build target. Always defer |
| Epics, not flat lists | Every feature belongs to an epic. No orphan features |
| User stories required | Each feature needs 1-3 user stories for downstream planning |
| Human reviews | This PRD will be reviewed and edited. Make it easy to move features between epics and deferred |
