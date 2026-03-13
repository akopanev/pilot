# Protocol: PRD Review

Review the current PRD and produce structured feedback. You are an advisor —
your job is to find gaps, contradictions, clarity issues, and missing details.
You do NOT modify the PRD. You write a feedback document that another agent
(the decision-maker) will read and act on.

## Output Principles

Your feedback will be consumed by an AI agent (Opus) that holds the pen on
the PRD. Write for an agent that needs to understand exactly what's wrong
and exactly how to fix it, without any ambiguity.

- **Be specific.** Cite the exact section, heading, or feature by name.
  Quote the problematic text. Don't say "the onboarding section is vague" —
  say "Onboarding Step 3 says 'user picks preferences' but doesn't specify
  which preferences, how many options, or what happens if they skip."
- **Propose concrete fixes.** For every issue, suggest a specific resolution.
  Not "add more detail" — instead "add: the preferences screen offers 5-8
  category options as tappable chips, minimum 1 selection required, with a
  'Skip' button that applies defaults."
- **Prioritize.** Mark each issue as `critical` (PRD cannot be used downstream
  without this fix), `important` (significantly improves quality), or `minor`
  (nice-to-have improvement).
- **Maximum detail.** Do not self-limit. If you find 50 issues, report all 50.
  The decision-maker will filter.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — review written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- **Feature baseline**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`
- **Web research**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_RESEARCH}}`

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_REVIEW_OUTPUT}}`

## Execution

1. Read the PRD completely.
2. Read the feature baseline.
3. Read the web research.
4. `<signal:update>reviewing PRD</signal:update>`
5. Analyze the PRD against the review checklist below.
6. Write structured feedback to `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_REVIEW_OUTPUT}}`.
7. `<signal:completed>review complete — N critical, M important, K minor issues</signal:completed>`

## Review Checklist

Evaluate the PRD against ALL of these dimensions:

### Completeness
- Does every feature have: scope (in/out), user stories, interaction description, error states?
- Does every screen in the Screen Inventory have: purpose, entry points, exit points?
- Are all features from the baseline either included in an epic OR listed in Deferred with rationale?
- Are all demand signals from the research addressed (built or explicitly deferred)?
- Does every epic have a clear goal tied to a core use case?

### Consistency
- Do screen IDs match between Key Flows, Screen Inventory, and epic feature descriptions?
- Are feature names consistent throughout (same feature isn't called different names)?
- Do epic numbers match the ordering rules (Foundation=1, Onboarding=N-1, Paywall=N)?
- Are all core use cases from the Overview actually served by at least one feature epic?

### Clarity
- Can an AI agent design a screen from each feature description alone (without seeing competitors)?
- Can an AI agent write implementation tickets from the scope definitions?
- Are all edge cases and error states described?
- Are navigation flows explicit (no "then the user somehow gets to...")?
- Is every technical term defined or self-evident?

### Structure
- Does the PRD follow the required epic ordering?
- Is every feature in exactly one epic (no duplicates)?
- Does the Screen Inventory cover every screen mentioned in the PRD?
- Are user stories in the correct format ("As a [user], I want [action] so that [outcome]")?

### Baseline Coverage
- Cross-reference the feature baseline: are core features addressed?
- Cross-reference the research: are top demand signals addressed?
- Are deferral rationales honest and traceable to the cut-line rules?

## Output Format

Write the review in this format:

```
# PRD Review — Round {{var:PILOT_PRD_ROUND}}

> Reviewed: {{var:PILOT_PRD}}
> Issues found: N critical, M important, K minor

## Critical Issues

Issues that must be fixed — the PRD cannot be used downstream without these.

### [Issue Title]
**Section:** [exact section/heading in the PRD]
**Problem:** [what's wrong — quote the problematic text]
**Impact:** [why this matters for downstream agents]
**Suggested fix:** [concrete, specific resolution]

### [Next Issue]
...

## Important Issues

Issues that significantly improve PRD quality.

### [Issue Title]
**Section:** [exact section/heading]
**Problem:** [what's wrong]
**Suggested fix:** [concrete resolution]

### [Next Issue]
...

## Minor Issues

Nice-to-have improvements.

- **[Section]**: [brief description of issue and fix]
- ...

## Coverage Gaps

Features or demand signals from the baseline/research that appear
unaddressed (neither in an epic nor in Deferred).

- **[Feature/Signal]** — present in [baseline/research], not found in PRD
- ...
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Never modify the PRD | You are an advisor. Write feedback only |
| Be specific | Cite sections, quote text, name features. No vague feedback |
| Propose fixes | Every issue must include a concrete suggested resolution |
| Prioritize | Every issue is critical, important, or minor |
| No limit | Report ALL issues found. Do not self-censor or summarize |
| Cross-reference | Check the PRD against both the baseline and research inputs |
| Assume AI reader | Your feedback is for an AI agent, not a human. Be explicit |
