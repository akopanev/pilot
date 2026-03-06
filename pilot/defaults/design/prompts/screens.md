# Protocol: Screen Map

Convert the PRD's screen inventory and navigation structure into a
structured screens.yaml. Validate completeness against user stories,
enrich with transition types, and fill gaps using competitor patterns.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — screens.yaml written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
- **Competitor data**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/`
  - `apps.json` — app metadata
  - `*/features.md` — per-app feature extractions (includes navigation patterns,
    onboarding flows, screen observations)

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}`

## Execution

1. Read the PRD. It contains:
   - **Screens table** — screen inventory with ID, epic, purpose, entry, exits
   - **Navigation section** — tab bar layout and key flows
   - **Onboarding flow** — step-by-step screens
   - **Epics with user stories** — each user story maps to screens
2. Read `apps.json` and every `*/features.md` file. Use competitor
   navigation patterns to validate and enrich the PRD's screen list.
3. Open 2-3 screenshots per competitor that show navigation structure
   (home screen, tab bar, onboarding flow). Screenshots show actual
   screen flows that features.md text may miss.
4. `<signal:update>building screen map from PRD + N competitors</signal:update>`
5. **Validate completeness.** Walk through every user story in every epic.
   Each must map to at least one screen in the PRD's screen table. If a
   user story has no screen, add one. If a screen has no user story, flag it.
6. Convert the PRD's screen table + navigation into the structured YAML
   format below. Add transition types (push, modal, replace, tab) based
   on competitor patterns — the PRD says WHAT connects, you decide HOW.
7. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}`.
8. `<signal:completed>N screens mapped</signal:completed>`

## Output Format

```yaml
# Screen inventory — generated from PRD + competitor analysis
# Each screen maps to one or more user stories from the PRD.

app_structure:
  navigation_type: tab_bar          # tab_bar | drawer | stack_only
  tabs:
    - id: tab_home
      label: Home
      icon: home
      root_screen: home_dashboard
    - id: tab_history
      label: History
      icon: chart
      root_screen: history_list
    # ...

screens:
  # --- Onboarding ---
  - id: onboarding_welcome
    epic: onboarding
    purpose: introduce_value
    description: >
      First screen after launch. Shows app promise with illustration.
      User taps continue to proceed.
    entry:
      - source: app_launch_first_time
        type: root                   # root | push | modal | replace | tab
    primary_cta:
      label: Continue
      action: navigate
      target: onboarding_goal
    secondary_actions: []
    transitions:
      - target: onboarding_goal
        trigger: primary_cta

  - id: onboarding_goal
    epic: onboarding
    purpose: collect_user_goal
    description: >
      User selects their primary goal. Single-select list.
      Selection advances automatically.
    entry:
      - source: onboarding_welcome
        type: push
    primary_cta:
      label: null                    # auto-advance on selection
      action: navigate
      target: onboarding_preferences
    transitions:
      - target: onboarding_preferences
        trigger: goal_selected

  # --- Paywall ---
  - id: paywall
    epic: paywall
    purpose: convert_user
    description: >
      Subscription options with trial. Skip button always visible.
      Shown after onboarding completes.
    entry:
      - source: onboarding_complete
        type: modal
    primary_cta:
      label: Start Free Trial
      action: purchase
      target: home_dashboard
    secondary_actions:
      - label: Continue for Free
        action: navigate
        target: home_dashboard
    transitions:
      - target: home_dashboard
        trigger: purchase_success
      - target: home_dashboard
        trigger: skip

  # --- Core screens ---
  - id: home_dashboard
    epic: daily_tracking          # matches PRD epic name
    purpose: primary_hub
    description: >
      Main screen. Shows today's progress, quick-add actions,
      and daily goal status.
    entry:
      - source: paywall
        type: replace
      - source: tab_home
        type: tab
    primary_cta:
      label: Add Entry
      action: navigate
      target: log_entry
    transitions:
      - target: log_entry
        trigger: primary_cta
      - target: entry_detail
        trigger: tap_entry

  # ... continue for all screens
```

## How to Identify Screens

| PRD element | Implies |
|:------------|:--------|
| User story "I want to [action]" | A screen where that action happens |
| "User sees [thing]" | A screen showing that thing |
| Feature with "list" or "history" | List screen + detail screen |
| Feature with "create" or "add" | Form/input screen |
| Feature with "settings" or "preferences" | Settings screen |
| Navigation tab | Root screen for that tab |
| Onboarding flow step | One screen per step |
| Epic goal | At least one primary screen |

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Every user story = a screen | If a user story can't be traced to a screen, one is missing |
| No orphan screens | Every screen has entry + exit |
| Transitions are explicit | Don't leave implicit "somehow gets to X". State the trigger |
| Competitor-informed | Use competitor navigation patterns as evidence for structure |
| PRD is truth | Screens implement the PRD. Don't add features not in the PRD |
| Epic ownership | Every screen belongs to exactly one epic |
| Keep descriptions concrete | What the user SEES and DOES, not abstract purpose |
| Include all states screens | Settings, profile, edit screens — not just happy path |
