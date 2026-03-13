# PRD Pipeline Improvements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add multi-model PRD refinement loop and maximum-detail instructions to all pipeline prompts.

**Architecture:** Three new pipeline stages (`review_codex`, `review_gemini`, `refine_critique`) added after the existing `prd` stage, with a convergence-based loop back to `review_codex`. All existing prompts updated with clarity/detail directives. No engine changes — uses existing signal routing and `signal:var` for round counter.

**Tech Stack:** YAML pipeline config, Markdown prompt templates, existing executors (claude-code, codex, gemini).

---

### Task 1: Update `prompts/research.md` — Maximum Detail Directive

**Files:**
- Modify: `pilot/defaults/prd/prompts/research.md`

**Step 1: Add clarity directive to the prompt**

Add the following block immediately after line 1 (`# Protocol: Web Research`) and before the existing description paragraph:

```markdown
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
```

Also update the Rules table — change the `User voice` row's constraint from:
```
Direct quotes are the most valuable data. Collect as many as possible
```
to:
```
Direct quotes are the most valuable data. Collect ALL relevant quotes — do not limit or summarize to save space. Every quote adds context for downstream agents
```

**Step 2: Verify the file reads correctly**

Run: `head -30 pilot/defaults/prd/prompts/research.md`
Expected: New "Output Principles" section visible after the title.

**Step 3: Commit**

```bash
git add pilot/defaults/prd/prompts/research.md
git commit -m "feat(prompts): add max-detail directive to research prompt"
```

---

### Task 2: Update `prompts/analyze.md` — Maximum Detail Directive

**Files:**
- Modify: `pilot/defaults/prd/prompts/analyze.md`

**Step 1: Add clarity directive to the prompt**

Add the following block after line 1 (`# Protocol: Feature Extraction`) and before the existing description:

```markdown
## Output Principles

Each `features.md` file will be consumed by an AI agent in the baseline stage,
not a human reviewer. Write for an agent with zero prior context about this app.

- **Maximum detail.** Describe every feature you observe in the screenshots,
  no matter how small. Include interaction patterns, visual states, data
  displayed, and UI elements. Never skip a feature because it seems minor.
- **Structured and navigable.** Use consistent formatting so the downstream
  agent can reliably parse and merge features across multiple apps.
- **No implicit knowledge.** If you see a toggle, describe what it controls.
  If you see a chart, describe what data it shows and what axes/labels exist.
  Name every visible element explicitly.
- **Exhaust the screenshots.** Every screenshot must be fully described.
  If a screenshot shows 10 features, list all 10. Do not pick "top" features.
```

Also update the Per-App Agent Prompt section — in the output format comment for Features, change:
```
- **Feature name** — what it does, how the user interacts with it
```
to:
```
- **Feature name** — what it does, how the user interacts with it, what data
  is shown, what states exist (empty, populated, error). Include every detail
  visible in the screenshots. 2-3 sentences minimum per feature.
```

And update the Rules table — change the `Concise` row:
```
| Concise | One line per feature. Name + what it does. No source citations needed |
```
to:
```
| Thorough | 2-3 sentences per feature minimum. Name + what it does + interaction details + visible states. No source citations needed |
```

**Step 2: Verify the file**

Run: `head -20 pilot/defaults/prd/prompts/analyze.md`
Expected: New "Output Principles" section visible.

**Step 3: Commit**

```bash
git add pilot/defaults/prd/prompts/analyze.md
git commit -m "feat(prompts): add max-detail directive to analyze prompt"
```

---

### Task 3: Update `prompts/baseline.md` — Maximum Detail Directive

**Files:**
- Modify: `pilot/defaults/prd/prompts/baseline.md`

**Step 1: Add clarity directive to the prompt**

Add the following block after line 1 (`# Protocol: Feature Baseline`) and before the existing description:

```markdown
## Output Principles

This baseline document will be consumed by an AI agent writing the PRD,
not a human PM. Write for an agent that has zero context about the category.

- **Maximum detail.** Every feature entry must include enough detail for an
  AI agent to write user stories, scope definitions, and screen designs
  without seeing the original apps. 3-5 sentences per feature minimum.
- **No lossy merging.** When deduplicating features across apps, preserve
  all variant details. If three apps implement "reminders" differently,
  describe all three approaches in the merged entry.
- **Structured and navigable.** Consistent formatting, clear categories,
  explicit tagging. The downstream agent will parse this programmatically.
- **No implicit knowledge.** Define category-specific terms. Explain why
  a feature is core vs. nice-to-have — show the reasoning chain from
  user sentiment to the tag.
```

Also update the Rules table — change the `Enough detail` row:
```
| Enough detail | A PM reading this should understand the feature's scope without seeing the apps |
```
to:
```
| Maximum detail | An AI agent reading this must be able to write user stories, scope features, and design screens without seeing the original apps. 3-5 sentences per feature minimum. Include all implementation variants observed across competitors |
```

And in the Output Format, update the Core Features entry template from:
```
- **Feature name** `→ use case N` — what it does, how the user interacts with it. 2-3 sentences with enough detail for a PM to understand scope and expected behavior.
```
to:
```
- **Feature name** `→ use case N` — what it does, how the user interacts with it, what data it displays, what states exist (empty, populated, error), common implementation patterns observed across competitors, and any notable UX variations. 3-5 sentences with enough detail for an AI agent to write complete user stories and scope definitions.
```

**Step 2: Verify the file**

Run: `head -20 pilot/defaults/prd/prompts/baseline.md`
Expected: New "Output Principles" section visible.

**Step 3: Commit**

```bash
git add pilot/defaults/prd/prompts/baseline.md
git commit -m "feat(prompts): add max-detail directive to baseline prompt"
```

---

### Task 4: Update `prompts/prd.md` — Maximum Detail Directive

**Files:**
- Modify: `pilot/defaults/prd/prompts/prd.md`

**Step 1: Add clarity directive to the prompt**

Add the following block after line 4 (`Shadow strategy — replicate what top competitors ship...`) and before `## Signals`:

```markdown
## Output Principles

This PRD will be consumed by AI agents in the design and planning pipelines,
not a human PM. It is the single source of truth for all downstream automation.

- **Maximum detail in every section.** Every feature must include complete
  scope, explicit boundaries (what's in vs. what's out), detailed user stories,
  and concrete interaction descriptions. An AI agent must be able to design
  screens and write implementation tickets from this document alone.
- **No implicit knowledge.** Spell out every assumption. If the app needs
  a settings screen, describe what's on it. If a flow has error states,
  describe them. If a feature has edge cases, list them.
- **Structured and machine-parseable.** Use consistent heading levels, table
  formats, and naming conventions throughout. Screen IDs, epic numbers, and
  feature IDs must be used consistently so downstream agents can cross-reference.
- **Complete screen inventory.** Every screen referenced anywhere in the PRD
  must appear in the Screen Inventory table. No orphan references.
- **Exhaustive deferred list.** Every feature from the baseline that is NOT
  in MVP must appear in the Deferred section with a clear rationale.
```

Also update the Rules table — change the `Scope each feature` row:
```
| Scope each feature | Every MVP feature needs concrete scope. "Add social features" is not scope |
```
to:
```
| Scope each feature | Every MVP feature needs exhaustive scope: included behaviors, excluded behaviors, edge cases, error states, data shown, interaction patterns. An AI agent must be able to design and implement from this description alone |
```

And change the `Human reviews` row:
```
| Human reviews | This PRD will be reviewed and edited. Make it easy to move features between epics and deferred |
```
to:
```
| AI-consumable | This PRD is consumed by AI agents for design and planning. Every section must be self-contained, unambiguous, and complete. Make it easy to move features between epics and deferred |
```

**Step 2: Verify the file**

Run: `head -20 pilot/defaults/prd/prompts/prd.md`
Expected: New "Output Principles" section visible.

**Step 3: Commit**

```bash
git add pilot/defaults/prd/prompts/prd.md
git commit -m "feat(prompts): add max-detail directive to prd prompt"
```

---

### Task 5: Create `prompts/review.md` — PRD Review Prompt

**Files:**
- Create: `pilot/defaults/prd/prompts/review.md`

**Step 1: Write the review prompt**

```markdown
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

```markdown
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
```

**Step 2: Verify the file exists and is well-formed**

Run: `wc -l pilot/defaults/prd/prompts/review.md`
Expected: ~140 lines

**Step 3: Commit**

```bash
git add pilot/defaults/prd/prompts/review.md
git commit -m "feat(prompts): add PRD review prompt for multi-model refinement"
```

---

### Task 6: Create `prompts/refine_critique.md` — Refine + Critique Prompt

**Files:**
- Create: `pilot/defaults/prd/prompts/refine_critique.md`

**Step 1: Write the refine/critique prompt**

```markdown
# Protocol: PRD Refine & Critique

You are the decision-maker. Read the current PRD and all review feedback,
evaluate each piece of feedback, apply warranted changes to the PRD, and
decide whether another review round is needed.

You hold the pen — only you modify the PRD. The reviewers are advisors.
Weigh their feedback critically: apply what improves the PRD, reject what
doesn't, and resolve conflicts between reviewers.

## Output Principles

The refined PRD will be consumed by AI agents in design and planning pipelines.
Apply the same output principles as the original PRD generation:

- **Maximum detail.** Every change you make should increase, not decrease,
  the level of detail. When expanding a section, be exhaustive.
- **No implicit knowledge.** Every assumption must be explicit. Every edge
  case must be described. Every flow must be complete.
- **Structured and machine-parseable.** Maintain consistent formatting,
  heading levels, table formats, and naming conventions.
- **Complete.** After refinement, the PRD must be a self-contained document.
  No reviewer feedback should be needed to understand it.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:var key=NAME>value</signal:var>` — persist variable
- `<signal:repeat>summary of changes</signal:repeat>` — PRD was changed, loop back for re-review
- `<signal:converged>summary</signal:converged>` — PRD is stable, no substantive changes needed
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- **Codex review**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_REVIEW_CODEX}}`
- **Gemini review**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_REVIEW_GEMINI}}`
- **Feature baseline**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`
- **Current round**: `{{var:PILOT_PRD_ROUND}}` (default: 1)
- **Max rounds**: `{{var:PILOT_PRD_REFINE_ROUNDS}}` (default: 3)

## Output

- Updated PRD: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- Changelog entry: append to `{{var:PILOT_CONFIG_DIR}}/data/prd_changelog.md`

## Execution

1. Read the current PRD.
2. Read the Codex review feedback file.
3. Read the Gemini review feedback file.
4. Read the feature baseline (for cross-reference).
5. `<signal:update>refining PRD — round {{var:PILOT_PRD_ROUND}}</signal:update>`
6. **Evaluate each piece of feedback:**
   - For each critical issue: apply the fix unless the reviewer is factually wrong.
   - For each important issue: apply if it genuinely improves the PRD. Reject if
     it's a style preference or would reduce clarity.
   - For each minor issue: apply if trivial to fix. Skip otherwise.
   - When reviewers conflict: use your judgment. Prefer the fix that adds more
     detail and clarity. Note the conflict in the changelog.
7. **Apply all accepted changes to the PRD.** Write the updated PRD to
   `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`.
8. **Write a changelog entry** — append a round summary to
   `{{var:PILOT_CONFIG_DIR}}/data/prd_changelog.md` (see format below).
9. **Decide whether to loop or stop:**

### Decision Logic

```
current_round = {{var:PILOT_PRD_ROUND}} (integer, default 1)
max_rounds = {{var:PILOT_PRD_REFINE_ROUNDS}} (integer, default 3)

IF no substantive changes were made (only minor/cosmetic or no changes):
    → signal converged
ELSE IF current_round >= max_rounds:
    → signal converged (safety cap reached)
ELSE:
    → increment round counter
    → signal repeat
```

10. **Emit the round counter** (always, before the domain signal):
    `<signal:var key=PILOT_PRD_ROUND>{current_round + 1}</signal:var>`

11. **Emit the domain signal:**
    - Changes made + under cap: `<signal:repeat>round N complete — applied X changes, re-reviewing</signal:repeat>`
    - No changes or cap reached: `<signal:converged>PRD stable after N rounds — M total changes applied</signal:converged>`

## Changelog Format

Append this to `data/prd_changelog.md` (create if it doesn't exist):

```markdown
## Round N

**Changes applied:**
- [Section]: [what changed and why]
- [Section]: [what changed and why]
- ...

**Feedback rejected:**
- [Reviewer] [Section]: [what was suggested and why it was rejected]
- ...

**Conflicts resolved:**
- [Section]: [Codex said X, Gemini said Y, decision: Z because...]
- ...
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| You hold the pen | Only you modify the PRD. Reviewers advise |
| Critical = mandatory | Apply all critical fixes unless factually wrong |
| Detail always increases | Never reduce detail. Every change should add clarity |
| Honest convergence | Only signal converged if truly no substantive changes. Don't shortcut |
| Changelog always | Every round gets a changelog entry, even if no changes |
| Preserve structure | Maintain the PRD's required epic ordering and format |
| Cross-reference | Check fixes against the baseline to avoid introducing errors |
| Round counter | Always emit the updated round counter before the domain signal |
```

**Step 2: Verify the file exists and is well-formed**

Run: `wc -l pilot/defaults/prd/prompts/refine_critique.md`
Expected: ~120 lines

**Step 3: Commit**

```bash
git add pilot/defaults/prd/prompts/refine_critique.md
git commit -m "feat(prompts): add PRD refine/critique prompt for convergence loop"
```

---

### Task 7: Update `pipeline.yaml` — Add Review/Refine Stages and Loop

**Files:**
- Modify: `pilot/defaults/prd/pipeline.yaml`

**Step 1: Add new config variables**

In the `vars:` section of `pipeline.yaml`, add these lines after `PILOT_LANGUAGES`:

```yaml
  PILOT_PRD_ROUND: "1"                  # Current refinement round (managed by refine_critique)
  PILOT_PRD_REFINE_ROUNDS: "3"          # Max refinement rounds (safety cap)
  PILOT_REVIEW_CODEX: "data/review_codex.md"     # Codex review output
  PILOT_REVIEW_GEMINI: "data/review_gemini.md"    # Gemini review output
```

**Step 2: Update the `prd` stage signal routing**

Change the `prd` stage's `on_signal` from:

```yaml
    on_signal:
      completed: __succeed__
      default: __fail__
```

to:

```yaml
    on_signal:
      completed: review_codex
      default: __fail__
```

**Step 3: Add the three new stages**

Add these stages after the `prd` stage block (before the end of the `stages:` section):

```yaml
  review_codex:
    prompt: |
      {{file:prompts/review.md}}
    runner:
      executor: codex
      model: o3
    on_signal:
      completed: review_gemini
      default: __fail__

  review_gemini:
    prompt: |
      {{file:prompts/review.md}}
    runner:
      executor: gemini
      model: gemini-2.5-pro
    on_signal:
      completed: refine_critique
      default: __fail__

  refine_critique:
    prompt: |
      {{file:prompts/refine_critique.md}}
    runner:
      executor: claude-code
      model: opus
    on_signal:
      repeat: review_codex
      converged: __succeed__
      default: __fail__
```

**Step 4: Add stage-specific review output variable overrides**

The `review_codex` and `review_gemini` stages use the same prompt (`review.md`) but need to write to different output files. The prompt references `{{var:PILOT_REVIEW_OUTPUT}}`. We need to set this per-stage via `pre_step`.

Update the `review_codex` stage to add a `pre_step`:

```yaml
  review_codex:
    pre_step: |
      echo "PILOT_REVIEW_OUTPUT=data/review_codex.md" >> "$PILOT_CONFIG_DIR/.pilot/vars"
    prompt: |
      {{file:prompts/review.md}}
    runner:
      executor: codex
      model: o3
    on_signal:
      completed: review_gemini
      default: __fail__
```

Update the `review_gemini` stage to add a `pre_step`:

```yaml
  review_gemini:
    pre_step: |
      echo "PILOT_REVIEW_OUTPUT=data/review_gemini.md" >> "$PILOT_CONFIG_DIR/.pilot/vars"
    prompt: |
      {{file:prompts/review.md}}
    runner:
      executor: gemini
      model: gemini-2.5-pro
    on_signal:
      completed: refine_critique
      default: __fail__
```

**Step 5: Verify the complete pipeline.yaml is valid YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('pilot/defaults/prd/pipeline.yaml'))" && echo "valid"`
Expected: `valid`

**Step 6: Verify stage transitions form a valid graph**

Run: `python3 -c "from pilot.config import load_config; c = load_config('pilot/defaults/prd/pipeline.yaml'); print('stages:', list(c.stages.keys()))" 2>&1`
Expected: `stages: ['gather', 'gather_reviews', 'research', 'analyze', 'baseline', 'prd', 'review_codex', 'review_gemini', 'refine_critique']`

**Step 7: Commit**

```bash
git add pilot/defaults/prd/pipeline.yaml
git commit -m "feat(pipeline): add review/refine loop with codex + gemini reviewers"
```

---

### Task 8: End-to-End Verification

**Files:**
- Read: `pilot/defaults/prd/pipeline.yaml` (verify final state)
- Read: `pilot/defaults/prd/prompts/review.md` (verify exists)
- Read: `pilot/defaults/prd/prompts/refine_critique.md` (verify exists)

**Step 1: Verify all files exist**

Run: `ls -la pilot/defaults/prd/prompts/`
Expected: 6 files: `analyze.md`, `baseline.md`, `prd.md`, `research.md`, `review.md`, `refine_critique.md`

**Step 2: Verify pipeline config loads without errors**

Run: `python3 -c "from pilot.config import load_config; c = load_config('pilot/defaults/prd/pipeline.yaml'); [print(f'{s}: {list(c.stages[s].on_signal.keys())}') for s in c.stages]"`

Expected output:
```
gather: ['ready', 'default']
gather_reviews: ['ready', 'default']
research: ['completed', 'default']
analyze: ['completed', 'default']
baseline: ['completed', 'default']
prd: ['completed', 'default']
review_codex: ['completed', 'default']
review_gemini: ['completed', 'default']
refine_critique: ['repeat', 'converged', 'default']
```

**Step 3: Verify the loop transition**

Run: `python3 -c "from pilot.config import load_config; c = load_config('pilot/defaults/prd/pipeline.yaml'); t = c.stages['refine_critique'].on_signal['repeat']; print(f'repeat -> {t.to}')"`

Expected: `repeat -> review_codex`

**Step 4: Verify all prompts contain the Output Principles section**

Run: `grep -l "Output Principles" pilot/defaults/prd/prompts/*.md`

Expected: all 6 prompt files listed.

**Step 5: Final commit (if any fixes were needed)**

```bash
git add -A pilot/defaults/prd/
git commit -m "fix: address verification issues in pipeline improvements"
```

Only run this if previous steps required fixes. If everything passed, skip.
