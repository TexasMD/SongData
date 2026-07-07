# MusicDB Pro Console

Stitch-inspired React console for browsing the MusicDB SQLite prototype.

## Run Locally

From the repository root, start the read-only API:

```powershell
$env:MUSICDB_SQLITE_PATH = "D:\Music\MusicDB\data\staging\jules\music_antigravity_review.sqlite"
python -m pip install -r api\requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

## Data Safety

- The API opens `MUSICDB_SQLITE_PATH` read-only, defaulting to `D:\Music\MusicDB\data\staging\jules\music_antigravity_review.sqlite`.
- The frontend does not write to `data\processed\Main_Song_Database.csv`.
- Similarity, covers, and vibe search are review/navigation helpers only.

## Interface Notes

- The UI follows the local Stitch reference under `D:\Music\MusicDB\stitch`.
- The main grid uses AG Grid for dense sorting/filtering/column resizing.
- The right inspector and bottom action bar are driven by selected grid rows.
