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
Checks out default branch, pulls latest, queries `tk ready` for next task. Creates `feat/<id>` branch. Emits `<signal:var key=PILOT_TASK_ID>` and `<signal:ready>`.

No tasks? Emits `<signal:completed>` → pipeline stops.

### implement (AI)
Reads task (`tk show`), reads source, implements, verifies (build/lint/tests), self-reviews, commits. Emits progress updates throughout.

Always advances to review (no domain signal needed).

### review (AI)
Reads task + notes, checks out feature branch, diffs against base. Runs build/lint/tests, then manual verification (correctness, completeness, scope, security).

- **PASS**: Adds note to ticket (`tk add-note`), emits `<signal:approved>` → merge
- **FAIL**: Adds note with `file:line` issues + fix steps, emits `<signal:rejected>` → fix

### merge (shell)
Squash-merges feature branch into default branch, deletes feature branch, closes ticket (`tk close`). Returns to pick.

### fix (AI)
Reads task notes (FAIL reasons from `tk show`), surgically fixes only reported issues, verifies, commits. Returns to review.

## Vars

| Var | Source | Purpose |
|:----|:-------|:--------|
| `PILOT_DEFAULT_BRANCH` | pipeline.yaml | Base branch (default: `master`) |
| `PILOT_TASK_ID` | pick stage (`<signal:var>`) | Current task identifier |

## Customization

- **Tracker**: Scripts use `tk` ([ticket](https://github.com/wedow/ticket)). Replace commands in `scripts/pick.sh` and `scripts/merge.sh` for other trackers.
- **Prompts**: Edit `prompts/*.md` to match your project conventions, add `{{file:path}}` references for project context.
- **Runners**: Change executor/model in `pipeline.yaml` per stage.
- **Branch naming**: Edit `feat/$TASK` pattern in scripts and prompts.
