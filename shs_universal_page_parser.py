#!/usr/bin/env python3
import argparse
import csv
import logging
import multiprocessing
import os
import re
import sqlite3
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any, List

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def parse_args():
    parser = argparse.ArgumentParser(description="Universal SHS Webpage Parser")
    parser.add_argument("--input-dir", type=str, help="Directory containing HTML files")
    parser.add_argument("--input-file", type=str, help="Single HTML file to parse")
    parser.add_argument("--output-csv", type=str, required=True, help="Output CSV file path")
    parser.add_argument("--output-db", type=str, help="Output SQLite DB file path")
    parser.add_argument("--workers", type=int, default=multiprocessing.cpu_count(), help="Number of worker processes")
    return parser.parse_args()

def read_html_file(filepath: Path) -> str:
    """Reads HTML file with fallback encoding."""
    try:
        return filepath.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            return filepath.read_text(encoding='iso-8859-1')
        except UnicodeDecodeError:
            return filepath.read_text(encoding='cp1252', errors='replace')

def extract_canonical_url(soup: BeautifulSoup) -> str:
    """Extract canonical URL or fallback to og:url."""
    link = soup.find('link', rel='canonical')
    if link and link.get('href'):
        return link['href']
    meta = soup.find('meta', property='og:url')
    if meta and meta.get('content'):
        return meta['content']
    return ""

def classify_entity(canonical_url: str, filepath: Path, soup: BeautifulSoup) -> tuple[str, str]:
    """Deterministically classify entity type and ID using a cascading hierarchy."""
    # Signal 1: Canonical URL or og:url
    if canonical_url:
        match = re.search(r'/(work|performance|artist|release|web-cover)/(\d+)', canonical_url)
        if match:
            return match.group(1), match.group(2)

    # Signal 2: Root container data-controller
    wrapper = soup.find(attrs={"data-controller": True})
    if wrapper and isinstance(wrapper.get('data-controller'), str):
        match = re.search(r'/(work|performance|artist|release|web-cover)/(\d+)', str(wrapper['data-controller']))
        if match:
            return match.group(1), match.group(2)

    # Signal 3: Filename regex
    filename = filepath.name
    match = re.search(r'CYT-(work|performance|artist|release|web-cover)-.*?-(\d+)\.html', filename)
    if match:
        return match.group(1), match.group(2)

    return "unknown", ""

def is_all_versions(url: str) -> str:
    return str(url.endswith('/all'))

def clean_text(text: str) -> str:
    """Removes excessive whitespace."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def extract_dl_metadata(soup: BeautifulSoup) -> dict[str, str]:
    """Lossless extraction of definition lists."""
    data = {}
    for dl in soup.find_all('dl'):
        for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
            key = dt.get_text(strip=True).replace(':', '').strip()
            # Clean up known verbose keys
            key = re.sub(r'^International Standard Musical Work Code.*$', 'ISWC', key).strip()
            # Get text from dd, preserving spaces between elements if separated
            value = clean_text(dd.get_text(separator=' | ', strip=True))
            data[key] = value
    return data

def standardize_date(raw_date: str) -> str:
    """Standardizes date, cleaning float representations like 1985.0"""
    if not raw_date:
        return ""
    # Strip .0 if present
    cleaned = re.sub(r'\.0$', '', str(raw_date).strip())
    # Further parse with shs_dates logic could be added here
    return cleaned

def extract_h1_and_title(soup: BeautifulSoup, metadata: dict[str, Any]):
    title_tag = soup.find('title')
    metadata['page_title'] = clean_text(title_tag.get_text()) if title_tag else ""

    h1 = soup.find('h1')
    if h1:
        name_span = h1.find(attrs={"itemprop": "name"})
        metadata['document_heading'] = clean_text(name_span.get_text()) if name_span else clean_text(h1.get_text())
    else:
        metadata['document_heading'] = ""

def parse_html_page(filepath: Path, soup: BeautifulSoup, html_content: str) -> dict[str, Any]:
    """Parse a single HTML file and return metadata dict."""
    metadata = {}
    metadata['Filename'] = filepath.name

    canonical_url = extract_canonical_url(soup)
    metadata['canonical_url'] = canonical_url

    entity_type, entity_id = classify_entity(canonical_url, filepath, soup)
    metadata['shs_entity_type'] = entity_type
    metadata['shs_entity_id'] = entity_id
    metadata['is_all_versions_view'] = is_all_versions(canonical_url)

    extract_h1_and_title(soup, metadata)

    dl_data = extract_dl_metadata(soup)

    # Map discovered fields (dynamic inclusion)
    for k, v in dl_data.items():
        # Standardize dates on the fly if it looks like a date key
        if 'date' in k.lower() or k.lower() in ('released on', 'first recorded in', 'first recorded on'):
            metadata[k] = standardize_date(v)
        else:
            metadata[k] = v

    # Explicit mapping for core fields based on entity
    if entity_type == 'work':
        metadata['work_title'] = metadata['document_heading']
        metadata['work_id'] = entity_id
        if 'Language' in dl_data:
            metadata['work_language'] = dl_data['Language']

    elif entity_type == 'performance':
        metadata['performance_title'] = metadata['document_heading']
        metadata['performance_id'] = entity_id

        # Extract Performing Artist from h1 <em>by</em> block
        h1 = soup.find('h1')
        if h1:
            em_by = h1.find('em')
            if em_by and 'by' in em_by.get_text(strip=True).lower():
                artist_a = em_by.find_next_sibling('a')
                if artist_a:
                    metadata['performing_artist'] = clean_text(artist_a.get_text())

    elif entity_type == 'artist':
        metadata['artist_name'] = metadata['document_heading']
        metadata['artist_id'] = entity_id

    elif entity_type == 'release':
        metadata['release_title'] = metadata['document_heading']
        metadata['release_id'] = entity_id

    # Table badges (e.g., [1st], Instrumental, Live, Medley)
    # Simple regex search on the raw html for now
    html_lower = html_content.lower()
    metadata['is_instrumental'] = str('badge-instrumental' in html_lower or '>instrumental<' in html_lower)
    metadata['is_live'] = str('badge-live' in html_lower or '>live<' in html_lower)
    metadata['is_medley'] = str('badge-medley' in html_lower or '>medley<' in html_lower)
    metadata['is_first_release'] = str('badge-original' in html_lower or '[1st]' in html_content)

    return metadata

def apply_business_rules(metadata: dict[str, Any]) -> dict[str, Any]:
    """Applies specific data processing rules like title disambiguation and AARW."""
    # Standardize specific fields (floats)
    for k, v in metadata.items():
        if isinstance(v, str) and v.endswith('.0') and re.match(r'^\d{4}\.0$', v):
            # Only if it looks like a year e.g., 1985.0
            metadata[k] = v[:-2]

    # AARW Classification (Artist Autocover / Re-recording With)
    # If it's a performance and performing artist matches original artist loosely
    if metadata.get('shs_entity_type') == 'performance':
        perf_artist = metadata.get('performing_artist', '').lower()
        orig_artist = metadata.get('Written by', '').lower() # Sometimes Original Artist

        # Simple heuristic for AARW
        if perf_artist and orig_artist and (perf_artist in orig_artist or orig_artist in perf_artist):
            metadata['performance_type_classification'] = 'AARW'
        elif metadata.get('is_first_release') == 'True':
            metadata['performance_type_classification'] = '1strel'
        else:
            metadata['performance_type_classification'] = 'cover'

    # Disambiguate short titles
    title = metadata.get('work_title') or metadata.get('performance_title', '')
    if title and len(title) <= 4:
        artist = metadata.get('performing_artist') or metadata.get('Written by', '')
        if artist:
            metadata['disambiguated_title'] = f"{title} ({artist})"

    return metadata

def extract_tables(soup: BeautifulSoup, parent_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []

    # Process standard DataTables usually found on SHS
    for table in soup.find_all('table'):
        headers = []
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                headers.append(clean_text(th.get_text()))

        tbody = table.find('tbody') or table
        for tr in tbody.find_all('tr'):
            if not tr.find('td'):
                continue

            row_data = parent_metadata.copy()
            cells = tr.find_all('td')

            # Map by header if we have them, otherwise just collect
            for i, cell in enumerate(cells):
                header_name = headers[i] if i < len(headers) and headers[i] else f"Column_{i}"
                row_data[header_name] = clean_text(cell.get_text(separator=' | '))

                # Look for links in the cell
                links = cell.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    if '/artist/' in href:
                        row_data['table_artist_id'] = href.split('/')[-1]
                    elif '/performance/' in href:
                        row_data['table_performance_id'] = href.split('/')[-1]
                    elif '/work/' in href:
                        row_data['table_work_id'] = href.split('/')[-1]
                    elif '/release/' in href:
                        row_data['table_release_id'] = href.split('/')[-1]

            # Identify badges in the row (like [1st], Instrumental)
            row_html = str(tr).lower()
            if 'badge-original' in row_html or '[1st]' in row_html:
                row_data['row_is_first_release'] = 'True'
            if 'badge-instrumental' in row_html or '>instrumental<' in row_html:
                row_data['row_is_instrumental'] = 'True'

            rows.append(row_data)

    return rows

def write_sqlite(data: list[dict[str, Any]], output_db_path: str):
    if not data:
        return
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())

    keys = list(all_keys)
    # Sanitize keys for sqlite columns
    safe_keys = [re.sub(r'[^a-zA-Z0-9_]', '_', k) for k in keys]

    with sqlite3.connect(output_db_path) as conn:
        cursor = conn.cursor()
        cols_def = ", ".join([f'"{k}" TEXT' for k in safe_keys])
        cursor.execute(f'CREATE TABLE IF NOT EXISTS shs_data ({cols_def})')

        insert_sql = f'INSERT INTO shs_data ({", ".join([f'"{k}"' for k in safe_keys])}) VALUES ({", ".join(["?" for _ in safe_keys])})'

        records = []
        for row in data:
            records.append(tuple(str(row.get(k, '')) for k in keys))

        cursor.executemany(insert_sql, records)
        conn.commit()
    logger.info(f"Successfully wrote {len(data)} rows to {output_db_path}")

def process_file(filepath: Path) -> list[dict[str, Any]]:
    """Worker function to process a single file."""
    try:
        html_content = read_html_file(filepath)
        soup = BeautifulSoup(html_content, 'lxml')

        parent_metadata = parse_html_page(filepath, soup, html_content)
        parent_metadata = apply_business_rules(parent_metadata)

        rows = extract_tables(soup, parent_metadata)
        if not rows:
            rows = [parent_metadata]

        for row in rows:
            apply_business_rules(row)

        return rows
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to process {filepath.name}: {e}")
        return [{'Filename': filepath.name, 'Error': str(e)}]

def write_csv(data: list[dict[str, Any]], output_path: str):
    if not data:
        logger.warning("No data to write.")
        return

    # Aggregate all dynamic keys
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())

    # Put priority standard columns first
    priority_cols = [
        'Filename', 'canonical_url', 'shs_entity_type', 'shs_entity_id', 'is_all_versions_view',
        'page_title', 'document_heading', 'work_title', 'work_id', 'performance_title', 'performance_id',
        'performing_artist', 'artist_name', 'artist_id', 'release_title', 'release_id'
    ]

    fieldnames = [c for c in priority_cols if c in all_keys]
    other_cols = sorted([c for c in all_keys if c not in fieldnames and c != 'Error'])
    fieldnames.extend(other_cols)
    if 'Error' in all_keys:
        fieldnames.append('Error')

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    logger.info(f"Successfully wrote {len(data)} rows to {output_path}")

def write_audit_queue(data: list[dict[str, Any]], output_path: str):
    """Write non-latin / translation exclusions."""
    # Dummy logic: if work_language isn't English/Instrumental, put in audit queue
    audit_data = [
        row for row in data
        if row.get('work_language') and row['work_language'].lower() not in ('english', 'instrumental')
    ]

    if audit_data:
        write_csv(audit_data, output_path)
        logger.info(f"Wrote {len(audit_data)} rows to audit queue: {output_path}")

def execute_pipeline(args):
    files = []
    if args.input_file:
        files.append(Path(args.input_file))
    elif args.input_dir:
        files = list(Path(args.input_dir).glob("*.html"))

    logger.info(f"Found {len(files)} HTML files to process.")

    parsed_data = []
    if args.workers > 1:
        with multiprocessing.Pool(args.workers) as pool:
            results = pool.map(process_file, files)
            for res in results:
                parsed_data.extend(res)
    else:
        for f in files:
            parsed_data.extend(process_file(f))

    write_csv(parsed_data, args.output_csv)
    write_audit_queue(parsed_data, 'excluded_adaptations.csv')
    if getattr(args, 'output_db', None):
        write_sqlite(parsed_data, args.output_db)

def main():
    args = parse_args()
    if not args.input_dir and not args.input_file:
        logger.error("Must provide either --input-dir or --input-file")
        return

    logger.info(f"Starting parser with {args.workers} workers...")
    execute_pipeline(args)

if __name__ == "__main__":
    main()
