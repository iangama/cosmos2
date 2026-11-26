"""Seal the new scene's four compound recipes after its own native/visual journey."""
import argparse
import hashlib
import json
from pathlib import Path

import is6_layers_profile_support as support

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--first-label',required=True)
    parser.add_argument('--restart-label',required=True)
    parser.add_argument('--visual-label',required=True)
    args=parser.parse_args()
    for label in vars(args).values():
        if not label or len(label)>20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    out=ROOT/f'evidence/is6-moons-layers-profile-plan-{args.label}.json'
    if out.exists():raise FileExistsError('Preserve compound plan')
    files=[Path(__file__),ROOT/'IS-6-LUAS-CAMADAS-CONTRATO.md']
    natives=[]
    for label in [args.first_label,args.restart_label]:
        native_path=ROOT/f'evidence/is6-moons-layers-native-{label}.json'
        process_path=ROOT/f'evidence/is6-moons-layers-native-process-{label}.json'
        native=json.loads(native_path.read_text());process=json.loads(process_path.read_text())
        assert native['accepted'] and native['completed'] and native['atlas_unchanged']
        assert process['accepted'] and set(process['processes'].values())=={0}
        assert process['native_receipt_sha256']==sha(native_path)
        natives.append(native);files.extend([native_path,process_path])
    assert natives[0]['phase']=='first' and natives[1]['phase']=='restart'
    visual_path=ROOT/f'evidence/is6-moons-layers-visual-{args.visual_label}.json'
    visual=json.loads(visual_path.read_text())
    assert visual['accepted'] and visual['completed'] and len(visual['captures'])==23
    assert {c['sha256'] for c in visual['captures']}=={c['sha256'] for n in natives for c in n['captures']}
    assert all(sha(ROOT/c['path'])==c['sha256'] for c in visual['captures'])
    files.append(visual_path)
    sources={p:s for n in natives for p,s in n['source_sha256'].items() if Path(p).suffix.lower() not in {'.zip','.png'}}
    for name in ['profile-is6-moons-layers.py','audit-is6-moons-layers-profile.py','run-is6-moons-layers-profile.py',
                 'is6_layers_profile_support.py','is6_pair_profile_support.py','collect_gpu_pdh_v3.py',
                 'windows_gpu_pdh_v2.py','gpu_pdh_audit_v3.py','gpu_pdh_audit_v2.py','owned_process_snapshot.py',
                 'native_product_memory_v2.py','owned_process_preparation.py','is6_owned_profile_host.py',
                 'verify-gpu-pdh-report-v3.py','launch-is6-principal-moons-candidate-v2.py','open-moons-app.py']:
        files.append(ROOT/'scripts'/name)
    for name in ['IS-6-GPU-IDENTIDADE-PROCESSOS.md','IS-6-GPU-PDH-PYTHON-CONTRATO.md','IS-6-GPU-PDH-PYTHON-TEMPO.md']:
        files.append(ROOT/name)
    sources.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    assert all(sha(ROOT/name)==seal for name,seal in sources.items())
    windows=[]
    for index,(target,kind) in enumerate(support.WINDOWS,1):
        reference='sol:naif:'+target
        settings=support.settings(natives[1]['source_phase'],reference);settings.pop('body_id')
        windows.append(dict(run=index,reference_id=reference,kind=kind,settings=settings,recipe=support.recipe(kind),
                            source_identity_policy='Resolve body_id and source_guard from the new live paused four-body copy.'))
    plan=dict(accepted=True,completed=True,candidate='0.25.1',source_sha256=sources,windows=windows,
              warmup_s=30,window_s=60,resolution=[1920,1080],UI_scale=1.,required_GPU_samples=66,
              limits_before_execution=support.LIMITS,expected_mode='experiment',expected_worker='paused',
              scope='Own expanded-scene compound render/API profile with unchanged imported records. K5A remains refused; no save throughput, sixteen-body dynamics, promotion or full IS6 acceptance.')
    out.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,windows=4,sources=len(sources),measurement_executed=False)))


if __name__=='__main__':main()
