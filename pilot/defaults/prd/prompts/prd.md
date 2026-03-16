# Protocol: PRD Generation

Write a parity-first PRD based on the baseline, web research, and optionally a user brief.
Goal: shadow proven competitors as faithfully as possible from the available evidence, while
filling unavoidable gaps automatically using majority patterns and clearly labeled assumptions.

## Output Principles

This PRD will be consumed by AI agents in the design and planning pipelines.

- **Parity first.** Prefer cloning the dominant competitor pattern over inventing a cleaner
  or leaner alternative. If evidence is incomplete, infer from the strongest market pattern.
- **No fake certainty.** The document should distinguish between observed facts, strong
  inferences, and fallback assumptions, but still make clear build decisions.
- **Implementation-ready.** Every feature should include scope, supporting flows, edge cases,
  error/loading/empty states, and interactions detailed enough for downstream agents.
- **Complete enough to build.** Do not leave obvious production gaps like settings, edit/delete,
  restore purchases, or permissions undefined if the product shape implies them.
- **Escalate only material uncertainty.** Ask the human only when ambiguity materially changes
  scope, architecture, monetization, or the core user journey.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — PRD written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Parity baseline**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`
- **Web research**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}`
- **User brief** (optional): `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_BRIEF}}`

## Output

- PRD: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- Human Q&A pack: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD_QA}}`

## Execution

1. Read the parity baseline.
2. Read the web research.
3. Try to read the user brief. If the file doesn't exist or is empty, proceed without it.
4. `<signal:update>writing parity-first PRD</signal:update>`
5. Build the PRD using this decision order:
   - explicit user brief, if present
   - high-confidence observed market patterns
   - medium-confidence supported inferences
   - low-confidence default parity assumptions only when needed to avoid an obviously incomplete product
6. For every ambiguous area, decide one of:
   - **include with high confidence**
   - **include with medium confidence**
   - **include as default assumption**
   - **defer**
   - **escalate to human Q&A** only if the ambiguity materially changes build scope or business behavior
7. Write the PRD to `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`.
8. Write a concise human Q&A pack to `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD_QA}}`.
9. `<signal:completed>PRD + Q&A pack written</signal:completed>`

---

## Hard Constraints

1. **Epic 1 is always Foundation.** Technical setup only.
2. **Feature epics come next.** Group by user outcome, not by layer.
3. **Second-to-last epic is always Onboarding.**
4. **Last epic is always Monetization Gate (Paywall).**
5. **App only. No extensions.** Defer widgets, watch apps, App Clips, etc.
6. **React Native, cross-platform.**
7. **Localization from day one.** MVP ships with: {{var:PILOT_LANGUAGES}}.

---

## Gap-Filling Rules

Apply these before creating human questions.

1. **Use majority competitor patterns first.**
   - If most competitors use a tab bar, use a tab bar.
   - If a visible list clearly implies detail/edit/delete, include those flows.
   - If monetization exists, include restore purchases and manage subscription entry.
   - If reminders are central, include reminder settings and contextual permission prompts.

2. **Assume production-grade states.**
   - Loading, empty, error, retry, and offline fallback where appropriate.
   - Success confirmations where user actions need reassurance.
   - Destructive action confirmation for delete/cancel if standard for the flow.

3. **Assume support surfaces required by visible features.**
   - Settings for visible personalization
   - Edit flows for user-created content
   - Detail views for tappable cards/lists
   - Account/access management where auth or sync is implied

4. **Only escalate to human Q&A if unresolved ambiguity changes one of:**
   - business model or paywall behavior
   - auth requirements
   - core navigation structure
   - major data model boundaries
   - primary onboarding path

---

## Output Format

```markdown
# PRD: [Product Name]

## Overview
One paragraph. What this app is, who it is for, and what it does.

**Core use cases** (1-3):
1. [Primary use case]
2. [Secondary use case]
3. [Third use case if needed]

## Strategy
Shadow existing winners. Replicate dominant competitor patterns and only
deviate when the brief explicitly requires it.

## Target User
Concrete paragraph.

## Evidence Posture

- **High-confidence patterns** — what is directly observed or explicit
- **Medium-confidence patterns** — what is strongly inferred
- **Default assumptions used** — what was filled in automatically to avoid obvious product gaps

---

## Epic 1: Foundation

**Goal**: Technical scaffolding only. No user-facing product behavior.

- Project setup
- Core data models
- Base navigation shell with placeholder screens
- Localization infrastructure
- Auth skeleton if applicable
- Theme setup

**NOT in Foundation**: real product flows, settings editors, profile forms, paywall UI, onboarding UI.

---

## Epic 2: [Epic Name]

**Goal**: the user outcome this epic delivers and why it matters.

### Features

#### F1: Feature Name
- **Evidence level**: high / medium / assumed
- **Parity rationale**: which competitor patterns or baseline findings support inclusion
- **What**: user-facing behavior in detail
- **Scope**: included behavior, excluded behavior, supporting flows, and system behavior
- **States**: default, loading, empty, error, success, destructive confirmation, offline fallback if relevant
- **User stories**:
  - As a [user], I want [action] so that [outcome].
- **Notes for downstream design/implementation**: concrete interaction and data details

#### F2: Feature Name
- ...

#### Localization
- User-facing strings introduced by this epic across all supported languages

---

## Epic N: [Feature Epic Name]
(repeat)

---

## Epic N+1: Onboarding

**Goal**: Get the user to the first meaningful value moment quickly, while matching the strongest competitor pattern available.

### First-Run Flow
For each step:
- **Screen**
- **Evidence level**
- **What the user sees**
- **What the user does**
- **Why this step exists**
- **What happens on skip/back/dismiss**

### Data Collection
Fields collected, why they exist, which are required vs skippable, and defaults if skipped.

### Permissions
Which permissions are requested, the exact contextual trigger, fallback behavior if denied, and where the user can enable later.

### Aha Moment
Define the first value moment precisely.

### Activation Hooks
3-5 hooks in the first session.

---

## Epic N+2: Monetization Gate

**Goal**: Match the likely winning monetization moment and behavior from competitor evidence.

- **Evidence level**
- **Placement**
- **What the user sees**
- **Primary CTA**
- **Skip / close behavior**
- **Restore purchases**
- **Manage subscription access point**
- **Free-tier behavior after skip**
- **What unlocks on subscribe**

---

## Navigation & Screens

### Tabs
| Tab | Label | Root Screen | Confidence |
|:----|:------|:------------|:-----------|

### Key Flows
- **First launch**: ...
- **Primary recurring loop**: ...
- **Settings/account loop**: ...
- **Paywall loop**: ...

### Screen Inventory

| Screen ID | Epic | What the user does here | Comes from | Goes to | Confidence |
|:----------|:-----|:------------------------|:-----------|:--------|:-----------|

Rules:
- Include confirmed screens, likely supporting screens, and standard utility screens needed for parity.
- Use medium/low confidence labels when the screen is inferred or assumed.
- Every user story must map to at least one screen.

## Deferred

Features intentionally not in scope.

- **Feature name** — why deferred

## Assumptions Register

Only assumptions actually used in the PRD.

- **Assumption**
  - **Why used**
  - **Affected sections**
  - **Risk if wrong**
  - **Default chosen**

## Open Questions

Only questions that materially change scope or product behavior.
Keep this list short.
```

## Human Q&A Pack Format

Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD_QA}}` in this format:

```markdown
# PRD Q&A Pack

Only questions worth asking a human before implementation starts.

## High-Priority Questions

1. **Question**
   - **Why it matters**
   - **Current default in PRD**
   - **Impact if answered differently**

## Nice-To-Confirm

- **Question**
  - **Current default in PRD**
  - **Why confirmation would help**
```

Prefer 5-12 questions total. If there are none, write `No material open questions.`

---

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Shadow, do not innovate | Prefer the dominant competitor pattern |
| Fill gaps automatically | Use majority defaults before asking humans |
| Label uncertainty | High / medium / assumed where relevant |
| Keep the build coherent | Do not defer obvious support flows that the visible product needs |
| Defer only deliberate non-MVP scope | Not because evidence was incomplete |
| Human Q&A must stay small | Ask only what materially changes scope or business behavior |
| AI-consumable | The PRD must remain the main source of truth for downstream automation |
