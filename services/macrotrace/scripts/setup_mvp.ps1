[CmdletBinding()]
param(
    [switch]$SkipSnapshot,
    [switch]$SyncData,
    [switch]$SkipTests,
    [string]$PythonExecutable = '',
    [string]$SnapshotUrl = 'https://github.com/ZhenyuanPAN822/macrotrace/releases/latest/download/MacroTrace-data.zip'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$DatabasePath = Join-Path $ProjectRoot 'data\macrotrace.duckdb'
$EnvironmentFile = Join-Path $ProjectRoot '.env.local'
$EnvironmentExample = Join-Path $ProjectRoot '.env.local.example'

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $Created = $false
    Write-Host 'Creating a Python 3.11+ virtual environment...'

    if ($PythonExecutable) {
        & $PythonExecutable -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
        if ($LASTEXITCODE -ne 0) {
            throw 'The selected Python executable must be Python 3.11 or newer.'
        }
        & $PythonExecutable -m venv (Join-Path $ProjectRoot '.venv')
        $Created = $LASTEXITCODE -eq 0
    } else {
        $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($PythonLauncher) {
            & $PythonLauncher.Source -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                & $PythonLauncher.Source -3 -m venv (Join-Path $ProjectRoot '.venv')
                $Created = $LASTEXITCODE -eq 0
            }
        }

        if (-not $Created) {
            foreach ($CommandName in @('python', 'python3')) {
                $PythonCommand = Get-Command $CommandName -ErrorAction SilentlyContinue
                if (-not $PythonCommand) {
                    continue
                }
                & $PythonCommand.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
                if ($LASTEXITCODE -ne 0) {
                    continue
                }
                & $PythonCommand.Source -m venv (Join-Path $ProjectRoot '.venv')
                $Created = $LASTEXITCODE -eq 0
                if ($Created) {
                    break
                }
            }
        }
    }

    if (-not $Created -or -not (Test-Path -LiteralPath $VenvPython)) {
        throw 'Could not create the virtual environment. Install Python 3.11 or newer and try again.'
    }
}

& $VenvPython -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw 'MacroTrace requires Python 3.11 or newer.'
}

if (-not (Test-Path -LiteralPath $EnvironmentFile) -and (Test-Path -LiteralPath $EnvironmentExample)) {
    Copy-Item -LiteralPath $EnvironmentExample -Destination $EnvironmentFile
    Write-Host 'Created .env.local with empty credential fields.'
}

Write-Host 'Installing MacroTrace dependencies...'
& $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $ProjectRoot 'requirements.txt')

if (-not $SkipSnapshot -and -not (Test-Path -LiteralPath $DatabasePath)) {
    $DataDirectory = Split-Path -Parent $DatabasePath
    $DownloadDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("macrotrace-" + [guid]::NewGuid().ToString('N'))
    $ArchivePath = Join-Path $DownloadDirectory 'MacroTrace-data.zip'
    New-Item -ItemType Directory -Path $DownloadDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $DataDirectory -Force | Out-Null
    try {
        Write-Host 'Downloading the reviewed official-data snapshot...'
        Invoke-WebRequest -Uri $SnapshotUrl -OutFile $ArchivePath
        Expand-Archive -LiteralPath $ArchivePath -DestinationPath $DownloadDirectory -Force
        $DownloadedDatabase = Get-ChildItem -LiteralPath $DownloadDirectory -Filter '*.duckdb' -File | Select-Object -First 1
        if (-not $DownloadedDatabase) {
            throw 'The snapshot archive did not contain a DuckDB file.'
        }
        Move-Item -LiteralPath $DownloadedDatabase.FullName -Destination $DatabasePath -Force
        Write-Host 'Installed data\macrotrace.duckdb.'
    } finally {
        Remove-Item -LiteralPath $DownloadDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if ($SyncData) {
    Write-Host 'Synchronizing real official data...'
    & $VenvPython (Join-Path $PSScriptRoot 'sync_data.py')
}

if (-not $SkipTests) {
    Write-Host 'Running tests...'
    & $VenvPython -m pytest (Join-Path $ProjectRoot 'tests')
}

Write-Host 'MacroTrace setup is complete.' -ForegroundColor Green
Write-Host 'Open it with: .\scripts\start_macrotrace.ps1'
Write-Host 'Keep that terminal open; press Ctrl+C when you want to stop the server.'
