"""Live three-sample validation of strictly selected native GPU paths."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import hashlib
import json
import re
import subprocess
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('is6_gpu_preflight_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
label='is6-scoped-preflight-20261102b'
folder=ROOT/'output/is6-gpu-scoped-preflight-20261102b';receipt=ROOT/'evidence/is6-gpu-scoped-preflight-20261102b.json'
if folder.exists() or receipt.exists():raise FileExistsError('Preserve preflight')
native=ROOT/'evidence/is6-product-native-20261102f.json';parent=json.loads(native.read_text());assert parent['accepted']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes=dict(parent['source_sha256'])
for p in [native,Path(__file__),ROOT/'IS-6-PERFIL-REVISAO-B.md',ROOT/'scripts/collect-is6-gpu-memory-scoped.ps1',ROOT/'evidence/is6-gpu-collection-analysis-20261102a.json']:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
assert all(sha(ROOT/n)==v for n,v in hashes.items());folder.mkdir()
with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
    for n in hashes:z.write(ROOT/n,n)
r=dict(accepted=False,completed=False,source_sha256=hashes,owner_sha256=sha(ROOT/'user/sessions/latest.json'),scope='Three live selected-path GPU samples only; no sustained profile acceptance.')
try:
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert session['is6SpatialCandidate'] and session['serverScript'].replace('\\','/').endswith('/output/is6-spatial-product0.18.2/app/server.py')
    assert h.get('/api/state')['mode']=='atlas'
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/collect-is6-gpu-memory-scoped.ps1'),'-Label',label,'-Samples','3','-ExpectedMode','atlas'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=40)
    (folder/'collector.log').write_text(result.stdout,encoding='utf-8');(folder/'collector-errors.log').write_text(result.stderr,encoding='utf-8')
    assert result.returncode==0,'Collector rejected; see preserved log'
    gpu_path=ROOT/('evidence/gpu-memory-'+label+'.json');g=json.loads(gpu_path.read_text(encoding='utf-8-sig'))
    assert g['schema']==3 and g['valid'] and g['failure'] is None and not g['counter_errors'] and len(g['samples'])==3
    paths=set(g['configured_counter_paths']);assert paths==set(g['counter_paths_after']) and len(paths)==len(g['configured_counter_paths'])
    owned=set(g['owned_processes']);seen=set()
    for s in g['samples']:
        assert not s['invalid_samples'] and s['scenario']['mode']=='atlas' and s['scenario']['renderer_confirmed']
        assert set(v['path'] for v in s['raw_counter_samples'])==paths
        assert all(v['status']==0 and type(v['cooked_value']) in [int,float] and v['cooked_value']>=0 for v in s['raw_counter_samples'])
        for path in paths:
            match=re.fullmatch(r'\\gpu process memory\(pid_(\d+)_[^)]+\)\\(dedicated usage|shared usage)',path)
            if match:
                assert int(match[1]) in owned;seen.add(int(match[1]))
            else:assert re.fullmatch(r'\\gpu adapter memory\([^)]+\)\\dedicated usage',path)
        assert any(p['pid']==session['app'] and p['counter']=='dedicated usage' for p in s['product'])
        assert all(p['pid'] in owned for p in s['product'])
    assert seen==set(g['owned_gpu_processes']) and owned-seen==set(g['owned_without_exposed_gpu_counter'])
    assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256'] and all(sha(ROOT/n)==v for n,v in hashes.items())
    r.update(accepted=True,completed=True,paths=len(paths),samples=3,GPU_report=gpu_path.relative_to(ROOT).as_posix(),GPU_sha256=sha(gpu_path),own_gpu_pids=sorted(seen),session=session)
except Exception:r['failure']=traceback.format_exc()
finally:
    try:h.native('openspace.toggleShutdown();return {closing=true}')
    except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
    receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in {'source_sha256','session'}},ensure_ascii=False))
raise SystemExit(0 if r['accepted'] else 1)
