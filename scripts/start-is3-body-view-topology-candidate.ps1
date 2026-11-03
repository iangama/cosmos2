param([switch]$Benchmark1080, [switch]$InspectCEF)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$candidate = Join-Path $root 'output\is3-body-view-topology-product'
$mutexCreated = $false
$mutex = New-Object System.Threading.Mutex($true, 'Local\Cosmos2Launcher', [ref]$mutexCreated)
$sessionFile = Join-Path $root 'output\session.json'
if (Test-Path $sessionFile) {
    try {
        $existingSession = Get-Content $sessionFile | ConvertFrom-Json
        $existing = Get-Process -Id $existingSession.app -ErrorAction Stop
        if ($existing.ProcessName -eq 'OpenSpace' -and $existing.Path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
            Write-Output 'Cosmos2 ja esta aberto; confirme a candidata ativa antes de testar.'
            $mutex.Dispose()
            exit 0
        }
    } catch { }
}
if (!$mutexCreated) {
    Write-Output 'Cosmos2 esta iniciando em outra janela.'
    $mutex.Dispose()
    exit 0
}
$env:COSMOS2_ROOT = $root.Replace('\', '/')
$env:OPENSPACE_USER = "$env:COSMOS2_ROOT/user"
$env:COSMOS2_STORAGE = Join-Path $candidate 'gravity-sessions'
Remove-Item Env:\COSMOS2_OFFLINE -ErrorAction SilentlyContinue
Remove-Item Env:\COSMOS2_CACHE -ErrorAction SilentlyContinue
if ($InspectCEF) { $env:COSMOS2_INSPECT_CEF = '1' }
else { Remove-Item Env:\COSMOS2_INSPECT_CEF -ErrorAction SilentlyContinue }
if ($Benchmark1080) { $env:COSMOS2_WINDOW_CONFIG = "$env:COSMOS2_ROOT/config/window-1080.json" }
else { Remove-Item Env:\COSMOS2_WINDOW_CONFIG -ErrorAction SilentlyContinue }
$python = Join-Path $root '.tooling\python\Scripts\python.exe'
$runtime = Join-Path $root '.runtime-cloud'
$serverScript = Join-Path $candidate 'app\server.py'
if (!(Test-Path $python) -or !(Test-Path "$runtime\bin\OpenSpace.exe") -or !(Test-Path $serverScript)) {
    throw 'Ambiente/candidata solar ausente.'
}
New-Item -ItemType Directory -Force "$root\output\logs", "$root\output\cache", "$root\user\screenshots", "$candidate\gravity-sessions" | Out-Null
Copy-Item "$root\config\cosmos2.cfg" "$runtime\cosmos2.cfg" -Force
$serverArgs = '-u "{0}"' -f $serverScript
$server = Start-Process $python -ArgumentList $serverArgs -WorkingDirectory $root -RedirectStandardOutput "$root\output\server.log" -RedirectStandardError "$root\output\server-errors.log" -PassThru
try {
    $app = Start-Process "$runtime\bin\OpenSpace.exe" -ArgumentList @('--file', 'cosmos2.cfg', '--bypassLauncher') -WorkingDirectory $runtime -RedirectStandardOutput "$root\output\engine.log" -RedirectStandardError "$root\output\engine-errors.log" -PassThru
    @{ solarIntegrationCandidate = $true; solarTidesCandidate = $true; earthFieldCandidate = $true; jupiterFieldCandidate = $true; bodyVectorCandidate = $true; bodyLinesCandidate = $true; bodyViewCandidate = $true; bodyViewTopologyCandidate = $true; solarInitialFormat = 'solar_four_physical_centers/1.0.0';
       cloudCandidate = $false; serverScript = $serverScript; storage = $env:COSMOS2_STORAGE;
       app = $app.Id; server = $server.Id; runtime = $runtime; runtimeVariant = 'cloud';
       runtimeSelectionReason = 'explicit-unapproved-IS3-persistent-view-topology-candidate';
       started = [DateTime]::UtcNow.ToString('o'); offline = $false; coldCache = $false; cache = $null
    } | ConvertTo-Json | Set-Content $sessionFile
    & $python "$root\scripts\bootstrap-native-ui.py" > "$root\output\bootstrap-ui.log" 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Warning 'A interface inicial nao confirmou abertura; veja output/bootstrap-ui.log.' }
    $app.WaitForExit()
    if ($null -ne $app.ExitCode -and $app.ExitCode -ne 0) { throw "OpenSpace encerrou com codigo $($app.ExitCode)." }
} finally {
    if (!$server.HasExited) {
        try {
            Invoke-RestMethod -Uri 'http://127.0.0.1:4700/api/shutdown' -Method Post -Body '{}' -ContentType 'application/json' -TimeoutSec 3 | Out-Null
            $server.WaitForExit(8000) | Out-Null
        } catch { Write-Warning 'Servidor local nao respondeu ao encerramento.' }
        if (!$server.HasExited) { Stop-Process -Id $server.Id }
    }
    $mutex.Dispose()
}
