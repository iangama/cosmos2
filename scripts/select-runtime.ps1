function Test-Cosmos2ApprovedCloudProfile {
    param([string]$Root, $Profile, [string]$EngineHash, [string]$Flag)
    if ($Profile.benchmark -notmatch '^evidence/native-benchmark-[a-z0-9_-]+\.json$' -or
        $Profile.review -notmatch '^evidence/native-benchmark-[a-z0-9_-]+-review\.json$') { return $false }
    if ((Get-FileHash (Join-Path $Root $Profile.benchmark) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Profile.benchmark_sha256 -or
        (Get-FileHash (Join-Path $Root $Profile.review) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Profile.review_sha256) { return $false }
    $review = Get-Content (Join-Path $Root $Profile.review) -Raw -ErrorAction Stop | ConvertFrom-Json
    return ($review.$Flag -eq $true -and $review.engine_sha256 -eq $EngineHash -and $review.benchmark_sha256 -eq $Profile.benchmark_sha256)
}

function Test-Cosmos2CloudApproval {
    param([string]$Root)
    try {
        $file = Join-Path $Root 'evidence/c211-cloud-validated.json'
        if (!(Test-Path $file)) { return $false }
        $approval = Get-Content $file -Raw -ErrorAction Stop | ConvertFrom-Json
        if ($approval.schema -ne 1 -or $approval.performance_approved -ne $true -or $approval.runtime_variant -ne 'cloud' -or
            $approval.status -ne '3_13_science_worker_native_migration_P256_and_10000_profile_approved' -or
            $approval.engine_sha256 -notmatch '^[0-9a-f]{64}$') { return $false }
        $engineHash = (Get-FileHash (Join-Path $Root '.runtime-cloud/bin/OpenSpace.exe') -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($engineHash -ne $approval.engine_sha256) { return $false }
        if (!(Test-Cosmos2ApprovedCloudProfile $Root $approval.cloud_profile $engineHash 'three_cloud10k_routes_verified') -or
            !(Test-Cosmos2ApprovedCloudProfile $Root $approval.p256_profile $engineHash 'three_P256_routes_verified')) { return $false }
        $properties = @($approval.app_files_sha256.PSObject.Properties)
        $required = @('server.py','session.py','worker.py','laboratory.py','cloud_driver.py','cloud_transport.py','cloud_bridge.py','ui/app.js','ui/test-cloud.js','ui/index.html','ui/style.css')
        foreach ($name in $required) { if ($properties.Name -notcontains $name) { return $false } }
        foreach ($property in $properties) {
            if ($property.Name -notmatch '^(?:[a-z0-9_-]+/)*[a-z0-9_-]+\.(?:py|js|html|css)$' -or
                $property.Value -notmatch '^[0-9a-f]{64}$') { return $false }
            if ((Get-FileHash (Join-Path $Root ('app/'+$property.Name)) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $property.Value) { return $false }
        }
        return $true
    } catch { return $false }
}

function Select-Cosmos2Runtime {
    param([string]$Root, [bool]$Built, [ValidateSet('auto','baseline','query','cloud')][string]$Variant='auto')
    if (!$Built) {
        if ($Variant -in @('query','cloud')) { throw 'A variante local requer -Built.' }
        return @{ path = (Join-Path $Root '.runtime'); variant = 'official'; reason = 'without-Built' }
    }
    $baseline = @{ path = (Join-Path $Root '.runtime-built'); variant = 'baseline'; reason = 'explicit-baseline' }
    if ($Variant -eq 'baseline') { return $baseline }
    if ($Variant -eq 'cloud') {
        return @{ path = (Join-Path $Root '.runtime-cloud'); variant = 'cloud'; reason = 'explicit-unapproved-cloud-candidate' }
    }
    $query = Join-Path $Root '.runtime-perf-query'
    if ($Variant -eq 'query') { return @{ path = $query; variant = 'query'; reason = 'explicit-query' } }
    if (Test-Cosmos2CloudApproval $Root) {
        return @{ path = (Join-Path $Root '.runtime-cloud'); variant = 'cloud'; reason = 'approved-C211-engine-and-app-hashes' }
    }
    $baseline.reason = 'no-matching-approved-query-receipt'
    try {
        $approval = Get-Content (Join-Path $Root 'evidence/c211-p256-validated.json') -Raw | ConvertFrom-Json
        if ($approval.schema -ne 1 -or $approval.performance_approved -ne $true -or $approval.runtime_variant -ne 'query' -or
            $approval.status -ne '3_12_science_worker_native_migration_256_profile_approved' -or
            $approval.engine_sha256 -notmatch '^[0-9a-f]{64}$') { return $baseline }
        $engineHash = (Get-FileHash (Join-Path $query 'bin/OpenSpace.exe') -Algorithm SHA256).Hash.ToLowerInvariant()
        $reviewPath = Join-Path $Root $approval.review
        $benchmarkPath = Join-Path $Root $approval.benchmark
        if ($engineHash -ne $approval.engine_sha256 -or
            (Get-FileHash $reviewPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $approval.review_sha256 -or
            (Get-FileHash $benchmarkPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $approval.benchmark_sha256) { return $baseline }
        $review = Get-Content $reviewPath -Raw | ConvertFrom-Json
        if ($review.three_P256_routes_verified -ne $true -or $review.engine_sha256 -ne $engineHash -or
            $review.benchmark_sha256 -ne $approval.benchmark_sha256) { return $baseline }
        return @{ path = $query; variant = 'query'; reason = 'approved-P256-engine-hash' }
    } catch {
        return $baseline
    }
}
