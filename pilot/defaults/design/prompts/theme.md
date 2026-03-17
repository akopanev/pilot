# Protocol: Visual Theme

Derive the app's visual direction from the product category, target user,
and competitor visual patterns. Output a comprehensive design specification
that can be used to create screens in Figma.

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

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_THEME}}`

## Execution

1. Read the PRD — extract target user, category, emotional tone.
2. Try to read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_DESIGN_REFS}}/`. If the
   directory exists and has images, open every one. These are the user's
   visual references — they take priority over competitor patterns for
   style decisions (colors, density, tone). Competitors still inform
   what's standard for the category.
3. Read `apps.json` for app metadata.
4. Open 2-3 representative screenshots from EACH competitor app
   (home screen, main feature screen, onboarding if available). Study:
   - Color palettes — dominant, accent, background
   - Typography — weight, size hierarchy, serif vs sans
   - Spacing — dense vs airy, padding patterns
   - Border radius — sharp vs rounded vs fully round
   - Visual weight — heavy/bold vs light/subtle
   - Dark mode presence
5. Read `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_SCREENS}}` — note screen count
   and types to calibrate density.
6. `<signal:update>deriving theme from category + N competitors</signal:update>`
7. Synthesize the theme. Design references (if provided) take priority
   for visual style. Competitor patterns fill gaps and validate category norms.
8. Write `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_THEME}}`.
9. `<signal:completed>theme defined</signal:completed>`

## Output Format

```yaml
# Theme — visual direction + design tokens

# --- Visual direction ---
# Human-readable. Used by design and planning agents.
direction:
  category: wellness
  emotional_tone: calm, trustworthy, clean
  density: airy                        # dense | comfortable | airy
  contrast: medium                     # low | medium | high
  style: >
    Soft blues and greens, generous whitespace, rounded shapes.
    Light backgrounds with a single accent color for CTAs.
  reference_apps:
    - name: "Competitor A"
      influence: "color palette, soft shapes"
    - name: "Competitor B"
      influence: "spacing, typography weight"

# --- Color palette ---
colors:
  light:
    background: "#FFFFFF"
    surface: "#F5F7FA"                 # cards, elevated elements
    foreground: "#1A1A2E"              # primary text
    foreground_secondary: "#6B7280"    # secondary/muted text
    primary: "#4A90D9"                 # brand, main CTAs
    primary_foreground: "#FFFFFF"      # text on primary
    secondary: "#E8F0FE"              # secondary buttons, tags
    secondary_foreground: "#4A90D9"
    accent: "#FF6B6B"                  # highlights, badges
    accent_foreground: "#FFFFFF"
    border: "#E5E7EB"
    input_border: "#D1D5DB"
    destructive: "#EF4444"
    destructive_foreground: "#FFFFFF"

  dark:
    background: "#0F172A"
    surface: "#1E293B"
    foreground: "#F1F5F9"
    foreground_secondary: "#94A3B8"
    primary: "#60A5FA"
    primary_foreground: "#0F172A"
    secondary: "#1E3A5F"
    secondary_foreground: "#60A5FA"
    accent: "#F87171"
    accent_foreground: "#0F172A"
    border: "#334155"
    input_border: "#475569"
    destructive: "#EF4444"
    destructive_foreground: "#F1F5F9"

  supports_dark_mode: true

# --- Typography ---
typography:
  font_family: "Inter"                 # or SF Pro, Nunito, etc.
  scale:
    display: { size: 32, weight: 700, line_height: 1.2 }
    h1:      { size: 28, weight: 700, line_height: 1.25 }
    h2:      { size: 22, weight: 600, line_height: 1.3 }
    h3:      { size: 18, weight: 600, line_height: 1.35 }
    body:    { size: 16, weight: 400, line_height: 1.5 }
    body_sm: { size: 14, weight: 400, line_height: 1.45 }
    caption: { size: 12, weight: 400, line_height: 1.4 }
    button:  { size: 16, weight: 600, line_height: 1.0 }

# --- Spacing & layout ---
spacing:
  unit: 4                             # base unit in px
  screen_padding: 16                   # horizontal screen margins
  section_gap: 24                      # vertical gap between sections
  card_padding: 16
  element_gap: 12                      # gap between elements in a group

# --- Shape ---
shape:
  border_radius:
    small: 8                           # inputs, chips
    medium: 12                         # cards, buttons
    large: 16                          # modals, sheets
    full: 9999                         # pills, avatars
  shadows:
    card: "0 1px 3px rgba(0,0,0,0.08)"
    elevated: "0 4px 12px rgba(0,0,0,0.12)"
    modal: "0 8px 24px rgba(0,0,0,0.16)"

# --- Iconography ---
icons:
  style: outlined                      # outlined | filled | duotone
  weight: regular                      # light | regular | bold
  set: lucide                          # lucide | phosphor | sf-symbols | material
```

## Deriving the Theme

| Signal | What to derive |
|:-------|:---------------|
| Category (wellness, fitness, finance...) | Emotional tone → color temperature, density |
| Target user (age, motivation) | Contrast level, typography weight |
| Competitor screenshots | Actual color palettes, spacing, radius patterns |
| Screen count + complexity | Density — more screens = can be airier per screen |
| Dark mode in competitors | Whether to support dark mode |

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Evidence-based | Every choice traces to competitor patterns or category norms |
| Both modes | Define light and dark unless competitors unanimously skip dark mode |
| Complete | Every token must have a value. No "TBD" or "inherit" |
| Direction is for humans | The `direction` section is read by planning agents. Keep it descriptive |
| Tokens are for design tools | The color/typography/spacing/shape sections feed into Figma Make — keep values precise |
| Conservative | When in doubt, follow the majority of competitors |
| Platform-aware | Typography sizes and spacing should feel native on mobile (iOS/Android) |
