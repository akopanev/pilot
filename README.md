# pilot

Fresh-context orchestrator for AI-driven development.

Runs any methodology (GSD, BMAD, Ralph, custom) in a loop — each round gets a clean context window. The methodology manages its own state via files on disk. Pilot just keeps the loop going.

**The value:** Your methodology defines *what* to build. Pilot handles *how* to execute it — fresh context per round, signal-based flow control, multi-prompt composition. Model/executor switching is WIP.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/akopanev/pilot/master/install.sh | bash
```

Creates `.pilot/` in your project.

## Quick start

```bash
# GSD methodology (included)
.pilot/pilot.sh -m opus -p .pilot/prompts/gsd.md -p BRIEF.md -e claude-code -n 20

# stack prompts: methodology + context + instructions
.pilot/pilot.sh -m opus -p .pilot/prompts/gsd.md -p BRIEF.md -p "skip research phase" -e claude-code -n 20

# any methodology — just point at your prompt
.pilot/pilot.sh -m opus -p my-workflow.md -e claude-code -n 10

# codex + o3
.pilot/pilot.sh -m o3 -p PROMPT.md -e codex -n 10

# verbose — stream agent output live
.pilot/pilot.sh -m opus -p .pilot/prompts/gsd.md -p BRIEF.md -e claude-code -n 20 -v
```

## How it works

```
while true:
    read prompts (files + inline text, concatenated)
    run executor with prompt + loop signals
    if <loop:update> → print progress in real-time
    if <loop:done> → exit
    if <loop:failed> → stop with error
    next round (fresh context)
```

Each round is a fresh process. The agent reads state from disk, does one step, updates state, exits. Pilot restarts it for the next step. The methodology controls the flow — pilot is just the loop.

## Prompts

Pilot is methodology-agnostic. Pass one or more `-p` flags — they get concatenated:

```bash
.pilot/pilot.sh -m opus -p methodology.md -p project-brief.md -p extra-context.md -e claude-code -n 20
```

Files are re-read each round, so you can edit mid-loop.

**Included:**
- `prompts/gsd.md` — [GSD (Get Shit Done)](https://github.com/pashpashpash/get-shit-done) loop adapter

**Works with any methodology** that manages state via files: BMAD, Ralph, Compound Engineering, or your own.

## Signals

Appended to every prompt automatically. The agent emits:

- `<loop:update>status</loop:update>` — progress, printed in real-time
- `<loop:done>summary</loop:done>` — all work complete, loop exits (exit 0)
- `<loop:failed>reason</loop:failed>` — stuck or blocked, loop stops (exit 1)

## Options

```
pilot.sh -m <model> -p <prompt> [-p ...] -e <executor> -n <max-rounds> [-v]

-m, --model <name>        model to use (e.g. opus, o3)
-p, --prompt <file|text>  prompt file or inline text (repeatable)
-e, --executor <tool>     claude-code, codex
-n, --max-rounds <n>      max loop iterations (0 = unlimited)
-v, --verbose             stream agent output live
```

All parameters except `-v` are required.

## Safety

- **Max rounds** enforced via `-n`
- **3 consecutive failures** → auto-stop
- **Short round detection** — warns if round < 5 seconds

## Docker

```bash
# first run (builds image)
.pilot/scripts/pilot-docker.py --build -m opus -p .pilot/prompts/gsd.md -p BRIEF.md -e claude-code -n 20

# subsequent runs
.pilot/scripts/pilot-docker.py -m opus -p .pilot/prompts/gsd.md -p BRIEF.md -e claude-code -n 20
```

Handles macOS Keychain extraction, credential forwarding, workspace mounting. See [Docker details](#docker-details) below.

## Files

```
pilot.sh                    # the loop
prompts/gsd.md              # GSD methodology adapter
scripts/pilot-docker.py     # docker launcher
scripts/init-docker.sh      # container credential setup
Dockerfile                  # node:22 + claude-code + codex + gh + python3
```

## Docker details

- macOS Keychain extraction for subscription-based Claude auth
- Selective credential copy (skips multi-GB cache)
- Codex config (`~/.codex/`) forwarded
- `$(pwd)` mounted as `/workspace` (read-write)
- `.gitconfig` forwarded
- `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` pass-through
- Non-root user with matching UID
- Codex sandbox: `danger-full-access` in Docker (`PILOT_DOCKER=1`)
