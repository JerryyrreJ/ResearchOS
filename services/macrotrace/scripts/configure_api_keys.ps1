[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$FromEnvironment
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $ProjectRoot '.env.local'

function Read-SecretPlainText {
    param([Parameter(Mandatory)][string]$Prompt)

    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

$names = @(
    'FRED_API_KEY',
    'BLS_API_KEY',
    'BEA_API_KEY',
    'CENSUS_API_KEY',
    'EIA_API_KEY',
    'DEEPSEEK_API_KEY'
)

$values = [ordered]@{}
foreach ($name in $names) {
    $value = if ($FromEnvironment) {
        [Environment]::GetEnvironmentVariable($name, 'Process')
    }
    else {
        Read-SecretPlainText -Prompt "Paste $name"
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "$name cannot be empty. No file was written."
    }
    $values[$name] = $value.Trim()
}

$lines = foreach ($name in $names) {
    "$name=$($values[$name])"
}
$lines += 'DEEPSEEK_MODEL=deepseek-v4-flash'

$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllLines($EnvPath, $lines, $utf8WithoutBom)

Write-Host "Saved API credentials to the local ignored file:" -ForegroundColor Green
Write-Host $EnvPath
Write-Host "Credential values were not printed."

if (-not $SkipTests) {
    & (Join-Path $PSScriptRoot 'test_connectors.ps1') -EnvFile $EnvPath
}
