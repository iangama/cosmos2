$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot/select-runtime.ps1"
$checks=@()
function Check($condition,$name){if(!$condition){throw "Runtime selection failed: $name"};$script:checks+=$name}
Check ((Select-Cosmos2Runtime $root $false).variant -eq 'official') 'official-without-Built'
Check ((Select-Cosmos2Runtime $root $true baseline).variant -eq 'baseline') 'explicit-baseline-preserved'
Check ((Select-Cosmos2Runtime $root $true query).variant -eq 'query') 'explicit-query-preserved'
$actual=Select-Cosmos2Runtime $root $true
Check ($actual.variant -eq $(if(Test-Cosmos2CloudApproval $root){'cloud'}else{'query'})) 'actual-default-matches-approval'
$fixture=Join-Path $root ('output/cloud-runtime-selection-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory "$fixture/evidence","$fixture/.runtime-cloud/bin","$fixture/app/ui" | Out-Null
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'missing-approvals-fall-back'
'test cloud engine' | Set-Content "$fixture/.runtime-cloud/bin/OpenSpace.exe"
$engine=(Get-FileHash "$fixture/.runtime-cloud/bin/OpenSpace.exe").Hash.ToLowerInvariant()
$profiles=@{}
foreach($kind in @('cloud','p256')){
    $benchmark="evidence/native-benchmark-fixture-$kind.json"
    '{"completed":true}' | Set-Content "$fixture/$benchmark"
    $benchmarkHash=(Get-FileHash "$fixture/$benchmark").Hash.ToLowerInvariant()
    $review="evidence/native-benchmark-fixture-$kind-review.json"
    $body=@{engine_sha256=$engine;benchmark_sha256=$benchmarkHash}
    $body[$(if($kind -eq 'cloud'){'three_cloud10k_routes_verified'}else{'three_P256_routes_verified'})]=$true
    $body | ConvertTo-Json | Set-Content "$fixture/$review"
    $profiles[$kind]=@{benchmark=$benchmark;benchmark_sha256=$benchmarkHash;review=$review;review_sha256=(Get-FileHash "$fixture/$review").Hash.ToLowerInvariant()}
}
$files=@{}
foreach($name in @('server.py','session.py','worker.py','laboratory.py','cloud_driver.py','cloud_transport.py','cloud_bridge.py','ui/app.js','ui/test-cloud.js','ui/index.html','ui/style.css')){
    "approved $name" | Set-Content "$fixture/app/$name"
    $files[$name]=(Get-FileHash "$fixture/app/$name").Hash.ToLowerInvariant()
}
$approval=@{schema=1;performance_approved=$true;runtime_variant='cloud';
    status='3_13_science_worker_native_migration_P256_and_10000_profile_approved';engine_sha256=$engine;
    cloud_profile=$profiles.cloud;p256_profile=$profiles.p256;app_files_sha256=$files}
$approvalFile="$fixture/evidence/c211-cloud-validated.json"
$valid=$approval | ConvertTo-Json -Depth 20
$valid | Set-Content $approvalFile
Check ((Select-Cosmos2Runtime $fixture $true).reason -eq 'approved-C211-engine-and-app-hashes') 'both-profiles-and-app-select-cloud'
Check ((Select-Cosmos2Runtime $fixture $false).variant -eq 'official') 'cloud-approval-does-not-change-without-Built'
Check ((Select-Cosmos2Runtime $fixture $true baseline).variant -eq 'baseline') 'cloud-approval-does-not-change-explicit-baseline'
Check ((Select-Cosmos2Runtime $fixture $true query).variant -eq 'query') 'cloud-approval-does-not-change-explicit-query'
foreach($kind in @('cloud','p256')){
    $changed=$valid | ConvertFrom-Json
    $changed.($kind+'_profile')=$null
    $changed | ConvertTo-Json -Depth 20 | Set-Content $approvalFile
    Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') "missing-$kind-profile-refused"
}
$valid | Set-Content $approvalFile
$original=[IO.File]::ReadAllBytes("$fixture/.runtime-cloud/bin/OpenSpace.exe")
'different executable' | Set-Content "$fixture/.runtime-cloud/bin/OpenSpace.exe"
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'different-engine-refused'
[IO.File]::WriteAllBytes("$fixture/.runtime-cloud/bin/OpenSpace.exe",$original)
$original=[IO.File]::ReadAllBytes("$fixture/app/ui/app.js")
'different app' | Set-Content "$fixture/app/ui/app.js"
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'different-app-refused'
[IO.File]::WriteAllBytes("$fixture/app/ui/app.js",$original)
$changed=$valid | ConvertFrom-Json;$changed.performance_approved=$false
$changed | ConvertTo-Json -Depth 20 | Set-Content $approvalFile
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'unapproved-performance-refused'
$changed=$valid | ConvertFrom-Json
$changed.app_files_sha256 | Add-Member -MemberType NoteProperty -Name '../outside.py' -Value $engine
$changed | ConvertTo-Json -Depth 20 | Set-Content $approvalFile
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'manifest-path-traversal-refused'
$valid | Set-Content $approvalFile
'corrupt review' | Set-Content "$fixture/$($profiles.p256.review)"
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'corrupt-review-refused'
'invalid json' | Set-Content $approvalFile
Check ((Select-Cosmos2Runtime $fixture $true).variant -eq 'baseline') 'corrupt-approval-refused'
$refused=$false;try{Select-Cosmos2Runtime $root $false cloud | Out-Null}catch{$refused=$true}
Check $refused 'cloud-requires-Built'
$receipt=@{checks=$checks;fixture=$fixture;actual_default=$actual;selector_sha256=(Get-FileHash "$PSScriptRoot/select-runtime.ps1").Hash.ToLowerInvariant();scope='Cloud auto-selection requires matching engine, both profile reviews/benchmarks and approved installed app bytes; legacy explicit/without-Built preserved.'}
$receipt | ConvertTo-Json -Depth 10 | Set-Content "$root/evidence/runtime-cloud-auto-selection-check.json"
$receipt | ConvertTo-Json -Depth 10
