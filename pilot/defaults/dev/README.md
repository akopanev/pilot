# Development Pipeline

Autonomous dev loop: pick task, implement, review, merge. Repeats until no tasks remain.

Uses [ticket](https://github.com/wedow/ticket) (`tk`) for task management — git-backed issue tracker designed for AI agents.

## Flow

```
pick ──ready──> implement ──> review ──approved──> merge ──> pick
                                │
                             rejected
                                │
                               fix ──────> review
```

## Stages

### pick (shell)
Checks out default branch, pulls latest, queries `tk ready` for next task. Creates feature branch. Emits `PILOT_TASK_ID`, `PILOT_WORKING_BRANCH` as vars and `<signal:ready>`.

No tasks? Emits `<signal:completed>` → pipeline stops.

### implement (AI)
Reads task (`tk show`), reads source, implements, verifies (build/lint/tests), self-reviews, commits. Emits progress updates throughout.

Always advances to review (no domain signal needed).

### review (AI)
Reads task + notes, checks out working branch, diffs against base. Runs build/lint/tests, then manual verification (correctness, completeness, scope, security).

- **PASS**: Adds note to ticket (`tk add-note`), emits `<signal:approved>` → merge
- **FAIL**: Adds note with `file:line` issues + fix steps, emits `<signal:rejected>` → fix

### merge (shell)
Squash-merges working branch into default branch, deletes working branch, closes ticket (`tk close`). Returns to pick.

### fix (AI)
Reads task notes (FAIL reasons from `tk show`), surgically fixes only reported issues, verifies, commits. Returns to review.

## Vars & State

Vars live in `.pilot/vars` — persisted across rounds, cleaned on pipeline exit.

| Var | Set by | Used by | Purpose |
|:----|:-------|:--------|:--------|
| `PILOT_DEFAULT_BRANCH` | pipeline.yaml (`vars:`) | pick, merge, review | Base branch |
| `PILOT_TASK_ID` | pick (`<signal:var>`) | implement, review, fix | Current task ID |
| `PILOT_WORKING_BRANCH` | pick (`<signal:var>`) | implement, review, fix, merge | Feature branch name |

**Round-by-round flow (vars + state):**

```
Round 1 — pick
  state: pick                            ← .pilot/state
  vars:  PILOT_DEFAULT_BRANCH=master     ← from pipeline.yaml
  ── pick.sh runs ──
  pick.sh emits:
    <signal:var key=PILOT_TASK_ID>nw-5c46</signal:var>
    <signal:var key=PILOT_WORKING_BRANCH>feat/nw-5c46</signal:var>
    <signal:ready>nw-5c46</signal:ready>
  engine writes vars → .pilot/vars:
    PILOT_DEFAULT_BRANCH=master
    PILOT_TASK_ID=nw-5c46
    PILOT_WORKING_BRANCH=feat/nw-5c46
  engine routes: ready → implement
  state: implement                       ← .pilot/state updated

Round 2 — implement
  state: implement
  engine resolves prompt templates:
    {{var:PILOT_TASK_ID}}         → "nw-5c46"
    {{var:PILOT_WORKING_BRANCH}}  → "feat/nw-5c46"
  ── codex runs with resolved prompt ──
  no domain signal → default → review
  state: review

Round 3 — review
  engine resolves prompt templates:
    {{var:PILOT_TASK_ID}}           → "nw-5c46"
    {{var:PILOT_WORKING_BRANCH}}    → "feat/nw-5c46"
    {{var:PILOT_DEFAULT_BRANCH}}    → "master"
  ── claude-code runs ──
  emits <signal:approved> → merge
  state: merge

Round 4 — merge
  merge.sh uses env vars: $PILOT_WORKING_BRANCH, $PILOT_DEFAULT_BRANCH, $PILOT_TASK_ID
  ── squash merge, delete branch, close ticket ──
  default → pick
  state: pick

  ... next task or <signal:completed> → __succeed__ (cleans state + vars)
```

Vars are available two ways:
- **`{{var:NAME}}`** in prompts — resolved by engine before sending to executor (100% reliable)
- **`$NAME`** as env vars — available in shell scripts

## Prompts & Templates

Prompts are markdown files in `prompts/`. The engine resolves two template types before sending to the executor:

- **`{{file:path}}`** — inline file contents (relative to `.pilot/`). Recursive — files can include other files.
- **`{{var:NAME}}`** — inline var value from `.pilot/vars`.

To add project-specific context to prompts, create files and reference them:

```markdown
## Context
{{file:context/project.md}}
{{file:context/conventions.md}}
```

## Customization

- **Tracker**: Scripts use `tk` ([ticket](https://github.com/wedow/ticket)). Replace commands in `scripts/pick.sh` and `scripts/merge.sh` for other trackers.
- **Prompts**: Edit `prompts/*.md` to match your project conventions, add `{{file:path}}` references for project context.
- **Runners**: Change executor/model in `pipeline.yaml` per stage.
- **Branch naming**: Change the `BRANCH="feat/$TASK"` line in `scripts/pick.sh` — all other files use the var.
