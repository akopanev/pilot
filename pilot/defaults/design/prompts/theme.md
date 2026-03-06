# Protocol: Visual Theme

Derive the app's visual direction from the product category, target user,
and competitor visual patterns. Output values that configure gluestack's
theming system — NOT a parallel design system.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — theme.yaml written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **PRD**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_PRD}}`
  (target user, category, strategy, overview)
- **Competitor data**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_APPTWEAK_OUTPUT_DIR}}/`
  - `apps.json` — app metadata (icons, descriptions)
  - `*/` — app folders with screenshots
- **Screen map**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}`
- **Design references** (optional): `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DESIGN_REFS}}/`
  Screenshots, mockups, or Dribbble shots showing desired visual direction.
  If the directory exists, open every image. These override competitor
  patterns — they represent what the user WANTS it to look like.
- **Gluestack skills**: the `gluestack-ui-v4:styling` skill is available as
  project instructions. Use it to understand the token system you're configuring

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_THEME}}`

## Execution

1. Read the PRD — extract target user, category, emotional tone.
2. Try to read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DESIGN_REFS}}/`. If the
   directory exists and has images, open every one. These are the user's
   visual references — they take priority over competitor patterns for
   style decisions (colors, density, tone). Competitors still inform
   what's standard for the category.
3. Review the `gluestack-ui-v4:styling` skill (loaded as project instructions).
   Understand the semantic token names and CSS variable system.
   Your output configures THIS system — you're choosing values for
   gluestack's existing token slots, not inventing new ones.
   Only use tokens documented in the skill — do not invent custom tokens.
4. Read `apps.json` for app metadata.
5. Open 2-3 representative screenshots from EACH competitor app
   (home screen, main feature screen, onboarding if available). Study:
   - Color palettes — dominant, accent, background
   - Typography — weight, size hierarchy, serif vs sans
   - Spacing — dense vs airy, padding patterns
   - Border radius — sharp vs rounded vs fully round
   - Visual weight — heavy/bold vs light/subtle
   - Dark mode presence
6. Read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}` — note screen count
   and types to calibrate density.
7. `<signal:update>deriving theme from category + N competitors</signal:update>`
8. Synthesize the theme. Design references (if provided) take priority
   for visual style. Competitor patterns fill gaps and validate category norms.
9. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_THEME}}`.
10. `<signal:completed>theme defined</signal:completed>`

## Output Format

The theme file has two sections: visual direction (for humans and planning
agents) and gluestack config (for implementation).

```yaml
# Theme — visual direction + gluestack configuration

# --- Visual direction ---
# Human-readable. Used by planning agents to understand the style.
direction:
  category: wellness
  emotional_tone: calm, trustworthy, clean
  density: airy                        # dense | comfortable | airy
  contrast: medium                     # low | medium | high
  reference_apps:
    - name: "Competitor A"
      influence: "color palette, soft shapes"
    - name: "Competitor B"
      influence: "spacing, typography weight"
  notes: >
    Soft blues and greens, generous whitespace, rounded shapes.
    Competitors unanimously use light backgrounds with a single
    accent color for CTAs. Dark mode support is universal.

# --- Gluestack CSS variables ---
# These values populate gluestack's semantic token slots.
# Use the EXACT token names from gluestack's styling system.
# The implement agent copies these into the gluestack provider config.
# Only use semantic tokens documented in the gluestack-ui-v4:styling skill.
# Do NOT invent custom tokens (no success, warning, overlay, etc.).
tokens:
  light:
    "--color-background": "#FFFFFF"
    "--color-foreground": "#1A1A2E"
    "--color-primary": "#4A90D9"
    "--color-primary-foreground": "#FFFFFF"
    "--color-secondary": "#E8F0FE"
    "--color-secondary-foreground": "#4A90D9"
    "--color-muted": "#F5F7FA"
    "--color-muted-foreground": "#6B7280"
    "--color-accent": "#FF6B6B"
    "--color-accent-foreground": "#FFFFFF"
    "--color-card": "#FFFFFF"
    "--color-card-foreground": "#1A1A2E"
    "--color-popover": "#FFFFFF"
    "--color-popover-foreground": "#1A1A2E"
    "--color-border": "#E5E7EB"
    "--color-input": "#E5E7EB"
    "--color-ring": "#4A90D9"
    "--color-destructive": "#EF4444"
    "--color-destructive-foreground": "#FFFFFF"

  dark:
    "--color-background": "#0F172A"
    "--color-foreground": "#F1F5F9"
    "--color-primary": "#60A5FA"
    "--color-primary-foreground": "#0F172A"
    "--color-secondary": "#1E3A5F"
    "--color-secondary-foreground": "#60A5FA"
    "--color-muted": "#1E293B"
    "--color-muted-foreground": "#94A3B8"
    "--color-accent": "#F87171"
    "--color-accent-foreground": "#0F172A"
    "--color-card": "#1E293B"
    "--color-card-foreground": "#F1F5F9"
    "--color-popover": "#1E293B"
    "--color-popover-foreground": "#F1F5F9"
    "--color-border": "#334155"
    "--color-input": "#334155"
    "--color-ring": "#60A5FA"
    "--color-destructive": "#EF4444"
    "--color-destructive-foreground": "#F1F5F9"

  supports_dark_mode: true
```

## Deriving the Theme

| Signal | What to derive |
|:-------|:---------------|
| Category (wellness, fitness, finance...) | Emotional tone → color temperature, density |
| Target user (age, motivation) | Contrast level, typography weight |
| Competitor screenshots | Actual color palettes, spacing, radius patterns |
| Screen count + complexity | Density — more screens = can be airier per screen |
| Dark mode in competitors | Whether to support dark mode |
| Gluestack token names | ONLY use tokens from the gluestack-ui-v4:styling skill |

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Configure, don't invent | You're setting values for gluestack's token system. Use their variable names exactly |
| Evidence-based | Every choice traces to competitor patterns or category norms |
| Both modes | Define light and dark unless competitors unanimously skip dark mode |
| Complete | Every token must have a value. No "TBD" or "inherit" |
| Direction is for humans | The `direction` section is read by planning agents. Keep it descriptive |
| Tokens are for code | The `tokens` section is copied into gluestack config. Keep it exact |
| Conservative | When in doubt, follow the majority of competitors |
