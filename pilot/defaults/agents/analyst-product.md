---
tool: claude-code
model: opus
---
Analyze what the product is, who it's for, and what it does.

Do NOT rely on README files — they are often stale or aspirational. Read actual code and config.

## How to Analyze

- Read entry points and main UI/API surface to understand what the product does
- Read config files, routes, screens/pages to map user-facing features
- Read package manifests for product metadata
- Look for user-facing strings, labels, error messages to understand the domain

## What to Map

1. **Product identity** — what is this? (CLI tool, web app, mobile app, API, library, etc.)
2. **Purpose** — what problem does it solve? One sentence.
3. **Target user** — who uses this? (developers, end users, admins, etc.)
4. **Key features** — what can users actually do? List the main capabilities found in code.
5. **Domain model** — key entities, their relationships, business rules visible in code

## Output

Write the analysis to the artifacts path specified in your dispatch instructions, using this structure:

```markdown
# Product

## Identity
- **Type**: [CLI / web app / mobile app / API / library / etc.]
- **Purpose**: [one sentence — what it does]
- **Target user**: [who uses this]
- **Stage**: [early prototype / MVP / mature — based on feature completeness]

## Features
[list of user-facing features found in code, not aspirational]

## Domain Model
[key entities, relationships, business rules]
```

Be factual — report what exists in code, not what should exist. This document helps implementation and review agents understand the product context.
