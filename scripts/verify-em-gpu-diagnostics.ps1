param([ValidatePattern('^[a-z0-9_-]{1,30}$')][string]$Label='20261023a')
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$root="$project/output/em-gpu-diagnostic-tests-$Label"
if(Test-Path $root){throw 'Preserve existing test evidence.'}
New-Item -ItemType Directory "$root/output" | Out-Null
$destination="$project/evidence/em-gpu-diagnostic-tests-$Label.json"
if(Test-Path $destination){throw 'Preserve existing receipt.'}
$session=@{app=1;server=2;test_fixture=$true}
$ExpectedWorker='running';$ExpectedPotential='visible';$ExpectedElectric='visible'
function Import-Function([string]$File,[string]$Name) {
  $tokens=$null;$parseErrors=$null
  $ast=[System.Management.Automation.Language.Parser]::ParseFile($File,[ref]$tokens,[ref]$parseErrors)
  if($parseErrors.Count){throw ($parseErrors | Out-String)}
  $found=$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $Name},$true)
  if($found.Count -ne 1){throw "Missing or duplicate function $Name"}
  return [scriptblock]::Create($found[0].Extent.Text)
}
function Invoke-RestMethod {param($Uri,$TimeoutSec) if($script:TestHTTPFailure){throw 'Synthetic HTTP failure before snapshot'};return $script:TestSnapshot}
function Set-Path($Object,[string]$Path,$Value){
  $parts=$Path.Split('.');$target=$Object
  for($i=0;$i -lt $parts.Count-1;$i++){$target=$target.($parts[$i])}
  $target.($parts[-1])=$Value
}
$report=@{schema=1;accepted=$false;scope='Offline fixtures; original and diagnostic acceptance must match. Does not recreate the historical native refusal.';cases=@();sources=@{}}
try {
  $script:scenarioDiagnosticIndex=0
  foreach($kind in @('potential','cloud')) {
    $original="$project/scripts/collect-em-$kind-gpu-memory.ps1"
    $candidate="$project/scripts/collect-em-$kind-gpu-memory-diagnostic.ps1"
    $report.sources[$original]=(Get-FileHash $original -Algorithm SHA256).Hash.ToLowerInvariant()
    $report.sources[$candidate]=(Get-FileHash $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
    . (Import-Function $original 'Read-Scenario')
    $legacyFunction=${function:Read-Scenario}
    . (Import-Function $candidate 'Save-ScenarioRefusal')
    . (Import-Function $candidate 'Read-Scenario')
    $collectorSha256=(Get-FileHash $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
    $ExpectedMode=if($kind -eq 'cloud'){'emcloud'}else{'em'}
    if($kind -eq 'potential') {
      $fixture=@{state=@{system_id='system';revision=0;time_s=0;paused=$false;requested_model_s_per_wall_s=1;
          experiment=@{mode='mutual_electrostatic';system=@{ids=@(1..128)}};editor=@{visual=@{electric_visible=$true}}};
        worker_error=$null;native=@{active=$true;error=$null;confirmation=@{state='accepted';metadata=@{system_id='system';revision=0;time_s=0};objects=@(1..128)};
          potential=@{error=$null;confirmation_uncertain=$false;settings=@{visible=$true};render=@{sample_count=1089;segment_count=100;layer_id='layer';metadata=@{system_id='system';revision=0;time_s=0}}}}}
      $mutations=@(
        @{path='native.active';value=$false},@{path='native.confirmation.state';value='refused'},
        @{path='native.error';value='failure'},@{path='worker_error';value='failure'},
        @{path='native.confirmation.metadata.system_id';value='wrong'},@{path='native.confirmation.metadata.revision';value=1},
        @{path='native.confirmation.metadata.time_s';value=2},@{path='native.confirmation.objects';value=@(1)},
        @{path='state.experiment.mode';value='wrong'},@{path='state.experiment.system.ids';value=@(1)},
        @{path='state.paused';value=$true},@{path='native.potential.error';value='failure'},
        @{path='native.potential.confirmation_uncertain';value=$true},@{path='native.potential.render';value=$null},
        @{path='native.potential.render.sample_count';value=1088},@{path='native.potential.render.metadata.system_id';value='wrong'},
        @{path='native.potential.render.metadata.revision';value=1},@{path='native.potential.settings.visible';value=$false},
        @{path='state.editor.visual.electric_visible';value=$false})
    } else {
      $metadata=@{system_id='system';edit_token='token';source_id='source';cloud_id='cloud';model='SI_prescribed_EM_test_cloud_boris_v2';length_unit_m=1;time_unit_s=1;time_s=0;count=10000}
      $fixture=@{state=@{system_id='system';edit_token='token';source_id='source';cloud_id='cloud';time_s=0;count=10000;paused=$false;revision=0;requested_model_s_per_wall_s=1;dt_s=.01};
        worker_error=$null;native=@{active=$true;error=$null;confirmation=@{state='accepted';metadata=$metadata}};
        field_map=@{measurement=@{samples=@(1..97)}};visual=@{cloud_visible=$true;electric_visible=$true;magnetic_visible=$true}}
      $mutations=@(
        @{path='native.active';value=$false},@{path='native.confirmation.state';value='refused'},
        @{path='native.error';value='failure'},@{path='worker_error';value='failure'},
        @{path='native.confirmation.metadata.system_id';value='wrong'},@{path='native.confirmation.metadata.edit_token';value='wrong'},
        @{path='native.confirmation.metadata.source_id';value='wrong'},@{path='native.confirmation.metadata.cloud_id';value='wrong'},
        @{path='native.confirmation.metadata.model';value='wrong'},@{path='native.confirmation.metadata.length_unit_m';value=2},
        @{path='native.confirmation.metadata.time_unit_s';value=2},@{path='native.confirmation.metadata.time_s';value=2},
        @{path='native.confirmation.metadata.count';value=9999},@{path='state.count';value=9999},
        @{path='field_map.measurement.samples';value=@(1)},@{path='state.paused';value=$true})
    }
    $cases=@(@{path='positive';value=$null})+$mutations+@(@{path='HTTP';value=$null})
    foreach($case in $cases) {
      $script:TestSnapshot=$fixture | ConvertTo-Json -Depth 20 | ConvertFrom-Json
      $script:TestHTTPFailure=$case.path -eq 'HTTP'
      if($case.path -notin @('positive','HTTP')){Set-Path $script:TestSnapshot $case.path $case.value}
      $legacyAccepted=$true;$currentAccepted=$true
      try{& $legacyFunction | Out-Null}catch{$legacyAccepted=$false}
      $countBefore=@(Get-ChildItem "$root/output" -Filter '*.json').Count
      try{Read-Scenario | Out-Null}catch{$currentAccepted=$false}
      if($currentAccepted -ne $legacyAccepted){throw "Acceptance changed for $kind $($case.path)"}
      if($currentAccepted -ne ($case.path -eq 'positive')){throw "Unexpected fixture acceptance $kind $($case.path)"}
      $files=@(Get-ChildItem "$root/output" -Filter '*.json')
      if(!$currentAccepted) {
        if($files.Count -ne $countBefore+1){throw 'Missing refusal diagnostic.'}
        $latest=$files | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
        $record=Get-Content $latest.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        if($record.accepted -ne $false -or $record.failed_predicates.Count -eq 0){throw 'Missing failed predicates.'}
        if($case.path -ne 'HTTP' -and ($record.snapshot | ConvertTo-Json -Depth 30 -Compress) -ne ($script:TestSnapshot | ConvertTo-Json -Depth 30 -Compress)){throw 'Snapshot changed in diagnostic.'}
      }
      $report.cases+=@{kind=$kind;case=$case.path;legacy_accepted=$legacyAccepted;diagnostic_accepted=$currentAccepted;refusal_saved=(!$currentAccepted)}
    }
  }
  $report.accepted=$true
} catch {$report.failure=$_.Exception.Message}
$report.script_sha256=(Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
$report | ConvertTo-Json -Depth 10 | Set-Content $destination -Encoding UTF8
@{accepted=$report.accepted;cases=$report.cases.Count;failure=$report.failure;receipt=$destination} | ConvertTo-Json
if(!$report.accepted){exit 1}
