"""Fork the historical EM collectors, adding refusal-time evidence only."""
from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]
helper = r'''
$script:scenarioDiagnosticIndex=0
function Save-ScenarioRefusal($Snapshot,$Predicates,[string]$Reason) {
  $script:scenarioDiagnosticIndex++
  $path="$root/output/em-scenario-refusal-$Label-$script:scenarioDiagnosticIndex.json"
  if(Test-Path $path){throw 'Diagnostico de recusa existente; preserve o label.'}
  $failed=@($Predicates.GetEnumerator() | Where-Object { !$_.Value } | ForEach-Object { $_.Key })
  @{ schema=1;accepted=$false;utc=[DateTime]::UtcNow.ToString('o');collector_pid=$PID;
     collector_sha256=$collectorSha256;reason=$Reason;predicates=$Predicates;failed_predicates=$failed;
     expected_worker=$ExpectedWorker;expected_mode=$ExpectedMode;
     expected_potential=$ExpectedPotential;expected_electric=$ExpectedElectric;
     snapshot=$Snapshot;session=$session;
     scope='Snapshot at refusal time; criteria unchanged; not an explanation of the historical incomplete run.' } |
    ConvertTo-Json -Depth 100 | Set-Content $path -Encoding UTF8
}
'''

COMMON = r'''
  $predicates=[ordered]@{
    native_active=[bool]$snapshot.native.active
    confirmation_accepted=($confirmation.state -eq 'accepted')
    native_error_absent=($null -eq $snapshot.native.error)
    worker_error_absent=($null -eq $snapshot.worker_error)
    system_identity=($confirmation.metadata.system_id -eq $state.system_id)
    revision_identity=($confirmation.metadata.revision -eq $state.revision)
    native_time_within_one_second=([Math]::Abs($confirmation.metadata.time_s - $state.time_s) -le 1)
    objects_128=($confirmation.objects.Count -eq 128)
    mutual_electrostatic=($state.experiment.mode -eq 'mutual_electrostatic')
    active_count_128=($state.experiment.system.ids.Count -eq 128)
    expected_worker=($ExpectedWorker -eq 'any' -or [bool]$state.paused -eq ($ExpectedWorker -eq 'paused'))
  }
'''
POTENTIAL = r'''
  $potential=$snapshot.native.potential
  $predicates['potential_error_absent']=!$potential.error
  $predicates['potential_confirmation_certain']=!$potential.confirmation_uncertain
  $predicates['potential_render_present']=($null -ne $potential.render)
  $predicates['potential_samples_1089']=($potential.render.sample_count -eq 1089)
  $predicates['potential_system_identity']=($potential.render.metadata.system_id -eq $state.system_id)
  $predicates['potential_revision_identity']=($potential.render.metadata.revision -eq $state.revision)
  $predicates['expected_potential_visibility']=([bool]$potential.settings.visible -eq ($ExpectedPotential -eq 'visible'))
  $predicates['expected_electric_visibility']=([bool]$state.editor.visual.electric_visible -eq ($ExpectedElectric -eq 'visible'))
'''
CLOUD = r'''
  $predicates=[ordered]@{
    native_active=[bool]$snapshot.native.active
    confirmation_accepted=($confirmation.state -eq 'accepted')
    native_error_absent=($null -eq $snapshot.native.error)
    worker_error_absent=($null -eq $snapshot.worker_error)
    system_identity=($metadata.system_id -eq $state.system_id)
    edit_token_identity=($metadata.edit_token -eq $state.edit_token)
    source_identity=($metadata.source_id -eq $state.source_id)
    cloud_identity=($metadata.cloud_id -eq $state.cloud_id)
    model_identity=($metadata.model -eq 'SI_prescribed_EM_test_cloud_boris_v2')
    length_unit_SI=($metadata.length_unit_m -eq 1)
    time_unit_SI=($metadata.time_unit_s -eq 1)
    native_time_within_one_second=([Math]::Abs($metadata.time_s - $state.time_s) -le 1)
    native_count_10000=($metadata.count -eq 10000)
    active_count_10000=($state.count -eq 10000)
    field_samples_97=($snapshot.field_map.measurement.samples.Count -eq 97)
    expected_worker=($ExpectedWorker -eq 'any' -or [bool]$state.paused -eq ($ExpectedWorker -eq 'paused'))
  }
'''

report = {'schema': 1, 'scope': 'New diagnostic collector forks; historical collectors and criteria preserved.', 'files': []}
for name in ['potential','cloud']:
    path = ROOT / ('scripts/collect-em-'+name+'-gpu-memory.ps1')
    target = path.with_name(path.stem+'-diagnostic.ps1')
    if target.exists():raise FileExistsError(target)
    original = path.read_text(encoding='utf-8-sig')
    start = original.index('function Read-Scenario {')
    end = original.index('\n$before=Read-Scenario', start)
    body = original[start:end]
    body = body.replace('function Read-Scenario {', 'function Read-Scenario {\n  $snapshot=$null\n  $predicates=[ordered]@{http_request_succeeded=$false}\n  try {', 1)
    insertion = CLOUD if name=='cloud' else COMMON+POTENTIAL
    body = body.replace('  $rendererConfirmed=', insertion+'\n  $rendererConfirmed=', 1)
    body = body.rstrip()[:-1]+'''  } catch {
    Save-ScenarioRefusal $snapshot $predicates $_.Exception.Message
    throw
  }
}'''
    target.write_text(original[:start]+helper+'\n'+body+original[end:], encoding='utf-8-sig')
    report['files'].append({'original':path.relative_to(ROOT).as_posix(),'original_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'candidate':target.relative_to(ROOT).as_posix(),'candidate_sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
receipt=ROOT/'evidence/em-gpu-diagnostic-forks-20261023.json'
if receipt.exists():raise FileExistsError(receipt)
receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
