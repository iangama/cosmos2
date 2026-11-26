param([switch]$ConfigureOnly)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$cmake = Join-Path $root '.tooling\python\Scripts\cmake.exe'
$source = Join-Path $root '.upstream\openspace'
$build = Join-Path $root 'build\openspace'
# Core mission topics, CEF endpoints and galaxy helpers reference these modules
# even in the reduced profile. Their definitions must be linked with callers.
$enabled = @('base','space','globebrowsing','atmosphere','cefwebgui','webbrowser','debugging','sync','spout','galaxy','digitaluniverse','spacecraftinstruments','webgui','volume')
$arguments = @('-S', $source, '-B', $build, '-G', 'Visual Studio 17 2022', '-A', 'x64',
    "-DCMAKE_GENERATOR_INSTANCE=$root\.tooling\vs-buildtools",
    '-DDISABLE_VCPKG=ON', '-DOPENSPACE_APPLICATION_OPENSPACE-LAUNCHER=OFF',
    '-DOPENSPACE_HAVE_TESTS=OFF', '-DSGCT_BUILD_TESTS=OFF',
    '-DOPENSPACE_APPLICATION_ASSETBUILDER=OFF', '-DOPENSPACE_APPLICATION_TASKRUNNER=OFF',
    '-DOPENSPACE_APPLICATION_DOCSWRITER=OFF', '-DOPENSPACE_APPLICATION_SYNC=OFF',
    '-DOPENSPACE_APPLICATION_OPENSPACE-MINVR=OFF')
Get-ChildItem "$source\modules" -Directory | ForEach-Object {
    $name = $_.Name
    $state = if ($enabled -contains $name) { 'ON' } else { 'OFF' }
    $arguments += "-DOPENSPACE_MODULE_$($name.ToUpper())=$state"
}
$ErrorActionPreference = 'Continue' # PowerShell 5 maps native stderr warnings to errors.
& $cmake @arguments 2>&1 | Tee-Object "$root\output\configure-engine.log"
if ($LASTEXITCODE -ne 0) { throw "CMake configure failed: $LASTEXITCODE" }
if (!$ConfigureOnly) {
    & "$root\.tooling\python\Scripts\python.exe" "$root\scripts\stage-build-dependencies.py"
    if ($LASTEXITCODE -ne 0) { throw "Dependency staging failed: $LASTEXITCODE" }
    & $cmake --build $build --config Release --target OpenSpace --parallel 6 2>&1 | Tee-Object "$root\output\build-engine.log"
    $manifestRetries = 0
    while ($LASTEXITCODE -ne 0 -and $manifestRetries -lt 3 -and (Select-String -Path "$root\output\build-engine.log" -Pattern 'c101008d' -Quiet)) {
        $manifestRetries++
        & "$root\.tooling\python\Scripts\python.exe" "$root\scripts\finalize-engine-manifest.py"
        if ($LASTEXITCODE -eq 0) {
            & $cmake --build $build --config Release --target OpenSpace --parallel 6 2>&1 | Tee-Object "$root\output\build-engine.log" -Append
        }
    }
    if ($LASTEXITCODE -ne 0) { throw "CMake build failed: $LASTEXITCODE" }
}
$ErrorActionPreference = 'Stop'
