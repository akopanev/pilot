# Protocol: Conversion Review

Task: `{{var:PILOT_TASK_ID}}`

Review the iOS → Dart conversion for this task. Compare the original
Swift/Obj-C source against the generated Dart code. Check for functional
equivalence, codebook compliance, and Flutter best practices.

Write your review to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_REVIEW_OUTPUT}}`

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:failed>reason</signal:failed>` — fatal only
- No signal = advance to next stage

## Steps

1. `tk show {{var:PILOT_TASK_ID}}` — read the full ticket: source files,
   target files, codebook references, acceptance criteria, prior notes.
2. `<signal:update>review: {{var:PILOT_TASK_ID}}</signal:update>`
3. `git checkout {{var:PILOT_WORKING_BRANCH}}`
4. Read the **codebook**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK}}`
5. Read every **iOS source file** listed in the ticket.
6. Read every **Dart target file** produced by the conversion.
   Read the full files, not just the diff.
7. **Compare and judge**:

   - **Functional equivalence**: Does the Dart code do everything the
     Swift code does? Go method by method, property by property. Check:
     - All public methods have Dart equivalents
     - Error handling is preserved (not silently dropped)
     - Edge cases are handled (nil checks, empty collections, boundary values)
     - Business logic produces the same results

   - **Codebook compliance**: Does the conversion follow the codebook?
     - Correct type mappings (Date → DateTime, not String)
     - Correct pattern mappings (delegates → the chosen pattern)
     - Correct state management (the chosen approach, not setState)
     - Correct project structure (files in the right directories)
     - Correct naming conventions

   - **Flutter quality**: Is it good Dart/Flutter code?
     - Widget composition (not monolithic build methods)
     - Proper use of const constructors
     - No unnecessary StatefulWidgets
     - Correct lifecycle management (dispose, cancel streams)
     - Proper async handling (no fire-and-forget)

   - **Dependencies**: Are imports correct?
     - Referencing already-converted files with correct paths
     - Using packages from codebook, not inventing alternatives
     - No circular dependencies

8. Write the review to `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_REVIEW_OUTPUT}}`.

## Review Format

```markdown
# Conversion Review: [task ID]

## Summary
[1-2 sentence overall assessment]

## Functional Equivalence
- [method/feature]: [OK / MISSING / INCORRECT — details]
- ...

## Codebook Compliance
- [pattern/type]: [OK / DEVIATION — details]
- ...

## Flutter Quality
- [aspect]: [OK / ISSUE — details]
- ...

## Issues
1. [file:line] [severity: critical/important/minor] — [issue description]
   FIX: [concrete fix]
2. ...

## Verdict
[PASS / FAIL — with summary of blocking issues if FAIL]
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Read both sides | Read the Swift source AND the Dart output. You can't review a conversion without both |
| Use the codebook | Check conversions against codebook patterns, not your own preferences |
| Method by method | Don't skim. Compare each method/property in the source against the target |
| Every issue = concrete fix | If you can't describe a fix, the issue isn't actionable — skip it |
| No nitpicking | dart format handles style. You handle logic and correctness |
| Write to file | Output goes to the review file, not just stdout |
| Don't fix code | Your job is to review, not to edit. Write findings, let the fix agent handle them |
