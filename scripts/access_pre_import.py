#!/usr/bin/env python3
"""
Enhanced Pre‑Import Pipeline for Access
---------------------------------------

This script:
 1. Cleans all CSVs
 2. Infers schema (PK/FK candidates)
 3. Builds dependency graph
 4. Computes correct Access import order
 5. Detects orphan foreign keys
 6. Writes cleaned CSVs + reports

Author: Seth’s Copilot
"""

import csv
import re
import json
from pathlib import Path
from collections import defaultdict, deque

TARGET_DIR = Path(r"C:\Users\sethm\Music\MusicDB-Access")
CLEAN_DIR = TARGET_DIR / "cleaned"
REPORT_DIR = TARGET_DIR / "reports"


NUMERIC_FIELD_REGEX = re.compile(r"(id|_id|pk|fk|number|count|index)$", re.IGNORECASE)
YEAR_FIELD_REGEX = re.compile(r"(year|release_year)$", re.IGNORECASE)


def clean_value(field, value):
    if value is None:
        return ""

    v = str(value).strip()
    v = v.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    v = v.replace('"', '""')

    if v.lower() in ("none", "null", "n/a", "na", "-", "--", "unknown"):
        return ""

    if NUMERIC_FIELD_REGEX.search(field):
        return re.sub(r"[^\d\.-]", "", v)

    if YEAR_FIELD_REGEX.search(field):
        m = re.search(r"\b(\d{4})\b", v)
        return m.group(1) if m else ""

    return v


def clean_csv(path: Path):
    cleaned_path = CLEAN_DIR / (path.stem + "_clean.csv")

    with path.open("r", encoding="utf-8-sig", newline="") as f_in, cleaned_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f_out:

        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(
            f_out, fieldnames=reader.fieldnames, quoting=csv.QUOTE_ALL
        )
        writer.writeheader()

        for row in reader:
            cleaned_row = {
                field: clean_value(field, row.get(field, ""))
                for field in reader.fieldnames
            }
            writer.writerow(cleaned_row)

    return cleaned_path


def infer_schema(csv_path: Path):
    """Infer PK and FK candidates based on column names."""
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames

        pk_candidates = [
            f for f in fields if f.lower() in ("id", "pk") or f.lower().endswith("_id")
        ]
        fk_candidates = [
            f for f in fields if f.lower().endswith("_id") and f.lower() != "id"
        ]

        return {
            "table": csv_path.stem.removesuffix("_clean"),
            "fields": fields,
            "pk_candidates": pk_candidates,
            "fk_candidates": fk_candidates,
        }


def load_table(csv_path: Path):
    rows = []
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_dependency_graph(schemas):
    # Map parent -> children to unblock children when parent is imported
    graph = defaultdict(set)

    # Ensure all tables exist in the graph, even if they have no children
    for schema in schemas:
        table = schema["table"]
        if table not in graph:
            graph[table] = set()

    for schema in schemas:
        table = schema["table"]
        for fk in schema["fk_candidates"]:
            parent_table = fk.removesuffix("_id")
            if parent_table + "s" in graph:
                parent_table = parent_table + "s"
            elif parent_table not in graph and parent_table + "s" not in graph:
                # Ensure parent_table is in graph to prevent KeyError
                graph[parent_table] = set()
            graph[parent_table].add(table)

    return graph


def topological_sort(graph):
    indegree = defaultdict(int)

    # Ensure all nodes in graph keys exist in indegree
    for t in graph:
        if t not in indegree:
            indegree[t] = 0

    # Calculate indegrees based on parent -> children relationships
    for parent, children in graph.items():
        for child in children:
            indegree[child] += 1

    queue = deque([t for t in indegree if indegree[t] == 0])
    order = []

    while queue:
        t = queue.popleft()
        order.append(t)
        for child in graph.get(t, []):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    return order


def get_table_pks(csv_path: Path, pk_field: str) -> set:
    """Stream a CSV and extract only the primary keys to save memory."""
    pks = set()
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row.get(pk_field)
            if val is not None and val != "":
                pks.add(val)
    return pks


def detect_orphans(clean_paths, schemas):
    fk_orphans = []

    schemas_by_table = {s["table"]: s for s in schemas}
    paths_by_table = {p.stem.removesuffix("_clean"): p for p in clean_paths}

    # Pre-cache all PK sets to avoid reading parent tables multiple times
    table_pks = {}
    for table, path in paths_by_table.items():
        schema = schemas_by_table.get(table)
        pk_field = "id"
        if schema and schema["pk_candidates"]:
            pk_field = schema["pk_candidates"][0]
        else:
            # Fallback if no schema or pk_candidates: peek at headers
            with path.open("r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                for h in headers:
                    if h.lower() in ("id", "pk") or h.lower().endswith("id"):
                        pk_field = h
                        break
        table_pks[table] = get_table_pks(path, pk_field)

    for schema in schemas:
        table = schema["table"]
        if table not in paths_by_table:
            continue

        path = paths_by_table[table]

        # Stream the child table row by row
        with path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                for fk in schema["fk_candidates"]:
                    parent = fk.removesuffix("_id")
                    if parent + "s" in table_pks:
                        parent += "s"

                    if parent in table_pks:
                        parent_ids = table_pks[parent]
                    else:
                        parent_ids = set()  # Parent table doesn't exist

                    fk_val = r.get(fk)
                    if fk_val and fk_val not in parent_ids:
                        fk_orphans.append(
                            {
                                "table": table,
                                "fk_field": fk,
                                "fk_value": fk_val,
                                "row": r,
                            }
                        )

    return fk_orphans


def main():
    CLEAN_DIR.mkdir(exist_ok=True, parents=True)
    REPORT_DIR.mkdir(exist_ok=True, parents=True)
    csv_files = sorted(TARGET_DIR.glob("*.csv"))
    clean_paths = []

    print("Cleaning CSVs...")
    for p in csv_files:
        clean_paths.append(clean_csv(p))

    print("Inferring schema...")
    schemas = [infer_schema(p) for p in clean_paths]

    with (REPORT_DIR / "schemas.json").open("w") as f:
        json.dump(schemas, f, indent=2)

    print("Building dependency graph...")
    graph = build_dependency_graph(schemas)

    with (REPORT_DIR / "dependency_graph.json").open("w") as f:
        json.dump(graph, f, indent=2)

    print("Computing import order...")
    order = topological_sort(graph)

    with (REPORT_DIR / "import_order.txt").open("w") as f:
        for t in order:
            f.write(t + "\n")

    print("Detecting orphan foreign keys...")
    orphans = detect_orphans(clean_paths, schemas)

    with (REPORT_DIR / "fk_orphans.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=["table", "fk_field", "fk_value", "row"])
        writer.writeheader()
        for o in orphans:
            writer.writerow(o)

    print("\nPipeline complete.")
    print(f"Cleaned CSVs → {CLEAN_DIR}")
    print(f"Reports → {REPORT_DIR}")
    print("Import order written to import_order.txt")


if __name__ == "__main__":
    main()
