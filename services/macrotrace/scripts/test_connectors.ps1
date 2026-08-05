[CmdletBinding()]
param(
    [string]$EnvFile = (Join-Path (Split-Path -Parent $PSScriptRoot) '.env.local')
)

$ErrorActionPreference = 'Stop'

function Import-DotEnv {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Secret file not found. Run scripts/configure_api_keys.ps1 first."
    }

    foreach ($line in Get-Content -LiteralPath $Path -Encoding utf8) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) {
            continue
        }
        $parts = $line -split '=', 2
        if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[0])) {
            throw "Invalid .env.local line."
        }
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
    }
}

function Add-Result {
    param(
        [Parameter(Mandatory)][string]$Connector,
        [Parameter(Mandatory)][scriptblock]$Test
    )

    try {
        $detail = & $Test
        $script:Results.Add([pscustomobject]@{
            Connector = $Connector
            Status = 'PASS'
            Detail = [string]$detail
        })
    }
    catch {
        $statusCode = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        $detail = if ($statusCode) {
            "HTTP $statusCode"
        }
        else {
            $_.Exception.GetType().Name
        }
        $script:Results.Add([pscustomobject]@{
            Connector = $Connector
            Status = 'FAIL'
            Detail = $detail
        })
    }
}

Import-DotEnv -Path $EnvFile

$requiredSecrets = @(
    'FRED_API_KEY',
    'BLS_API_KEY',
    'BEA_API_KEY',
    'CENSUS_API_KEY',
    'EIA_API_KEY'
)
foreach ($name in $requiredSecrets) {
    $value = [Environment]::GetEnvironmentVariable($name, 'Process')
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Missing required credential: $name"
    }
}

$Results = [System.Collections.Generic.List[object]]::new()

Add-Result -Connector 'FRED/ALFRED' -Test {
    $uri = 'https://api.stlouisfed.org/fred/series/observations' +
        '?series_id=GDP&file_type=json&sort_order=desc&limit=1' +
        '&api_key=' + [uri]::EscapeDataString($env:FRED_API_KEY)
    $response = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 30
    "observations=$($response.observations.Count)"
}

Add-Result -Connector 'BLS v2' -Test {
    $body = @{
        seriesid = @('CUUR0000SA0')
        startyear = '2025'
        endyear = '2026'
        registrationkey = $env:BLS_API_KEY
    } | ConvertTo-Json
    $response = Invoke-RestMethod `
        -Uri 'https://api.bls.gov/publicAPI/v2/timeseries/data/' `
        -Method Post `
        -ContentType 'application/json' `
        -Body $body `
        -TimeoutSec 30
    if ($response.status -ne 'REQUEST_SUCCEEDED') {
        throw 'BLS request did not succeed.'
    }
    "status=$($response.status)"
}

Add-Result -Connector 'BEA' -Test {
    $uri = 'https://apps.bea.gov/api/data/' +
        '?method=GETDATASETLIST&ResultFormat=JSON' +
        '&UserID=' + [uri]::EscapeDataString($env:BEA_API_KEY)
    $response = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 30
    $datasets = @($response.BEAAPI.Results.Dataset)
    if ($datasets.Count -eq 0) {
        throw 'BEA returned no datasets.'
    }
    "datasets=$($datasets.Count)"
}

Add-Result -Connector 'Census' -Test {
    $uri = 'https://api.census.gov/data/2024/acs/acs1' +
        '?get=NAME%2CB01001_001E&for=us%3A%2A' +
        '&key=' + [uri]::EscapeDataString($env:CENSUS_API_KEY)
    $response = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 30
    if (@($response).Count -lt 2) {
        throw 'Census returned no data rows.'
    }
    "rows=$(@($response).Count - 1)"
}

Add-Result -Connector 'EIA v2' -Test {
    $uri = 'https://api.eia.gov/v2/' +
        '?api_key=' + [uri]::EscapeDataString($env:EIA_API_KEY)
    $response = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 30
    $routes = @($response.response.routes)
    if ($routes.Count -eq 0) {
        throw 'EIA returned no routes.'
    }
    "routes=$($routes.Count)"
}

Add-Result -Connector 'Treasury Fiscal Data' -Test {
    $uri = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/' +
        'v2/accounting/od/debt_to_penny?sort=-record_date&page%5Bsize%5D=1'
    $response = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 30
    "rows=$(@($response.data).Count)"
}

Add-Result -Connector 'Federal Reserve DDP' -Test {
    $response = Invoke-WebRequest `
        -Uri 'https://www.federalreserve.gov/datadownload/Choose.aspx?rel=H15' `
        -Method Get `
        -UseBasicParsing `
        -TimeoutSec 30
    "http=$($response.StatusCode)"
}

Add-Result -Connector 'New York Fed Markets' -Test {
    $response = Invoke-RestMethod `
        -Uri 'https://markets.newyorkfed.org/api/rates/all/latest.json' `
        -Method Get `
        -TimeoutSec 30
    $rates = @($response.refRates)
    if ($rates.Count -eq 0) {
        throw 'New York Fed returned no reference rates.'
    }
    "rates=$($rates.Count)"
}

$Results | Format-Table -AutoSize

if (@($Results | Where-Object Status -eq 'FAIL').Count -gt 0) {
    exit 1
}

