param(
    [Parameter(Mandatory = $true)]
    [string]$Title,

    [Parameter(Mandatory = $true)]
    [string]$Artist,

    [string]$Output = "D:\Music\MusicDB\basket\coverdata_shs_ci.csv"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyScript = Join-Path $scriptDir "coverdata_shs_ci.py"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found on PATH."
}

python $pyScript --title $Title --artist $Artist --output $Output
