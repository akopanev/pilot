# PILOT

Config-driven state machine for AI agent workflows. Define stages, signals, and transitions in YAML — the engine runs the graph.

## Quick Start

```bash
# Install (Python 3.11+)
curl -sSL https://raw.githubusercontent.com/akopanev/pilot/master/install.sh | bash

# Scaffold .pilot/ in your project
cd your-project && pilot init

# Run locally
pilot run .pilot/pipeline.yaml

# Run in Docker (claude-code, codex, opencode pre-installed)
pilot-docker run .pilot/pipeline.yaml
```

Installs `pilot` and `pilot-docker` to `~/.local/bin/`.

## How It Works

Stages are nodes. Signals are edges. The engine loops:

**run stage → parse signals → follow edge → next stage**

```
       pick ──ready──▶ implement ──▶ review ──approved──▶ merge ──▶ pick
         │                             │
     completed                      rejected
         │                             │
       (exit)                         fix ──────────────▶ review
```

No stage is special. Any stage can point to any other stage — loops, branches, convergence are all just config. Agents emit signals; they don't decide routing.

## Config

```yaml
version: "0.1"
starting: pick

vars:
  PILOT_DEFAULT_BRANCH: master

stages:
  pick:
    runner:
      executor: shell
      command: "{{file:scripts/pick.sh}}"
    on_signal:
      ready: implement
      completed: __exit__
      default: pick

  implement:
    prompt: "{{file:prompts/implement.md}}"
    runner: { executor: codex, model: o3 }
    fallback_runner: { executor: claude-code, model: sonnet }
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

### Runners

| Executor | Description |
|----------|-------------|
| `shell` | Shell scripts/commands (uses `command:`) |
| `claude-code` | Claude Code (`--dangerously-skip-permissions`) |
| `codex` | OpenAI Codex (`--sandbox full-auto`) |
| `opencode` | OpenCode (`-m provider/model`) |
| anything else | Generic CLI (`<tool> --model M -p PROMPT`) |

Each stage has a `runner` and optional `fallback_runner`. Primary retries twice, then fallback retries twice. Three consecutive round failures stop the pipeline.

### Signals

Agents and scripts emit signals as XML tags in their output:

```xml
<signal:ready>tk-5c46</signal:ready>
<signal:approved>all checks pass</signal:approved>
<signal:rejected>tests failing</signal:rejected>
```

The engine matches the first domain signal against `on_signal:` to route. `default` catches rounds with no signal. `__exit__` stops the pipeline.

**Built-in signals** (not routed):
- `update` — real-time progress display
- `var` — persist a key-value pair: `<signal:var key=NAME>value</signal:var>`

### Templates

Prompts and commands support two template types, resolved fresh each round:

- **`{{file:path}}`** — inline file contents (relative to `.pilot/`, recursive)
- **`{{var:NAME}}`** — inline a var from `.pilot/vars`

### Vars

Key-value pairs persisted in `.pilot/vars`. Available as `{{var:NAME}}` in templates and as `$NAME` env vars in shell stages.

Set from three places: `vars:` in config, `<signal:var>` from agents, or direct file edit. Cleaned on pipeline exit.

## Docker

```bash
pilot-docker run .pilot/pipeline.yaml
pilot-docker --build run .pilot/pipeline.yaml    # rebuild image
ANTHROPIC_API_KEY=sk-... pilot-docker run .pilot/pipeline.yaml
```

Hermetic container with claude-code, codex, opencode pre-installed. Auto-builds image, mounts workspace, forwards credentials (Keychain, API keys, configs), matches host UID.

## Customization

**Stages** — add/remove/rewire stages in `pipeline.yaml`. Any graph topology works.

**Runners** — swap executor and model per stage. Mix shell scripts with different AI providers in one pipeline.

**Prompts** — edit `prompts/*.md`. Use `{{file:context/project.md}}` to inject project-specific context without duplicating it across prompts.

**Tracker** — the engine is tracker-agnostic. The default template uses [ticket](https://github.com/wedow/ticket) (`tk`). Replace commands in `scripts/pick.sh` and `scripts/merge.sh` for any other tracker.

**New pipelines** — `pipeline.yaml` is not limited to dev workflows. Define any stage graph: CI, deploy, content review, data processing — anything that benefits from signal-driven routing between AI/shell steps.

## CLI

```
pilot run <pipeline.yaml>              Run the pipeline
pilot run <pipeline.yaml> --dry-run    Show stages without executing
pilot run <pipeline.yaml> --verbose    Stream executor output to terminal
pilot validate <pipeline.yaml>         Validate config
pilot init                             Scaffold .pilot/ with default dev pipeline
```

## Persistence

| File | Purpose | Crash-safe | Cleaned on exit |
|------|---------|------------|-----------------|
| `.pilot/state` | Current stage | Yes | Yes |
| `.pilot/vars` | Key-value pairs | Yes | Yes |
| `.pilot/logs/` | Session logs (timestamped) | — | No |
