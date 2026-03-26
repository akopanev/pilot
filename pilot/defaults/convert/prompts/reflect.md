# Protocol: Reflect — Epic Retrospective

Epic `{{var:PILOT_CURRENT_EPIC}}` (`{{var:PILOT_CURRENT_EPIC_TITLE}}`) is
complete. All its tasks have been converted, reviewed, and merged. Step
back, review the work, and update the codebook with learnings.

## Signals
- `<signal:update>message</signal:update>` — progress
- No signal = advance to pick_epic (next epic)

## Inputs

- **Codebook**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK}}`
- **Codebook changelog**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK_CHANGELOG}}`
- **Analysis**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_ANALYSIS}}`
- **Flutter project**: `{{var:PILOT_FLUTTER_DIR}}/`
- **Epic tickets**: `tk show {{var:PILOT_CURRENT_EPIC}}` + child tasks

## Execution

1. `<signal:update>reflecting on {{var:PILOT_CURRENT_EPIC_TITLE}}</signal:update>`
2. Read the codebook.
3. Read the completed epic and all its child task tickets (including notes).
   The notes contain the full history: verify results, review feedback,
   fix attempts, escalations.
4. Read the Dart files produced by this epic in `{{var:PILOT_FLUTTER_DIR}}/lib/`.
5. **Review the code holistically**:
   - Is there consistency across the files produced by different tasks?
   - Are imports between files correct?
   - Do the files follow the codebook's patterns?
   - Are there any patterns that emerged that the codebook didn't cover?
6. **Run `flutter analyze`** on the full project. If issues exist from
   this epic's files, fix them and commit.
7. **Identify codebook updates**. Things to look for:
   - Type mappings that turned out differently than planned
     (e.g., "Swift's Result<T,E> maps better to Dart's sealed class than
     to exceptions — updating codebook")
   - Pattern mappings that needed adjustment
   - New Flutter packages that were needed but weren't in the codebook
   - Common conversion pitfalls that future tasks should avoid
   - Naming conventions that drifted and need correction
8. **Update the codebook** if learnings exist. Edit
   `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK}}` — add, modify, or
   clarify mappings. Don't remove mappings that still work for other code.
9. **Append to codebook changelog**:

```markdown
## After {{var:PILOT_CURRENT_EPIC_TITLE}}

**Updated:**
- [Section]: [what changed and why]

**Added:**
- [New mapping/pattern]: [what was learned]

**Issues found:**
- [Consistency problem or tech debt to address later]
```

10. Commit and push:
    ```bash
    git add . && git commit -m "convert: reflect on {{var:PILOT_CURRENT_EPIC_TITLE}}"
    git push
    ```
    The push is important — this pipeline runs remotely. Each epic's work
    must be pushed so nothing is lost.

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Read the actual code | Don't just check tickets. Read the Dart files produced |
| Fix what you find | If flutter analyze fails, fix it now. Don't leave it for the next epic |
| Update the codebook | This is the whole point. Future epics depend on an accurate codebook |
| Be specific | "Changed X because Y" not "updated some mappings" |
| Don't refactor | Note problems but don't rewrite prior conversions. Fix consistency, not style |
| Changelog is mandatory | Even if no codebook changes — record "no updates needed" |
| Keep codebook focused | Don't bloat it with one-off observations. Only add patterns that apply broadly |
