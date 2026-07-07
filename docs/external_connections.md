# External Connections and Credentials

## Rule

No active MusicDB script should contain a literal API key, client secret, token, password, or personal source credential.

Use environment variables instead:

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `DISCOGS_TOKEN`
- `MUSICBRAINZ_USER_AGENT`

See `.env.example` for the expected names.

## Current Connections

- Spotify Web API: credentialed metadata lookup and verification.
- iTunes Search API: public metadata lookup and verification.
- Discogs API: credentialed metadata lookup and verification.
- MusicBrainz API: public lookup with a clear User-Agent.
- SecondHandSongs: generated search links only.
- WhoSampled: generated search links only.
- Ultimate Guitar: generated search links only, with fields for official and best tab URLs after verification.

## Credential Finding

The legacy `D:\Music\Main_Song_Database` scripts contain hardcoded Spotify and Discogs credentials. Those values were not carried forward into active MusicDB scripts. Treat those credentials as exposed and rotate them before using related services again.
