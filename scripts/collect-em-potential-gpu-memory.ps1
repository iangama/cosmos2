param(
  [ValidatePattern('^[a-z0-9_-]{1,40}$')][string]$Label='current',
  [ValidateRange(1,120)][int]$Samples=3,
  [Parameter(Mandatory=$true)][ValidateSet('em')][string]$ExpectedMode,
  [ValidateSet('any','paused','running')][string]$ExpectedWorker='any',
  [ValidateSet('visible','hidden')][string]$ExpectedPotential='visible',
  [ValidateSet('visible','hidden')][string]$ExpectedElectric='visible',
  [switch]$SignalReady
)
$ErrorActionPreference='Stop'
$collectorSha256=(Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
$root=Split-Path $PSScriptRoot -Parent
$journalPath="$root/output/gpu-memory-journal-$Label.jsonl"
if (Test-Path $journalPath) { throw 'Diario da coleta ja existe; use outro label.' }
$journal=[System.IO.StreamWriter]::new($journalPath,$false,[System.Text.UTF8Encoding]::new($false))
$journal.AutoFlush=$true
function Write-Stage([string]$Stage) {
  $journal.WriteLine((@{ stage=$Stage;utc=[DateTime]::UtcNow.ToString('o');collector_pid=$PID } | ConvertTo-Json -Compress))
}
Write-Stage 'initializing'
$session=Get-Content "$root/output/session.json" | ConvertFrom-Json
$engine=Get-Process -Id $session.app
if (!$engine.Path.StartsWith(($root.TrimEnd([char]92)+[char]92),[StringComparison]::OrdinalIgnoreCase)) { throw 'PID do motor fora do projeto.' }
function Read-Scenario {
  $snapshot=Invoke-RestMethod -Uri 'http://127.0.0.1:4700/api/em/state' -TimeoutSec 3
  $state=$snapshot.state
  $confirmation=$snapshot.native.confirmation
  $rendererConfirmed=($snapshot.native.active -and $confirmation.state -eq 'accepted' -and
    $null -eq $snapshot.native.error -and $null -eq $snapshot.worker_error -and
    $confirmation.metadata.system_id -eq $state.system_id -and
    $confirmation.metadata.revision -eq $state.revision -and
    [Math]::Abs($confirmation.metadata.time_s - $state.time_s) -le 1 -and $confirmation.objects.Count -eq 128)
  if (!$rendererConfirmed -or $state.experiment.mode -ne 'mutual_electrostatic' -or $state.experiment.system.ids.Count -ne 128) {
    throw 'Cenario EM128 nativo nao confirmado pela API Windows.'
  }
  if ($ExpectedWorker -ne 'any') {
    if ([bool]$state.paused -ne ($ExpectedWorker -eq 'paused')) { throw "Estado esperado do worker $ExpectedWorker nao confirmado." }
  }
  $potential=$snapshot.native.potential
  if($potential.error -or $potential.confirmation_uncertain -or $null -eq $potential.render -or $potential.render.sample_count -ne 1089 -or
     $potential.render.metadata.system_id -ne $state.system_id -or $potential.render.metadata.revision -ne $state.revision -or
     [bool]$potential.settings.visible -ne ($ExpectedPotential -eq 'visible') -or [bool]$state.editor.visual.electric_visible -ne ($ExpectedElectric -eq 'visible')) {
    throw 'Camadas potencial/E esperadas nao confirmadas.'
  }
  return [PSCustomObject]@{ mode='em';renderer_confirmed=$rendererConfirmed;
    paused=$state.paused;fixture_count=$state.experiment.system.ids.Count;system_id=$state.system_id;
    revision=$state.revision;requested_rate=$state.requested_model_s_per_wall_s;
    physical_time=$state.time_s;native_time=$confirmation.metadata.time_s;potential_visible=$potential.settings.visible;electric_visible=$state.editor.visual.electric_visible;potential_layer_id=$potential.render.layer_id;potential_time_s=$potential.render.metadata.time_s;potential_samples=$potential.render.sample_count;potential_segments=$potential.render.segment_count }
}
$before=Read-Scenario
Write-Stage 'process_inventory_before'
$all=Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name
$owned=[System.Collections.Generic.HashSet[int]]::new()
$owned.Add([int]$session.app) | Out-Null
$owned.Add([int]$session.server) | Out-Null
do {
  $countBefore=$owned.Count
  foreach($process in $all) { if($owned.Contains([int]$process.ParentProcessId)) { $owned.Add([int]$process.ProcessId) | Out-Null } }
} while($owned.Count -ne $countBefore)
$names=@{}
foreach($process in $all) { if($owned.Contains([int]$process.ProcessId)) { $names[[int]$process.ProcessId]=$process.Name } }
$records=@()
$counterErrors=@()
$counterPaths=@('\GPU Process Memory(*)\Dedicated Usage','\GPU Process Memory(*)\Shared Usage','\GPU Adapter Memory(*)\Dedicated Usage')
Write-Stage 'collecting'
# Preserve invalid paths/statuses and all requested timestamps for diagnosis.
# A report containing ANY such error remains rejected below, exactly as before.
Get-Counter -Counter $counterPaths -SampleInterval 1 -MaxSamples $Samples -ErrorAction Continue -ErrorVariable +counterErrors | ForEach-Object {
  $set=$_
  $scenario=Read-Scenario
  $product=@();$adapters=@();$invalid=@()
  foreach($counter in $set.CounterSamples) {
    if($counter.Status -ne 0) { $invalid+=@{ path=$counter.Path;status=$counter.Status };continue }
    if($counter.InstanceName -match '^pid_(\d+)_(.*)') {
      $processId=[int]$Matches[1]
      if($owned.Contains($processId)) { $product+=[PSCustomObject]@{ pid=$processId;name=$names[$processId];instance=$counter.InstanceName;counter=($counter.Path.Split([char]92)[-1]);bytes=[double]$counter.CookedValue } }
    } elseif($counter.Path -like '*gpu adapter memory*') {
      $adapters+=@{ instance=$counter.InstanceName;bytes=[double]$counter.CookedValue }
    }
  }
  if (!($product | Where-Object { $_.pid -eq $session.app -and $_.counter -eq 'dedicated usage' })) { throw 'Contador dedicado do motor ausente; coleta recusada.' }
  foreach($property in @('mode','paused','fixture_count','system_id','revision','requested_rate','potential_visible','electric_visible','potential_layer_id')) {
    if ($scenario.$property -ne $before.$property) { throw "Cenario mudou durante a coleta: $property." }
  }
  $records+=[PSCustomObject]@{ utc=$set.Timestamp.ToUniversalTime().ToString('o');scenario=$scenario;product=$product;adapters_all_applications=$adapters;
    product_dedicated_sum_bytes=($product | Where-Object { $_.counter -eq 'dedicated usage' } | Measure-Object bytes -Sum).Sum;
    invalid_samples=$invalid }
  $journal.WriteLine(($records[-1] | ConvertTo-Json -Depth 9 -Compress))
  if ($SignalReady -and $records.Count -eq 1) {
    @{ engine_pid=$session.app;label=$Label;first_sample_utc=$records[0].utc } |
      ConvertTo-Json | Set-Content "$root/output/gpu-memory-ready-$Label.json" -Encoding UTF8
  }
}
Write-Stage 'scenario_after'
$after=Read-Scenario
foreach($property in @('mode','paused','fixture_count','system_id','revision','requested_rate','potential_visible','electric_visible','potential_layer_id')) {
  if ($after.$property -ne $before.$property) { throw "Cenario mudou ao terminar a coleta: $property." }
}
if ((Get-Process -Id $session.app).StartTime -ne $engine.StartTime) { throw 'Identidade do motor mudou durante a coleta.' }
Write-Stage 'process_inventory_after'
$afterAll=Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId
foreach($process in $afterAll) {
  if($owned.Contains([int]$process.ParentProcessId) -and !$owned.Contains([int]$process.ProcessId)) { throw 'Novo processo filho durante a coleta; repetir com inventario atualizado.' }
}
Write-Stage 'sealing_report'
$report=@{ schema=2;session=$session;label=$Label;samples=$records;expected_mode=$ExpectedMode;expected_worker=$ExpectedWorker;expected_potential=$ExpectedPotential;expected_electric=$ExpectedElectric;
  counter_errors=@($counterErrors | ForEach-Object { @{ id=$_.FullyQualifiedErrorId;message=$_.Exception.Message } });
  scenario_before=$before;scenario_after=$after;engine_started_utc=$engine.StartTime.ToUniversalTime().ToString('o');
  engine_sha256=(Get-FileHash $engine.Path -Algorithm SHA256).Hash.ToLowerInvariant();
  collector_sha256=$collectorSha256;
  method='Windows GPU Process Memory/Adapter Memory counters';
  owned_processes=@($owned | ForEach-Object { [int]$_ });scope='Per-process totals include cross-process shared allocations and can overcount. Adapter values include other applications. Diagnostic samples, not a sustained G0 acceptance; documented Windows counter defects must be considered.';
  sources=@('https://devblogs.microsoft.com/directx/gpus-in-the-task-manager/','https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/gpu-process-memory-counters-report-wrong-value') }
$destination="$root/evidence/gpu-memory-$Label.json"
if ((Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $collectorSha256) { throw 'Coletor alterado durante execucao; repetir a coleta.' }
$temporary="$destination.$PID.tmp"
$report | ConvertTo-Json -Depth 9 | Set-Content $temporary -Encoding UTF8
Move-Item $temporary $destination -Force
Write-Stage 'report_persisted'
$journal.Dispose()
if ($counterErrors.Count -gt 0 -or @($records | Where-Object { $_.invalid_samples.Count -gt 0 }).Count -gt 0 -or $records.Count -ne $Samples) {
  throw "ColetaGPU invalida; caminhos/status preservados em $destination. Nenhuma amostra foi descartada ou substituida."
}
@{ label=$Label;samples=$records.Count;max_product_dedicated_sum_bytes=($records | Measure-Object product_dedicated_sum_bytes -Maximum).Maximum;owned_processes=$owned.Count } | ConvertTo-Json
