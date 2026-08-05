$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8000'
$root = Split-Path -Parent $PSScriptRoot
$thesis = Get-Content -LiteralPath "$root\fixtures\contracts\sample_thesis_build.json" -Raw -Encoding UTF8
$evidence = Get-Content -LiteralPath "$root\fixtures\contracts\sample_evidence_bundle.json" -Raw -Encoding UTF8

Invoke-RestMethod -Method Post -Uri "$base/v1/theses" -ContentType 'application/json' -Body $thesis | Out-Null
$first = Invoke-RestMethod -Method Post -Uri "$base/v1/theses/THESIS_DEMO_001/compile"
Write-Host "Initial state: $($first.compile_result.conclusion_state)"
Write-Host "Issues: $((($first.compile_result.issues).code) -join ', ')"
$verified = Invoke-RestMethod -Method Post -Uri "$base/v1/theses/THESIS_DEMO_001/verify" -ContentType 'application/json' -Body ("{`"evidence_bundle`":" + $evidence + "}")
Write-Host "Recompiled state: $($verified.compile_result.conclusion_state)"
Write-Host "Allowed language: $($verified.compile_result.language_policy.allowed_level)"
Write-Host "Docs: $base/docs"
