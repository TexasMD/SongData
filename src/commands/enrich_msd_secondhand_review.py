from __future__ import annotations

import csv
import logging
import json
import time
from pathlib import Path

from src.whosampled_client import scrape_whosampled, client

logger = logging.getLogger(__name__)

def run(
    write_enabled: bool,
    review_csv: Path,
    sources: str,
    output_csv: Path,
) -> None:
    if not review_csv.exists():
        logger.error(f"Review CSV not found: {review_csv}")
        return

    logger.info(f"Reading review rows from %s", review_csv)
    with review_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        review_rows = list(reader)

    missing_shs_rows = [
        row for row in review_rows
        if "missing_shs_performance_url" in row.get("review_flags", "")
    ]

    logger.info("Found %d rows missing SHS performance URL", len(missing_shs_rows))

    if not write_enabled:
        logger.info("DRY RUN: Would enrich %d rows with WhoSampled data", len(missing_shs_rows))
        return

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    evidence_rows = []
    blocked_count = 0
    error_count = 0
    confirmed_count = 0

    unresolved_rows = []

    def log_progress(source: str, query_kind: str, query_url: str, result_count: int | None, timestamp: str):
        pass

    blocked_detected = False

    for row in missing_shs_rows:
        if blocked_detected:
            unresolved_rows.append(row)
            continue

        left_title = row.get("left_title", "")
        left_artist = row.get("left_artist", "")
        right_title = row.get("right_title", "")
        right_artist = row.get("right_artist", "")
        left_rec_id = row.get("left_recording_id", "")
        right_rec_id = row.get("right_recording_id", "")

        found_relationship = False

        for title, artist, rec_id, direction in [
            (left_title, left_artist, left_rec_id, "left"),
            (right_title, right_artist, right_rec_id, "right"),
        ]:
            if not title or not artist:
                continue

            logger.info("Querying WhoSampled for %s - %s", title, artist)

            initial_delay = client.base_delay

            try:
                covers = scrape_whosampled(title, artist, callback=log_progress)

                # If the delay has more than doubled, it means we hit a 403/429
                if client.base_delay > initial_delay * 2:
                    logger.warning("Detected WhoSampled block/rate-limit. Stopping scraping to save partial results.")
                    blocked_count += 1
                    blocked_detected = True
                    break

                if covers:
                    for cover in covers:
                        evidence = dict(cover)
                        evidence["query_title"] = title
                        evidence["query_artist"] = artist
                        evidence["query_recording_id"] = rec_id
                        evidence["query_direction"] = direction
                        evidence["clique_id"] = row.get("clique_id", "")

                        evidence["relationship_found"] = "Yes"
                        confirmed_count += 1
                        found_relationship = True

                        evidence_rows.append(evidence)
            except Exception as e:
                # The exception might happen after client.base_delay has already been increased.
                # So we check here too.
                if client.base_delay > initial_delay * 2:
                    logger.warning("Detected WhoSampled block/rate-limit via exception. Stopping scraping to save partial results.")
                    blocked_count += 1
                    blocked_detected = True
                    break
                logger.error("Error querying WhoSampled for %s - %s: %s", title, artist, e)
                error_count += 1

        if not found_relationship and not blocked_detected:
            unresolved_rows.append(row)

    logger.info("Writing %d evidence rows to %s", len(evidence_rows), output_csv)

    if evidence_rows:
        fieldnames = list(evidence_rows[0].keys())
        # Ensure all rows have all fieldnames
        for er in evidence_rows:
            for k in er.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        with output_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(evidence_rows)

    logger.info("Summary:")
    logger.info("- Evidence rows written: %d", len(evidence_rows))
    logger.info("- Relationship found (confirmed): %d", confirmed_count)
    logger.info("- Errors/Blocked: %d", error_count + blocked_count)
    logger.info("- Unresolved rows: %d", len(unresolved_rows))

    if unresolved_rows:
        logger.info("- Rows still unresolved:")
        for row in unresolved_rows:
            logger.info("  %s - %s / %s - %s", row.get("left_title", ""), row.get("left_artist", ""), row.get("right_title", ""), row.get("right_artist", ""))

    if evidence_rows:
        logger.info("- Top confirmed examples:")
        for i, example in enumerate(evidence_rows[:10]):
            logger.info("  %d. %s - %s (URL: %s)", i + 1, example.get("title", ""), example.get("artist", ""), example.get("source_url", example.get("url", "")))
