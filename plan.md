# Plan for `shs_universal_page_parser.py`

1. **Setup & Initialization**:
   - Create the script `shs_universal_page_parser.py`.
   - Implement CLI using `argparse` with arguments for `--input-dir`, `--input-file`, `--output-csv`, `--workers`.
   - Setup multithreading/multiprocessing support.
   - Configure logging.

2. **Stage 1: Intake & Document Fingerprinting**:
   - Implement file reading with encoding fallback (try `utf-8`, then `ISO-8859-1`/`CP1252`).
   - Extract canonical URL, meta `og:url` to uniquely identify the page entity and ID.

3. **Stage 2: Entity Categorization & Routing**:
   - Use regex on canonical URL to extract `shs_entity_type` (work, performance, artist, release, web_cover).
   - If missing, fallback to data-controller, breadcrumbs, filename regex.
   - Determine `is_all_versions_view` boolean based on url suffix `/all`.

4. **Stage 3: Metadata Extraction Engine**:
   - Write functions to extract metadata based on the 85-field specification (`shs_page_metadata_dictionary.csv`).
   - Extract `h1` and page `<title>`.
   - Extract definition list (`<dl>`) attributes mapping them correctly based on the entity type (e.g. `written_by`, `released_on`, `work_language`).
   - Standardize dates using logic from `shs_dates.py`. Parse year/month/day. Remove `.0` floating point suffixes.
   - Extract IDs correctly: `iswc`, `ipi`, `spotify_track_id`, etc.
   - For `work` and `performance` pages, detect specific markers/badges (e.g., `is_first_release`, `is_instrumental`, `is_live`).

5. **Stage 4: Data Processing & Business Rules**:
   - Implement logic to handle conflicting fields or special cases (e.g. `adapted_from`, `uses_parts_from`, medley tracking).
   - Address AARW classifications.

6. **Stage 5: Output Generation**:
   - Assemble a row of data containing the full 85-field schema.
   - Handle export logic to CSV.
   - Set up an audit queue output (`excluded_adaptations.csv`) for non-Latin / translations.

7. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done**.

8. **Test & Validation**:
   - Run the script against the 20 archetype pages in `SHSmetadataScrapingGuide/` (using `--input-dir`).
   - Generate `shs_parsed_archetypes_output.csv` and verify it contains all fields populated correctly.
