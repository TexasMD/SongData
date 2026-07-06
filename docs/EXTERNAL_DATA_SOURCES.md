# External Data Sources for MusicDB Enrichment

This document lists external datasets, APIs, and community projects that can be used to fill missing metadata in the MusicDB (BPM, Key, Mood, Tuning, etc.).

## 1. High-Value Datasets

### AcousticBrainz (MTG-UPF)
- **Content**: BPM, Key, Mood, Genre, and audio descriptors for millions of tracks.
- **Identifiers**: MusicBrainz Recording ID.
- **Accessibility**: Public JSON dumps (Low-level and High-level) and CSV summary files.
- **Use Case**: Primary source for algorithmic BPM and Key validation.
- **Link**: [AcousticBrainz Downloads](https://acousticbrainz.org/download)

### Spotify Audio Features (via Kaggle)
- **Content**: Tempo (BPM), Key, Energy, Valence, Danceability, Acousticness.
- **Identifiers**: Spotify Track ID.
- **Accessibility**: Numerous public CSV datasets on Kaggle (e.g., 50k - 1M track collections).
- **Use Case**: Enrichment of mood (Valence) and performance energy.
- **Link**: [Kaggle Spotify Datasets](https://www.kaggle.com/datasets?search=spotify+audio+features)

### Ultimate Guitar Metadata (via Kaggle)
- **Content**: Difficulty, Key, Capo position, Tuning.
- **Identifiers**: Artist/Title (requires normalization).
- **Accessibility**: "Top 850 Guitar Tabs" and other scraped datasets on Kaggle.
- **Use Case**: Filling performance metadata for guitar-centric tracks.
- **Link**: [Top 850 Guitar Tabs](https://www.kaggle.com/datasets/thomaskonstantin/top-850-guitar-tabs)

## 2. Research and MIR Collections

### mirdata (Python Library)
- **Content**: Standardized loaders for dozens of MIR (Music Information Retrieval) datasets.
- **Datasets**: AcousticBrainz, DALI (lyrics/alignment), MAESTRO (piano), etc.
- **Use Case**: Accessing ground-truth academic datasets for specific performance metrics.
- **Link**: [mirdata GitHub](https://github.com/mir-dataset-loaders/mirdata)

### Lakh MIDI Dataset
- **Content**: Tempo, Key, and multitrack instrumentation derived from MIDI files.
- **Link**: [Lakh MIDI Dataset](http://hermandong.com/lakh-pianoroll-dataset/dataset.html)

## 3. Community and Enthusiast Projects

### Steal Your Stats (Grateful Dead)
- **Content**: Setlist roles (Opener, Closer), song durations, and stats.
- **Use Case**: Pattern for "Setlist Role" and "Energy" tagging for live performance.
- **Link**: [Steal Your Stats](https://reddit.com/r/gratefuldead/comments/1u4xkpk/...)

### TraCoTools
- **Content**: Exchange and visualization of DJ metadata (BPM, Key, Beatgrids).
- **Link**: [TraCoTools](https://dark-controller.com/tracotools/)

## 4. Integration Recommendations

1. **AcousticBrainz Mapping**: Prioritize mapping MusicDB recordings to MusicBrainz IDs to unlock AcousticBrainz descriptors.
2. **Kaggle CSV Import**: Use Python scripts to join Kaggle Spotify/UG datasets with MusicDB based on Spotify IDs or normalized Title/Artist pairs.
3. **Generative Refinement**: Use identified external sources as "High Confidence" anchors to train or verify generative suggestions for missing rows.
4. **Link Verification**: Use SecondHandSongs datasets to verify existing `SHS Link` fields and discover missing cover-song relationships.
