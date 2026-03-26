# Protocol: Epic Decomposition — Conversion Tasks

You're decomposing one epic into conversion tasks. You have access to the
iOS source code, the codebook, and the existing Flutter project. Read the
code, understand what needs to be converted, and create focused tasks.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — epic fully ticketed
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Codebook**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK}}`
- **Analysis**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_ANALYSIS}}`
- **Inventory**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_INVENTORY}}`
- **Current epic ID**: `{{var:PILOT_CURRENT_EPIC}}`
- **Current epic title**: `{{var:PILOT_CURRENT_EPIC_TITLE}}`
- **Current epic content**:
{{var:PILOT_CURRENT_EPIC_CONTENT}}
- **Existing tickets**: `tk list` for cross-epic dependencies
- **iOS source**: `{{var:PILOT_IOS_DIR}}/` (read the actual files)
- **Flutter project**: `{{var:PILOT_FLUTTER_DIR}}/` (what's already converted)

## Execution

### Step 1: Read and understand

1. Read the codebook — this is your conversion pattern reference.
2. **Read the iOS source files listed in this epic.** Not just the file
   names — read the actual code. Understand:
   - What each class/struct/enum does
   - How they relate to each other
   - Which are simple (data classes, enums) vs complex (stateful logic)
   - What their public APIs look like
   - What external deps they use
3. Read the Flutter project's current state — `{{var:PILOT_FLUTTER_DIR}}/lib/`.
   See what's already converted. Check the imports and public APIs so you
   know what's available for this epic's tasks to build on.
4. Run `tk list` to see existing tickets.
5. `<signal:update>read sources, decomposing {{var:PILOT_CURRENT_EPIC_TITLE}}</signal:update>`

**Do NOT proceed until you have read the source files.** You can't create
good tasks from file names alone.

### Step 2: Think about the decomposition

Based on what you read in the code:
- What are the natural conversion units? Files that belong together?
- What's the dependency order within this epic?
- What's simple enough for fast conversion vs what needs careful work?
- Are there shared utilities or base classes that need to come first?
- How does this connect to what's already converted?

Each task should convert one **logical unit** — a group of related files
that make sense together. For model epics, maybe one or a few related
model files per task. For service epics, a service with its helpers.
For UI epics, a screen with its supporting widgets.

**Sizing**: keep tasks focused. Each should be one clear conversion job.
Small enough that the AI can do it well, big enough to be meaningful.

### Step 3: Create tasks

For each task, define:

- **Title**: verb-first, specific. "Convert User and Profile models to
  Dart freezed classes"
- **Description**: the conversion agent reads ONLY this ticket. Include:
  - **Source files** — exact iOS paths to read
  - **Target files** — exact Dart paths to create (codebook structure)
  - **What to convert** — classes, methods, protocols. Be specific about
    which codebook patterns apply (e.g., "Codable → freezed with
    json_serializable per codebook")
  - **Dependencies** — already-converted Dart files to import (exact paths)
  - **How it fits** — what depends on this output
  - **Acceptance criteria** — testable. At minimum:
    ```
    AC1: flutter analyze passes with no errors
    AC2: All public APIs from source files have Dart equivalents
    ```
  - **Out of scope** — what NOT to convert
- **Tags**: model, service, ui, network, persistence, state
- **Depends on**: task deps within this epic, or `tk` IDs for cross-epic

### Step 4: Create tickets in parallel

Launch one Agent per task — ALL in a single message so they run
concurrently. Each agent runs `tk create`:

```
Create a ticket using tk. Run this command and return ONLY the ticket ID:

tk create "[Task Title]" \
  -d "[description]" \
  -t task \
  --parent {{var:PILOT_CURRENT_EPIC}} \
  --tags [tags]

Return the ticket ID (format: xx-xxxx). Nothing else.
```

### Step 5: Wire dependencies

After all agents return:

```bash
tk dep [T2_ID] [T1_ID]
tk dep [T3_ID] [T2_ID]
# cross-epic deps if any
```

### Step 6: Verify

```bash
tk dep tree --full {{var:PILOT_CURRENT_EPIC}}
```

`<signal:completed>{{var:PILOT_CURRENT_EPIC_TITLE}}: N tasks, D deps</signal:completed>`

## Rules

| Rule | Constraint |
|:-----|:-----------|
| One epic only | Decompose `{{var:PILOT_CURRENT_EPIC_TITLE}}`, nothing else |
| Read the code | Read actual source files. You can't make good tasks from file names alone |
| Use the codebook | Every task should reference relevant codebook patterns |
| Check existing code | Know what's already converted before creating tasks |
| Self-contained tickets | The conversion agent reads ONLY the ticket. It must have everything |
| Specific paths | Both source (iOS) and target (Dart) file paths must be exact |
| Acceptance criteria | Every task needs testable criteria |
| Dependency order | Convert what's depended on first |
| Parallel agents | Create ALL tickets in ONE message |
| --parent is mandatory | Every task: `--parent {{var:PILOT_CURRENT_EPIC}}` |
| Use your judgment | You read the code. You know what makes sense. Group accordingly |
