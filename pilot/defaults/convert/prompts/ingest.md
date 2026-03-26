# Protocol: Ingest iOS Codebase

You are about to convert a large iOS app to Flutter/Dart. Before anything
else, you need to deeply understand what this app is and how it works.

Read the code. Explore freely. Follow imports, trace call chains, open
files that look important. Your analysis feeds every downstream stage —
the codebook, epics, and every conversion task depend on what you find
here. Be thorough.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — analysis written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Inventory**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_INVENTORY}}`
  (JSON: file lists, deps, stats from the inventory scan)
- **iOS source**: `{{var:PILOT_IOS_DIR}}/`
  (the actual project — read the source files)

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_ANALYSIS}}`

## Execution

1. Read the inventory JSON to get the lay of the land — file counts,
   dependency list, project structure.
2. `<signal:update>ingesting {{var:PILOT_IOS_DIR}} — reading source files</signal:update>`
3. **Explore the codebase.** You have full freedom to read any file. Start
   wherever makes sense — entry points, the most-imported files, the
   biggest files, whatever gives you the fastest understanding. Some
   things to look for as you explore:
   - What does the app DO? What are its features from a user's perspective?
   - How is it structured? MVC? MVVM? Coordinators? Mixed? Layered?
   - Where's the boundary between UI and business logic?
   - What patterns repeat? (base classes, protocols, common utilities)
   - What depends on what? Can you see natural layers?
   - What's going to be easy to convert vs hard?
   - Are there parts that are dead code or deprecated?
   - What third-party deps are used and WHY?
4. **Think out loud in your analysis.** Don't just list files — explain
   what you understand about the app's architecture, where the complexity
   lives, what the tricky parts will be. Future stages need your
   reasoning, not just your catalog.

## What the analysis must cover

The downstream stages need to know:

- **What the app does** — features, user flows, screens
- **How the code is layered** — models, networking, services, persistence,
  state management, UI. Which files belong to which layer.
- **Dependency graph** — what depends on what, both between files/modules
  and in terms of third-party packages
- **Complexity assessment** — which parts are straightforward conversion
  (data models, simple services) vs which need careful thought (custom UI,
  complex state, native integrations)
- **Conversion risks** — patterns with no clean Flutter equivalent, heavily
  used base classes, native-only APIs, anything that might block conversion
- **Your recommendations** — based on what you see in the code, what
  should be converted first? What patterns should the Dart app use? What
  iOS patterns should NOT be translated literally?

Structure your analysis however makes sense for this specific codebase.
The format should serve the content, not the other way around.

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Read the code | Read actual source files. Don't guess from file names alone |
| Think, don't just list | Explain WHY things are the way they are. Your reasoning matters for downstream stages |
| Be specific | File paths, class names, method signatures — not vague descriptions |
| Layer-first lens | Identify and separate: models, services, UI. The conversion goes in that order |
| Rate complexity | Every module gets simple/medium/complex. This drives model selection during conversion |
| Note what's risky | Patterns that will be hard to convert, native APIs, deep UIKit coupling |
| Skip tests | Focus on production code |
| Skip Pods/SPM internals | Analyze what deps are USED for, not their source code |
| Take your time | This is the most important stage. A shallow analysis means bad epics, bad tasks, bad conversions |
