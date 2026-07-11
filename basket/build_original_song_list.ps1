param(
    [string]$SongData = "D:\Music\MusicDB\basket\Song_Data.csv",
    [string]$CoverList = "D:\Music\MusicDB\basket\listcoversongs.csv",
    [string]$Output = "D:\Music\MusicDB\basket\original_songs.csv"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyScript = Join-Path $scriptDir "build_original_song_list.py"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found on PATH."
}

python $pyScript --song-data $SongData --covers $CoverList --output $Output
