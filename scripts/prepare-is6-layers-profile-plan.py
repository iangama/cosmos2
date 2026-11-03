"""Freeze the four K3 measurement recipes; this does not run a benchmark."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import is6_layers_profile_support as support

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
out=ROOT/('evidence/is6-layers-profile-plan-'+args.label+'.json')
if out.exists():raise FileExistsError('Preserve measurement plan')
anchor=ROOT/'evidence/is6-layers-product-cut-20261103b.json'
cut=json.loads(anchor.read_text());assert cut['accepted'] and cut['candidate']=='0.19.1' and cut['promoted'] is False
native=ROOT/'evidence/is6-layers-native-20261103b.json'
r=json.loads(native.read_text());assert r['accepted'] and r['completed']
sources=copy.deepcopy(cut['source_sha256'])
for p in [Path(__file__),Path(support.__file__),ROOT/'scripts/is6_pair_profile_support.py',
          ROOT/'IS-6-COEXISTENCIA-PERFIL-K3-CONTRATO.md',anchor,native]:
    sources[p.relative_to(ROOT).as_posix()]=sha(p)
assert all(sha(ROOT/n)==seal for n,seal in sources.items())
windows=[]
for index,(target,kind) in enumerate(support.WINDOWS,1):
    reference='sol:naif:'+target
    selected=support.settings(r['source_phase'],reference)
    # A future live copy has new body/session identities. Resolve its body_id
    # from reference_id and obtain a fresh source guard before each create.
    selected.pop('body_id')
    windows.append(dict(run=index,reference_id=reference,kind=kind,settings=selected,
        recipe=support.recipe(kind),source_identity_policy='Resolve body_id and source_guard from the new live paused four-body copy; never replay archived UUIDs.'))
plan=dict(accepted=True,completed=True,candidate='0.19.1',source_sha256=sources,windows=windows,
    warmup_s=30,window_s=60,resolution=[1920,1080],UI_scale=1.,limits_before_execution=support.LIMITS,
    required_GPU_samples=66,expected_mode='experiment',expected_worker='paused',
    scope='Prerequisite and recipe checks only. Collector/auditor not implemented or executed; no frame, API-latency, resource or final UI performance acceptance.')
out.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(prepared=True,windows=len(windows),commands=sum(len(w['recipe']) for w in windows),benchmark_run=False)))
