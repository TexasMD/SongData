# Handoff: Identity Churn Review For Jules

Use this prompt with Google Jules.

```text
You are reviewing the MusicDB / SongData repo for identity-churn risk.

Repo/branch:
- Repository: TexasMD/SongData
- Branch/PR branch: codex/reorganize-musicdb
- Working project root: D:\Music\MusicDB if local, otherwise use the GitHub branch state.

Context:
Codex has created a clean patch workflow and several patch manifests, but we
have intentionally not promoted the remaining generated CSV churn wholesale.

Please review these files first:
- docs/reorganization_inventory/20260716_identity_churn/identity_churn_audit.md
- docs/reorganization_inventory/20260716_identity_churn/identity_churn_summary.json
- docs/reorganization_inventory/20260716_identity_churn/recordings_possible_id_matches.csv
- docs/reorganization_inventory/20260716_identity_churn/songs_possible_id_matches.csv
- docs/reorganization_inventory/20260716_identity_churn/recordings_unpaired_added.csv
- docs/reorganization_inventory/20260716_identity_churn/recordings_unpaired_removed.csv
- docs/reorganization_inventory/20260716_identity_churn/songs_unpaired_added.csv
- docs/reorganization_inventory/20260716_identity_churn/songs_unpaired_removed.csv
- docs/reorganization_inventory/20260716_identity_churn/external_link_id_replacements.csv

Important policy:
Many of these rows appear to involve unofficial recordings, cover-song releases,
topic-channel uploads, feature-credit cleanup, or otherwise ambiguous release
identities. Do not treat text cleanup as verified identity metadata. If a row is
ambiguous/questionable, recommend warning flags rather than official replacement.

Your task:
1. Independently assess whether any added/removed Song ID or Recording ID pairs
   are safe identity replacements.
2. Classify each possible match as:
   - safe replacement
   - likely same musical work but ambiguous recording/release identity
   - cover/unofficial upload/topic-channel artifact
   - likely different entity
   - insufficient evidence
3. Review whether the current recommendation is correct:
   "Do not promote generated CSV files wholesale. Keep scalar cleanup/warning
   patches, but do not accept ID churn without source-backed review."
4. Identify any patch manifests that should be adjusted, added, or rejected.
5. Produce a concise report with:
   - findings
   - evidence
   - recommended action
   - any exact rows/IDs requiring manual review

Do not rewrite the generated CSV files directly. Prefer a Markdown review report
or small CSV review table.
```
