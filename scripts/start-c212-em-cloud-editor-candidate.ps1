param([switch]$Benchmark1080, [switch]$InspectCEF)
$Built = $true
$Offline = $false
$ColdCache = $false
$CloudCandidate = $false
$RuntimeVariant = 'auto'
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$mutexCreated = $false
$mutex = New-Object System.Threading.Mutex($true, 'Local\Cosmos2Launcher', [ref]$mutexCreated)
$sessionFile = Join-Path $root 'output\session.json'
if (Test-Path $sessionFile) {
    try {
        $existingSession = Get-Content $sessionFile | ConvertFrom-Json
        $existing = Get-Process -Id $existingSession.app -ErrorAction Stop
        if ($existing.ProcessName -eq 'OpenSpace' -and $existing.Path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
            Add-Type '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr handle);' -Name Cosmos2Focus -Namespace Native
            [Native.Cosmos2Focus]::SetForegroundWindow($existing.MainWindowHandle) | Out-Null
            Write-Output 'Cosmos2 ja esta aberto.'
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
if ($Offline -and !$Built) { throw 'O perfil offline verificado requer o build proprio (-Built).' }
if ($Offline) { $env:COSMOS2_OFFLINE = '1' }
else { Remove-Item Env:\COSMOS2_OFFLINE -ErrorAction SilentlyContinue }
if ($InspectCEF) { $env:COSMOS2_INSPECT_CEF = '1' }
else { Remove-Item Env:\COSMOS2_INSPECT_CEF -ErrorAction SilentlyContinue }
if ($ColdCache) {
    $env:COSMOS2_CACHE = "$env:COSMOS2_ROOT/output/cache-cold-$([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))"
} else { Remove-Item Env:\COSMOS2_CACHE -ErrorAction SilentlyContinue }
if ($Benchmark1080) { $env:COSMOS2_WINDOW_CONFIG = "$env:COSMOS2_ROOT/config/window-1080.json" }
else { Remove-Item Env:\COSMOS2_WINDOW_CONFIG -ErrorAction SilentlyContinue }
if ($CloudCandidate -and !$Built) { throw 'A candidata local exige -Built.' }
if ($CloudCandidate) { $env:COSMOS2_STORAGE = Join-Path $root 'output\c211-cloud-candidate\sessions' }
else { $env:COSMOS2_STORAGE = Join-Path $root 'output\c212-em-cloud-editor-product\gravity-sessions' }
$python = Join-Path $root '.tooling\python\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Prepare o ambiente Python isolado e requirements-windows.txt.' }
. "$PSScriptRoot\select-runtime.ps1"
$runtimeSelection = Select-Cosmos2Runtime -Root $root -Built ([bool]$Built) -Variant $RuntimeVariant
$runtime = Join-Path $root '.runtime-topic-cleanup'
$runtimeSelection = @{ path = $runtime; variant = 'topic-cleanup'; reason = 'explicit-unapproved-EM-cloud-source-editor-candidate' }
if (!(Test-Path "$runtime\bin\OpenSpace.exe")) { throw 'Prepare o runtime com scripts/prepare-runtime.py.' }
foreach ($texture in @('earth.jpg', 'earth-night.jpg', 'moon.png', 'milkyway.jpg')) {
    if (!(Test-Path "$root\data\textures\$texture")) { throw 'Prepare as texturas com scripts/prepare-scene.py.' }
}
if (!(Test-Path "$root\data\galaxy\stars.speck")) { throw 'Prepare a galaxia com scripts/prepare-galaxy.py.' }
New-Item -ItemType Directory -Force "$root\output\logs", "$root\output\cache", "$root\user\screenshots" | Out-Null
Copy-Item "$root\config\cosmos2.cfg" "$runtime\cosmos2.cfg" -Force
$serverScript = Join-Path $root 'output\c212-em-cloud-editor-product\app\server.py'
$serverArgs = '-u "{0}"' -f $serverScript
$server = Start-Process $python -ArgumentList $serverArgs -WorkingDirectory $root -RedirectStandardOutput "$root\output\server.log" -RedirectStandardError "$root\output\server-errors.log" -PassThru
try {
    $app = Start-Process "$runtime\bin\OpenSpace.exe" -ArgumentList @('--file', 'cosmos2.cfg', '--bypassLauncher') -WorkingDirectory $runtime -RedirectStandardOutput "$root\output\engine.log" -RedirectStandardError "$root\output\engine-errors.log" -PassThru
    @{ emCloudEditorCandidate = $true; emIntegrationCandidate = $true; emTimeCandidate = $true; emTopicCleanupCandidate = $true; emCandidate = $true; emPotentialCandidate = $true; emCloudCandidate = $true; emCloudNativeCandidate = $true; emKernelVersion = "0.4.0"; cloudCandidate = [bool]$CloudCandidate; serverScript = $serverScript; app = $app.Id; server = $server.Id; runtime = $runtime; runtimeVariant = $runtimeSelection.variant; runtimeSelectionReason = $runtimeSelection.reason; started = [DateTime]::UtcNow.ToString('o'); offline = [bool]$Offline; coldCache = [bool]$ColdCache; cache = $env:COSMOS2_CACHE } | ConvertTo-Json | Set-Content "$root\output\session.json"
    & $python "$root\scripts\bootstrap-native-ui.py" > "$root\output\bootstrap-ui.log" 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Warning 'A interface inicial nao confirmou abertura; veja output/bootstrap-ui.log.' }
    $app.WaitForExit()
    if ($null -ne $app.ExitCode -and $app.ExitCode -ne 0) { throw "OpenSpace encerrou com codigo $($app.ExitCode). Veja output/logs." }
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
