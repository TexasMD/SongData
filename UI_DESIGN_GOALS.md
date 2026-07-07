# Pro Console: Primary UI Design Goals

This document outlines the core requirements and design philosophies for the MusicDB Pro Console interface.

## 1. Visual Identity
*   **Style:** Industrial Studio Console / High-Performance Metadata Manager
*   **Philosophy:** Information density over whitespace. Utility-first interaction. 0px border radius.
*   **Inspiration:** Ableton Live, Pioneer Rekordbox, Excel.

## 2. Grid & Data Interaction (Excel-like Behavior)
*   **Data Grid:** The primary view must operate like a high-performance spreadsheet.
*   **Column Features:** Every column must support:
    *   Reordering via drag-and-drop.
    *   Searching and filtering (text, numeric, boolean).
    *   Ascending/Descending sorting.
*   **Row Management:** Default data fetch should load exactly 100 rows for immediate snappy performance, with the ability to load more or "all rows" on demand.

## 3. Settings & Customization
*   The Settings menu must be fully functional and accessible from the top toolbar.
*   **Column Selector:** A checklist interface allowing users to quickly toggle the visibility of specific columns.
*   **Pagination/Density Control:** A selector to adjust the number of rows fetched/shown (e.g., 50, 100, 500, All).

## 4. Bulk Actions (Floating Action Toolbar)
When one or more rows are selected in the grid, a floating action toolbar must appear with the following utility actions:
*   **Add to List:** Adds the selected tracks to a specific playlist or export list.
*   **Find Similar:** (Single or multi-select) Uses the Similarity Engine to find tracks mathematically close to the selection.
*   **Find Covers:** Scans the database to find cover versions of the selected track(s).
*   **Commonalities:** Uses AI to analyze the selected tracks and identify what they have in common (e.g., "These are all high-BPM synth-pop tracks from the 1980s").
