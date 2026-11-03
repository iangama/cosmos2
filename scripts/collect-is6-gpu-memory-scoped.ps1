param(
  [ValidatePattern('^[a-z0-9_-]{1,40}$')][string]$Label='current',
  [ValidateRange(1,120)][int]$Samples=3,
  [Parameter(Mandatory=$true)][ValidateSet('atlas','experiment')][string]$ExpectedMode,
  [ValidateSet('any','paused','running')][string]$ExpectedWorker='any',
  [switch]$SignalReady
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$destination="$root/evidence/gpu-memory-$Label.json"
if(Test-Path $destination){throw 'Preservar coleta anterior; usar outro label.'}
$collectorSha256=(Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
$session=Get-Content "$root/output/session.json" | ConvertFrom-Json
$engine=Get-Process -Id $session.app
if(!$engine.Path.StartsWith(($root.TrimEnd([char]92)+[char]92),[StringComparison]::OrdinalIgnoreCase)){throw 'Motor fora do projeto.'}
function Canonical-Path([string]$value){
  $value=$value.ToLowerInvariant();$offset=$value.IndexOf('\gpu ')
  if($offset -lt 0){throw "CaminhoGPU inesperado:$value"}
  return $value.Substring($offset)
}
function Read-Scenario {
  $state=Invoke-RestMethod 'http://127.0.0.1:4700/api/state' -TimeoutSec 3
  $confirmed=[bool]$state.engine_connected
  if($state.mode -eq 'atlas' -and !$confirmed){
    $nav=Invoke-RestMethod 'http://127.0.0.1:4700/api/navigation/state' -TimeoutSec 3
    $confirmed=($null -ne $nav.navigation.Anchor -and $nav.camera.position_render_m.Count -eq 3)
  }
  if($state.mode -ne $ExpectedMode -or !$confirmed){throw 'Cenario/motor nao confirmado.'}
  if($ExpectedWorker -ne 'any' -and ($null -eq $state.physics -or [bool]$state.physics.paused -ne ($ExpectedWorker -eq 'paused'))){throw 'Estado do worker divergente.'}
  return [PSCustomObject]@{mode=$state.mode;renderer_confirmed=$confirmed;paused=$state.physics.paused;fixture_count=$state.physics.fixture_count;revision=$state.physics.revision;requested_rate=$state.physics.requested_rate;physical_time=$state.physics.time}
}
function Select-GpuPaths($ownedSet){
  $selected=@()
  foreach($path in (Get-Counter -ListSet 'GPU Process Memory').PathsWithInstances){
    $normal=Canonical-Path $path
    if($normal -match '^\\gpu process memory\(pid_(\d+)_[^)]+\)\\(dedicated usage|shared usage)$' -and $ownedSet.Contains([int]$Matches[1])){$selected+=$normal}
  }
  foreach($path in (Get-Counter -ListSet 'GPU Adapter Memory').PathsWithInstances){
    $normal=Canonical-Path $path
    if($normal -match '^\\gpu adapter memory\([^)]+\)\\dedicated usage$'){$selected+=$normal}
  }
  return @($selected | Sort-Object -Unique)
}
$records=@();$counterErrors=@();$failure=$null;$counterPaths=@();$afterPaths=@();$all=@();$afterAll=@();$owned=[System.Collections.Generic.HashSet[int]]::new()
try {
  $before=Read-Scenario
  $all=@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name)
  $owned.Add([int]$session.app)|Out-Null;$owned.Add([int]$session.server)|Out-Null
  do{$count=$owned.Count;foreach($p in $all){if($owned.Contains([int]$p.ParentProcessId)){$owned.Add([int]$p.ProcessId)|Out-Null}}}while($owned.Count -ne $count)
  $names=@{};foreach($p in $all){if($owned.Contains([int]$p.ProcessId)){$names[[int]$p.ProcessId]=$p.Name}}
  $counterPaths=@(Select-GpuPaths $owned)
  $productPaths=@($counterPaths | Where-Object {$_ -like '\gpu process memory*'})
  if(!($productPaths | Where-Object {$_ -match ('^\\gpu process memory\(pid_'+$session.app+'_.*\\dedicated usage$')})){throw 'Contador dedicado do motor ausente.'}
  $instances=@($productPaths | ForEach-Object {$_ -replace '\\(dedicated usage|shared usage)$',''} | Sort-Object -Unique)
  foreach($instance in $instances){if($productPaths -notcontains ($instance+'\dedicated usage') -or $productPaths -notcontains ($instance+'\shared usage')){throw 'ParDedicated/Shared incompleto.'}}
  Get-Counter -Counter $counterPaths -SampleInterval 1 -MaxSamples $Samples -ErrorAction Continue -ErrorVariable +counterErrors | ForEach-Object {
    $set=$_;$scenario=Read-Scenario;$product=@();$adapters=@();$invalid=@();$raw=@();$seen=@()
    foreach($counter in $set.CounterSamples){
      $path=Canonical-Path $counter.Path;$seen+=$path
      $finite=!([double]::IsNaN($counter.CookedValue) -or [double]::IsInfinity($counter.CookedValue))
      $raw+=[PSCustomObject]@{path=$path;status=[uint32]$counter.Status;cooked_value=if($finite){[double]$counter.CookedValue}else{[string]$counter.CookedValue}}
      if($counter.Status -ne 0 -or !$finite -or $counter.CookedValue -lt 0){$invalid+=@{path=$path;status=$counter.Status};continue}
      if($path -match '^\\gpu process memory\(pid_(\d+)_[^)]+\)\\(dedicated usage|shared usage)$'){
        $processId=[int]$Matches[1];$kind=$Matches[2]
        if(!$owned.Contains($processId)){throw 'Contador de processo fora do escopo.'}
        $product+=[PSCustomObject]@{pid=$processId;name=$names[$processId];instance=$counter.InstanceName;counter=$kind;bytes=[double]$counter.CookedValue}
      }else{$adapters+=@{instance=$counter.InstanceName;bytes=[double]$counter.CookedValue}}
    }
    if(@(Compare-Object $counterPaths @($seen|Sort-Object -Unique)).Count -ne 0 -or $seen.Count -ne $counterPaths.Count){throw 'Conjunto de contadores retornados divergente.'}
    foreach($key in @('mode','paused','fixture_count','revision','requested_rate')){if($scenario.$key -ne $before.$key){throw "Cenario alterado:$key"}}
    $records+=[PSCustomObject]@{utc=$set.Timestamp.ToUniversalTime().ToString('o');scenario=$scenario;product=$product;adapters_all_applications=$adapters;raw_counter_samples=$raw;invalid_samples=$invalid;product_dedicated_sum_bytes=($product|Where-Object {$_.counter -eq 'dedicated usage'}|Measure-Object bytes -Sum).Sum}
    if($SignalReady -and $records.Count -eq 1){@{engine_pid=$session.app;label=$Label;first_sample_utc=$records[0].utc}|ConvertTo-Json|Set-Content "$root/output/gpu-memory-ready-$Label.json" -Encoding UTF8}
  }
  $after=Read-Scenario
  foreach($key in @('mode','paused','fixture_count','revision','requested_rate')){if($after.$key -ne $before.$key){throw "Cenario final alterado:$key"}}
  if((Get-Process -Id $session.app).StartTime -ne $engine.StartTime){throw 'Identidade do motor alterada.'}
  $afterAll=@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name)
  foreach($p in $afterAll){if($owned.Contains([int]$p.ParentProcessId) -and !$owned.Contains([int]$p.ProcessId)){throw 'Novo processo filho; repetir com inventario atualizado.'}}
  foreach($processId in $owned){if(!($afterAll|Where-Object {$_.ProcessId -eq $processId})){throw 'Processo proprio saiu durante coleta.'}}
  $afterPaths=@(Select-GpuPaths $owned)
  if(@(Compare-Object $counterPaths $afterPaths).Count -ne 0){throw 'InstanciasGPU proprias/adaptadores mudaram; repetir.'}
  if($counterErrors.Count -gt 0 -or @($records|Where-Object {$_.invalid_samples.Count -gt 0}).Count -gt 0 -or $records.Count -ne $Samples){throw 'ColetaGPU invalida; nenhuma amostra pode ser descartada/substituida.'}
}catch{$failure=@{id=$_.FullyQualifiedErrorId;message=$_.Exception.Message}}
if((Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $collectorSha256){throw 'Coletor alterado durante execucao.'}
$exposed=@($records|ForEach-Object {$_.product}|ForEach-Object {$_.pid}|Sort-Object -Unique)
$report=@{schema=3;session=$session;label=$Label;valid=($null -eq $failure);failure=$failure;samples=$records;expected_mode=$ExpectedMode;expected_worker=$ExpectedWorker;counter_errors=@($counterErrors|ForEach-Object {@{id=$_.FullyQualifiedErrorId;message=$_.Exception.Message}});scenario_before=$before;scenario_after=$after;engine_started_utc=$engine.StartTime.ToUniversalTime().ToString('o');engine_sha256=(Get-FileHash $engine.Path -Algorithm SHA256).Hash.ToLowerInvariant();collector_sha256=$collectorSha256;owned_processes=@($owned|ForEach-Object {[int]$_});owned_gpu_processes=$exposed;owned_without_exposed_gpu_counter=@($owned|Where-Object {$exposed -notcontains $_});inventory_before=$all;inventory_after=$afterAll;configured_counter_paths=$counterPaths;counter_paths_after=$afterPaths;method='Preselected owned GPU Process Memory paths and adapter counters; no wildcard sampling of unrelated processes';scope='Windows process GPU counters can overcount shared allocations. Processes without exposed paths are recorded, not assigned zero. Any selected invalid/missing path, PDH error, inventory/path change or sample loss rejects the whole capture.'}
$temporary="$destination.$PID.tmp";$report|ConvertTo-Json -Depth 12|Set-Content $temporary -Encoding UTF8
Move-Item $temporary $destination
if($null -ne $failure){throw "ColetaGPU recusada; diagnostico preservado em $destination : $($failure.message)"}
@{label=$Label;valid=$true;samples=$records.Count;paths=$counterPaths.Count;owned_processes=$owned.Count}|ConvertTo-Json
