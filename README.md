# PILOT

Config-driven pipeline engine for AI agents. Define stages, transitions, and runners in YAML — the engine handles the state machine.

## Install

```bash
# One-line install (from private repo)
curl -sSL https://raw.githubusercontent.com/akopanev/pilot/main/install.sh | bash

# Or from a local checkout
PILOT_REPO=/path/to/pilot bash install.sh
```

Requires Python 3.11+. Installs to `~/.pilot/` with wrappers at `~/.local/bin/pilot` and `~/.local/bin/pilot-docker`.

## Quick Start

```bash
# Scaffold .pilot/ in your project
cd your-project
pilot init

# Preview the pipeline
pilot run .pilot/pipeline.yaml --dry-run

# Run the pipeline
pilot run .pilot/pipeline.yaml
```

`pilot init` creates:

```
.pilot/
├── pipeline.yaml           # pipeline config
├── prompts/                # prompt templates
│   ├── implement.md
│   ├── review.md
│   └── fix.md
└── scripts/                # shell stages
    ├── pick.sh
    └── merge.sh
```

Runtime state (gitignored):

```
.pilot/
├── state                   # current stage + round (crash recovery)
└── vars                    # persistent key-value pairs
```

## Docker

Run in a hermetic container with all tools pre-installed (claude-code, codex).

```bash
# Run from any project directory — image auto-builds on first use
cd ~/my-project
pilot-docker run .pilot/pipeline.yaml --dry-run
pilot-docker run .pilot/pipeline.yaml

# Force rebuild after pilot source changes
pilot-docker --build run .pilot/pipeline.yaml

# With API keys instead of CLI auth
ANTHROPIC_API_KEY=sk-... pilot-docker run .pilot/pipeline.yaml
```

The `pilot-docker` wrapper:
- Auto-builds the image on first use
- Mounts `$(pwd)` as `/workspace`
- Extracts Claude credentials from macOS Keychain
- Forwards codex/git config read-only
- Matches host UID for correct file ownership

---

## How It Works

PILOT is a state machine. Each **stage** runs an executor (shell script or AI agent), parses **signals** from the output, and transitions to the next stage based on the config.

```
pick ──ready──> implement ──> review ──approved──> merge ──> pick
                                 │
                              rejected
                                 │
                                fix ──────> review
```

The agent doesn't decide routing — the config does.

## Pipeline Config

```yaml
version: "0.1"

vars:                         # exported as env vars every round
  PILOT_DEFAULT_BRANCH: master

stages:
  pick:
    runner:
      executor: shell         # shell stages use command:
      command: |
        {{file:scripts/pick.sh}}
    on_signal:
      ready: implement        # signal → next stage
      completed: __exit__     # stop pipeline
      default: pick           # no signal → retry

  implement:
    prompt: |                 # AI stages use prompt:
      {{file:prompts/implement.md}}
    runner:
      executor: codex
      model: o3
    fallback_runner:          # fallback if primary fails (2 retries each)
      executor: claude-code
      model: sonnet
    on_signal:
      default: review
```

### Stages

Named steps. First stage in YAML is the entry point.

### Runners

Executors that run each stage:

| Executor | Mode | Description |
|----------|------|-------------|
| `shell` | command | Run shell scripts/commands |
| `claude-code` | AI | Claude Code (JSON stream, `--dangerously-skip-permissions`) |
| `codex` | AI | OpenAI Codex CLI (`--sandbox full-auto`) |
| `opencode` | AI | OpenCode (`--dangerously-skip-permissions`) |
| anything else | AI | Generic CLI tool (`<tool> --model M -p PROMPT`) |

### Signals

Structured output from agents/scripts — XML tags in stdout:

```xml
<signal:ready>tk-5c46</signal:ready>
<signal:approved>all checks pass</signal:approved>
<signal:var key=PILOT_TASK_ID>tk-5c46</signal:var>
<signal:update>running tests...</signal:update>
<signal:failed>build error</signal:failed>
```

Built-in signals:
- `update` — progress display (doesn't affect routing)
- `failed` — stop pipeline with error
- `var` — persist key-value pair to `.pilot/vars`

Domain signals (`ready`, `approved`, `rejected`, etc.) are config-defined per stage.

### Transitions

Signal-to-stage mapping in `on_signal:`:
- `ready: implement` — go to implement on `ready` signal
- `completed: __exit__` — stop the pipeline
- `default: pick` — fallback when no domain signal is emitted

### Templates

Resolved in prompts and commands before execution:
- `{{file:path}}` — inline file contents (relative to config dir, recursive)
- `{{var:NAME}}` — inline var value from `.pilot/vars`

### Retry & Fallback

Engine behavior (not in config): primary runner retries twice, then fallback runner retries twice. If all 4 attempts fail, the round fails. Three consecutive round failures stop the pipeline.

## Persistence

**State** (`.pilot/state`) — current stage and round number. Survives crashes — the engine resumes where it left off. Cleaned on `__exit__`.

**Vars** (`.pilot/vars`) — persistent key-value pairs exported as env vars every round:

```
PILOT_DEFAULT_BRANCH=master
PILOT_TASK_ID=tk-5c46
```

Three sources:
1. `vars:` in pipeline.yaml — written every round
2. `<signal:var key=NAME>value</signal:var>` — emitted by agents/scripts
3. Direct file edit — scripts can write to `.pilot/vars` directly

All cleaned on `__exit__`.

## Commands

```
pilot run <pipeline.yaml>              Run the pipeline
pilot run <pipeline.yaml> --dry-run    Show stages without executing
pilot validate <pipeline.yaml>         Validate config
pilot init                             Scaffold .pilot/ with default dev pipeline
```

## Project Structure

```
src/pilot/
  cli.py            CLI entry point
  config.py         YAML loading + validation
  models.py         Stage, Runner, Transition, PipelineConfig
  engine.py         State machine loop (retry, fallback, signals)
  signals.py        <signal:NAME> parser (XML with attrs)
  templates.py      {{file:path}} and {{var:NAME}} resolution
  state.py          .pilot/state read/write
  vars.py           .pilot/vars read/write/export
  display.py        Terminal output (rich)
  executors/
    shell.py        Shell command executor
    claude.py       Claude Code (JSON stream)
    codex.py        Codex CLI
    opencode.py     OpenCode (dangerous mode)
    generic.py      Generic CLI tool
  defaults/
    develop/        Shipped dev pipeline template
scripts/
  pilot-docker      Docker wrapper with credential forwarding
  init-docker.sh    Container entrypoint (credential copy)
```
