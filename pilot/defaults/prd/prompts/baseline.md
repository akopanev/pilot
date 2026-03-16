# Protocol: Parity Baseline

Merge per-app evidence files into a parity-first baseline for PRD generation.
Do not compress the market into a pure demand summary. Preserve what is common,
what is likely required, and which implementation patterns appear strongest.

## Output Principles

This baseline document will be consumed by an AI agent writing the PRD.

- **Preserve provenance.** Keep app names, prevalence counts, and notable implementation
  variants. Downstream agents need to know not just what exists, but whose pattern is being copied.
- **Preserve confidence.** Separate observed category patterns from inferred support flows
  and default assumptions.
- **Favor parity over minimization.** When a feature or support flow is common across strong
  competitors, treat it as part of the expected product shape even if reviews do not praise it directly.
- **Be implementation-useful.** Include states, supporting flows, monetization behaviors,
  navigation conventions, and operational defaults that a real clone would need.
- **Still be honest.** If evidence is weak, mark it weak. Do not pretend screenshot gaps are certainty.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — baseline written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Per-app evidence**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/*/features.md`
- **Web research**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}`
- **App metadata**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`

## Execution

1. Read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/apps.json`.
2. Read every `features.md` file.
3. Read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}`.
4. `<signal:update>building parity baseline from N apps + web research</signal:update>`
5. Identify the dominant product shape:
   - common core use cases
   - common navigation shell
   - common onboarding pattern
   - common monetization model
   - common support flows needed to make the visible product usable
6. Merge all evidence into three buckets:
   - **Observed market patterns** — clearly visible or explicit across one or more apps
   - **Supported inferred patterns** — strongly implied by multiple apps, reviews, or market norms
   - **Default parity assumptions** — standard production behaviors likely required for a credible clone
7. For each feature or flow, record:
   - prevalence count (`X / N apps`)
   - representative apps
   - notable variants
   - confidence (`high`, `medium`, `low`)
   - whether it is part of the likely MVP parity surface or a clear defer candidate
8. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}` in the format below.
9. `<signal:completed>baseline: X observed patterns, Y inferred patterns, Z parity assumptions</signal:completed>`

## Output Format

```markdown
# Parity Baseline

> Based on N competitor apps plus web research.

## Category Shape

### Core Use Cases
1. **[Use case]** — what job this category primarily solves.
2. **[Use case]** — ...
3. **[Use case]** — ... (if applicable)

### Dominant Product Shape

- **Navigation shell** — tab bar / stack / mixed, with evidence
- **Primary retention loop** — what brings users back repeatedly
- **Onboarding style** — wizard / immediate action / preference capture / mixed
- **Monetization model** — subscription / freemium / one-time. Dominant price point. Trial norms

## Observed Market Patterns

Things clearly visible in screenshots, store copy, or repeated explicit review language.

### [Category]

- **Feature or flow name**
  - **Prevalence**: X / N apps
  - **Representative apps**: App A, App B, App C
  - **What it does**: detailed description
  - **States and support flows**: loading, empty, error, create/edit/delete, settings, detail, etc.
  - **Implementation variants**: how different competitors handle it
  - **Confidence**: high
  - **Parity recommendation**: include / likely include / defer

## Supported Inferred Patterns

Things not always shown end-to-end, but strongly implied by evidence.

### [Category]

- **Feature or support flow**
  - **Prevalence**: X / N apps directly or indirectly support this
  - **Evidence chain**: why this is inferred
  - **Likely behavior**: what a clone should probably implement
  - **Confidence**: medium
  - **Parity recommendation**: include / likely include / defer

## Default Parity Assumptions

Production-grade behaviors to assume when evidence is incomplete but omission would
make the cloned app feel obviously unfinished.

- **Assumption**
  - **Why assume it**: standard for apps in this category or required by visible flows
  - **Typical implementation**: what most credible apps do
  - **Confidence**: low / medium
  - **Use only if**: condition for applying the assumption

## Navigation And Screen Clues

- **Confirmed screens** — clearly visible or explicit
- **Likely supporting screens** — strongly implied
- **Standard utility screens** — settings, edit, detail, manage subscription, restore purchases, etc.
- **Primary flow patterns** — first launch, core loop, settings/account loop

## Pricing Landscape

Concrete numbers from app_details.json and per-app evidence. No vague descriptions.

- **Dominant model** — subscription / freemium / one-time, with count (X / N apps)
- **Price points** — exact prices per competitor (app name: $X.XX/period)
- **Trial norms** — length, payment method required, per competitor
- **Free vs. paid line** — what features are typically free, what requires subscription
- **Outliers** — any competitor with a notably different approach

## Onboarding Clues

- **Observed onboarding steps**
- **Likely missing onboarding steps**

## Paywall Clues

- **Observed paywall behaviors** — placement, timing, offer framing per competitor
- **Likely paywall support behaviors** — restore purchases, skip/close, trial disclosure, manage subscription entry

## Sentiment Signals

- **What users repeatedly love**
- **What users repeatedly hate**
- **What causes churn or switching**

## Gaps That Still Matter

Only include unresolved gaps that materially change product scope, architecture, or monetization.

- **Question**
  - **Why it matters**
  - **Best default if unanswered**
  - **Confidence**
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Keep app names | Provenance matters for shadowing |
| Preserve prevalence | Always note counts where possible |
| Separate buckets | Observed, inferred, and assumed must not collapse together |
| Parity over purity | Common support flows matter even if users rarely praise them explicitly |
| No fake certainty | Weak evidence must stay weak |
| Implementation detail required | Include support states and production behaviors, not just headline features |
