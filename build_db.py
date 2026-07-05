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

    # Read CSVs and insert data
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

                cursor.execute('''
                INSERT INTO Songs (title, artist, version, spotify_id, mbid, bpm, key, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (title, artist, version, spotify_id, mbid, bpm, key, notes))

                song_id = cursor.lastrowid

                # Handle playlists
                if playlists_str:
                    playlists = [p.strip() for p in playlists_str.split(';') if p.strip()]
                    for playlist in playlists:
                        cursor.execute('''
                        INSERT OR IGNORE INTO Playlists (name) VALUES (?)
                        ''', (playlist,))

                        cursor.execute('SELECT id FROM Playlists WHERE name = ?', (playlist,))
                        playlist_id = cursor.fetchone()[0]

                        cursor.execute('''
                        INSERT OR IGNORE INTO SongPlaylists (song_id, playlist_id)
                        VALUES (?, ?)
                        ''', (song_id, playlist_id))

    conn.commit()
    conn.close()
    print(f"Database successfully built at {db_file_path}")

if __name__ == '__main__':
    build_db()
