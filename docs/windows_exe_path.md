# Windows App / EXE Path

Goal: ship a tweakable local Windows application for MusicDB without risking the
active CSV/database files.

## Current Baseline

- API: FastAPI app in `api/main.py`.
- UI: Vite/React app in `frontend`.
- Frontend build works:

```powershell
cd frontend
npm run build
```

- API-related tests pass:

```powershell
python -m pytest tests\test_api_display_normalization.py tests\test_db_access_and_vibe.py tests\test_config_and_commands.py -q
```

## Recommended Packaging Sequence

1. **Local launcher first**
   Add a Windows-friendly launcher that starts the FastAPI API, serves the built
   frontend, and opens the local UI in the browser.

2. **Read-only app mode**
   Keep the first `.exe` read-only for browsing, filtering, vibe search, and
   cover-source smoke checks. Route writes through patch manifests.

3. **Bundled static frontend**
   Build `frontend/dist` and serve it from FastAPI so the app has one local web
   surface instead of separate Vite and API processes.

4. **PyInstaller prototype**
   Package the Python API/launcher with PyInstaller. Keep data files external
   under `D:\Music\MusicDB` at first so the executable can be rebuilt without
   embedding private/generated databases.

5. **Controlled write actions**
   Add UI buttons only for reviewable workflows:
   - run source health checks
   - generate patch manifests
   - apply patch manifests with backups
   - export review reports

## Non-Goals For The First EXE

- Do not embed Spotify, YouTube Music, or other credentials.
- Do not directly overwrite `Main_Song_Database.csv`.
- Do not promote generated `SongDB_v2` churn without a patch or review report.
- Do not replace the current scraper stack until the replacement beats the smoke-test baseline.
