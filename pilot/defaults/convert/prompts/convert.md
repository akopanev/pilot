# Protocol: Convert

Task: `{{var:PILOT_TASK_ID}}`

Convert the iOS source files specified in this task to Dart/Flutter,
following the codebook for all patterns, types, and conventions.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:failed>reason</signal:failed>` — fatal only: can't checkout, missing tool,
  broken environment. Never for analysis/format failures
- No signal = advance to verify

## Steps

1. **Read task**: `tk show {{var:PILOT_TASK_ID}}`. The ticket contains:
   - Source files (iOS) to convert
   - Target files (Dart) to create
   - Codebook references for patterns and mappings
   - Dependencies (already-converted Dart files to import)
   - Acceptance criteria with check commands
   - Out of scope
2. **Checkout**: `git checkout {{var:PILOT_WORKING_BRANCH}}`.
3. **Read codebook**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK}}`.
   This is your pattern reference — follow it for types, naming, architecture.
4. **Read source files**: Open every iOS file listed in the ticket. Read
   the full file, not just the parts you think you need. Understand:
   - What each class/struct/enum does
   - Its public API (methods, properties)
   - Its dependencies (imports, injected services)
   - Edge cases and error handling
5. **Read dependencies**: Open the already-converted Dart files listed in
   the ticket's dependencies section. Understand their public API so your
   imports and usage are correct.
6. `<signal:update>convert: {{var:PILOT_TASK_ID}}</signal:update>`
7. **Convert**: Write the Dart files. For each source file:
   - Create the target file at the path specified in the ticket
   - Apply codebook type mappings (Swift types → Dart types)
   - Apply codebook pattern mappings (delegates → callbacks/streams, etc.)
   - Use the codebook's chosen state management, DI, and navigation
   - Preserve all business logic — the Dart code must do the same thing
   - Use Dart idioms, not literal Swift translation:
     - Dart `factory` constructors for named constructors
     - Dart `extension` for Swift extensions
     - Dart sealed classes for Swift enums with associated values
     - Dart `async`/`await` for completion handlers
     - Dart collection methods (`map`, `where`, `fold`) for loops
   - Add necessary imports (both package and local)
   - Add necessary dependencies to `pubspec.yaml` if not already present
8. **Verify**: Run `flutter analyze` in `{{var:PILOT_FLUTTER_DIR}}/`.
   If anything fails — read the error, fix the code, re-run.
   Repeat until clean. Up to 3 fix cycles. Then commit regardless.
9. **Format**: Run `dart format {{var:PILOT_FLUTTER_DIR}}/lib/`.
10. **Commit**: `git add . && git commit -m "{{var:PILOT_TASK_ID}}: <summary>"`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Read the codebook | Every conversion decision must match the codebook. If unsure, check the codebook |
| Read the source fully | Understand the iOS code before writing Dart. Don't guess from class names |
| Read dependencies | Check already-converted Dart files so imports and API usage are correct |
| Preserve behavior | The Dart code must do the same thing as the Swift code. Don't drop edge cases |
| Don't translate literally | Use Dart/Flutter idioms. A UITableViewDataSource is not a class in Flutter — it's a ListView.builder |
| Stay on task | Convert only the files listed in the ticket. Don't touch other files |
| pubspec.yaml | Add packages only if the ticket's conversion requires them and they're in the codebook |
| Git | No pull. No base branch edits. Merge script handles push |
| Fixable ≠ fatal | Analysis/format failures are fixable. Read the error, fix, re-run. Never emit `failed` for these |
| No tests | Don't write tests unless the ticket explicitly asks for them |
