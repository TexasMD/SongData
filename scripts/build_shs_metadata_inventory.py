"""Build a source-scoped inventory of saved SHS HTML and SHS scrape fields.

The original 94-page inventory supplies the first 15 columns and first 220
rows. The two source directories are read only. Dynamic CYT reference IDs are
represented by the existing ``cyt:source-reference:*`` row, not one row per ID.

Usage (PowerShell)::

    python scripts\build_shs_metadata_inventory.py --check
    python scripts\build_shs_metadata_inventory.py --write

``--check`` compares a rebuilt CSV with the existing output without writing it.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from lxml import html

HTML_ROOT = Path(r"E:\CYT\sources\original\SHS")
SCRAPE_ROOT = Path(r"E:\CYT\sources\original\SHS-scrape")
BASE_INVENTORY = Path(
    r"E:\MusicDBsourcematerial\raw\saved_web_pages"
    r"\SHStest2_processor_20260906_consolidated\SHS_metadata_inventory.csv"
)
OUTPUT = Path(r"E:\csv\SHS_metadata_inventory_09302026.csv")
EXTRA_FIELDS = [
    "source_scope",
    "origin_class",
    "source_artifact_or_table",
    "observed_html_files_3834",
    "observed_html_occurrences_3834",
    "scrape_nonblank_rows_by_file",
    "value_quality_note",
]


def scan_html(root: Path) -> tuple[dict[str, dict[str, dict[str, int]]], int]:
    occurrences: dict[str, Counter[str]] = defaultdict(Counter)
    file_counts: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    paths = sorted(root.glob("*.html"))
    for path in paths:
        document = html.parse(str(path)).getroot()
        found: dict[str, Counter[str]] = defaultdict(Counter)
        for node in document.xpath("//head/meta"):
            for attr in ("name", "property", "http-equiv", "itemprop", "charset"):
                value = node.get(attr)
                if value is not None:
                    found["head_meta"][attr + ":" + (value or "(blank)")] += 1
                    break
        for node in document.xpath("//head/link"):
            found["head_link"][node.get("rel") or "(blank)"] += 1
        for node in document.xpath(
            "//*[@itemprop or @itemtype or @property or @typeof or @itemid or @itemref]"
        ):
            for attr in ("itemprop", "itemtype", "property", "typeof", "itemid", "itemref"):
                value = node.get(attr)
                if value is not None:
                    key_value = value if attr in ("itemprop", "itemtype", "property", "typeof") else "(value)"
                    found["semantic_attribute"][attr + ":" + key_value] += 1
        for node in document.xpath('//main//dt|//section[@id="main"]//dt'):
            label = " ".join(node.itertext()).strip().rstrip(":").strip()
            found["detail_label"][label or "(blank)"] += 1
        for node in document.xpath('//main//thead//th|//section[@id="main"]//thead//th'):
            label = " ".join(node.itertext()).strip()
            found["table_heading"][label or "(blank)"] += 1
        for node in document.xpath(
            '//script[@type="application/ld+json" or @type="application/json"]'
        ):
            found["structured_script"][node.get("type")] += 1
        for node in document.xpath(
            "//*[@data-cyt-date-status or @data-cyt-date-sort or @data-cyt-date-precision]"
        ):
            for attr in ("data-cyt-date-status", "data-cyt-date-sort", "data-cyt-date-precision"):
                if node.get(attr) is not None:
                    found["date_attribute"][attr] += 1
        for family, counts in found.items():
            occurrences[family].update(counts)
            for key in counts:
                file_counts[family][key].add(str(path))
    return {
        family: {
            key: {"occurrences": count, "files": len(file_counts[family][key]), "file_set": file_counts[family][key]}
            for key, count in counts.items()
        }
        for family, counts in occurrences.items()
    }, len(paths)


def scan_scrape(root: Path) -> tuple[list[dict], dict[str, int]]:
    csv_sets: list[dict] = []
    json_keys: Counter[str] = Counter()

    def walk(value: object, prefix: str = "", depth: int = 0) -> None:
        if depth > 6:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else key
                json_keys[path] += 1
                walk(child, path, depth + 1)
        elif isinstance(value, list):
            # The inventory describes observed shapes, not every array item.
            for child in value[:1]:
                walk(child, prefix + "[]", depth + 1)

    for path in sorted(root.rglob("*.csv")):
        counts: Counter[str] = Counter()
        row_count = 0
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            headers = next(reader)
            for record in reader:
                row_count += 1
                for index, key in enumerate(headers):
                    if key.strip() and index < len(record) and record[index].strip():
                        counts[key] += 1
        csv_sets.append(
            {"path": str(path.relative_to(root)), "rows": row_count,
             "headers": headers, "nonblank": dict(counts)}
        )
    for path in root.rglob("*.jsonl"):
        with path.open(encoding="utf-8-sig") as handle:
            for line in handle:
                try:
                    walk(json.loads(line))
                except json.JSONDecodeError:
                    continue
    for path in root.rglob("*.json"):
        if path.name.startswith("manifest") or "catalog_manifest" in path.name:
            continue
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        values = list(data.values())[:10000] if isinstance(data, dict) else data[:10000]
        for value in values:
            walk(value)
    return csv_sets, dict(json_keys)


def html_stats(key: str, families: dict) -> tuple[int | str, int | str]:
    pair: tuple[str, str] | None = None
    if key.startswith("cyt:"):
        pair = "head_meta", "name:" + key
    elif key.startswith("meta["):
        match = re.match(r"meta\[(name|property|http-equiv|itemprop|charset)=([^\]]+)\]", key)
        if match:
            pair = "head_meta", match.group(1) + ":" + match.group(2)
    elif key.startswith(("itemprop:", "itemtype:")):
        pair = "semantic_attribute", key
    elif key.startswith("detail:"):
        pair = "detail_label", key[7:]
    elif key.startswith("table-column:"):
        pair = "table_heading", key[13:]
    elif key.startswith("link[rel="):
        match = re.match(r"link\[rel=([^\]]+)\]", key)
        if match:
            pair = "head_link", match.group(1)
    elif key.startswith("data-cyt-date-"):
        pair = "date_attribute", key
    if key == "cyt:source-reference:*":
        head_meta = families.get("head_meta", {})
        occurrences = sum(
            value["occurrences"] for name, value in head_meta.items()
            if name.startswith("name:cyt:source-reference:")
        )
        file_set = set()
        for name, value in head_meta.items():
            if name.startswith("name:cyt:source-reference:"):
                file_set.update(value.get("file_set", set()))
        return len(file_set) if file_set else "", occurrences or ""
    if pair:
        stats = families.get(pair[0], {}).get(pair[1])
        if stats:
            return stats["files"], stats["occurrences"]
    return "", ""


def make_rows(
    base_rows: list[dict], fields: list[str], families: dict,
    csv_sets: list[dict], json_keys: dict[str, int], scrape_root: Path,
) -> list[dict]:
    rows: list[dict] = []
    keys: set[str] = set()

    def add(row: dict) -> None:
        key = row["metadata_key"]
        if key not in keys:
            keys.add(key)
            rows.append({field: row.get(field, "") for field in fields})

    def generated(
        key: str, definition: str, category: str, status: str, scope: str,
        origin: str, artifact: str, observed_files: int | str = "",
        occurrences: int | str = "", scrape_counts: str = "", note: str = "",
        rule: str = "",
    ) -> None:
        row = {field: "" for field in fields}
        row.update(
            metadata_key=key, plain_english_definition=definition, category=category,
            collection_status=status, applies_to_page_types="as present",
            source_html_or_evidence=artifact,
            identification_rule=rule or "Exact field name or path",
            parsing_and_normalization="Preserve raw value and source context; normalize only in a separate field",
            output_name_or_path=key, cardinality="Zero or more per source record",
            confidence_or_review_rule="Observed field presence does not establish entity identity or relationship truth",
            preservation_notes="Keep source path, source row or HTML locator, and original value",
            source_scope=scope, origin_class=origin, source_artifact_or_table=artifact,
            observed_html_files_3834=observed_files,
            observed_html_occurrences_3834=occurrences,
            scrape_nonblank_rows_by_file=scrape_counts, value_quality_note=note,
        )
        add(row)

    for source_row in base_rows:
        row = dict(source_row)
        observed_files, occurrences = html_stats(row["metadata_key"], families)
        row.update(
            source_scope="saved HTML; 94-page processor inventory",
            origin_class=(
                "derived display/audit" if row["category"] in (
                    "normalized CYT metadata", "audit and review metadata",
                    "derived entity registry", "entity reference registry", "JSON structural metadata",
                ) else "source or structural observation"
            ),
            source_artifact_or_table="SHS/*.html; 94-page inventory source",
            observed_html_files_3834=observed_files,
            observed_html_occurrences_3834=occurrences,
            scrape_nonblank_rows_by_file="", value_quality_note="",
        )
        if row["metadata_key"] == "cyt:source-reference:*":
            row["observed_html_files_3834"] = ""
            row["value_quality_note"] = "Dynamic REF keys collapsed to one field family; file count not computed"
        if row["metadata_key"].startswith("cyt:") and row["metadata_key"] not in (
            "cyt:source-original-url", "cyt:source-relative-url",
            "cyt:source-reference-count", "cyt:source-reference:*",
        ):
            row["value_quality_note"] = "Managed CYT field from processor inventory; source HTML may lack this exact meta tag"
        add(row)

    for family, entries in families.items():
        for raw, stats in entries.items():
            if family == "head_meta":
                if raw.startswith("name:cyt:source-reference:"):
                    continue
                attr, value = raw.split(":", 1)
                key, category = f"meta[{attr}={value}]", "observed head metadata"
                note = "CYT enrichment in source HTML; not an SHS-native field" if value.startswith("cyt:") else ""
            elif family == "head_link":
                key, category = f"link[rel={raw}]", "head link metadata"
                note = "Technical or discovery link; URL is stored in HTML"
            elif family == "semantic_attribute":
                if raw.startswith(("itemid:", "itemref:")):
                    continue
                key = raw
                category = "schema.org microdata" if raw.startswith(("itemprop:", "itemtype:")) else "other semantic markup"
                note = "Non-SHS page markup observed in source folder" if raw.startswith(("typeof:mw:", "property:mw:")) else ""
            elif family == "detail_label":
                key, category = "detail:" + raw, "labelled definition metadata"
                note = "Context-specific label; raw value and linked IDs require separate extraction"
            elif family == "table_heading":
                key, category = "table-column:" + raw, "table metadata"
                note = "A column heading is not itself a performance or relationship assertion"
            elif family == "structured_script":
                key, category = "script[type=" + raw + "]", "embedded structured metadata"
                note = "Preserve raw script and parse JSON only when valid"
            elif family == "date_attribute":
                key, category = raw, "date sort metadata"
                note = "Derived date attribute; retain displayed date separately"
            else:
                continue
            generated(
                key, f'Observed {family.replace("_", " ")} field {raw}.', category,
                "observed_in_full_html_root", "saved HTML", "source or enrichment observation",
                "SHS/*.html", stats["files"], stats["occurrences"], note=note,
                rule="Exact HTML attribute, label, or heading",
            )

    by_column: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for dataset in csv_sets:
        for heading in dataset["headers"]:
            if heading:
                by_column[heading].append((
                    dataset["path"], dataset["rows"], dataset["nonblank"].get(heading, 0)
                ))
    quality = {
        "work_id": "Primary website scrape often contains navigation strings rather than a numeric SHS work ID; validate before identity use",
        "performance_id": "Primary website scrape often contains the navigation string versions; validate before identity use. Some consolidated IDs are synthetic",
        "artist_birth_date": "Blank in the primary 86,669-row website scrape",
        "artist_nationality": "Blank in the primary 86,669-row website scrape",
        "work_title": "Blank in the primary 86,669-row website scrape; may be filled in derived data",
        "total_samples_count": "Blank in the primary 86,669-row website scrape",
        "pagination_sort_parameter": "Blank in the primary 86,669-row website scrape",
        "performance_info_badge": "May concatenate multiple badges; preserve raw text",
        "original_first_release_year": "Derived from consolidated scrape; verify source-work lineage before interpreting as root-original chronology",
        "performance_type": "Derived classification in consolidated scrape; not an SHS-native type assertion",
        "is_original_release": "Derived flag in consolidated scrape; do not promote without direct evidence",
        "raw_metadata_json": "Nested API/source payload; retain without flattening away relationships",
        "relationship_type": "Exporter-derived relationship label; verify endpoint identities and source relationship evidence",
    }
    for heading, sources in sorted(by_column.items(), key=lambda item: item[0].casefold()):
        paths = [path for path, _, _ in sources]
        direct = any("files\\01_SHSscrapeMyMusicBase.csv" in path or "database_exports\\staging_shs.csv" in path for path in paths)
        api = any("files\\06_requested_artist_shs_results.csv" in path or "files\\07_shs_artist_probe" in path for path in paths)
        antigrav = any("SHS-scrape-antigrav" in path for path in paths)
        external = heading.startswith(("spotify_", "whosampled_", "musicbrainz_")) or heading == "musicbrainz_MBID"
        audit = heading.endswith(("_hash", "_json")) or heading in (
            "batch_id", "created_at", "source_file", "source_row_id", "source_row_number",
            "policy_version", "confidence_status",
        )
        if external:
            origin = "cross-provider enrichment; not SHS-native"
        elif direct:
            origin = "website scrape source or copied staging"
        elif api:
            origin = "API response or query/export context"
        elif antigrav:
            origin = "consolidated/derived scrape field"
        elif audit:
            origin = "derived evidence or audit field"
        else:
            origin = "derived or normalized scrape export"
        category = "cross-provider context column" if external else "scraped SHS data column"
        if audit:
            category = "scrape provenance and audit column"
        note = quality.get(heading, "")
        if external and not note:
            note = "Source is another provider or cross-provider match; not native SHS metadata"
        if heading in (
            "shs_work_ids", "shs_performance_ids", "shs_source_urls", "shs_metadata_json",
            "shs_live_work_ids", "shs_live_performance_ids", "shs_live_source_urls",
            "shs_live_metadata_json",
        ):
            note = "SHS candidate/enrichment output; verify exact provider IDs and source evidence"
        if heading == "source_scrape_file":
            note = "Lineage pointer to scrape input file"
        counts = "; ".join(f"{path}: {nonblank}/{total}" for path, total, nonblank in sources)
        artifact = "; ".join(paths)
        definition = heading.replace("_", " ").strip().capitalize() + " field in scraped SHS dataset(s)."
        generated(
            "scrape.csv:" + heading, definition, category, "observed_scrape_column",
            "SHS-scrape", origin, artifact, scrape_counts=counts, note=note,
            rule="Exact CSV header; preserve per-file row context",
        )

    for path in sorted(json_keys, key=str.casefold):
        if path.startswith("payload."):
            origin = "SHS API raw payload"
        elif path.startswith(("details", "matched")):
            origin = "SHS API cache payload"
        else:
            origin = "scrape query or cache wrapper"
        note = "Array paths were inspected from the first item of each array; additional item shapes may exist" if "[]" in path else ""
        generated(
            "scrape.json:" + path, f"Observed JSON path {path}.",
            "scraped SHS JSON path", "observed_json_path", "SHS-scrape", origin,
            "SHS-scrape-codex/files/13_raw_metadata_audit.jsonl; SHS-scrape-codex/files/14_shs_live_cache.json",
            note=note, rule="Exact nested JSON key path; [] denotes an array item",
        )

    seen_sql: set[str] = set()
    for database in sorted(scrape_root.rglob("*.sqlite")):
        uri = "file:" + str(database).replace("\\", "/") + "?mode=ro&immutable=1"
        connection = sqlite3.connect(uri, uri=True)
        for (table,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'shs_search_%'"
        ):
            for column in connection.execute(f'PRAGMA table_info("{table}")'):
                name = column[1]
                if name in by_column or name in seen_sql or re.fullmatch(r"unnamed_column_\d+", name):
                    continue
                seen_sql.add(name)
                artifact = str(database.relative_to(scrape_root)) + "#" + table
                generated(
                    "scrape.sqlite:" + name,
                    f"SQLite column {name} in scraped-data store.",
                    "scrape database and state field", "observed_sqlite_schema",
                    "SHS-scrape", "storage, API request state, or consolidated data",
                    artifact,
                    note="Database schema presence does not imply a populated value; inspect source table and lineage",
                    rule="Exact SQLite table column",
                )
        connection.close()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-root", type=Path, default=HTML_ROOT)
    parser.add_argument("--scrape-root", type=Path, default=SCRAPE_ROOT)
    parser.add_argument("--base-inventory", type=Path, default=BASE_INVENTORY)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Rebuild in memory and compare with output")
    mode.add_argument("--write", action="store_true", help="Write the output CSV")
    args = parser.parse_args()
    with args.base_inventory.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        base_fields = list(reader.fieldnames or [])
        base_rows = list(reader)
    fields = base_fields + EXTRA_FIELDS
    families, html_count = scan_html(args.html_root)
    csv_sets, json_keys = scan_scrape(args.scrape_root)
    rows = make_rows(base_rows, fields, families, csv_sets, json_keys, args.scrape_root)
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    data = ("\ufeff" + text.getvalue()).encode("utf-8")
    if args.check:
        if args.output.read_bytes() != data:
            raise SystemExit(f"Inventory differs from {args.output}: {len(rows)} rows")
        print(f"Matches {args.output}: {len(rows)} rows, {len(fields)} columns, {html_count} HTML files")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
        print(f"Wrote {args.output}: {len(rows)} rows, {len(fields)} columns, {html_count} HTML files")


if __name__ == "__main__":
    main()
