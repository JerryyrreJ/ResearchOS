[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [switch]$NoBrowser,
    [switch]$WorkspaceShell
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$webRoot = Join-Path $root 'apps\web'
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
$backend = $null
$frontend = $null

function Find-Python312 {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        $candidate = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) {
            return $candidate.Trim()
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $candidate = & python -c "import sys; print(sys.executable if sys.version_info[:2] >= (3, 12) else '')"
        if ($candidate) {
            return $candidate.Trim()
        }
    }
    throw '需要 Python 3.12 或更高版本。请先安装 Python 3.12，然后重新运行 start.ps1。'
}

function Wait-LocalUrl([string]$Url, [string]$Name) {
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2 | Out-Null
            return
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "$Name 启动超时，请查看当前窗口中的错误提示。"
}

Set-Location -LiteralPath $root

if (-not (Test-Path -LiteralPath $venvPython)) {
    $python312 = Find-Python312
    Write-Host '正在创建本地 Python 环境…'
    & $python312 -m venv (Join-Path $root '.venv')
}

if (-not $SkipInstall) {
    Write-Host '正在同步 Python 数据插件…'
    & $venvPython -m pip install --disable-pip-version-check -e '.[data-plugins]'
    if ($WorkspaceShell -and -not (Test-Path -LiteralPath (Join-Path $webRoot 'node_modules'))) {
        Write-Host '正在安装前端依赖…'
        Push-Location $webRoot
        try {
            & npm.cmd ci
        }
        finally {
            Pop-Location
        }
    }
}

Write-Host '正在更新本地数据库结构…'
& $venvPython -m alembic upgrade head

$env:NEXT_PUBLIC_RESEARCHOS_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
$env:WRANGLER_LOG_PATH = '.wrangler/wrangler.log'

try {
    Write-Host '正在启动统一 Python 后端…'
    $backend = Start-Process -FilePath $venvPython `
        -ArgumentList @('-m', 'uvicorn', 'researchos.api.main:app', '--host', '127.0.0.1', '--port', '8000') `
        -WorkingDirectory $root -WindowStyle Hidden -PassThru
    Wait-LocalUrl 'http://127.0.0.1:8000/api/v1/health' '后端'

    if ($WorkspaceShell) {
        Write-Host '正在启动 ResearchOS 工作区外壳…'
        $frontend = Start-Process -FilePath 'npx.cmd' `
            -ArgumentList @('vinext', 'dev', '--host', '127.0.0.1', '--port', '3000') `
            -WorkingDirectory $webRoot -WindowStyle Hidden -PassThru
        Wait-LocalUrl 'http://127.0.0.1:3000' '工作区外壳'
    }

    Write-Host ''
    Write-Host 'MacroTrace / ResearchOS 已启动：' -ForegroundColor Green
    Write-Host '  主产品：http://127.0.0.1:8000'
    if ($WorkspaceShell) {
        Write-Host '  ResearchOS 工作区：http://127.0.0.1:3000'
    }
    Write-Host '  API：http://127.0.0.1:8000/docs'
    Write-Host '  产品主线：数据证据层 → 实证研究图 → 研究报告'
    if (-not $NoBrowser) {
        Start-Process 'http://127.0.0.1:8000'
    }
    Read-Host '按 Enter 停止本地服务'
}
finally {
    if ($frontend -and -not $frontend.HasExited) {
        Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    }
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
}
