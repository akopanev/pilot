# Protocol: Figma Make Briefs

Consolidate theme, shared components, and per-screen details into
self-contained briefs — one markdown file per screen, ready to paste
into Figma Make. Also produce a feeding order so screens are designed
in a logical sequence (shared patterns first, then screens that depend
on them).

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — briefs written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Theme**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_THEME}}`
- **Screen map**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}`
- **Shared components**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS_DIR}}/_components.yaml`
- **Screen details**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS_DIR}}/{screen_id}.yaml`
- **Design references** (optional): `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DESIGN_REFS}}/`

## Output

- Briefs directory: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_BRIEFS_DIR}}/`
- One file per screen: `{nn}_{screen_id}.md` (nn = sequence number)
- Feeding guide: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_BRIEFS_DIR}}/_order.md`
- Shared components brief: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_BRIEFS_DIR}}/00_shared_components.md`

## Execution

1. Read theme.yaml, screens.yaml, _components.yaml, and all screen detail files.
2. `<signal:update>generating briefs for N screens</signal:update>`
3. **Determine feeding order.** Group screens into batches that should be
   designed together (e.g. onboarding flow, tab root screens, detail screens).
   Within each batch, order by dependency (a screen referenced as a navigation
   target should come after its parent).
4. Write `_order.md` — the feeding guide (see format below).
5. Write `00_shared_components.md` — shared component designs to establish
   first in Figma before any screens.
6. For each screen, write a self-contained brief `{nn}_{screen_id}.md`
   (see format below). The brief must include enough context that Figma Make
   can design the screen WITHOUT reading any other file.
7. `<signal:completed>N briefs + feeding guide written</signal:completed>`

## Feeding Guide Format (`_order.md`)

```markdown
# Figma Make — Feeding Order

Design screens in this order. Each batch builds on the previous.
Complete one batch before starting the next.

## Batch 0: Shared Components
- `00_shared_components.md`
- Establishes: empty states, error states, loading skeletons, toasts,
  list items, confirmation sheets
- These become reusable Figma components used by all screens

## Batch 1: Onboarding Flow
- `01_onboarding_welcome.md`
- `02_onboarding_goal.md`
- `03_onboarding_preferences.md`
- Why first: linear flow, establishes visual language

## Batch 2: Tab Root Screens
- `04_home_dashboard.md`
- `05_history_list.md`
- `06_profile.md`
- Why second: most complex screens, establish layout patterns

## Batch 3: Secondary Screens
- `07_log_entry.md`
- `08_entry_detail.md`
- ...

## Batch 4: Overlays & Sheets
- `09_paywall.md`
- `10_settings.md`
- ...

## Notes
- Each brief is self-contained — paste it directly into Figma Make
- Shared components (Batch 0) should be created as Figma components
  so subsequent screens can instance them
- If Figma Make struggles with a brief, split the screen:
  design the layout first, then add states in a follow-up prompt
```

## Shared Components Brief Format (`00_shared_components.md`)

```markdown
# Shared Components

Design these as reusable Figma components. They are used across
multiple screens in the app.

## Design System Context
<!-- Inline the relevant theme tokens -->
- **Colors**: primary {primary}, background {bg}, surface {surface}, ...
- **Typography**: {font_family} — body {body_size}/{body_weight}, ...
- **Spacing**: base unit {unit}px, screen padding {screen_padding}px
- **Shapes**: card radius {medium}px, button radius {small}px

## Components to Design

### 1. Empty State
Full-width centered layout used when a screen has no data.
- Illustration placeholder (120×120, centered)
- Title: h3, centered, foreground color
- Subtitle: body, centered, foreground_secondary
- Optional CTA button: primary style, centered below subtitle
- Vertical spacing: 16px between elements
- Used on: home (no entries), history (no records), ...

### 2. Error State
Centered layout shown when data fails to load.
- Alert icon (48×48, destructive color)
- Title: h3, "Something went wrong"
- Message: body, foreground_secondary
- "Try Again" button: secondary style
- Used on: any screen that fetches data

### 3. Loading Skeleton
...

### 4. Toast Notification
...

### 5. Confirmation Bottom Sheet
...

### 6. Standard List Item
...
```

## Per-Screen Brief Format (`{nn}_{screen_id}.md`)

Each brief is self-contained. Include everything Figma Make needs.

```markdown
# Screen: Home Dashboard

## Design Context
<!-- Compact theme summary — just enough for this screen -->
**App**: {app_name} — {category} app for {target_user}
**Style**: {emotional_tone}, {density} density
**Colors** (light mode):
- Background: {bg} | Surface: {surface} | Primary: {primary}
- Text: {fg} | Secondary text: {fg_secondary}
- Accent: {accent} | Border: {border}
**Typography**: {font_family}
- h2: {size}/{weight} | body: {size}/{weight} | caption: {size}/{weight}
**Spacing**: screen padding {n}px, section gap {n}px, element gap {n}px
**Shapes**: cards {n}px radius, buttons {n}px radius

## Screen Purpose
Main hub. Shows today's tracking progress, quick-add actions, and log.
Tab bar root screen — always accessible via Home tab.

## Layout
- Type: scrollable_sections, vertical scroll
- Safe areas: top + bottom (tab bar)
- Header: large title "Today", right actions: bell icon, gear icon

## Content (top to bottom)

### 1. Greeting (text, h2)
"Good morning, {name}"
Spacing below: 16px

### 2. Progress Ring (centered, 160px diameter)
- Circular progress showing water intake percentage
- Center: large percentage text
- Below ring: "{current} / {goal} ml" in body text
- Spacing below: 24px

### 3. Quick Add Row (3 equal-width buttons)
- "250ml" — secondary style, droplet icon
- "500ml" — secondary style, droplet icon
- "Custom" — outline style, plus icon
- Spacing below: 24px

### 4. Section Header
"Today's Log" left-aligned, "{count} entries" right-aligned, caption style
Spacing below: 12px

### 5. Entry List
- Each row: water-drop icon (left) | "{amount} ml" title + "{time}" subtitle | subtle separator
- Uses **Standard List Item** shared component
- Spacing below: 0 (extends to bottom)

### Floating Action Button
Plus icon, bottom-right, primary color, elevated shadow

## States

### Empty State
Uses **Empty State** shared component:
- Illustration: water-drop
- Title: "No entries yet"
- Subtitle: "Tap + to start tracking your water intake"
- CTA: "Add your first entry" → navigates to log entry

### Loading State
Uses **Loading Skeleton** shared component:
- Skeleton shimmer on: progress ring area, entry list (3 placeholder rows)
- Greeting + quick add buttons render immediately

### Error State
Uses **Error State** shared component:
- Message: "Could not load your data. Check your connection."
- Replaces progress ring + list area

## Interactions
- Pull down: refresh data
- Tap entry: navigate to entry detail
- Long press entry: context menu (edit, delete)
- Swipe left on entry: quick delete with undo toast
- Tap FAB: navigate to log entry
```

## Brief Writing Rules

| Rule | Constraint |
|:-----|:-----------|
| Self-contained | Every brief includes its own theme context. No external file references |
| Markdown only | Plain markdown — no YAML, no code blocks for data. Figma Make reads prose better |
| Concrete copy | Real UI text, real values, real units. Not "some label" |
| Visual order | Content sections listed top-to-bottom exactly as they appear |
| Reference shared components | Don't re-describe shared patterns — say "Uses **Empty State** shared component" with the specific params |
| Light mode first | Design in light mode. Dark mode comes from the color mapping in theme |
| One default state | The main content section describes the happy-path default state |
| States are separate sections | Loading, empty, error each get their own section describing what changes |
| Pixel values | Convert theme spacing units to px in the brief (unit × multiplier). Figma Make works in pixels |
| Keep it scannable | Use headers, bullet points, bold for key values. No long paragraphs |
| Size budget | Each brief should be under ~1500 words. If a screen is too complex, add a note to split it into layout + states as two Figma Make passes |
