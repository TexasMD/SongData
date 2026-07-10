import { useEffect, useMemo, useRef, useState } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import type { ColDef, GetContextMenuItemsParams, MenuItemDef } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';

ModuleRegistry.registerModules([AllCommunityModule]);

const API_BASE_URL = import.meta.env.VITE_MUSICDB_API_URL ?? 'http://localhost:8000/api';

type Recording = {
  recording_id: string;
  title?: string;
  artist?: string;
  album?: string;
  version?: string;
  release_year?: number;
  duration?: string;
  genre?: string;
  genre_detail?: string;
  bpm?: number;
  key?: string;
  mood_tags?: string;
  event_tags?: string;
  situation_tags?: string;
  playlists?: string;
  crowd_energy?: string;
  spotify_track_id?: string;
  musicbrainz_recording_id?: string;
  similarity_score?: number;
  reasons?: string;
  score_breakdown?: Record<string, number>;
};

type Columns = Record<string, boolean>;

const defaultColumns: Columns = {
  recording_id: true,
  title: true,
  artist: true,
  album: true,
  bpm: true,
  key: true,
  genre: true,
  mood_tags: true,
  playlists: true,
  similarity_score: true,
};

const coreFields = Object.keys(defaultColumns);

function text(value: unknown, fallback = '-') {
  if (value === null || value === undefined || value === '') return fallback;
  return String(value);
}

function tagList(value?: string) {
  return (value ?? '')
    .split(/[;,]/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 4);
}

function App() {
  const gridRef = useRef<AgGridReact<Recording>>(null);
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [selectedRows, setSelectedRows] = useState<Recording[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [localFilter, setLocalFilter] = useState('');
  const [vibeQuery, setVibeQuery] = useState('');
  const [queryNote, setQueryNote] = useState('');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [rowLimit, setRowLimit] = useState<number | 'All'>(500);
  const [visibleColumns, setVisibleColumns] = useState<Columns>(defaultColumns);

  const selectedSong = selectedRows[0];

  const rowLimitQuery = rowLimit === 'All' ? 1000 : rowLimit;

  const fetchJson = async <T,>(url: string, init?: RequestInit): Promise<T> => {
    const response = await fetch(url, init);
    if (!response.ok) {
      const body = await response.text();
      throw new Error(body || `${response.status} ${response.statusText}`);
    }
    return response.json() as Promise<T>;
  };

  const loadRecordings = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchJson<{ results: Recording[] }>(
        `${API_BASE_URL}/recordings?limit=${rowLimitQuery}`,
      );
      setRecordings(data.results ?? []);
      setQueryNote('VIEW: ALL_TRACKS_V2');
      setSelectedRows([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recordings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRecordings();
  }, [rowLimit]);

  const runVibeSearch = async () => {
    if (!vibeQuery.trim()) {
      await loadRecordings();
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await fetchJson<{ sql: string; results: Recording[] }>(
        `${API_BASE_URL}/vibe_search`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: vibeQuery }),
        },
      );
      setRecordings(data.results ?? []);
      setQueryNote(data.sql);
      setSelectedRows([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Vibe search failed');
    } finally {
      setLoading(false);
    }
  };

  const findSimilar = async () => {
    if (!selectedSong) return;
    setLoading(true);
    setError('');
    try {
      const data = await fetchJson<{ results: Recording[] }>(
        `${API_BASE_URL}/similarity/${encodeURIComponent(selectedSong.recording_id)}?limit=30`,
      );
      setRecordings(data.results ?? []);
      setQueryNote(`SIMILAR TO ${selectedSong.recording_id}`);
      setSelectedRows([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Similarity search failed');
    } finally {
      setLoading(false);
    }
  };

  const runCoverUpdate = async (rows?: Recording[]) => {
    const targets = rows ?? selectedRows;
    if (!targets.length) return;
    setLoading(true);
    setError('');
    try {
      const data = await fetchJson<{ covers: Recording[]; stage_dir?: string; run_id?: string }>(`${API_BASE_URL}/cover_updates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recording_ids: targets.map((row) => row.recording_id) }),
      });
      setRecordings(data.covers ?? []);
      const targetLabel = targets.length === 1 ? targets[0].recording_id : `${targets.length} TRACKS`;
      setQueryNote(`COVER UPDATE FOR ${targetLabel}${data.stage_dir ? ` -> ${data.stage_dir}` : ''}`);
      setSelectedRows([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cover search failed');
    } finally {
      setLoading(false);
    }
  };

  const columnDefs = useMemo<ColDef<Recording>[]>(() => [
    {
      field: 'recording_id',
      headerName: 'ID',
      hide: !visibleColumns.recording_id,
      width: 124,
      cellClass: 'console-id',
    },
    { field: 'title', headerName: 'Title', hide: !visibleColumns.title, minWidth: 240, flex: 1.2 },
    { field: 'artist', headerName: 'Artist', hide: !visibleColumns.artist, minWidth: 190, flex: 1 },
    { field: 'album', headerName: 'Album', hide: !visibleColumns.album, minWidth: 180, flex: 1 },
    { field: 'bpm', headerName: 'BPM', hide: !visibleColumns.bpm, width: 82, cellClass: 'console-hot' },
    { field: 'key', headerName: 'Key', hide: !visibleColumns.key, width: 84, cellClass: 'console-cyan' },
    { field: 'genre', headerName: 'Genre', hide: !visibleColumns.genre, minWidth: 130 },
    {
      field: 'mood_tags',
      headerName: 'Mood',
      hide: !visibleColumns.mood_tags,
      minWidth: 160,
      valueGetter: ({ data }) => tagList(data?.mood_tags).join(', '),
    },
    {
      field: 'playlists',
      headerName: 'Playlists',
      hide: !visibleColumns.playlists,
      minWidth: 160,
      valueGetter: ({ data }) => tagList(data?.playlists).join(', '),
    },
    {
      field: 'similarity_score',
      headerName: 'Score',
      hide: !visibleColumns.similarity_score,
      width: 92,
      valueFormatter: ({ value }) => (value ? Number(value).toFixed(1) : '-'),
      cellClass: 'console-score',
    },
  ], [visibleColumns]);

  const defaultColDef = useMemo<ColDef<Recording>>(() => ({
    sortable: true,
    filter: true,
    resizable: true,
    suppressHeaderMenuButton: false,
  }), []);

  const onSelectionChanged = () => {
    const rows = gridRef.current?.api.getSelectedRows() ?? [];
    setSelectedRows(rows);
  };

  const clearSelection = () => {
    gridRef.current?.api.deselectAll();
    setSelectedRows([]);
  };

  const toggleColumn = (field: string) => {
    setVisibleColumns((previous) => ({ ...previous, [field]: !previous[field] }));
  };

  const getContextMenuItems = (params: GetContextMenuItemsParams<Recording>) => {
    const selected = gridRef.current?.api.getSelectedRows() ?? [];
    const targets = selected.length > 0 ? selected : params.node?.data ? [params.node.data] : [];
    const items = [...(params.defaultItems ?? [])] as Array<string | MenuItemDef>;
    if (targets.length > 0) {
      items.push('separator');
      items.push({
        name: `Update Covers${targets.length > 1 ? ` (${targets.length})` : ''}`,
        action: () => {
          void runCoverUpdate(targets);
        },
      });
    }
    return items as any;
  };

  return (
    <div className="console-shell">
      <header className="console-topbar">
        <div className="brand-lockup">
          <span className="brand-mark">+</span>
          <h1>STUDIO_CONSOLE_V1</h1>
        </div>
        <nav className="top-tabs" aria-label="Console views">
          <button className="active">Matrix</button>
          <button>Resources</button>
          <button>Patch Bay</button>
          <button>Automation</button>
        </nav>
        <div className="command-zone">
          <input
            aria-label="Filter visible rows"
            value={localFilter}
            onChange={(event) => setLocalFilter(event.target.value)}
            placeholder="SEARCH / FILTER"
          />
          <input
            aria-label="Mood or vibe search"
            value={vibeQuery}
            onChange={(event) => setVibeQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') void runVibeSearch();
            }}
            placeholder="MOOD / VIBE"
          />
          <button onClick={() => void runVibeSearch()}>Run</button>
          <button onClick={() => setIsSettingsOpen(true)} aria-label="Grid settings">Settings</button>
        </div>
      </header>

      <div className="console-body">
        <aside className="left-rail" aria-label="Major modes">
          <button className="rail-active" title="Grid">GRID</button>
          <button title="Filters">FLT</button>
          <button title="Similarity">SIM</button>
          <button title="Sources">SRC</button>
        </aside>

        <main className="grid-stage">
          <div className="grid-toolbar">
            <div className="toolbar-left">
              <button onClick={() => void loadRecordings()}>Refresh</button>
              <button onClick={() => setIsSettingsOpen(true)}>Columns</button>
              <span>{queryNote}</span>
            </div>
            <div className="toolbar-right">
              {loading && <span className="status-hot">Loading</span>}
              {error && <span className="status-error">{error}</span>}
            </div>
          </div>
          <section className="ag-theme-quartz-dark console-grid" aria-label="MusicDB recordings grid">
            <AgGridReact<Recording>
              ref={gridRef}
              rowData={recordings}
              columnDefs={columnDefs}
              defaultColDef={defaultColDef}
              getContextMenuItems={getContextMenuItems}
              rowSelection={{
                mode: 'multiRow',
                checkboxes: true,
                headerCheckbox: true,
                enableClickSelection: false,
              }}
              onSelectionChanged={onSelectionChanged}
              quickFilterText={localFilter}
              rowHeight={28}
              headerHeight={32}
              animateRows={false}
            />
          </section>
        </main>

        <aside className="inspector" aria-label="Selected song inspector">
          <div className="inspector-kicker">{selectedSong ? selectedSong.recording_id : 'NO_SELECTION'}</div>
          <h2>{text(selectedSong?.title, 'Select a track')}</h2>
          <p>{selectedSong ? `${text(selectedSong.artist)} // ${text(selectedSong.release_year)} // ${text(selectedSong.album)}` : 'Use the grid checkboxes to inspect metadata and run similarity.'}</p>

          <div className="waveform" aria-hidden="true">
            {Array.from({ length: 52 }).map((_, index) => (
              <span key={index} style={{ height: `${8 + ((index * 11) % 34)}px` }} />
            ))}
          </div>

          <div className="inspector-fields">
            <label>
              BPM
              <output>{text(selectedSong?.bpm)}</output>
            </label>
            <label>
              Key
              <output>{text(selectedSong?.key)}</output>
            </label>
            <label>
              Genre
              <output>{text(selectedSong?.genre)}</output>
            </label>
            <label>
              Version
              <output>{text(selectedSong?.version)}</output>
            </label>
          </div>

          <div className="tag-section">
            <h3>Mood / Context</h3>
            <div>
              {[...tagList(selectedSong?.mood_tags), ...tagList(selectedSong?.event_tags), ...tagList(selectedSong?.situation_tags)].map((tag) => (
                <span key={tag} className="tag-chip">{tag}</span>
              ))}
              {!selectedSong && <span className="empty-note">No active selection</span>}
            </div>
          </div>

          {selectedSong?.similarity_score && (
            <div className="score-panel">
              <h3>Similarity</h3>
              <strong>{Number(selectedSong.similarity_score).toFixed(1)}</strong>
              <p>{text(selectedSong.reasons, 'Structured match')}</p>
            </div>
          )}
        </aside>
      </div>

      <footer className="console-statusbar">
        <span>SYSTEM_ACTIVE_v2.4</span>
        <span>SHOWN: {recordings.length}</span>
        <span>SELECTED: {selectedRows.length}</span>
      </footer>

      {selectedRows.length > 0 && (
        <div className="selection-bar">
          <strong>{selectedRows.length} TRACKS SELECTED</strong>
          <button onClick={findSimilar} disabled={selectedRows.length !== 1}>Similar</button>
          <button onClick={() => void runCoverUpdate()} disabled={selectedRows.length === 0}>Update Covers</button>
          <button onClick={clearSelection}>Clear</button>
        </div>
      )}

      {isSettingsOpen && (
        <div className="settings-backdrop" role="dialog" aria-modal="true" aria-label="Grid settings">
          <section className="settings-panel">
            <header>
              <h2>Column Matrix</h2>
              <button onClick={() => setIsSettingsOpen(false)}>Close</button>
            </header>
            <label className="settings-select">
              Row Limit
              <select
                value={rowLimit}
                onChange={(event) => setRowLimit(event.target.value === 'All' ? 'All' : Number(event.target.value))}
              >
                <option value={100}>100 Rows</option>
                <option value={500}>500 Rows</option>
                <option value={1000}>1000 Rows</option>
                <option value="All">All Rows</option>
              </select>
            </label>
            <div className="column-list">
              {coreFields.map((field) => (
                <label key={field}>
                  <input
                    type="checkbox"
                    checked={visibleColumns[field]}
                    onChange={() => toggleColumn(field)}
                  />
                  <span>{field.replaceAll('_', ' ')}</span>
                </label>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default App;
