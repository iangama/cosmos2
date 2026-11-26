$ErrorActionPreference = 'Continue'
$root = Split-Path $PSScriptRoot -Parent
$cmake = Join-Path $root '.tooling/python/Scripts/cmake.exe'
& $cmake --build "$root/build/openspace" --config Release --target OpenSpace --parallel 6 2>&1 | Tee-Object "$root/output/build-render-state-diagnostic-runtime.log"
$retries = 0
while ($LASTEXITCODE -ne 0 -and $retries -lt 3 -and (Select-String -Path "$root/output/build-render-state-diagnostic-runtime.log" -Pattern 'c101008d' -Quiet)) {
    $retries++
    & "$root/.tooling/python/Scripts/python.exe" "$root/scripts/finalize-engine-manifest.py"
    if ($LASTEXITCODE -eq 0) {
        & $cmake --build "$root/build/openspace" --config Release --target OpenSpace --parallel 6 2>&1 | Tee-Object "$root/output/build-render-state-diagnostic-runtime.log" -Append
    }
}
if ($LASTEXITCODE -ne 0) { throw "GL diagnostic candidate build failed: $LASTEXITCODE" }
& "$root/.tooling/python/Scripts/python.exe" -Xutf8 "$root/scripts/stage-render-state-diagnostic-runtime.py"
if ($LASTEXITCODE -ne 0) { throw 'GL diagnostic runtime staging failed' }
