[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$AppUrl = "http://127.0.0.1:$Port/"

if (-not (Test-Path -LiteralPath $Python)) {
    throw 'Local environment is missing. Run .\scripts\setup_mvp.ps1 first.'
}

Set-Location $ProjectRoot
Write-Host "MacroTrace is starting at $AppUrl" -ForegroundColor Green
Write-Host 'Keep this terminal open. Press Ctrl+C to stop the server.'

$BrowserJob = $null
if (-not $NoBrowser) {
    $BrowserJob = Start-Job -ScriptBlock {
        param($Url)
        Start-Sleep -Seconds 2
        Start-Process $Url
    } -ArgumentList $AppUrl
}

try {
    & $Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port $Port
} finally {
    if ($BrowserJob) {
        Remove-Job -Job $BrowserJob -Force -ErrorAction SilentlyContinue
    }
}
