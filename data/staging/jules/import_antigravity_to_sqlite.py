import sqlite3
import csv
import os
import argparse
import sys

# Define file paths
MOOD_CSV = "data/staging/antigravity/mood_event_tag_suggestions.csv"
PERF_CSV = "data/staging/antigravity/performance_metadata_suggestions.csv"
LINKS_CSV = "data/staging/antigravity/external_link_verification.csv"
DB_PATH = "data/staging/jules/music_antigravity_review.sqlite"

def read_csv(filepath):
    if not os.path.exists(filepath):
        print(f"Warning: File not found: {filepath}")
        return []
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

REQ_MOOD = {'Recording ID', 'Title', 'Artist', 'Suggested Field', 'Suggested Value', 'Confidence', 'Rationale', 'Source'}
REQ_PERF = {'Recording ID', 'Title', 'Artist', 'Field', 'Suggested Value', 'Instrument', 'Confidence', 'Source URL', 'Notes'}
REQ_LINKS = {'Status'}
ALLOWED_STATUSES = {'verified_exact', 'official_tab_verified', 'best_tab_verified', 'no_good_match', 'needs_review'}

# Helper to create table from CSV data
def create_table_from_csv(cursor, table_name, csv_data, req_headers=None, check_status=False):
    if not csv_data:
        return

    headers = csv_data[0].keys()
    if req_headers:
        missing = req_headers - set(headers)
        if missing:
            raise ValueError(f"Missing required columns {missing} in {table_name}")
    if check_status and 'Status' in headers:
        for row in csv_data:
            if row.get('Status') not in ALLOWED_STATUSES:
                raise ValueError(f"Invalid Status '{row.get('Status')}' in {table_name}")
    # Clean headers to be SQL-friendly
    clean_headers = [h.replace(" ", "_") for h in headers]

    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    cols = ", ".join([f"\"{h}\" TEXT" for h in clean_headers])
    cursor.execute(f"CREATE TABLE {table_name} ({cols})")

    placeholders = ", ".join(["?" for _ in clean_headers])
    insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"

    rows_to_insert = [tuple(row.values()) for row in csv_data]
    cursor.executemany(insert_sql, rows_to_insert)
    print(f"Imported {len(rows_to_insert)} rows into {table_name}")

def import_to_sqlite(write=False):
    if not write:
        print("DRY RUN: SQLite import skipped. Use --write to execute.")
        return

    # Ensure output directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()



    # Import the tables
    create_table_from_csv(cursor, "antigravity_mood_event_suggestions", read_csv(MOOD_CSV), req_headers=REQ_MOOD)
    create_table_from_csv(cursor, "antigravity_performance_suggestions", read_csv(PERF_CSV), req_headers=REQ_PERF)
    create_table_from_csv(cursor, "antigravity_external_link_suggestions", read_csv(LINKS_CSV), req_headers=REQ_LINKS, check_status=True)

    # Create views
    print("Creating review views...")

    # 1. Non-blank tag suggestions
    cursor.execute("DROP VIEW IF EXISTS view_nonblank_tag_suggestions")
    cursor.execute("""
        CREATE VIEW view_nonblank_tag_suggestions AS
        SELECT * FROM antigravity_mood_event_suggestions
        WHERE Suggested_Value IS NOT NULL AND Suggested_Value != ''
    """)

    # 2. BPM/key rows
    cursor.execute("DROP VIEW IF EXISTS view_bpm_key_rows")
    cursor.execute("""
        CREATE VIEW view_bpm_key_rows AS
        SELECT * FROM antigravity_performance_suggestions
        WHERE Field IN ('BPM', 'Key')
    """)

    # 3. External search URLs
    cursor.execute("DROP VIEW IF EXISTS view_external_search_urls")
    cursor.execute("""
        CREATE VIEW view_external_search_urls AS
        SELECT * FROM antigravity_external_link_suggestions
        WHERE Source = 'Search Query'
    """)

    # 4. Verified-link candidates
    cursor.execute("DROP VIEW IF EXISTS view_verified_link_candidates")
    cursor.execute("""
        CREATE VIEW view_verified_link_candidates AS
        SELECT * FROM antigravity_external_link_suggestions
        WHERE Status IN ('verified_exact', 'official_tab_verified', 'best_tab_verified')
    """)

    conn.commit()
    conn.close()
    print(f"Database updated at {DB_PATH}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Execute the import")
    args = parser.parse_args()

    import_to_sqlite(write=args.write)
