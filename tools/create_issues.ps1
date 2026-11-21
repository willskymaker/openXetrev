# Crea su GitHub le issue descritte in docs/issues/*.md
#
# Ogni file: prima riga "# Titolo", seconda riga "Labels: a, b", poi il testo.
# Richiede la GitHub CLI con il login già fatto (gh auth login).
#
#   powershell -File tools\create_issues.ps1 -Repo willskymaker/openXetrev
param(
    [string]$Repo = "willskymaker/openXetrev",
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) {
    $gh = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter gh.exe -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $gh) { throw "GitHub CLI non trovata: winget install GitHub.cli" }

$files = Get-ChildItem (Join-Path $PSScriptRoot "..\docs\issues") -Filter *.md | Sort-Object Name
$labels = @{}
# Non ricreare le issue già presenti (stesso titolo), così lo script si può rilanciare.
$existing = @()
if (-not $DryRun) {
    $existing = (& $gh issue list --repo $Repo --state all --limit 200 --json title | ConvertFrom-Json) | ForEach-Object { $_.title }
}
foreach ($f in $files) {
    $lines = Get-Content $f.FullName -Encoding UTF8
    $title = ($lines[0] -replace '^#\s*', '').Trim()
    $lab = ($lines[1] -replace '^Labels:\s*', '').Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $body = ($lines | Select-Object -Skip 2) -join "`n"
    foreach ($l in $lab) { $labels[$l] = $true }
    if ($DryRun) { Write-Output "[prova] $title  [$($lab -join ', ')]"; continue }
    if ($existing -contains $title) { Write-Output "già presente, salto: $title"; continue }
    $tmp = New-TemporaryFile
    Set-Content $tmp $body -Encoding UTF8
    foreach ($l in $lab) { & $gh label create $l --repo $Repo --force 2>$null | Out-Null }
    $url = & $gh issue create --repo $Repo --title $title --body-file $tmp --label ($lab -join ',')
    Remove-Item $tmp
    Write-Output "$title -> $url"
}
