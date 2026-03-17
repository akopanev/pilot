# Protocol: Screen Detail

Enrich each screen with content blocks, visual hierarchy, states, and
interactions. Write one file per screen. Be visually specific — these
specs are used to create screens in Figma.

Design for reusability: identify repeated patterns (empty states, error
states, loading skeletons, list items, headers, toasts) and use consistent
block definitions across screens so they map to reusable components.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — all screen details written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Screen map**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}`
- **Theme**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_THEME}}`
- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- **Competitor screenshots**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/*/`
- **Design references** (optional): `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DESIGN_REFS}}/`
  If this directory exists, these are the user's desired visual direction.
  Use them to inform layout patterns and content density.

## Output

Write one file per screen to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS_DIR}}/{screen_id}.yaml`

Create the directory if it doesn't exist.

## Execution

1. Read the existing screens.yaml (screen index from previous stage).
2. Read theme.yaml — the `direction` section tells you density, contrast,
   emotional tone. The `typography`, `spacing`, and `shape` sections give
   you exact values to reference. This influences how much content fits
   per screen and how elements are styled.
3. Read the PRD — feature details, user stories, scope for each screen.
4. Try to read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DESIGN_REFS}}/`. If it
   exists, open every image — these show the user's desired look and feel.
   Use them to inform content density and layout choices.
5. Create the output directory:
   `mkdir -p {{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS_DIR}}`
6. `<signal:update>enriching N screens</signal:update>`
7. **Identify reusable patterns first.** Before writing individual screens,
   scan all screens and identify shared patterns: empty states, error states,
   loading skeletons, list item layouts, headers, toasts, modals, bottom sheets.
   Write these to `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS_DIR}}/_components.yaml`
   (see Reusable Components format below).
8. For each screen in screens.yaml, write a detail file (see format below).
   Reference shared components by name from `_components.yaml` instead of
   re-describing them inline.
   For screens that need visual reference, open 1-2 competitor screenshots
   showing a similar screen type.
9. `<signal:completed>N screen details written + shared components</signal:completed>`

## Per-Screen File Format

Each file: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS_DIR}}/{screen_id}.yaml`

```yaml
id: home_dashboard
epic: daily_tracking

layout: scrollable_sections         # see layout patterns below
scroll: vertical                    # vertical | horizontal | none | paged
safe_areas: true                    # respect top/bottom safe areas

# Header / navigation bar
header:
  style: large_title                 # large_title | inline | hidden
  title: "Today"
  left_action: null                  # null | back | menu | close
  right_actions:
    - icon: bell
      action: navigate_to_notifications
    - icon: gear
      action: navigate_to_settings

# Content blocks — ordered top-to-bottom as they appear on screen.
# Be visually specific: describe what the user sees, approximate sizes,
# typography levels, and spatial relationships.
blocks:
  - id: greeting
    type: text
    typography: h2
    content: "Good morning, {name}"
    spacing_below: 4                 # in theme spacing units

  - id: daily_progress
    type: progress_ring
    size: 160                        # diameter in px
    alignment: center
    content:
      metric: water_intake
      goal: daily_goal
      unit: ml
      center_text: "{percentage}%"
      subtitle: "{current} / {goal} ml"
    spacing_below: 6

  - id: quick_add
    type: action_row
    content:
      actions:
        - label: "250ml"
          style: secondary            # primary | secondary | outline
          icon: droplet
        - label: "500ml"
          style: secondary
          icon: droplet
        - label: "Custom"
          style: outline
          icon: plus
      layout: equal_width_row
      behavior: tap adds amount instantly (except Custom → opens input)
    spacing_below: 6

  - id: section_header_log
    type: section_header
    content:
      title: "Today's Log"
      trailing: "{count} entries"
    spacing_below: 3

  - id: today_log
    type: list
    content:
      items: today's water entries, newest first
      per_item:
        leading: icon (water drop, colored by amount)
        title: "{amount} ml"
        subtitle: "{time}"
        trailing: null
      separator: subtle_line
      empty_state:
        icon: droplet
        title: "No entries yet"
        subtitle: "Tap + to start tracking"
        cta: "Add your first entry"

# Floating action button (if applicable)
fab:
  icon: plus
  action: navigate_to_log_entry
  position: bottom_right

# Screen states — reference shared components from _components.yaml
# Every screen MUST define: default (the blocks above), loading, and
# empty/error for any block that fetches data.
states:
  loading:
    component: loading_skeleton
    blocks_affected: [daily_progress, today_log]
  empty:
    component: empty_state
    params:
      illustration: water-drop
      title: "No entries yet"
      subtitle: "Tap + to start tracking your water intake"
      cta_label: "Add your first entry"
      cta_action: navigate_to_log_entry
  error:
    component: error_state
    params:
      error_message: "Could not load your data. Check your connection."

# Interactions beyond navigation
interactions:
  - trigger: pull_down
    action: refresh data
  - trigger: tap_entry
    action: navigate to entry detail
  - trigger: long_press_entry
    action: show context menu (edit, delete)
  - trigger: swipe_left_entry
    action: quick delete with undo toast
```

## Reusable Components Format

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS_DIR}}/_components.yaml`

Define shared patterns that appear across multiple screens. Each screen
references these by `component:` name instead of re-describing them.

```yaml
# Shared reusable components — referenced by screen detail files

components:
  # --- State patterns ---
  empty_state:
    description: "Generic empty state — centered illustration + title + subtitle + optional CTA"
    layout: centered_hero
    blocks:
      - type: image
        content: "{illustration}"         # caller provides illustration name
        size: 120
        alignment: center
      - type: text
        typography: h3
        alignment: center
        content: "{title}"
      - type: text
        typography: body
        color: foreground_secondary
        alignment: center
        content: "{subtitle}"
      - type: button
        style: primary
        label: "{cta_label}"              # optional — omit block if no CTA
        action: "{cta_action}"

  error_state:
    description: "Generic error — icon + message + retry button"
    layout: centered_hero
    blocks:
      - type: image
        content: alert-circle icon
        size: 48
        color: destructive
        alignment: center
      - type: text
        typography: h3
        alignment: center
        content: "Something went wrong"
      - type: text
        typography: body
        color: foreground_secondary
        alignment: center
        content: "{error_message}"
      - type: button
        style: secondary
        label: "Try Again"
        action: retry

  loading_skeleton:
    description: "Skeleton shimmer placeholders matching block shapes"
    note: >
      Each screen specifies which blocks show skeletons. The skeleton
      mirrors the block's size and position with a shimmer animation.
      This is one reusable component — not N different skeletons.

  toast:
    description: "Temporary notification bar — appears at bottom, auto-dismisses"
    variants:
      success: { icon: check-circle, color: primary }
      error: { icon: alert-circle, color: destructive }
      undo: { icon: rotate-ccw, color: foreground, trailing_action: "Undo" }

  confirmation_sheet:
    description: "Bottom sheet with title + message + destructive action + cancel"
    blocks:
      - type: text
        typography: h3
        content: "{title}"
      - type: text
        typography: body
        content: "{message}"
      - type: button
        style: destructive
        label: "{confirm_label}"
      - type: button
        style: outline
        label: "Cancel"

  list_item:
    description: "Standard list row — leading icon/avatar + title + subtitle + trailing"
    layout: row
    content:
      leading: "{icon_or_avatar}"
      title: "{title}"
      subtitle: "{subtitle}"
      trailing: "{trailing_text_or_icon}"
      separator: subtle_line

  # Add more as identified from the screen inventory
```

Screens reference shared components like this:

```yaml
states:
  empty:
    component: empty_state
    params:
      illustration: water-drop
      title: "No entries yet"
      subtitle: "Tap + to start tracking your water intake"
      cta_label: "Add your first entry"
      cta_action: navigate_to_log_entry
  error:
    component: error_state
    params:
      error_message: "Could not load your data. Check your connection."
  loading:
    component: loading_skeleton
    blocks_affected: [daily_progress, today_log]
```

## Layout Patterns

| Pattern | Use for |
|:--------|:--------|
| `scrollable_sections` | Dashboard, home — stacked content sections |
| `centered_hero` | Onboarding, empty states — centered illustration + text + CTA |
| `form` | Input screens, settings — label + input pairs |
| `list` | History, search results — scrollable item list with optional search/filter bar |
| `detail` | Item detail — header area + scrollable body |
| `card_grid` | Selection screens — grid or horizontal scrolling cards |
| `bottom_sheet` | Pickers, confirmations — partial overlay |
| `full_overlay` | Paywall, alerts — full-screen overlay with dismiss |
| `paged` | Onboarding sequence — horizontal swipe with page dots |
| `split_header` | Profile, stats — fixed header/hero area + scrollable content below |

## Block Types

| Type | Description |
|:-----|:------------|
| `text` | Static text with typography level |
| `header` | Section or screen header with optional subtitle |
| `section_header` | Section divider with title and optional trailing text |
| `progress_ring` | Circular progress indicator |
| `progress_bar` | Horizontal progress bar |
| `action_row` | Row of buttons or quick actions |
| `list` | Scrollable list of items with defined per-item layout |
| `card` | Elevated container with internal content |
| `card_row` | Horizontal scrolling row of cards |
| `image` | Illustration, photo, or icon (describe what it shows) |
| `chart` | Data visualization (describe chart type + data) |
| `input_field` | Text input with label and optional validation |
| `toggle_row` | Label + toggle switch |
| `segmented_control` | Tab-like selector for filtering/switching views |
| `empty_state` | Centered illustration + message + optional CTA |
| `banner` | Dismissible notification or promotion bar |

## Rules

| Rule | Constraint |
|:-----|:-----------|
| One file per screen | `{screen_id}.yaml` in the screens directory |
| Components file first | Write `_components.yaml` before any screen files |
| Reuse shared components | Empty, error, loading, toast, list items, confirmation sheets — define once in `_components.yaml`, reference by name in screens |
| ALL states required | Every screen: default + loading. Add empty + error for every block that fetches data. No screen may skip states |
| Visually specific | Describe what appears with enough detail to design it in Figma |
| Typography levels | Reference theme typography scale (display, h1, h2, h3, body, body_sm, caption) |
| Spacing in units | Use theme spacing units for `spacing_below` |
| Content is concrete | Use actual copy, field names, units — not "some text here" |
| Order = visual order | Blocks listed top-to-bottom as they appear on screen |
| Theme-aware | Respect the theme's density when deciding how much fits per screen |
| Competitor-informed | Open screenshots when unsure about layout or content patterns |
| Don't redesign | Detail existing screens. Don't add, remove, or rename screens |
| Include header | Every screen should specify its header/navigation bar style |
| Consistency | Same block type (e.g. list_item) should have identical structure across screens — vary only content |
