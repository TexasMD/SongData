# Cover Scraper Health - 2026-07-16

Live smoke case:

```powershell
python scripts\smoke_cover_sources.py --title Hallelujah --artist "Leonard Cohen" --year 1984
```

The smoke script now includes SecondHandSongs diagnostics for:

- exact performance search count
- broad performance search count
- work search count
- performance detail cover/original counts
- known-cover presence checks for Jeff Buckley and John Cale

It also treats a zero-row source as suspicious when another checked source
returns at least 10 rows. In that case, the empty source gets one retry and is
marked `suspicious_empty_after_retry` if it still returns nothing.

Observed result:

| Source | Status | Result |
| --- | --- | --- |
| `cover.info` | Functional | Returned 210 cover/original relationship rows for `Hallelujah` / `Leonard Cohen`. |
| `SecondHandSongs` | Functional after API-domain/detail fix | The dedicated API domain returned 674 cover/original relationship rows through `/performance/1108` detail for the same known cover-heavy query. |
| `WhoSampled` | Blocked in current environment | Search requests returned HTTP 403 after backoff attempts. |

Additional SHS spot check:

```powershell
python scripts\smoke_cover_sources.py --title "Tainted Love" --artist "Gloria Jones" --year 1964 --source SecondHandSongs --output data\exports\codex\secondhandsongs_tainted_love_smoke_20260716.json
```

Result: SecondHandSongs returned 221 normalized cover rows for `Tainted Love`
/ `Gloria Jones`. The live API search found one exact original performance
at `https://api.secondhandsongs.com/performance/646`, 222 broad performance
matches across zero-based result pages, and a performance-detail result count
of 225.

SecondHandSongs API access works through `https://api.secondhandsongs.com`.
The API can be used without a key at lower rate limits. If SHS issues a real
project key, set it via:

```powershell
$env:SECONDHANDSONGS_API_KEY = "<your key>"
```

The client sends this as `X-API-Key` when present. Do not commit private keys.
The public key shown in SHS documentation appears to be an example and returned
`401 Unauthorized` in this environment.

Implementation notes:

- Use `https://api.secondhandsongs.com`, not the website search URL, for live API calls.
- SHS search pages are zero-based.
- Do not send `format=json` to the dedicated API domain.
- `pageSize=100` works; larger page sizes returned `400 Bad Request`.
- Prefer `/performance/{id}` detail once the exact source performance is found; detail returned a richer cover family than broad search pages.
- Derive smoke diagnostics from the scrape run's own source checks. Immediate duplicate SHS calls can return inconsistent windows under rate limits and make a healthy scrape look empty.
- `search/object` returned server errors in this environment and should not be used as the primary path yet.
- Repeated broad search calls can return inconsistent windows under SHS limits. Treat detail lookup as the primary source-family result and broad search as diagnostics.

Local parser/update tests still pass:

```powershell
python -m pytest tests\test_cover_sources.py tests\test_cover_updates.py -q
```

Result: 8 passed.

## Impression

The existing cover scraping system is tenuous:

- `cover.info` returns complete-looking results today.
- `SecondHandSongs` returns live API results after using the dedicated API domain, zero-based pagination, and performance-detail lookup; deeper completeness may still require a real issued key or source-specific review.
- `WhoSampled` parser coverage exists, but live access is blocked by anti-bot behavior in this environment.
- `WhoSampled` should be retained as a reliable third relationship source once
  exact cover/sample/remix evidence is captured, even though live automation is
  currently access-constrained.

Do not merge PR `#60` or any replacement WhoSampled implementation until it proves equal or better behavior against this smoke test and the existing parser tests.

The current WhoSampled implementation is fragile but intentionally rate-limited
and parser-tested. Any PR that replaces it must run this smoke script and
`tests\test_cover_sources.py` before merge.

## Recommended Next Step

Use `scripts\smoke_cover_sources.py` as the baseline health check before and after scraper changes. Treat cover-source results as source observations, not official verified metadata, unless exact source URLs and relationship evidence are captured.
