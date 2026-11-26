"""Revision0.26.1: route the sixteen-center reader through the native Laboratory."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is6-dynamics16-product0.26.0'
TARGET=ROOT/'output/is6-dynamics16-product0.26.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists(),'Preserve prepared revision'
    parent=json.loads((BASE/'build-manifest.json').read_text(encoding='utf8'))
    actual={p.relative_to(BASE/'app').as_posix():sha(p) for p in (BASE/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert actual==parent['files_sha256']
    refused=ROOT/'evidence/is6-dynamics16-native-admission-20261112a.json'
    assert not json.loads(refused.read_text())['accepted']
    lab=(BASE/'app/laboratory.py').read_text(encoding='utf8')
    old="if name in ('solar_reading', 'solar_tide', 'earth_field', 'jupiter_field'):"
    assert lab.count(old)==1
    lab=lab.replace(old,"if name in ('dynamics16_reading', 'solar_reading', 'solar_tide', 'earth_field', 'jupiter_field'):")
    runtime=(BASE/'app/dynamics16_runtime.py').read_text(encoding='utf8')
    assert runtime.count("version='0.26.0'")==1
    runtime=runtime.replace("version='0.26.0'","version='0.26.1'")
    compile(lab,'laboratory.py','exec');compile(runtime,'dynamics16_runtime.py','exec')
    shutil.copytree(BASE/'app',TARGET/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (TARGET/'app/laboratory.py').write_text(lab,encoding='utf8')
    (TARGET/'app/dynamics16_runtime.py').write_text(runtime,encoding='utf8')
    inputs=[Path(__file__),BASE/'build-manifest.json',refused]
    sources={**parent['source_sha256'],**{p.relative_to(ROOT).as_posix():sha(p) for p in inputs}}
    assert all(sha(ROOT/n)==s for n,s in sources.items())
    files={p.relative_to(TARGET/'app').as_posix():sha(p) for p in (TARGET/'app').rglob('*') if p.is_file()}
    manifest=dict(candidate='0.26.1',accepted=False,promoted=False,source_sha256=sources,files_sha256=files,
        changed=sorted(n for n,s in files.items() if actual.get(n)!=s),base_manifest=(BASE/'build-manifest.json').relative_to(ROOT).as_posix(),
        scene_profile=parent['scene_profile'],scope='Correct real native Laboratory dispatch; independent service and HTTP must be rerun on this immutable packet before switching.')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    # Prepared verification revisions include the real Laboratory routing method.
    verifier=ROOT/'scripts/verify-is6-dynamics16-service-v2.py';assert not verifier.exists()
    text=(ROOT/'scripts/verify-is6-dynamics16-service.py').read_text(encoding='utf8').replace('is6-dynamics16-product0.26.0','is6-dynamics16-product0.26.1')
    anchor="        assert len(worker.call('dynamics16_reading',**guard(restored),body_id=restored['bodies'][0]['id'])['result']['sources'])==15"
    assert text.count(anchor)==1
    extra="\n        from laboratory import Laboratory\n        bridge=Laboratory.__new__(Laboratory);bridge.mode='experiment'\n        def dispatch(request):\n            request=dict(request);name=request.pop('command');return worker.call(name,**request)\n        bridge._worker_command=dispatch\n        for body in restored['bodies']:\n            routed=bridge._apply(dict(command='dynamics16_reading',**guard(restored),body_id=body['id']))\n            assert len(routed['result']['sources'])==15\n        bridge.mode='atlas'\n        refuse('real Laboratory rejects reading outside experiment',lambda:bridge._apply(dict(command='dynamics16_reading',**guard(restored),body_id=restored['bodies'][0]['id'])))\n        report['checks']['real_Laboratory_apply_16_readings_and_mode_guard']=True"
    text=text.replace(anchor,anchor+extra)
    compile(text,str(verifier),'exec');verifier.write_text(text,encoding='utf8')
    verifier=ROOT/'scripts/verify-is6-dynamics16-http-v2.py';assert not verifier.exists()
    text=(ROOT/'scripts/verify-is6-dynamics16-http.py').read_text(encoding='utf8').replace('is6-dynamics16-product0.26.0','is6-dynamics16-product0.26.1').replace('verify-is6-dynamics16-service.py','verify-is6-dynamics16-service-v2.py')
    compile(text,str(verifier),'exec');verifier.write_text(text,encoding='utf8')
    print(json.dumps(dict(prepared=True,candidate='0.26.1',changed=manifest['changed'])),flush=True)


if __name__=='__main__':main()
