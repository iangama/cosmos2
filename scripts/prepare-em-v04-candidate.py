"""Separate EM0.4 candidate and explicit0.3 checkpoint/camera migration."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'output/c212-em-v03-product';STAGE=ROOT/'output/c212-em-v04-staging';DEST=ROOT/'output/c212-em-v04-product'
if DEST.exists():raise ValueError('Preserve existing candidate; preparation needs a new destination')
sys.path.insert(0,str(STAGE))
from em_migrate import migrate_v03,LEGACY_03_GENERATION
from em_experiment import Experiment,generation
kernel=json.loads((ROOT/'evidence/em-v04-kernel-check.json').read_text())
dynamics=json.loads((ROOT/'evidence/em-v04-mutual-dynamics-check.json').read_text())
for receipt in (kernel,dynamics):
    for name,sha in receipt['source_sha256'].items():
        if name.replace('\\','/').startswith('output/c212-em-v04-staging/'):
            assert hashlib.sha256((ROOT/name.replace('\\','/')).read_bytes()).hexdigest()==sha,('Test predates current scientific source',name)
assert kernel['scientific_generation']==generation()
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
ignore=shutil.ignore_patterns('__pycache__','*.pyc')
shutil.copytree(BASE/'app',DEST/'app',ignore=ignore);shutil.copytree(STAGE,DEST/'em',ignore=ignore)
sys.path.insert(0,str(DEST/'app'));from em_native import NativeEM
storage=DEST/'c212-em-worker/product';storage.mkdir(parents=True);archive=storage/'legacy-0_3';archive.mkdir()
migrations=[]
for source in sorted((BASE/'c212-em-worker/product').glob('*.json')):
    record=json.loads(source.read_bytes())
    if not isinstance(record,dict) or not {'generation','payload','sha256'}<=set(record):continue
    if record.get('schema')!=3 or record['generation']!=LEGACY_03_GENERATION:raise ValueError('Unrecognized legacy scientific checkpoint: '+source.name)
    shutil.copyfile(source,archive/source.name);dest=storage/source.name;ex=migrate_v03(source,dest)
    assert Experiment.load(dest).payload()==ex.payload()
    migrated={'source':str(source.relative_to(ROOT)),'destination':str(dest.relative_to(ROOT)),
              'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'destination_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'camera':None}
    view_source=source.with_name(source.stem+'.view.json')
    if view_source.exists():
        raw=view_source.read_bytes();envelope=json.loads(raw);payload=envelope['payload']
        canonical=lambda v:json.dumps(v,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
        assert set(envelope)=={'payload','sha256'} and hashlib.sha256(canonical(payload)).hexdigest()==envelope['sha256']
        assert payload['checkpoint_sha256']==migrated['original_sha256']
        NativeEM.validate_view(payload['view']);shutil.copyfile(view_source,archive/view_source.name)
        new_payload=deepcopy(payload);new_payload['checkpoint_sha256']=migrated['destination_sha256']
        new_envelope={'payload':new_payload,'sha256':hashlib.sha256(canonical(new_payload)).hexdigest()}
        view_dest=storage/view_source.name;view_dest.write_bytes(canonical(new_envelope)+b'\n')
        migrated['camera']={'original_sha256':hashlib.sha256(raw).hexdigest(),'destination_sha256':hashlib.sha256(view_dest.read_bytes()).hexdigest(),'pose_and_focus_unchanged':new_payload['view']==payload['view']}
    assert source.read_bytes()==(archive/source.name).read_bytes();migrations.append(migrated)
launcher=(ROOT/'scripts/start-c212-em-v03-candidate.ps1').read_text().replace('c212-em-v03-product','c212-em-v04-product')
launcher=launcher.replace('emKernelVersion = "0.3.0"','emKernelVersion = "0.4.0"')
(ROOT/'scripts/start-c212-em-v04-candidate.ps1').write_text(launcher)
for file in ('ui/index.html','ui/em.html'):
    p=DEST/'app'/file;s=p.read_text().replace('CANDIDATA EM 0.3','CANDIDATA EM 0.4').replace('candidata C2-12 · 0.3','candidata C2-12 · 0.4');p.write_text(s)
assert owner.read_bytes()==original
report={'status':'separate_EM0_4_candidate_and_explicit_EM0_3_migrations_prepared_native_not_yet_verified',
        'scientific_generation':generation(),'migrations':migrations,'owner_pointer_preserved':True,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (*STAGE.glob('*.py'),Path(__file__))},
        'scope':'Preserved0.3 candidate, originals archived before migration, camera adjunct explicitly rebound only after seal/core hash/pose validation. No native UI or performance acceptance.'}
(ROOT/'evidence/em-v04-prepared-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'migrated_checkpoints':len(migrations),'migrated_cameras':sum(m['camera'] is not None for m in migrations),'owner_pointer_preserved':True},indent=2))
