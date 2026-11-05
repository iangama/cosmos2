"""Freeze actual imported65x96 recipes and unchanged resource/frame limits."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT/'output/is6-spatial-import-product0.22.1/app'
sys.path.insert(0,str(APP))
import is6_spatial_import_store as storage
from is6_pair_profile_support import LIMITS
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--label',required=True)
args = parser.parse_args()
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
    parser.error('Invalid label')
out = ROOT/('evidence/is6-spatial-import-profile-plan-'+args.label+'.json')
folder = ROOT/('output/is6-spatial-import-profile-plan-'+args.label)
if out.exists() or folder.exists():
    raise FileExistsError('Preserve profile recipe')
manifest_path = APP.parent/'build-manifest.json'
manifest = json.loads(manifest_path.read_text())
assert manifest['candidate']=='0.22.1' and manifest['promoted'] is False
sources = {name:seal for name,seal in manifest['source_sha256'].items() if Path(name).suffix.lower() not in {'.zip','.png'}}
anchors = [ROOT/('evidence/'+name+'.json') for name in [
    'is6-spatial-import-native-20261105e','is6-spatial-import-native-20261105f',
    'is6-spatial-import-visual-20261105e','gpu-pdh-preflight-20261105b']]
for p in anchors:
    assert json.loads(p.read_text())['accepted']
for p in [Path(__file__),manifest_path,ROOT/'IS-6-IMPORTACAO-ESPACIAL-PERFIL-CONTRATO.md',
          ROOT/'scripts/is6_pair_profile_support.py',ROOT/'scripts/windows_gpu_pdh_v2.py',
          ROOT/'scripts/gpu_pdh_audit_v2.py',ROOT/'scripts/collect_gpu_pdh_v2.py',
          ROOT/'scripts/is6_owned_profile_host.py',ROOT/'scripts/verify-gpu-pdh-report-v2.py',*anchors]:
    sources[p.relative_to(ROOT).as_posix()] = sha(p)
for name,seal in manifest['files_sha256'].items():
    sources[(APP/name).relative_to(ROOT).as_posix()] = seal
assert all(sha(ROOT/name)==seal for name,seal in sources.items())
native = json.loads(anchors[1].read_text())
branch = native['imported_branch']
store = storage.Store(APP.parent/'is6-spatial-import-service-records')
reference = store.load(branch)
assert reference.origin is not None and reference.branch['parent'] is None
assert reference.payload['binding']['body_reference_id']=='sol:naif:10'
assert reference.payload['configuration']==storage.artifact.DEFAULT_CONFIGURATION
run = storage.artifact.Run.restore(reference.payload)
folder.mkdir()
record_path = folder/'reference.json'
record_path.write_bytes((store.branches/(branch+'.json')).read_bytes())
sources[record_path.relative_to(ROOT).as_posix()] = sha(record_path)
windows = []
for index,kind in enumerate(['static-visible','static-hidden','probes-visible','visibility'],1):
    initial = {**reference.view,'visible':kind!='static-hidden'}
    recipe = []
    if kind in {'probes-visible','visibility'}:
        for tick in range(120):
            view = dict(initial)
            if kind=='probes-visible':
                view.update(selected_radial_index=(tick*17)%65,selected_azimuth_index=(tick*11)%96,
                            reference_radial_index=(tick*19)%65)
            else:
                view['visible']=tick%2==1
            recipe.append(dict(tick=tick,offset_s=tick*.5,view=view,sample=run.sample(view)))
    item = dict(run=index,kind=kind,initial_view=initial,initial_sample=run.sample(initial),recipe=recipe)
    path = folder/('window-'+str(index)+'.json')
    path.write_text(json.dumps(item,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
    windows.append(dict(run=index,kind=kind,path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
plan = dict(accepted=True,completed=True,candidate='0.22.1',source_sha256=sources,branch_id=branch,
    reference_path=record_path.relative_to(ROOT).as_posix(),artifact_sha256=storage.artifact.digest(reference.payload),
    source_sha256_original=reference.origin['source_sha256'],original_view=reference.origin['view'],
    windows=windows,limits_before_execution=LIMITS,warmup_s=30,window_s=60,resolution=[1920,1080],UI_scale='1',
    GPU_samples=66,requires_paused_GPU_preflight=True,
    scope='Frozen prerequisites/recipes only; no profile measured or performance accepted.')
out.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(prepared=True,windows=4,commands=240,benchmark_run=False)))
