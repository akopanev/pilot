# GSD Loop Adapter

You are running inside a fresh-context loop. Each round you wake up with NO memory of previous rounds.

## Setup

This project uses the GSD (Get Shit Done) methodology. The full methodology is installed in `.claude/` — agents, commands, templates, references. Use them.

## Every Round

1. Read `.planning/STATE.md` — it tells you where you are and what's next
2. If `.planning/` doesn't exist, run `/gsd:new-project` to initialize
3. Execute the ONE next step indicated by STATE.md
4. Update STATE.md with what you did and what the next round should do

## Step Routing

Follow STATE.md. Typical progression:

- "plan phase N" → run `/gsd:plan-phase N`
- "execute phase N" → run `/gsd:execute-phase N`
- "verify phase N" → run `/gsd:verify-work N`
- "fix failures" → address verification failures, then re-verify
- all phases complete → emit `<loop:done>`

## Constraints

- **One step per round.** Do not chain multiple phases.
- **STATE.md is truth.** Read it first, update it last.
- **Use the full methodology.** Spawn subagents, use templates, follow deviation rules — everything GSD provides.
- **Commit per task.** Atomic commits as GSD specifies.

## Project Brief

If initializing, read `BRIEF.md` from the project root for the project description. If no brief exists, emit `<loop:failed>no BRIEF.md found</loop:failed>`.
