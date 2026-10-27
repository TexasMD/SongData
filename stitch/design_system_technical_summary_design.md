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