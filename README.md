# pilot

Fresh-context loop for AI-driven development. Runs an AI tool repeatedly, each round with a clean context window. Your methodology manages state via files on disk — pilot just keeps the loop going.

## How it works

```
while true:
    read prompt (file or inline text)
    run executor (claude-code or codex) with prompt + loop signals
    extract <loop:update> → print progress
    if <loop:done> → exit
    if <loop:failed> → stop with error
```

Each round is a fresh process — no memory of previous rounds. The methodology prompt tells the agent to read its state from disk, do one step, and stop. Pilot restarts it for the next step.

## Install

Run from your project root:

```bash
curl -fsSL https://raw.githubusercontent.com/akopanev/pilot/main/install.sh | bash
```

Creates `.pilot/` in your project. Add `.pilot/` to `.gitignore` or commit it — your call.

## Usage

```bash
# bare metal — claude-code (default executor)
./pilot.sh opus PROMPT.md
./pilot.sh opus "fix the login bug" --max-rounds 10

# bare metal — codex
./pilot.sh o3 PROMPT.md --executor codex

# docker (handles auth, mounts workspace)
./scripts/pilot-docker.sh opus PROMPT.md
./scripts/pilot-docker.sh o3 PROMPT.md --executor codex

# first docker run (or after changes)
./scripts/pilot-docker.sh --build opus PROMPT.md
```

## Executors

| Executor | CLI | Auth |
|----------|-----|------|
| `claude-code` (default) | `claude -p --dangerously-skip-permissions --model MODEL` | macOS Keychain or `ANTHROPIC_API_KEY` |
| `codex` | `codex exec --sandbox full-auto --model MODEL` | `~/.codex/` config or `OPENAI_API_KEY` |

## Signals

The agent emits XML signals that pilot extracts:

- `<loop:update>status message</loop:update>` — progress updates, printed as they occur
- `<loop:done>summary</loop:done>` — all work complete, loop exits (exit 0)
- `<loop:failed>reason</loop:failed>` — agent is stuck, loop stops (exit 1)

These are appended to every prompt automatically.

## Safety

- **MAX=50** rounds by default (override with `--max-rounds N`, `0` for unlimited)
- **3 consecutive failures** → stops automatically
- **Short round detection** — warns if a round completes in under 5 seconds

## Files

```
pilot.sh                    # the loop
scripts/pilot-docker.sh     # docker launcher (keychain extraction, volume mounts)
scripts/init-docker.sh      # container init (credential setup)
Dockerfile                  # node:22 + claude-code + codex + gh + python3
```

## Docker details

The Docker setup handles:
- macOS Keychain extraction for subscription-based Claude auth
- Selective credential copy (skips multi-GB cache)
- Codex config (`~/.codex/`) forwarded
- `$(pwd)` mounted as `/workspace` (read-write)
- `.gitconfig` forwarded
- `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` pass-through
- Non-root user with matching UID
- Codex uses `danger-full-access` sandbox in Docker (detected via `PILOT_DOCKER=1`)

## Writing prompts

Pilot is methodology-agnostic. Your prompt file defines what the agent does — including how state is managed. That's up to your methodology (BMAD, GSD, Ralph, etc.), not pilot.

The key contract: **state lives in files, not in memory**. Each round reads state from disk, does one step, writes updated state. Pilot just runs the loop.
