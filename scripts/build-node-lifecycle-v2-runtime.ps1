$ErrorActionPreference = 'Continue'
$root = Split-Path $PSScriptRoot -Parent
if (!(Test-Path "$root/output/node-lifecycle-v2-staging/preparation.json")) { throw 'Complete lifecyclev2 preparation required.' }
& "$root/.tooling/python/Scripts/cmake.exe" --build "$root/build/openspace" --config Release --target OpenSpace --parallel 6 2>&1 | Tee-Object "$root/output/build-node-lifecycle-v2-runtime.log"
$attempt = 0
while ($LASTEXITCODE -ne 0 -and $attempt -lt 3 -and (Select-String -Path "$root/output/build-node-lifecycle-v2-runtime.log" -Pattern 'c101008d' -Quiet)) {
    $attempt++
    & "$root/.tooling/python/Scripts/python.exe" "$root/scripts/finalize-engine-manifest.py"
    if ($LASTEXITCODE -eq 0) {
        & "$root/.tooling/python/Scripts/cmake.exe" --build "$root/build/openspace" --config Release --target OpenSpace --parallel 6 2>&1 | Tee-Object "$root/output/build-node-lifecycle-v2-runtime.log" -Append
    }
}
if ($LASTEXITCODE -ne 0) { throw "Node lifecyclev2 build failed: $LASTEXITCODE" }
& "$root/.tooling/python/Scripts/python.exe" -Xutf8 "$root/scripts/stage-node-lifecycle-v2-runtime.py"
if ($LASTEXITCODE -ne 0) { throw 'Node lifecyclev2 staging failed' }
