# PILOT

Config-driven state machine for AI agent workflows. Define stages, signals, and transitions in YAML — the engine runs the graph.

## CLI

```
pilot run <pipeline.yaml>              Run the pipeline
pilot run <pipeline.yaml> --dry-run    Show stages without executing
pilot run <pipeline.yaml> --verbose    Stream executor output to terminal
pilot run <pipeline.yaml> --var K=V    Set a pipeline var at launch (repeatable);
                                       overrides yaml `vars:` defaults
pilot validate <pipeline.yaml>         Validate config
pilot init                             List available pipelines
pilot init <name> [<name>...]          Install selected pipelines into .pilot/
pilot init --all [--force]             Install everything (--force to overwrite)
pilot init-skill                       List installed pipelines that have a skill template
pilot init-skill <name> [--force]      Copy <pipeline>'s SKILL.md template into
                                       .claude/skills/<name>/ for use in Claude Code
pilot graph <pipeline.yaml>            Generate PNG visualization of the pipeline
                                       (-o FILE sets output path; --no-open skips opening)
```

## Quick Start

```bash
# Install (Python 3.11+)
curl -sSL https://raw.githubusercontent.com/akopanev/pilot/master/install.sh | bash

# List available pipelines
cd your-project && pilot init

# Scaffold one or more into .pilot/
pilot init dev
pilot init dev plan          # multiple
pilot init --all             # everything

# Run locally
pilot run .pilot/dev/pipeline.yaml

# Run in Docker (claude-code, codex, gemini, opencode pre-installed)
pilot-docker run .pilot/dev/pipeline.yaml
```

Installs `pilot` and `pilot-docker` to `~/.local/bin/`.

## How It Works

Stages are nodes. Signals are edges. The engine loops:

**run stage → parse signals → follow edge → next stage**

```
       pick ──ready──▶ implement ──▶ verify ──approved──▶ review ──approved──▶ merge ──▶ pick
         │                              │                    │
     completed                       rejected             rejected
         │                              │                    │
       (exit)                          fix ◀─────────────────┘
                                        │
                                      stuck ──▶ escalate
```

No stage is special. Any stage can point to any other stage — loops, branches, convergence are all just config. Agents emit signals; they don't decide routing.

## Config

```yaml
version: "0.1"
starting: pick

vars:
  PILOT_DEFAULT_BRANCH: master

pre_pipeline: |
  echo "setup steps here"

on_pipeline_success: |
  echo "cleanup on success"

on_pipeline_failure: |
  echo "alert on failure"

stages:
  pick:
    runner:
      executor: shell
      command: "{{file:scripts/pick.sh}}"
    on_signal:
      ready: implement
      completed: __succeed__
      failed: __fail__
      default: pick

  implement:
    prompt: "{{file:prompts/implement.md}}"
    runner: { executor: codex, model: o3 }
    fallback_runner: { executor: claude-code, model: sonnet }
    pre_step: "echo 'starting implementation'"
    on_signal:
      default: review

  review:
    prompt: "{{file:prompts/review.md}}"
    runner: { executor: claude-code, model: opus }
    on_signal:
      approved: merge
      rejected: fix
      default: review
```

### Stages

Named nodes in the graph. `starting:` sets the entry point (defaults to first stage). On crash, the engine resumes from the persisted stage.

Each stage supports optional `pre_step` and `post_step` — shell commands that run before and after the executor.

### Runners

| Executor | Description |
|----------|-------------|
| `shell` | Shell scripts/commands (uses `command:`) |
| `claude-code` | Claude Code (`--dangerously-skip-permissions`) |
| `codex` | OpenAI Codex (`--dangerously-bypass-approvals-and-sandbox`) |
| `gemini` | Google Gemini CLI (`--approval-mode yolo`) |
| `antigravity` | Google Antigravity CLI / `agy` (`--dangerously-skip-permissions`) |
| `opencode` | OpenCode (`opencode run -m MODEL PROMPT`) |
| anything else | Generic CLI (`<tool> --model M -p PROMPT`) |

Each stage has a `runner` and optional `fallback_runner`. Primary retries twice, then fallback retries twice. Three consecutive round failures stop the pipeline.

A runner takes `executor` and optional `model`. Add `args:` — a list of raw CLI tokens appended verbatim to that executor's invocation — to tune anything pilot doesn't model directly. They land after the executor's own default flags (so they can override them) and just before the prompt, and are resolved per-runner, so `fallback_runner` and each ensemble runner carry their own. The shell executor rejects `args:` (put flags in `command:`).

```yaml
runner:
  executor: codex
  model: gpt-5.5
  args: ["-c", "model_reasoning_effort=high"]   # codex layers -c last-wins
fallback_runner:
  executor: claude-code
  model: opus
  args: ["--effort", "high"]                      # each CLI's own flags
```

### Ensemble stages

Run the same prompt across N runners in parallel — useful for brainstorm, architecture, multi-model second opinions. Each runner can carry its own `vars:` block (per-runner template overrides) so the same prompt can address each one differently.

```yaml
brainstorm:
  pre_step: |
    {{file:scripts/setup.sh}}        # mkdir round dir, emit OUTPUT_* vars
  prompt: "{{file:prompts/spar.md}}"  # references {{var:OUTPUT}}
  runners:
    - executor: claude-code
      model: opus
      vars:
        OUTPUT: "{{var:OUTPUT_OPUS}}"
    - executor: codex
      model: gpt-5
      vars:
        OUTPUT: "{{var:OUTPUT_GPT5}}"
    - executor: gemini
      model: gemini-2.5-pro
      vars:
        OUTPUT: "{{var:OUTPUT_GEMINI}}"
  parallel: true                    # default; set false to serialize
  min_success: 2                    # round passes if K of N succeed (default: all)
  per_runner_timeout: 600           # seconds; default: none
  on_signal:
    default: synthesize             # ensemble stages only support 'default'
```

`pre_step` (and `post_step`, `pre_pipeline`, etc.) can publish vars by emitting `<signal:var key=NAME>VALUE</signal:var>` to stdout — same protocol agents already use. The engine resolves each runner's `vars:` against the current var namespace before substituting them into that runner's prompt.

Constraints: ensemble stages require `prompt` (no `shell` executor in `runners`), can't define `fallback_runner`, and may only have `default` in `on_signal` — route via the next stage's signals.

### Signals

Agents and scripts emit signals as XML tags in their output:

```xml
<signal:ready>tk-5c46</signal:ready>
<signal:approved>all checks pass</signal:approved>
<signal:rejected>tests failing</signal:rejected>
```

The engine matches the first domain signal against `on_signal:` to route. `default` catches rounds with no signal.

**Exit transitions:**
- `__succeed__` — stop the pipeline (clean exit, state cleared)
- `__fail__` — stop the pipeline (failure exit, state preserved for resume)

**Built-in signals** (not routed):
- `update` — real-time progress display
- `var` — persist a key-value pair: `<signal:var key=NAME>value</signal:var>`

### Pipeline Hooks

Top-level shell commands that run at pipeline lifecycle boundaries:

| Hook | When |
|------|------|
| `pre_pipeline` | Before the main loop starts |
| `on_pipeline_success` | After the main loop completes successfully |
| `on_pipeline_failure` | On pipeline failure or exception |

### Templates

Prompts and commands support two template types, resolved fresh each round:

- **`{{file:path}}`** — inline file contents (relative to `.pilot/`, recursive up to depth 10)
- **`{{var:NAME}}`** — inline a var from `.pilot/vars`

### Vars

Key-value pairs persisted in `.pilot/vars`. Available as `{{var:NAME}}` in templates and as `$NAME` env vars in shell stages.

Sources, in precedence order (later overrides earlier):

1. `vars:` block in `pipeline.yaml` — defaults, written only when not already set.
2. `--var KEY=VALUE` on `pilot run` — explicit user input at launch (multi-line values pass through; newlines are stored as `\n` literals in the vars file).
3. `<signal:var key=NAME>VALUE</signal:var>` from any signal-scanned context — agent stdout, `pre_step`, `post_step`, and pipeline-level hooks (`pre_pipeline`, `on_pipeline_*`). Same protocol everywhere.
4. Direct file edit of `.pilot/<dir>/vars`.

Per-runner overrides (`runner.vars: {...}`) layer on top of the above for a single executor invocation only — they don't mutate the shared vars file.

Cleaned on successful pipeline exit; preserved on failure (so resumes can pick up where they left off).

## Default Pipelines

`pilot init` (no args) lists what's available and exits. Pass one or more pipeline names to install them, or `--all` for everything. `--force` overwrites without confirmation; otherwise existing files prompt before overwrite (and skip in non-interactive shells).

| Pipeline | Path | Description |
|----------|------|-------------|
| **dev** | `dev/pipeline.yaml` | Pick task → implement → verify → review → fix → merge loop |
| **prd** | `prd/pipeline.yaml` | Gather competitor data → research → analyze → baseline → generate PRD |
| **design** | `design/pipeline.yaml` | Screens → theme → per-screen detail |
| **plan** | `plan/pipeline.yaml` | Create epics → pick epic → decompose into tasks (loop) |
| **convert** | `convert/pipeline.yaml` | iOS (Swift/Obj-C) → Dart (Flutter) source conversion |
| **localize** | `localize/pipeline.yaml` | Translate content into multiple locales |
| **ensemble** | `ensemble/pipeline.yaml` | Panel of independent models answers one question in parallel — dissent over consensus |

### Dev Pipeline

The default development workflow. Picks tasks from a tracker, implements them with AI, runs automated verification (typecheck, lint, tests), sends to AI code review, and squash-merges on approval. Includes an escalation stage for stuck review/fix loops.

```
pick → implement → verify → review → merge → pick
                     ↓         ↓
                    fix ←──────┘
                     ↓
                  escalate
```

### PRD Pipeline

Competitive research and PRD generation. Gathers competitor data via AppTweak API, fetches App Store reviews, runs demand-side research, extracts features per competitor, merges into a baseline, and generates a product requirements document.

### Design Pipeline

Design system generation from a PRD. Creates screen specifications, establishes a visual theme, then generates per-screen detailed designs.

### Plan Pipeline

Task decomposition from a PRD. Creates epic-level tickets, then loops through each epic to decompose it into implementable tasks.

## Docker

```bash
pilot-docker run .pilot/pipeline.yaml
pilot-docker --build run .pilot/pipeline.yaml    # rebuild image
ANTHROPIC_API_KEY=sk-... pilot-docker run .pilot/pipeline.yaml
```

Hermetic container with claude-code, codex, gemini, opencode pre-installed. Auto-builds image, mounts workspace, forwards credentials (Keychain, API keys, configs), matches host UID.

## Customization

**Stages** — add/remove/rewire stages in `pipeline.yaml`. Any graph topology works.

**Runners** — swap executor and model per stage. Mix shell scripts with different AI providers in one pipeline.

**Prompts** — edit `prompts/*.md`. Use `{{file:context/project.md}}` to inject project-specific context without duplicating it across prompts.

**Tracker** — the engine is tracker-agnostic. The default template uses [ticket](https://github.com/wedow/ticket) (`tk`). Replace commands in `scripts/pick.sh` and `scripts/merge.sh` for any other tracker.

**New pipelines** — `pipeline.yaml` is not limited to dev workflows. Define any stage graph: CI, deploy, content review, data processing — anything that benefits from signal-driven routing between AI/shell steps.

## Skills

A pipeline can declare a `skill: |` field at the top of its `pipeline.yaml`. The string is the verbatim contents of a [Claude Code skill](https://code.claude.com/docs/en/skills) — frontmatter + markdown body. `pilot init-skill <name>` writes that string to `.claude/skills/<name>/SKILL.md`, exposing the pipeline as a `/<name>` slash command in Claude Code.

```yaml
# pipeline.yaml
version: "0.1"
starting: spar

skill: |
  ---
  name: ensemble
  description: |
    Spar with three independent models on a strategic question.
    Surfaces dissent rather than consensus.
  allowed-tools: Bash(pilot-docker run *)
  ---

  The user asked: $ARGUMENTS

  ```!
  pilot-docker run .pilot/ensemble/pipeline.yaml --var "QUESTION=$1" >&2
  cat "$(ls -td .pilot/ensemble/runs/* | head -1)/synthesized.md"
  ```

  [post-output instructions for Claude]

stages:
  ...
```

Pilot doesn't transform the skill content — it's copied verbatim. The pipeline author owns the launch incantation, allowed-tools, post-instructions, everything. If a pipeline has no `skill:` field, `pilot init-skill <name>` errors with a hint.

## Persistence

| File | Purpose | Crash-safe | Cleaned on exit |
|------|---------|------------|-----------------|
| `.pilot/state` | Current stage | Yes | On success only |
| `.pilot/vars` | Key-value pairs | Yes | On success only |
| `.pilot/logs/` | Session logs (timestamped, per-round) | — | No |
