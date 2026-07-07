#!/usr/bin/env python3
"""Create staged manual-review decisions from enriched skipped-review rows."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SKIPPED_REVIEW_CSV = PROJECT_DIR / "data" / "exports" / "codex" / "active_main_patch_skipped_review.csv"
DECISIONS_CSV = PROJECT_DIR / "data" / "staging" / "codex" / "manual_review_decisions.csv"
SUMMARY_JSON = PROJECT_DIR / "data" / "exports" / "codex" / "manual_review_decisions_summary.json"

SPOTIFY_CONFLICT_REASON = "active Spotify ID differs from active Spotify Track ID; manual review required"
REVIEWER = "Codex preference heuristic"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def haystack(row: dict[str, str], prefix: str) -> str:
    return " ".join(
        [
            clean(row.get(f"{prefix} Spotify Title")),
            clean(row.get(f"{prefix} Spotify Artist")),
            clean(row.get(f"{prefix} Spotify Album")),
        ]
    ).lower()


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def spotify_features(row: dict[str, str], prefix: str) -> dict[str, bool]:
    text = haystack(row, prefix)
    return {
        "remastered": has_any(text, [r"\bremaster(?:ed)?\b", r"\bremastered version\b"]),
        "live": has_any(text, [r"\blive\b", r"\bunplugged\b", r"\bconcert\b", r"\bsession\b"]),
        "extended_ep_7": has_any(
            text,
            [
                r"\bextended\b",
                r"\bextended play\b",
                r"\bep\b",
                r"\b7[ -]?inch\b",
                r"\b7\"",
                r"\b7''",
                r"\bsingle version\b",
                r"\bsingle edit\b",
                r"\bradio edit\b",
            ],
        ),
    }


def feature_score(features: dict[str, bool]) -> int:
    score = 0
    if features["remastered"]:
        score += 4
    if features["live"]:
        score -= 8
    if features["extended_ep_7"]:
        score -= 3
    return score


def describe_features(label: str, features: dict[str, bool]) -> str:
    names = [name for name, present in features.items() if present]
    return f"{label}: {', '.join(names) if names else 'standard/studio indicators'}"


def decide_spotify_conflict(row: dict[str, str]) -> tuple[str, str, str]:
    active_features = spotify_features(row, "Active")
    staged_features = spotify_features(row, "Staged")
    active_score = feature_score(active_features)
    staged_score = feature_score(staged_features)

    if active_score > staged_score:
        decision = "keep_active"
        accepted = clean(row.get("Active Value"))
        reason = "Accepted active Spotify Track ID based on stated preferences. "
    elif staged_score > active_score:
        decision = "use_staged"
        accepted = clean(row.get("Staged Value"))
        reason = "Accepted staged Spotify ID based on stated preferences. "
    else:
        decision = "needs_review"
        accepted = ""
        reason = "No decisive preference signal between active and staged Spotify metadata. "

    reason += (
        f"{describe_features('active', active_features)}; "
        f"{describe_features('staged', staged_features)}."
    )
    return decision, accepted, reason


def decision_for_row(row: dict[str, str], reviewed_at: str) -> dict[str, str]:
    if clean(row.get("Reason")) == SPOTIFY_CONFLICT_REASON:
        decision, accepted, reason = decide_spotify_conflict(row)
    else:
        decision = "needs_review"
        accepted = ""
        reason = f"No automatic preference rule applied for skipped-review reason: {clean(row.get('Reason'))}."

    return {
        "Active CSV Line": clean(row.get("Active CSV Line")),
        "Title": clean(row.get("Title")),
        "Artist": clean(row.get("Artist")),
        "Field": clean(row.get("Field")),
        "Decision": decision,
        "Accepted Value": accepted,
        "Reason": reason,
        "Reviewer": REVIEWER,
        "Reviewed At": reviewed_at,
        "Active Spotify Title": clean(row.get("Active Spotify Title")),
        "Active Spotify Artist": clean(row.get("Active Spotify Artist")),
        "Active Spotify Album": clean(row.get("Active Spotify Album")),
        "Staged Spotify Title": clean(row.get("Staged Spotify Title")),
        "Staged Spotify Artist": clean(row.get("Staged Spotify Artist")),
        "Staged Spotify Album": clean(row.get("Staged Spotify Album")),
        "Source Review Reason": clean(row.get("Reason")),
    }


def main() -> int:
    rows = read_csv(SKIPPED_REVIEW_CSV)
    reviewed_at = datetime.now(timezone.utc).isoformat()
    decisions = [decision_for_row(row, reviewed_at) for row in rows]
    fields = [
        "Active CSV Line",
        "Title",
        "Artist",
        "Field",
        "Decision",
        "Accepted Value",
        "Reason",
        "Reviewer",
        "Reviewed At",
        "Active Spotify Title",
        "Active Spotify Artist",
        "Active Spotify Album",
        "Staged Spotify Title",
        "Staged Spotify Artist",
        "Staged Spotify Album",
        "Source Review Reason",
    ]
    write_csv(DECISIONS_CSV, fields, decisions)

    summary = {
        "generated_at": reviewed_at,
        "input_csv": str(SKIPPED_REVIEW_CSV),
        "decisions_csv": str(DECISIONS_CSV),
        "rows": len(decisions),
        "decision_counts": dict(sorted(Counter(row["Decision"] for row in decisions).items())),
        "spotify_conflict_rows": sum(1 for row in rows if clean(row.get("Reason")) == SPOTIFY_CONFLICT_REASON),
        "preference_rules": [
            "Prefer remastered tracks.",
            "Prefer studio versions over live/unplugged/concert/session versions.",
            "Prefer standard versions over extended play, EP, 7-inch, single-version, and radio-edit variants.",
        ],
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
