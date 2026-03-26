# Protocol: Integrate

All epics have been converted. The Flutter project has models, services,
state management, and UI screens — but they may not be fully wired
together. Your job is to make the app launch and run.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — app wired and building
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Codebook**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK}}`
- **Analysis**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_ANALYSIS}}`
  (original app structure — navigation flow, app lifecycle)
- **Flutter project**: `{{var:PILOT_FLUTTER_DIR}}/`

## Execution

1. `<signal:update>integrating Flutter app</signal:update>`
2. Read the codebook — architecture decisions, navigation approach, DI setup.
3. Read the analysis — original app's navigation flow, entry point, lifecycle.
4. Read the Flutter project's current state:
   - `{{var:PILOT_FLUTTER_DIR}}/lib/` — all converted files
   - `{{var:PILOT_FLUTTER_DIR}}/pubspec.yaml` — dependencies
5. **Wire main.dart**:
   - App entry point with MaterialApp / CupertinoApp
   - Top-level providers (Riverpod ProviderScope, etc.)
   - Theme configuration
   - Initial route
6. **Wire navigation**:
   - Complete the router with ALL screens
   - Match the original app's navigation flow from the analysis
   - Handle deep links if the original app supported them
7. **Wire dependency injection**:
   - Ensure all services are provided at the right scope
   - Ensure repositories have their dependencies
   - Ensure screens can access their providers
8. **Check for missing glue**:
   - Screens that reference services not yet provided
   - Models imported with wrong paths
   - Packages in code but not in pubspec.yaml
   - Orphaned files not connected to anything
9. **Run flutter analyze**. Fix all errors.
10. **Run dart format**. Fix all formatting.
11. **Attempt build**: `flutter build ios --no-codesign` (if on macOS)
    or `flutter build apk` — fix any build errors.
12. Commit and push:
    ```bash
    git add . && git commit -m "convert: integration wiring"
    git push
    ```
13. `<signal:completed>app integrated and building</signal:completed>`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Read everything first | Understand the full project before wiring. Don't guess |
| Follow the codebook | Use the chosen state management, navigation, and DI patterns |
| Match original flow | The navigation graph should mirror the iOS app's flow from the analysis |
| Don't rewrite | Wire existing code together. Don't rewrite converted files |
| Must build | Don't emit completed until flutter analyze passes and build succeeds |
| No new features | Wire what was converted. Don't add splash screens, analytics, or features not in the original |
