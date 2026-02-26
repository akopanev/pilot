# pilot

Fresh-context orchestrator for AI-driven development.

Runs any methodology (GSD, BMAD, Ralph, custom) in a loop — each round gets a clean context window. The methodology manages its own state via files on disk. Pilot just keeps the loop going.

**The value:** Your methodology defines *what* to build. Pilot handles *how* to execute it — fresh context per round, signal-based flow control, multi-prompt composition. Engines are pluggable — bring your own.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/akopanev/pilot/master/install.sh | bash
```

Creates `.pilot/` in your project.

## Quick start

```bash
# GSD methodology (included)
.pilot/pilot.sh -m opus -p .pilot/prompts/signals.md -p .pilot/prompts/gsd.md -p BRIEF.md -e claude-code -n 20

# stack prompts: signals + methodology + context + instructions
.pilot/pilot.sh -m opus -p .pilot/prompts/signals.md -p .pilot/prompts/gsd.md -p BRIEF.md -p "skip research phase" -e claude-code -n 20

# any methodology — just point at your prompt
.pilot/pilot.sh -m opus -p .pilot/prompts/signals.md -p my-workflow.md -e claude-code -n 10

# codex + o3
.pilot/pilot.sh -m o3 -p .pilot/prompts/signals.md -p PROMPT.md -e codex -n 10

# custom engine
.pilot/pilot.sh -m opus -p .pilot/prompts/signals.md -p PROMPT.md -e ./my-engine.sh -n 10

# verbose — stream agent output live
.pilot/pilot.sh -m opus -p .pilot/prompts/signals.md -p .pilot/prompts/gsd.md -p BRIEF.md -e claude-code -n 20 -v
```

## How it works

```
while true:
    read prompts (files + inline text, concatenated)
    run engine with prompt
    if <loop:update> → print progress in real-time
    if <loop:done> → exit
    if <loop:failed> → stop with error
    next round (fresh context)
```

Each round is a fresh process. The agent reads state from disk, does one step, updates state, exits. Pilot restarts it for the next step. The methodology controls the flow — pilot is just the loop.

## Prompts

Pilot is methodology-agnostic. Pass one or more `-p` flags — they get concatenated:

```bash
.pilot/pilot.sh -m opus -p signals.md -p methodology.md -p project-brief.md -e claude-code -n 20
```

Files are re-read each round, so you can edit mid-loop.

**Included:**
- `prompts/signals.md` — loop signal protocol (update, done, failed, human)
- `prompts/gsd.md` — [GSD (Get Shit Done)](https://github.com/pashpashpash/get-shit-done) loop adapter

**Works with any methodology** that manages state via files: BMAD, Ralph, Compound Engineering, or your own.

## Signals

Defined in `prompts/signals.md` — include it in your prompt stack. The agent emits:

- `<loop:update>status</loop:update>` — progress, printed in real-time
- `<loop:done>summary</loop:done>` — all work complete, loop exits (exit 0)
- `<loop:failed>reason</loop:failed>` — stuck or blocked, loop stops (exit 1)
- `<loop:human>question</loop:human>` — needs human input, logged to `.pilot/human.md`

Pilot parses these from the output regardless of engine. The signal *instructions* (what the AI should emit) live in the prompt. The signal *handling* (what pilot does when it sees them) lives in the loop.

## Engines

Engines are pluggable scripts. Pilot ships with `claude-code` and `codex`, but you can write your own.

**Interface:**
```
engine.sh <prompt-file> <model> <logfile>
```

**Environment:**
- `VERBOSE` — `0` or `1`
- `PILOT_DOCKER` — `1` if running in Docker (optional)

**Contract:**
1. Read the prompt from `<prompt-file>`
2. Run the AI model
3. Write full output to `<logfile>`
4. If `VERBOSE=1`, also stream output to stdout
5. Return the exit code from the AI tool

**Resolution:** `-e claude-code` looks for `engines/claude-code.sh` next to `pilot.sh`. `-e ./my-engine.sh` uses the path directly.

## Options

```
pilot.sh -m <model> -p <prompt> [-p ...] -e <engine> -n <max-rounds> [-v]

-m, --model <name>        model to use (e.g. opus, o3)
-p, --prompt <file|text>  prompt file or inline text (repeatable)
-e, --engine <name|path>  engine: claude-code, codex, or path to custom script
-n, --max-rounds <n>      max loop iterations (0 = unlimited)
-v, --verbose             stream agent output live
--human-block             stop loop on <loop:human> signals (default: defer)
```

All parameters except `-v` and `--human-block` are required.

**Human-in-the-loop:** When the agent needs human input (credentials, decisions, approvals), it emits `<loop:human>`. The question is always logged to `.pilot/human.md`. By default the loop continues (defer) — questions accumulate and you batch-answer later. With `--human-block`, the loop stops and waits for you to answer in `human.md` before re-running.

## Safety

- **Max rounds** enforced via `-n`
- **3 consecutive failures** → auto-stop
- **Short round detection** — warns if round < 5 seconds

## Docker

```bash
# first run (builds image)
.pilot/scripts/pilot-docker.py --build -m opus -p .pilot/prompts/signals.md -p .pilot/prompts/gsd.md -p BRIEF.md -e claude-code -n 20

# subsequent runs
.pilot/scripts/pilot-docker.py -m opus -p .pilot/prompts/signals.md -p .pilot/prompts/gsd.md -p BRIEF.md -e claude-code -n 20
```

Handles macOS Keychain extraction, credential forwarding, workspace mounting. See [Docker details](#docker-details) below.

## Files

```
pilot.sh                    # the loop
engines/claude-code.sh      # claude code engine
engines/codex.sh            # openai codex engine
prompts/signals.md          # loop signal protocol
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
