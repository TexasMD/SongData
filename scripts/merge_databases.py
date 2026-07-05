#!/usr/bin/env python3
"""Compatibility wrapper for the old database merge command.

The old version wrote directly to data/processed/Main_Song_Database.csv.
This safer wrapper builds a non-destructive staging candidate instead.
"""

from __future__ import annotations

from merge_d_music_legacy import main


if __name__ == "__main__":
    raise SystemExit(main())
