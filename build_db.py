import csv
import sqlite3
import os

def build_db():
    staging_dir = os.path.join('data', 'staging', 'jules')
    db_file_path = os.path.join('data', 'exports', 'jules', 'MusicDB.sqlite')

    # Ensure export directory exists
    os.makedirs(os.path.dirname(db_file_path), exist_ok=True)

    # Remove existing db if we want to rebuild it from scratch
    if os.path.exists(db_file_path):
        os.remove(db_file_path)

    # Connect to database (this creates the file if it doesn't exist)
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        artist TEXT,
        version TEXT,
        spotify_id TEXT,
        mbid TEXT,
        bpm INTEGER,
        key TEXT,
        notes TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS SongPlaylists (
        song_id INTEGER,
        playlist_id INTEGER,
        PRIMARY KEY (song_id, playlist_id),
        FOREIGN KEY (song_id) REFERENCES Songs(id),
        FOREIGN KEY (playlist_id) REFERENCES Playlists(id)
    )
    ''')

    # Read CSVs and collect data
    songs_to_insert = []
    playlist_names_set = set()
    song_playlists_to_resolve = []

    song_id_counter = 1

    for filename in os.listdir(staging_dir):
        if not filename.endswith('.csv'):
            continue

        csv_file_path = os.path.join(staging_dir, filename)
        with open(csv_file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get('Title', '')
                artist = row.get('Artist', '')
                version = row.get('Version', '')
                spotify_id = row.get('Spotify ID', '')
                mbid = row.get('MBID', '')
                bpm = row.get('BPM', '')
                bpm = int(bpm) if bpm else None
                key = row.get('Key', '')
                notes = row.get('Notes', '')
                playlists_str = row.get('Playlists', '')

                songs_to_insert.append((song_id_counter, title, artist, version, spotify_id, mbid, bpm, key, notes))

                if playlists_str:
                    playlists = [p.strip() for p in playlists_str.split(';') if p.strip()]
                    for playlist in playlists:
                        playlist_names_set.add(playlist)
                        song_playlists_to_resolve.append((song_id_counter, playlist))

                song_id_counter += 1

    # Bulk insert songs
    cursor.executemany('''
    INSERT INTO Songs (id, title, artist, version, spotify_id, mbid, bpm, key, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', songs_to_insert)

    # Bulk insert playlists
    cursor.executemany('''
    INSERT OR IGNORE INTO Playlists (name) VALUES (?)
    ''', [(p,) for p in playlist_names_set])

    # Fetch playlist IDs
    cursor.execute('SELECT name, id FROM Playlists')
    playlist_name_to_id = dict(cursor.fetchall())

    # Bulk insert song playlists
    song_playlists_to_insert = [
        (song_id, playlist_name_to_id[playlist_name])
        for song_id, playlist_name in song_playlists_to_resolve
    ]
    cursor.executemany('''
    INSERT OR IGNORE INTO SongPlaylists (song_id, playlist_id)
    VALUES (?, ?)
    ''', song_playlists_to_insert)

    conn.commit()
    conn.close()
    print(f"Database successfully built at {db_file_path}")

if __name__ == '__main__':
    build_db()
