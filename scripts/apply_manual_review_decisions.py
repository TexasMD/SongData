#!/usr/bin/env python3
"""Apply resolved manual-review decisions to the active MusicDB CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
ACTIVE_CSV = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
STAGED_CSV = PROJECT_DIR / "data" / "staging" / "d_music_legacy_merge" / "merged_candidate_Main_Song_Database.csv"
DECISIONS_CSV = PROJECT_DIR / "data" / "staging" / "codex" / "manual_review_decisions.csv"
BACKUP_ROOT = PROJECT_DIR / "data" / "backups" / "manual_review_application"
REPORT_JSON = PROJECT_DIR / "data" / "exports" / "codex" / "manual_review_application_summary.json"
ACTION_CSV = PROJECT_DIR / "data" / "exports" / "codex" / "manual_review_application_actions.csv"


class ApplyError(RuntimeError):
    pass


def clean(value: object) -> str:
    return str(value or "").strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def active_row_for_decision(active_rows: list[dict[str, str]], decision: dict[str, str]) -> tuple[int, dict[str, str]]:
    line = int(clean(decision.get("Active CSV Line")))
    index = line - 2
    if index < 0 or index >= len(active_rows):
        raise ApplyError(f"Active CSV line {line} is outside active row range.")
    return line, active_rows[index]


def staged_row_for_decision(staged_rows: list[dict[str, str]], decision: dict[str, str]) -> dict[str, str]:
    line = int(clean(decision.get("Active CSV Line")))
    index = line - 2
    if index < 0 or index >= len(staged_rows):
        raise ApplyError(f"Staged CSV line {line} is outside staged row range.")
    return staged_rows[index]


def build_actions(
    active_headers: list[str],
    active_rows: list[dict[str, str]],
    staged_rows: list[dict[str, str]],
    decisions: list[dict[str, str]],
) -> list[dict[str, str]]:
    unresolved = [row for row in decisions if clean(row.get("Decision")) not in {"keep_active", "use_staged"}]
    if unresolved:
        raise ApplyError(f"Manual review still has {len(unresolved)} unresolved decisions.")

    actions: list[dict[str, str]] = []
    for decision in decisions:
        if clean(decision.get("Decision")) == "keep_active":
            continue

        field = clean(decision.get("Field"))
        context = clean(decision.get("Review Context Type"))
        accepted = clean(decision.get("Accepted Value"))
        line, active_row = active_row_for_decision(active_rows, decision)

        if context == "staged_only_row_signature":
            staged_row = staged_row_for_decision(staged_rows, decision)
            actions.append(
                {
                    "Action": "append_staged_row",
                    "Active CSV Line": str(line),
                    "Title": clean(decision.get("Title")),
                    "Artist": clean(decision.get("Artist")),
                    "Field": "__row_signature__",
                    "Old Value": "",
                    "New Value": clean(decision.get("Staged Value")),
                    "Reason": clean(decision.get("Reason")),
                    "_staged_row_json": json.dumps(staged_row, ensure_ascii=False),
                }
            )
            continue

        if field not in active_headers:
            raise ApplyError(f"Field {field!r} is not present in active CSV headers.")
        if not accepted:
            raise ApplyError(f"use_staged decision on line {line} for {field!r} has no accepted value.")

        old_value = clean(active_row.get(field))
        if old_value == accepted:
            action_type = "already_matches"
        else:
            action_type = "update_field"
        actions.append(
            {
                "Action": action_type,
                "Active CSV Line": str(line),
                "Title": clean(decision.get("Title")),
                "Artist": clean(decision.get("Artist")),
                "Field": field,
                "Old Value": old_value,
                "New Value": accepted,
                "Reason": clean(decision.get("Reason")),
                "_staged_row_json": "",
            }
        )
    return actions


def apply_actions(
    active_headers: list[str],
    active_rows: list[dict[str, str]],
    actions: list[dict[str, str]],
) -> None:
    for action in actions:
        if action["Action"] == "already_matches":
            continue
        if action["Action"] == "update_field":
            line = int(action["Active CSV Line"])
            active_rows[line - 2][action["Field"]] = action["New Value"]
            continue
        if action["Action"] == "append_staged_row":
            staged_row = json.loads(action["_staged_row_json"])
            active_rows.append({header: clean(staged_row.get(header)) for header in active_headers})
            continue
        raise ApplyError(f"Unknown action type: {action['Action']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply resolved MusicDB manual-review decisions.")
    parser.add_argument("--write", action="store_true", help="Actually modify the active database.")
    args = parser.parse_args()

    active_sha_before = sha256(ACTIVE_CSV)
    active_headers, active_rows = read_csv(ACTIVE_CSV)
    _, staged_rows = read_csv(STAGED_CSV)
    _, decisions = read_csv(DECISIONS_CSV)
    actions = build_actions(active_headers, active_rows, staged_rows, decisions)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_ROOT / timestamp / ACTIVE_CSV.name
    if args.write:
        backup_path.parent.mkdir(parents=True, exist_ok=False)
        shutil.copy2(ACTIVE_CSV, backup_path)
        apply_actions(active_headers, active_rows, actions)
        write_csv(ACTIVE_CSV, active_headers, active_rows)

    action_fields = ["Action", "Active CSV Line", "Title", "Artist", "Field", "Old Value", "New Value", "Reason"]
    write_csv(ACTION_CSV, action_fields, actions)

    active_sha_after = sha256(ACTIVE_CSV)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "write" if args.write else "dry_run",
        "active_database_modified": active_sha_before != active_sha_after,
        "active_csv": str(ACTIVE_CSV),
        "decisions_csv": str(DECISIONS_CSV),
        "actions_csv": str(ACTION_CSV),
        "backup_path": str(backup_path) if args.write else "",
        "active_sha_before": active_sha_before,
        "active_sha_after": active_sha_after,
        "decision_counts": dict(sorted(Counter(clean(row.get("Decision")) for row in decisions).items())),
        "action_counts": dict(sorted(Counter(row["Action"] for row in actions).items())),
        "field_action_counts": dict(sorted(Counter(row["Field"] for row in actions).items())),
        "action_count": len(actions),
        "active_rows_after": len(active_rows),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to apply these decisions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
