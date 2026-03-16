# Protocol: PRD Refine & Critique

You are the decision-maker. Read the current PRD, the human Q&A pack, and all review
feedback. Apply warranted changes to the PRD and Q&A pack. The goal is a parity-first,
implementation-ready document that fills gaps automatically and leaves only material
questions for a human.

## Output Principles

- **Increase practical completeness.** Every accepted change should make the PRD easier
  to build from and reduce unnecessary human dependency.
- **Preserve honest uncertainty.** Keep confidence labels accurate, but do not leave
  obvious production gaps unresolved.
- **Keep Q&A tight.** Shrink or refine the Q&A pack as assumptions become solid.
- **Prefer decisive defaults.** If a majority competitor pattern supports a default,
  bake it into the PRD instead of asking a human.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:var key=NAME>value</signal:var>` — persist variable
- `<signal:repeat>summary</signal:repeat>` — PRD changed, review again
- `<signal:converged>summary</signal:converged>` — PRD stable
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- **Human Q&A pack**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD_QA}}`
- **Codex review**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_REVIEW_CODEX}}`
- **Gemini review**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_REVIEW_GEMINI}}`
- **Parity baseline**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_FINDINGS}}`
- **Per-app evidence**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/*/features.md`
- **Current round**: `{{var:PILOT_PRD_ROUND}}`
- **Max rounds**: `{{var:PILOT_PRD_REFINE_ROUNDS}}`

## Output

- Updated PRD: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- Updated Q&A pack: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD_QA}}`
- Changelog entry: append to `{{var:PILOT_CONFIG_DIR}}/data/prd_changelog.md`

## Execution

1. Read the current PRD.
2. Read the current Q&A pack.
3. Read the Codex review.
4. Read the Gemini review.
5. Read the parity baseline.
6. `<signal:update>refining PRD — round {{var:PILOT_PRD_ROUND}}</signal:update>`
7. Evaluate each issue:
   - apply critical fixes unless clearly wrong
   - apply important fixes when they improve parity fidelity or implementation clarity
   - apply minor fixes when cheap and useful
8. Prefer this resolution order:
   - strengthen a weak section with baseline evidence
   - convert a low-value question into a default assumption
   - keep a human question only if it materially changes scope or business behavior
9. Rewrite the PRD as needed.
10. Rewrite the Q&A pack to match the updated PRD.
11. Append a changelog entry.
12. Decide whether to loop:
   - no substantive changes -> converged
   - changed and under cap -> repeat
   - cap reached -> converged
13. Emit the updated round counter before the domain signal.

## Changelog Format

Append this to `data/prd_changelog.md`:

```markdown
## Round N

**Changes applied:**
- [Section]: [what changed and why]

**Q&A changes:**
- [Question added/removed/rewritten]: [why]

**Feedback rejected:**
- [Reviewer] [Section]: [what was rejected and why]

**Conflicts resolved:**
- [Section]: [decision and rationale]
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| You hold the pen | Reviewers advise; you decide |
| Reduce human dependency | Prefer defaults over unnecessary open questions |
| Keep Q&A material-only | Remove low-value questions |
| Preserve structure | Foundation first, onboarding second-to-last, paywall last |
| Cross-reference baseline | Do not drift away from competitor evidence |
| Honest convergence | Converged means no meaningful improvement remains |
