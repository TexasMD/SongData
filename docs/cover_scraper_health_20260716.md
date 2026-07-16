# Cover Scraper Health - 2026-07-16

Live smoke case:

```powershell
python scripts\smoke_cover_sources.py --title Hallelujah --artist "Leonard Cohen" --year 1984
```

Observed result:

| Source | Status | Result |
| --- | --- | --- |
| `cover.info` | Functional | Returned 210 cover/original relationship rows for `Hallelujah` / `Leonard Cohen`. |
| `SecondHandSongs` | Not currently useful through this client | Current `search/performance?format=json` calls returned 0 rows for the same known cover-heavy query. |
| `WhoSampled` | Blocked in current environment | Search requests returned HTTP 403 after backoff attempts. |

SecondHandSongs supports an optional API key via:

```powershell
$env:SECONDHANDSONGS_API_KEY = "<your key>"
```

The client sends this as `X-API-Key` when present. Do not commit the key.

Local parser/update tests still pass:

```powershell
python -m pytest tests\test_cover_sources.py tests\test_cover_updates.py -q
```

Result: 6 passed.

## Impression

The existing cover scraping system is tenuous:

- `cover.info` is the only live source confirmed to return complete-looking results today.
- `SecondHandSongs` code has parser coverage, but the live endpoint path did not return results for a known high-coverage song.
- `WhoSampled` parser coverage exists, but live access is blocked by anti-bot behavior in this environment.

Do not merge PR `#60` or any replacement WhoSampled implementation until it proves equal or better behavior against this smoke test and the existing parser tests.

## Recommended Next Step

Use `scripts\smoke_cover_sources.py` as the baseline health check before and after scraper changes. Treat cover-source results as source observations, not official verified metadata, unless exact source URLs and relationship evidence are captured.
