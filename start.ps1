$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -e '.[test]'
}

Start-Process 'http://127.0.0.1:8000/docs'
Write-Host 'ResearchOS C 端已启动。关闭此窗口即可停止服务。'
.\.venv\Scripts\python.exe -m uvicorn apps.researchos_api.app.main:app --host 127.0.0.1 --port 8000

