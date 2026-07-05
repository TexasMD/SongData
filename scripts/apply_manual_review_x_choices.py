#!/usr/bin/env python3
"""Apply user x-mark choices to manual_review_decisions.csv."""

from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DECISIONS_CSV = PROJECT_DIR / "data" / "staging" / "codex" / "manual_review_decisions.csv"
SUMMARY_JSON = PROJECT_DIR / "data" / "exports" / "codex" / "manual_review_x_choice_summary.json"
BACKUP_DIR = PROJECT_DIR / "data" / "backups" / "manual_review_x_choices"

# Preserve duplicate CSV headers by using positional indexes.
ACTIVE_MARKER_COLUMNS = [11, 24]  # "Use Active", "keep active"
STAGED_MARKER_COLUMNS = [15, 39]  # two "Use staged" columns


def clean(value: object) -> str:
    return str(value or "").strip()


def is_x(row: list[str], index: int) -> bool:
    return index < len(row) and clean(row[index]).lower() == "x"


def value_at(row: list[str], header: list[str], name: str) -> str:
    try:
        index = header.index(name)
    except ValueError:
        return ""
    return clean(row[index]) if index < len(row) else ""


def set_value(row: list[str], header: list[str], name: str, value: str) -> None:
    index = header.index(name)
    while len(row) < len(header):
        row.append("")
    row[index] = value


def accepted_value(row: list[str], header: list[str], decision: str) -> str:
    field = value_at(row, header, "Field")
    if decision == "keep_active":
        if field == "__row_signature__":
            return value_at(row, header, "Active Review Title") or value_at(row, header, "Title")
        return value_at(row, header, "Active Value") or value_at(row, header, "Candidate Value")
    if decision == "use_staged":
        if field == "__row_signature__":
            return value_at(row, header, "Staged Value") or value_at(row, header, "Staged Review Title")
        return value_at(row, header, "Staged Value")
    return ""


def main() -> int:
    with DECISIONS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    data = rows[1:]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / timestamp / DECISIONS_CSV.name
    backup_path.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(DECISIONS_CSV, backup_path)

    reviewed_at = datetime.now(timezone.utc).isoformat()
    counts: Counter[str] = Counter()
    conflicts: list[int] = []

    for line_number, row in enumerate(data, start=2):
        active_marked = any(is_x(row, index) for index in ACTIVE_MARKER_COLUMNS)
        staged_marked = any(is_x(row, index) for index in STAGED_MARKER_COLUMNS)
        if active_marked and staged_marked:
            conflicts.append(line_number)
            continue
        if not active_marked and not staged_marked:
            counts["unmarked"] += 1
            continue

        decision = "keep_active" if active_marked else "use_staged"
        set_value(row, header, "Decision", decision)
        set_value(row, header, "Accepted Value", accepted_value(row, header, decision))
        set_value(row, header, "Reason", f"User selected {decision} by placing x in the review spreadsheet.")
        set_value(row, header, "Reviewer", "User x selection")
        set_value(row, header, "Reviewed At", reviewed_at)
        counts[decision] += 1

    with DECISIONS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    summary = {
        "generated_at": reviewed_at,
        "decisions_csv": str(DECISIONS_CSV),
        "backup_path": str(backup_path),
        "marker_columns": {
            "active": [header[index] for index in ACTIVE_MARKER_COLUMNS],
            "staged": [header[index] for index in STAGED_MARKER_COLUMNS],
        },
        "counts": dict(sorted(counts.items())),
        "conflicting_marked_csv_lines": conflicts,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if not conflicts else 2


if __name__ == "__main__":
    raise SystemExit(main())
