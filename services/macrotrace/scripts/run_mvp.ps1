[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $Python)) {
    throw 'Local environment is missing. Run .\scripts\setup_mvp.ps1 first.'
}

Set-Location $ProjectRoot
Write-Host "MacroTrace is available at http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop the server.'
& $Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port $Port
