Generate a structured Product Requirements Document from the user's input and project artifacts.

## Protocol
{{file:protocol.md}}

## Inputs

### User Input
{{file:{{input_file}}}}

### Project Knowledge
Read these artifact files selectively — only what's relevant to the user's request:
- `.pilot/{{artifacts_dir}}/PROJECT.md` — project identity, stack, health
- `.pilot/{{artifacts_dir}}/ARCHITECTURE.md` — current architecture and patterns
- `.pilot/{{artifacts_dir}}/UX.md` — UI patterns (if UI work)
- `.pilot/{{artifacts_dir}}/QA.md` — test patterns (if test work)
- `.pilot/{{artifacts_dir}}/OPS.md` — deploy patterns (if infra work)

## Process

1. Read `.pilot/{{input_file}}` — this is your primary source
2. Read relevant artifacts from `.pilot/{{artifacts_dir}}/` — they provide context and patterns, not requirements
3. If PROJECT.md health = `needs_attention`, incorporate warnings into Technical Context
4. If `.pilot/{{prd_file}}` already exists, treat this as a revision — diff against the previous version
5. Produce the PRD using the format below

## PRD Format

```
# PRD — {Title}

## Objective
1-2 sentences. What does this increment achieve?

## Requirements

### Functional
- {Concrete, verifiable requirement}
- {Each requirement = one testable statement}

### Non-Functional
- {Performance, security, accessibility, etc.}

## Technical Context
- Stack: {from PROJECT.md}
- Affected modules: {from ARCHITECTURE.md}
- Existing patterns to follow: {from artifacts}
- Health warnings: {from PROJECT.md health, if any}

## Patterns
- {Relevant patterns from artifacts that implementation should follow}

## Assumptions
- {Explicit assumptions — things taken as given}

## Scope
- Size: small | medium | large
- Complexity: low | moderate | high

## Non-Goals
- {What this increment explicitly does NOT do}
- {Boundaries that prevent scope creep}

## Open Questions
- {Ambiguities that ideally need user clarification}
- {If none, omit this section}
```

## Scope Guidelines

| Size | Meaning | Expected tasks |
|------|---------|----------------|
| small | Single feature, few files | 1-6 tasks |
| medium | Multi-file feature, some integration | 7-20 tasks |
| large | Cross-cutting change, many modules | 20+ tasks |

## Rules

1. User input is the primary source — do NOT invent requirements the user didn't ask for
2. Artifacts provide context and patterns — do NOT override user intent with codebase conventions
3. For greenfield projects: artifacts are thin (mostly patterns from blueprint), that's expected
4. Be explicit about Non-Goals — what this increment does NOT do
5. Every functional requirement must be verifiable (can be tested as done/not-done)
6. Health warnings from snapshot MUST appear in Technical Context if present
7. The PRD is a user-facing document — clear, reviewable, no jargon soup
8. Flag ambiguities in Open Questions — don't guess on critical decisions

## Output

Write the PRD:

<pilot:update path=".pilot/{{prd_file}}">[full PRD content]</pilot:update>

When complete:
<pilot:completed>PRD generated</pilot:completed>
