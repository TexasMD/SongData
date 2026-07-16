# Cover Scraper Health - 2026-07-16

Live smoke case:

```powershell
python scripts\smoke_cover_sources.py --title Hallelujah --artist "Leonard Cohen" --year 1984
```

Observed result:

| Source | Status | Result |
| --- | --- | --- |
| `cover.info` | Functional | Returned 210 cover/original relationship rows for `Hallelujah` / `Leonard Cohen`. |
| `SecondHandSongs` | Functional after API-domain/pagination fix | The dedicated API domain returned 425 exact-title cover/original relationship rows for the same known cover-heavy query. |
| `WhoSampled` | Blocked in current environment | Search requests returned HTTP 403 after backoff attempts. |

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
- For `Hallelujah`, page 8 returned no rows even though `totalResults` reported more results. Treat the current result as complete for the accessible API window, not necessarily complete for the entire SHS database without an issued API key.

Local parser/update tests still pass:

```powershell
python -m pytest tests\test_cover_sources.py tests\test_cover_updates.py -q
```

Result: 6 passed.

## Impression

The existing cover scraping system is tenuous:

- `cover.info` returns complete-looking results today.
- `SecondHandSongs` returns live API results after using the dedicated API domain and zero-based pagination; deeper completeness may require a real issued key or a different endpoint strategy.
- `WhoSampled` parser coverage exists, but live access is blocked by anti-bot behavior in this environment.

Do not merge PR `#60` or any replacement WhoSampled implementation until it proves equal or better behavior against this smoke test and the existing parser tests.

## Recommended Next Step

Use `scripts\smoke_cover_sources.py` as the baseline health check before and after scraper changes. Treat cover-source results as source observations, not official verified metadata, unless exact source URLs and relationship evidence are captured.
