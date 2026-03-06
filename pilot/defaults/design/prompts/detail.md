# Protocol: Screen Detail

Enrich each screen with content blocks, states, and interactions. Describe
WHAT appears on each screen — the implement agent (with gluestack skills)
decides HOW to build it.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — screens.yaml enriched
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

Enrich and overwrite: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}`

## Execution

1. Read the existing screens.yaml (screen inventory from previous stage).
2. Read theme.yaml — the `direction` section tells you density, contrast,
   emotional tone. This influences how much content fits per screen.
3. Read the PRD — feature details, user stories, scope for each screen.
4. Try to read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DESIGN_REFS}}/`. If it
   exists, open every image — these show the user's desired look and feel.
   Use them to inform content density and layout choices.
5. For screens that need visual reference, open 1-2 competitor screenshots
   showing a similar screen type.
6. `<signal:update>enriching N screens with detail</signal:update>`
7. For each screen, add the enrichment fields (see format below).
8. Write the enriched screens.yaml back to the same path.
9. `<signal:completed>N screens enriched</signal:completed>`

## Enrichment Fields

For each screen, add these fields alongside the existing ones:

```yaml
  - id: home_dashboard
    # ... existing fields (epic, purpose, description, entry, transitions) ...

    # --- Layout ---
    layout: scrollable_sections         # see layout patterns below
    scroll: vertical                    # vertical | horizontal | none | paged

    # --- Content blocks ---
    # Ordered top-to-bottom. Describe WHAT the user sees, not which
    # component renders it. The implement agent handles that.
    blocks:
      - id: greeting
        type: header
        content: "Good morning, {name} — here's your progress today"

      - id: daily_progress
        type: progress_ring
        content:
          metric: water_intake
          goal: daily_goal
          unit: ml
          shows: percentage, current/goal text

      - id: quick_add
        type: action_row
        content:
          actions: ["250ml", "500ml", "Custom"]
          behavior: tap adds amount instantly (except Custom → opens input)

      - id: today_log
        type: list
        content:
          items: today's water entries, newest first
          per_item: time, amount, icon
          empty: "No entries yet. Tap + to start tracking."

    # --- States ---
    states:
      loading: skeleton placeholders for progress + log
      empty: first-time user, no entries, show empty prompt
      error: data load failed, show retry

    # --- Interactions ---
    interactions:
      - pull to refresh
      - tap entry → entry detail screen
      - long press entry → edit / delete
```

## Layout Patterns

| Pattern | Use for |
|:--------|:--------|
| `scrollable_sections` | Dashboard, home — stacked content sections |
| `centered_hero` | Onboarding, empty states — centered illustration + text + CTA |
| `form` | Input screens, settings — label + input pairs |
| `list` | History, search results — scrollable item list |
| `detail` | Item detail — header area + scrollable body |
| `card_grid` | Selection screens — grid or horizontal cards |
| `bottom_sheet` | Pickers, confirmations — partial overlay |
| `full_overlay` | Paywall, alerts — full-screen overlay with dismiss |
| `paged` | Onboarding sequence — horizontal swipe |

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Describe, don't implement | Say WHAT appears, not which component renders it |
| States are mandatory | Every screen: default + loading at minimum. Add empty/error where data is fetched |
| Content is concrete | Use actual copy, field names, units — not "some text here" |
| Order = visual order | Blocks listed top-to-bottom as they appear on screen |
| Theme-aware | Respect the theme's density when deciding how much fits per screen |
| Competitor-informed | Open screenshots when unsure about layout or content patterns |
| Don't redesign | Enrich existing screens. Don't add, remove, or rename screens |
| Keep it lean | Short descriptions. The implement agent reads these for every screen — verbosity costs tokens |
