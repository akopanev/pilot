# PRD Pipeline Improvements — Design Document

**Date:** 2026-03-13
**Status:** Approved

## Problem

The current PRD pipeline generates a PRD in a single pass with no refinement. Intermediate outputs (research, analysis, baseline) may lose detail or context that downstream AI stages need. The result: PRDs that may have gaps, contradictions, or insufficient detail for autonomous AI execution in design and planning pipelines.

## Goals

1. **Crystal clarity across all stages** — every intermediate output (research.md, features.md, findings.md, prd.md) must be written with maximum detail and strong structure, optimized for downstream AI consumption.
2. **Multi-model PRD refinement loop** — after the initial PRD draft, multiple models review it from different perspectives, and the strongest model applies improvements. Loop until convergence or a safety cap.
3. **No token economy** — all prompts explicitly instruct for exhaustive detail. Never abbreviate, never summarize to save space, include all evidence and reasoning. Err on the side of too much detail.

## Design

### 1. Prompt Changes (All Stages)

Every prompt in the pipeline (research, analyze, baseline, prd, and the new review/refine stages) gets updated with these principles:

- **Maximum detail, structured output.** Use clear headings, consistent formatting, no prose walls. Every finding, feature, rationale, and decision must be explicitly stated.
- **No token economy.** Never abbreviate or omit information to save space. Include all supporting evidence, examples, and reasoning.
- **Downstream AI is the reader.** Write for crystal clarity — no ambiguity, no implicit knowledge, no "obvious" assumptions left unstated. Every output must stand alone as a complete document for an AI agent that has no prior context.

This applies to:
- `prompts/research.md` — demand signals, user voice, pain points
- `prompts/analyze.md` — per-app feature extraction from screenshots
- `prompts/baseline.md` — merged feature baseline
- `prompts/prd.md` — PRD generation

### 2. PRD Refinement Loop

#### New Pipeline Stages

After the existing `prd` stage, three new stages are added:

| Stage | Model | Role | Output |
|-------|-------|------|--------|
| `review_codex` | Codex (OpenAI) | Advisor — writes structured feedback | `data/review_codex.md` |
| `review_gemini` | Gemini | Advisor — writes structured feedback | `data/review_gemini.md` |
| `refine_critique` | Opus (Claude) | Decision-maker — reads PRD + reviews, applies changes, manages round counter | Updated `data/prd.md` |

#### Flow

```
gather → gather_reviews → research → analyze → baseline
  → prd (Opus, initial draft)
  → review_codex (Codex, writes feedback to data/review_codex.md)
  → review_gemini (Gemini, writes feedback to data/review_gemini.md)
  → refine_critique (Opus, reads PRD + both reviews, applies changes)
       ├─ changes made + round < N  →  repeat  →  review_codex
       ├─ no changes made           →  converged  →  __succeed__
       └─ round >= N                →  converged  →  __succeed__
```

#### Decision Authority

- **Opus always holds the pen.** Only the `refine_critique` stage modifies `data/prd.md`.
- **Codex and Gemini are advisors.** They write structured critique/feedback documents but never modify the PRD directly.
- **Opus weighs competing feedback**, resolves conflicts, and decides what to apply.

#### Stop Conditions

1. **Convergence (primary):** If Opus reads the reviews and determines no substantive changes are needed, it signals `converged`. The PRD is done.
2. **Safety cap (secondary):** If the round counter reaches `PILOT_PRD_REFINE_ROUNDS` (default: 3), signal `converged` regardless. Prevents runaway loops.
3. **Changes trigger re-review:** If Opus actually made changes to the PRD, it must signal `repeat` so the updated PRD gets fresh eyes from all three models.

#### Round Counter Mechanism

Uses existing `signal:var` primitive — no engine changes required:

- `refine_critique` reads `PILOT_PRD_ROUND` env var (default: 1)
- After processing, emits `<signal:var key=PILOT_PRD_ROUND>{incremented}</signal:var>`
- Checks round against `PILOT_PRD_REFINE_ROUNDS` to decide signal

### 3. New Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PILOT_PRD_REFINE_ROUNDS` | `3` | Maximum refinement rounds (safety cap) |
| `PILOT_REVIEW_CODEX` | `data/review_codex.md` | Codex review output path |
| `PILOT_REVIEW_GEMINI` | `data/review_gemini.md` | Gemini review output path |

### 4. New Prompts

Three new prompt files needed:

- **`prompts/review.md`** — Shared review prompt template. Instructs the model to read the current PRD and produce structured feedback organized by: gaps (missing information), contradictions (conflicting statements), clarity issues (ambiguous sections), completeness (missing features, screens, flows), and structural issues (ordering, grouping). The review must be specific — cite sections, quote problems, propose concrete fixes. Used by both `review_codex` and `review_gemini` stages.

- **`prompts/refine_critique.md`** — Instructs Opus to: (1) read the current PRD, (2) read all review feedback files, (3) evaluate each piece of feedback, (4) apply warranted changes to the PRD, (5) determine if substantive changes were made, (6) manage the round counter, (7) signal `repeat` or `converged`.

### 5. Pipeline Configuration Changes

The `pipeline.yaml` needs:
- Three new stage definitions (`review_codex`, `review_gemini`, `refine_critique`)
- Signal routing: `prd` → `review_codex` → `review_gemini` → `refine_critique`
- Self-loop routing: `refine_critique` `repeat` signal → `review_codex`
- Convergence routing: `refine_critique` `converged` signal → `__succeed__`
- Model assignment per stage node

### 6. Paper Trail

Each round's review files are overwritten (not accumulated), but the refine_critique prompt can log a summary of what changed per round to `data/prd_changelog.md` for traceability.

## What This Does NOT Change

- The pipeline engine — no new primitives needed, uses existing signals and vars
- The gather/gather_reviews shell stages — unchanged
- The downstream design and plan pipelines — they still consume `data/prd.md`
- The brief.md mechanism — still works as before

## Open Questions

1. Should the review prompt be identical for Codex and Gemini, or should they have different focus areas (e.g., Codex focuses on technical feasibility, Gemini on completeness)?
2. Should review files accumulate across rounds (append) or reset each round?
3. When Gemini executor lands, what model name/config does it use in pipeline.yaml?
