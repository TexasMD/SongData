---
name: Pro Console
colors:
  surface: '#141416'
  surface-dim: '#131314'
  surface-bright: '#3a393a'
  surface-container-lowest: '#0e0e0f'
  surface-container-low: '#1c1b1c'
  surface-container: '#201f20'
  surface-container-high: '#2a2a2b'
  surface-container-highest: '#353436'
  on-surface: '#e5e2e3'
  on-surface-variant: '#e5beb2'
  inverse-surface: '#e5e2e3'
  inverse-on-surface: '#313031'
  outline: '#ac897e'
  outline-variant: '#5c4037'
  surface-tint: '#ffb59e'
  primary: '#ffb59e'
  on-primary: '#5d1800'
  primary-container: '#ff5715'
  on-primary-container: '#521400'
  inverse-primary: '#ad3300'
  secondary: '#bdf4ff'
  on-secondary: '#00363d'
  secondary-container: '#00e3fd'
  on-secondary-container: '#00616d'
  tertiary: '#a3c9ff'
  on-tertiary: '#00315c'
  tertiary-container: '#0f93fe'
  on-tertiary-container: '#002a50'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbd0'
  primary-fixed-dim: '#ffb59e'
  on-primary-fixed: '#390b00'
  on-primary-fixed-variant: '#842500'
  secondary-fixed: '#9cf0ff'
  secondary-fixed-dim: '#00daf3'
  on-secondary-fixed: '#001f24'
  on-secondary-fixed-variant: '#004f58'
  tertiary-fixed: '#d3e4ff'
  tertiary-fixed-dim: '#a3c9ff'
  on-tertiary-fixed: '#001c38'
  on-tertiary-fixed-variant: '#004882'
  background: '#131314'
  on-background: '#e5e2e3'
  surface-variant: '#353436'
  surface-hover: '#1C1C1F'
  text-main: '#EAEAEA'
  text-muted: '#737378'
  border-grid: '#2A2A2E'
typography:
  display-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  header-table:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 28px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 14px
  body-standard:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
spacing:
  row-compact: 28px
  row-standard: 36px
  cell-padding-x: 8px
  drawer-width: 320px
  modal-width: 800px
  input-height: 28px
---

# Pro Console: High-Density Song Database - Design System & Technical Specification

## 1. Visual Identity & Brand Direction
**Style:** Industrial Studio Console / High-Performance Metadata Manager
**Philosophy:** Information density over whitespace. Utility-first interaction. 0px border radius.
**Inspiration:** Ableton Live, Pioneer Rekordbox, Excel.

## 2. Design Tokens (CSS Variables)
```css
:root {
  /* Colors */
  --color-primary: #FF5000;         /* Synth Orange: Actions, Toggles, Focus */
  --color-background: #09090A;      /* Pitch Black: Main Canvas */
  --color-surface: #141416;         /* Charcoal: Panels, Toolbars, Modals */
  --color-surface-hover: #1C1C1F;   /* Subtle Grey: Row Hovers, Button Hovers */
  --color-text: #EAEAEA;            /* Off-White: Primary Data, Labels */
  --color-muted: #737378;           /* Slate: Placeholders, Inactive Borders */
  --color-accent: #00E5FF;          /* Cyan LED: AI Search, Secondary Logic (OR) */
  --color-border: #2A2A2E;          /* Dark Slate: Structural Grids */

  /* Typography */
  --font-display: 'Space Grotesk', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* Sizing & Layout */
  --grid-row-height: 28px;
  --font-size-data: 11px;
  --font-size-header: 12px;
  --radius: 0px;
}
```

## 3. Core Component Specifications

### Main Grid Console (Table)
*   **Font:** `11px JetBrains Mono` for row data.
*   **Row Height:** Fixed `28px` for maximum density.
*   **Cell Padding:** `px-2` (8px horizontal).
*   **Border:** `1px solid var(--color-border)`.
*   **Hover State:** `bg-[var(--color-surface-hover)]`.
*   **Column Headers:** Draggable, sortable, resizable handles on the right edge.
*   **Selection:** Checkbox column (`w-10`) with `var(--color-primary)` fill on active.

### Filter Matrix Builder (Boolean Logic)
*   **Logic Connectors:** Vertical lines connecting rows. 
    *   `AND` = `var(--color-primary)`
    *   `OR` = `var(--color-accent)`
*   **Inputs:** Compact `h-7` (28px) inputs and dropdowns.
*   **Modal:** Centered, `800px` width, `var(--color-surface)` background.

### Column Settings Drawer
*   **Position:** Fixed Right, `320px` width.
*   **Density Toggle:** Segmented control switching between `Compact` (28px rows) and `Standard` (36px rows).
*   **List Items:** Draggable handles for reordering, checkbox for visibility.

## 4. Key Flows for Implementation
1.  **High-Speed Scan:** Users scan 100+ rows. Typography must be razor-sharp.
2.  **Complex Filter:** Construction of `(A AND B) OR C` logic using the Matrix Builder.
3.  **Column Customization:** Real-time visibility/order updates via the Settings Drawer.

## 5. Implementation Notes for AI
*   **Framework:** Tailwind CSS v3.
*   **Fonts:** Load `Space Grotesk` (Google Fonts) and `JetBrains Mono` (Google Fonts).
*   **Density:** Maintain strict `0px` border-radius and `1px` borders.
*   **Interactivity:** Use `var(--color-primary)` for all primary interactive cues.
