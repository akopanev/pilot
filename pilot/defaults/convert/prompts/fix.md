# Protocol: Fix

Task: `{{var:PILOT_TASK_ID}}`

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:stuck>description</signal:stuck>` — contradictions in notes, cannot fix
- `<signal:failed>reason</signal:failed>` — fatal only
- No signal = advance to verify

## Steps

1. `tk show {{var:PILOT_TASK_ID}}` — read ALL notes. Find the FAIL and VERIFY FAIL reasons.
2. Read the codebook: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK}}`.
3. `<signal:update>fix: {{var:PILOT_TASK_ID}}</signal:update>`
4. `git checkout {{var:PILOT_WORKING_BRANCH}}`
5. **Detect contradictions**: Read notes chronologically. If note A says
   "use Provider" and note B says "use Riverpod" — that's a Catch-22.
   Check the codebook to resolve. If the codebook doesn't help, emit
   `<signal:stuck>` with description. Do not attempt to fix.
6. **Fix**: Address every reported issue. Surgical — fix what was reported,
   nothing else. For conversion fixes:
   - Re-read the original iOS source if the note says logic is wrong
   - Check the codebook if the note says patterns are wrong
   - Fix imports if the note says dependencies are wrong
7. Run `flutter analyze` in `{{var:PILOT_FLUTTER_DIR}}/` after fixing.
   If new errors appear, fix those too.
8. Run `dart format {{var:PILOT_FLUTTER_DIR}}/lib/`.
9. `git add . && git commit -m "{{var:PILOT_TASK_ID}}: fix review issues"`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Fix what was reported | Don't argue with the reviewer. Don't add improvements. Fix the listed issues |
| Use the codebook | When fixing patterns, follow the codebook, not your own preferences |
| Stay surgical | Every change must address a reported issue. Don't refactor or clean up |
| Re-read source | If told the conversion is wrong, re-read the original iOS code. Don't guess |
| Git | No push. No pull. No base branch edits |
| Fixable ≠ fatal | Analysis failures are fixable. Never emit `failed` for these |
