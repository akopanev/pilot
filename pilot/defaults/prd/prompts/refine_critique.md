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

```
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
