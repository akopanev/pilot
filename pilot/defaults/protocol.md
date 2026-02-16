# Pilot Signal Protocol

Pilot communicates with agents via XML signals embedded in your output. When you need to signal the pipeline, output the exact XML tag below. Pilot parses these from your response and acts on them.

## Completion Signals

### completed — Step finished successfully
```
<pilot:completed>brief summary of what was done</pilot:completed>
```
Use when your task is done and verified. The pipeline moves to the next step.

### skip — Step not applicable
```
<pilot:skip>reason why this step was skipped</pilot:skip>
```
Use when the task doesn't apply (e.g., empty input, SKIP_ME marker).

## Review Signals (convergence loops only)

### approve — Review passed, no issues
```
<pilot:approve/>
```
Use when review found ZERO confirmed issues. Exits the review loop.

### reject — Issues found, needs another iteration
```
<pilot:reject>description of issues found and what needs fixing</pilot:reject>
```
The reject payload becomes `{{FEEDBACK}}` in the next iteration. Use when you found real issues that need fixing.

### blocked — Cannot proceed, needs human
```
<pilot:blocked>description of what's blocking progress</pilot:blocked>
```
Use when something prevents completion and requires human intervention. Halts the pipeline.

## Data Signals

### emit — Pass data to subsequent steps
```
<pilot:emit key="name">content to store</pilot:emit>
```
Stored in pipeline state. Subsequent steps access it via `{{emit.name}}`. Use for passing structured data between pipeline phases (e.g., snapshot, PRD).

### update — Write or update a file
```
<pilot:update path=".pilot/path/to/file.md">file content</pilot:update>
```
Writes content to the specified path (relative to project root). Creates parent directories if needed. Use for producing artifacts (PRD, task files, reports).

## Rules

1. **One terminal signal per step** — output exactly one of: completed, skip, approve, reject, blocked
2. **emit and update are additive** — you can output multiple emits and updates alongside a terminal signal
3. **Signal order matters** — pilot processes signals in order of appearance
4. **No signal = implicit completion** — if you output no terminal signal, pilot treats it as completed (but explicit is better)
5. **reject payload is critical** — the text in reject becomes the FEEDBACK for the fix step. Be specific about what's wrong and where.
