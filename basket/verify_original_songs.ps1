param(
    [string]$Input = "D:\Music\MusicDB\basket\original_songs.csv",
    [string]$Output = "D:\Music\MusicDB\basket\original_songs_verified.csv",
    [string]$Log = "D:\Music\MusicDB\data\logs\verify_original_songs.log"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyScript = Join-Path $scriptDir "verify_original_songs.py"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found on PATH."
}

python $pyScript --input $Input --output $Output --log $Log
