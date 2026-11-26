"""Seal the exact four-window recipe, accepted journey/visual inputs and all sources."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-dynamics16-product0.26.2/app'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);label=parser.parse_args().label
    assert label and len(label)<=20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    out=ROOT/f'evidence/is6-dynamics16-profile-plan-{label}.json';assert not out.exists()
    native_path=ROOT/'evidence/is6-dynamics16-native-20261112d.json';native=json.loads(native_path.read_text())
    visual_path=ROOT/'evidence/is6-dynamics16-visual-20261112b.json';visual=json.loads(visual_path.read_text())
    adapter_path=ROOT/'evidence/is6-dynamics16-gpu-adapter-20261112a.json';adapter=json.loads(adapter_path.read_text())
    assert native['functional_accepted'] and native['owner_view_restored'] and len(native['selections'])==16
    assert native['checks']['all16_selection_camera_reading_both_scales']['previous_cases']==16
    assert visual['accepted'] and visual['completed'] and len(visual['captures'])==6 and adapter['accepted']
    manifest_path=APP.parent/'build-manifest.json';manifest=json.loads(manifest_path.read_text())
    assert manifest['candidate']=='0.26.2' and manifest['inherited_service']['python_files_byte_identical']
    actual={p.relative_to(APP).as_posix():sha(p) for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert actual==manifest['files_sha256']
    sources={**manifest['source_sha256'],**native['source_sha256']}
    files=[Path(__file__),native_path,visual_path,adapter_path,manifest_path,
           ROOT/'IS-6-DINAMICA16-PERFIL-CONTRATO.md',ROOT/'IS-6-DINAMICA16-PERFIL-CONTRATO-V2.md',
           ROOT/'IS-6-GPU-IDENTIDADE-PROCESSOS.md',ROOT/'IS-6-GPU-PDH-PYTHON-CONTRATO.md',ROOT/'IS-6-GPU-PDH-PYTHON-TEMPO.md']
    names=['profile-is6-dynamics16.py','audit-is6-dynamics16-profile.py','run-is6-dynamics16-profile.py','open-dynamics16-app.py',
           'collect_gpu_pdh_dynamics16.py','gpu_pdh_audit_dynamics16.py','gpu_pdh_audit_dynamics16_base.py',
           'windows_gpu_pdh_v2.py','owned_process_snapshot.py','native_product_memory_v2.py','owned_process_preparation.py',
           'is6_owned_profile_host.py','cef_page_v2.py','benchmark-body-points-native.py','is6_pair_profile_support.py',
           'launch-is6-dynamics16-candidate-v5.py','native_ui_readiness.py','bootstrap-native-ui-v2.py']
    files += [ROOT/'scripts'/n for n in names]
    for capture in visual['captures']:
        assert sha(ROOT/capture['path'])==capture['sha256'];files.append(ROOT/capture['path'])
    sources.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    assert all(sha(ROOT/n)==s for n,s in sources.items())
    plan=dict(accepted=True,completed=True,candidate='0.26.2',source_sha256=sources,warmup_s=30,window_s=60,
        resolution=[1920,1080],UI_scale=1.,required_GPU_samples=66,
        windows=[dict(name='system_paused',paused=True,rate=1.,reference_id=None),dict(name='system_rate0.1',paused=False,rate=.1,reference_id=None),
                 dict(name='earth_rate1',paused=False,rate=1.,reference_id='sol:naif:399'),dict(name='titan_rate10',paused=False,rate=10.,reference_id='sol:naif:606')],
        limits_before_execution=dict(median_ms=16.7,p95_ms=25.,p99_ms=50.,over_100ms=0,RAM_bytes=8*2**30,GPU_bytes=5.5*2**30,measured_rate_min=.9),
        scope='Own sixteen-center dynamics profile; same frame and memory limits. Only scientific clock varies during moving-clock PDH collection. Not a replacement for K5A or full IS6 acceptance.')
    out.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,windows=4,sources=len(sources),measurement_executed=False)),flush=True)


if __name__=='__main__':main()
