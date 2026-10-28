import os
import csv
import json
import argparse
from bs4 import BeautifulSoup

def clean_text(text):
    if not text:
        return ""
    return " ".join(text.strip().split())

def parse_discogs(soup):
    metadata = {
        "json_ld": [],
        "meta_tags": {},
    }

    # JSON-LD
    for script in soup.find_all('script', type='application/ld+json'):
        if script.string:
            try:
                data = json.loads(script.string)
                metadata["json_ld"].append(data)
            except json.JSONDecodeError:
                pass

    # Meta tags
    for meta in soup.find_all('meta'):
        name = meta.get('name') or meta.get('property')
        content = meta.get('content')
        if name and content and (name.startswith('og:') or name.startswith('twitter:') or name == 'description'):
            metadata["meta_tags"][name] = clean_text(content)

    return metadata

def parse_musicbrainz(soup):
    metadata = {
        "properties": {},
        "tables": []
    }

    # Properties list
    for dl in soup.find_all('dl', class_='properties'):
        for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
            key = clean_text(dt.text).replace(':', '')
            val = clean_text(dd.text)
            metadata["properties"][key] = val

    # Tables (e.g., tracklists, relationships)
    for table in soup.find_all('table', class_='tbl'):
        table_data = []
        headers = [clean_text(th.text) for th in table.find_all('th')]
        for tr in table.find_all('tr'):
            row = [clean_text(td.text) for td in tr.find_all('td')]
            if row:
                if headers and len(headers) == len(row):
                    table_data.append(dict(zip(headers, row)))
                else:
                    table_data.append(row)
        if table_data:
            metadata["tables"].append(table_data)

    return metadata

def parse_wiki(soup):
    metadata = {
        "infobox": {},
        "tables": []
    }

    for i, table in enumerate(soup.find_all('table')):
        classes = table.get('class', [])
        # Extract infobox
        if 'infobox' in classes:
            for tr in table.find_all('tr'):
                th = tr.find('th')
                td = tr.find('td')
                if th and td:
                    metadata["infobox"][clean_text(th.text)] = clean_text(td.text)
        else:
            # Other tables
            table_data = []
            headers = [clean_text(th.text) for th in table.find_all('th')]
            for tr in table.find_all('tr'):
                row = [clean_text(td.text) for td in tr.find_all('td')]
                if row:
                    if headers and len(headers) == len(row):
                        table_data.append(dict(zip(headers, row)))
                    else:
                        table_data.append(row)
            if table_data:
                metadata["tables"].append(table_data)

    return metadata

def parse_spotify(soup):
    metadata = {
        "meta_tags": {}
    }

    for meta in soup.find_all('meta'):
        name = meta.get('name') or meta.get('property')
        content = meta.get('content')
        if name and content and (name.startswith('og:') or name.startswith('twitter:') or name == 'description'):
            metadata["meta_tags"][name] = clean_text(content)

    return metadata

def identify_source(filename, soup):
    lower_name = filename.lower()
    if "discogs" in lower_name:
        return "Discogs"
    elif "musicbrainz" in lower_name:
        return "MusicBrainz"
    elif "wiki" in lower_name:
        return "Wiki"
    elif "spotify" in lower_name:
        return "Spotify"

    # Fallback to checking title or tags
    title = soup.title.string if soup.title else ""
    if "discogs" in title.lower():
        return "Discogs"
    elif "musicbrainz" in title.lower():
        return "MusicBrainz"
    elif "wiki" in title.lower():
        return "Wiki"
    elif "spotify" in title.lower():
        return "Spotify"

    return "Unknown"

def scrape_directory(input_dir, output_csv):
    results = []

    for filename in os.listdir(input_dir):
        if not filename.endswith(".html"):
            continue

        filepath = os.path.join(input_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                html = f.read()
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

        soup = BeautifulSoup(html, 'html.parser')
        source = identify_source(filename, soup)
        title = clean_text(soup.title.string) if soup.title else ""

        extracted_data = {}
        if source == "Discogs":
            extracted_data = parse_discogs(soup)
        elif source == "MusicBrainz":
            extracted_data = parse_musicbrainz(soup)
        elif source == "Wiki":
            extracted_data = parse_wiki(soup)
        elif source == "Spotify":
            extracted_data = parse_spotify(soup)
        else:
            # Generic extraction if unknown
            extracted_data = parse_spotify(soup)

        row = {
            "Filename": filename,
            "Source": source,
            "Title": title,
            "JSON_LD": json.dumps(extracted_data.get("json_ld", [])),
            "MetaTags": json.dumps(extracted_data.get("meta_tags", {})),
            "Properties": json.dumps(extracted_data.get("properties", {})),
            "Infobox": json.dumps(extracted_data.get("infobox", {})),
            "Tables": json.dumps(extracted_data.get("tables", []))
        }
        results.append(row)

    if not results:
        print("No data extracted.")
        return

    fieldnames = ["Filename", "Source", "Title", "JSON_LD", "MetaTags", "Properties", "Infobox", "Tables"]

    # Write to CSV
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        print(f"Successfully scraped {len(results)} files to {output_csv}")
    except OSError as e:
        print(f"Error: Could not write to output file '{output_csv}'.")
        print(f"Details: {e}")
        print("Please ensure you have write permissions and the file is not open in another program.")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape metadata from HTML files")
    parser.add_argument("input_dir", help="Directory containing HTML files")
    parser.add_argument("output_csv", help="Path to output CSV file")
    args = parser.parse_args()

    scrape_directory(args.input_dir, args.output_csv)
