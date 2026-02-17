---
tool: claude-code
model: opus
---
Analyze the user experience — navigation, screens, components, and interaction patterns.

Read actual code, not documentation. For mobile apps this analysis is critical — screen flows, gestures, animations, and platform conventions matter.

## How to Analyze

- Map all screens/pages/views — read navigation config, router, tab bar, drawer, stack navigators
- Read 3-5 representative screen components to understand patterns
- Check for design system / component library usage (styled-components, Tailwind, NativeBase, etc.)
- Look for state management patterns (Redux, Zustand, Context, MobX, etc.)
- Check loading states, error states, empty states across screens
- Look for accessibility — labels, roles, screen reader support, contrast
- Check for i18n/l10n setup
- For mobile: check for platform-specific code (iOS/Android), gestures, animations, haptics

## What to Map

1. **Navigation structure** — screen hierarchy, tab bars, drawers, stacks, deep links
2. **Screen inventory** — list of all screens/pages with their purpose
3. **Component patterns** — design system, shared components, styling approach
4. **State management** — how UI state flows, where data lives, caching strategy
5. **Interaction patterns** — forms, lists, modals, toasts, pull-to-refresh, infinite scroll
6. **Platform handling** — responsive design, platform-specific code, web vs mobile differences
7. **UX gaps** — missing states (loading, error, empty), inconsistent patterns, accessibility issues

## Output

Write the analysis to the artifacts path specified in your dispatch instructions, using this structure:

```markdown
# UX

## Navigation
[screen hierarchy — stacks, tabs, drawers, modals, deep link structure]

## Screens
| Screen | Purpose | States |
|---|---|---|
| [name] | [what it does] | [loading/error/empty handled?] |

## Component Patterns
- **Design system**: [library or custom]
- **Styling**: [approach — CSS modules, styled-components, Tailwind, StyleSheet, etc.]
- **Shared components**: [list of reusable components]

## State Management
- **Approach**: [Redux / Context / Zustand / etc.]
- **Data flow**: [how state flows from API to UI]
- **Caching**: [strategy if any]

## Interaction Patterns
[forms, lists, modals, navigation transitions, gestures, animations]

## Platform
- **Targets**: [web / iOS / Android / all]
- **Platform-specific code**: [what differs per platform]
- **Responsive**: [approach if any]

## Gaps
[missing states, inconsistent patterns, accessibility issues, broken flows]
```

Be factual — report what exists in code. This document helps implementation agents match existing UX patterns and review agents catch inconsistencies.
