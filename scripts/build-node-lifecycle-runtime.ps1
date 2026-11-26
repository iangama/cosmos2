$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (!(Test-Path "$root/output/node-lifecycle-staging/preparation.json")) { throw 'Complete lifecycle preparation required before build.' }
& "$root/.tooling/python/Scripts/cmake.exe" --build "$root/build/openspace" --config Release --target OpenSpace --parallel 6 2>&1 | Tee-Object "$root/output/build-node-lifecycle-runtime.log"
if ($LASTEXITCODE -ne 0) { throw "Node lifecycle build failed: $LASTEXITCODE" }
& "$root/.tooling/python/Scripts/python.exe" -Xutf8 "$root/scripts/stage-node-lifecycle-runtime.py"
if ($LASTEXITCODE -ne 0) { throw 'Node lifecycle runtime staging failed' }
