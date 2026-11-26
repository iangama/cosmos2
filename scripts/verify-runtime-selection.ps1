$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot/select-runtime.ps1"
$checks = @()
function Check($condition, $name) {
    if (!$condition) { throw "Runtime selection failed: $name" }
    $script:checks += $name
}
Check ((Select-Cosmos2Runtime $root $false).variant -eq 'official') 'without-Built-preserves-official'
Check ((Select-Cosmos2Runtime $root $true baseline).variant -eq 'baseline') 'explicit-baseline'
Check ((Select-Cosmos2Runtime $root $true query).variant -eq 'query') 'explicit-query'
Check ((Select-Cosmos2Runtime $root $true cloud).reason -eq 'explicit-unapproved-cloud-candidate') 'cloud-only-explicit'
Check ((Select-Cosmos2Runtime $root $true).reason -eq 'approved-P256-engine-hash') 'actual-approved-default'
$refused = $false
try { Select-Cosmos2Runtime $root $false query | Out-Null } catch { $refused = $true }
Check $refused 'query-requires-Built'
$refused = $false
try { Select-Cosmos2Runtime $root $false cloud | Out-Null } catch { $refused = $true }
Check $refused 'cloud-requires-Built'
$fixture = Join-Path $root ('output/runtime-selection-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory "$fixture/evidence", "$fixture/.runtime-perf-query/bin" | Out-Null
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'missing-receipt-falls-back'
$approvalFile = "$fixture/evidence/c211-p256-validated.json"
'invalid json' | Set-Content $approvalFile
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'corrupt-receipt-falls-back'
$approval = Get-Content "$root/evidence/c211-p256-validated.json" -Raw | ConvertFrom-Json
Copy-Item "$root/$($approval.review)" "$fixture/$($approval.review)"
Copy-Item "$root/$($approval.benchmark)" "$fixture/$($approval.benchmark)"
'different engine bytes' | Set-Content "$fixture/.runtime-perf-query/bin/OpenSpace.exe"
$approval | ConvertTo-Json -Depth 20 | Set-Content $approvalFile
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'different-engine-falls-back'
$approval.engine_sha256 = (Get-FileHash "$fixture/.runtime-perf-query/bin/OpenSpace.exe").Hash.ToLowerInvariant()
$approval | ConvertTo-Json -Depth 20 | Set-Content $approvalFile
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'engine-inconsistent-with-review-falls-back'
$receipt = @{ checks = $checks; followup = 'Launcher auto selection after frozen c211p256q3; benchmark launch script remains archived in its original bytes.'; fixture = $fixture }
$receipt | ConvertTo-Json -Depth 10 | Set-Content "$root/evidence/runtime-auto-selection-check.json"
$receipt | ConvertTo-Json -Depth 10
