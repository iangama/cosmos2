"""Regression of the moving-clock adapter using archived rawPDH bytes, without measuring."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import traceback
import zipfile

import gpu_pdh_audit_dynamics16 as audit

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);label=parser.parse_args().label
    assert label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    out=ROOT/f'evidence/is6-dynamics16-gpu-adapter-{label}.json';folder=ROOT/f'output/is6-dynamics16-gpu-adapter-{label}'
    assert not out.exists() and not folder.exists()
    old=json.loads((ROOT/'evidence/is6-moons-layers-profile-20261112a.json').read_text())
    source=ROOT/old['runs'][0]['gpu_report'];assert sha(source)==old['runs'][0]['gpu_sha256']
    paused=json.loads(source.read_text());assert paused['valid']
    files=[Path(__file__),Path(audit.__file__),Path(audit.base.__file__),ROOT/'scripts/collect_gpu_pdh_dynamics16.py',
           ROOT/'scripts/prepare-is6-dynamics16-gpu.py',ROOT/'IS-6-DINAMICA16-PERFIL-CONTRATO.md',source]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files};folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    result=dict(accepted=False,completed=False,source_sha256=hashes,source_archive_sha256=sha(folder/'executed-sources.zip'),
                scope='Offline adapter regression on archived counter bytes plus synthetic scenario clock metadata. No new GPU/performance measurement.',refusals=[])
    def persist():out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    persist()
    try:
        result['paused_original']=audit.audit(paused,expected_samples=66)
        moving=copy.deepcopy(paused);moving['expected_worker']='any'
        for field,t in [('scenario_before',0.),('scenario_after',66.)]:moving[field].update(paused=False,physical_time=t)
        for i,row in enumerate(moving['samples']):row['scenario'].update(paused=False,physical_time=float(i))
        result['moving_synthetic_clock']=audit.audit(moving,expected_samples=66)
        cases=[]
        for key,value in [('mode','atlas'),('renderer_confirmed',False),('paused',True),('paused',0),
                          ('requested_rate',10),('revision',1),('fixture_count',16),('physical_time',True),
                          ('physical_time',-1.),('physical_time',float('nan')),('physical_time',float('inf'))]:
            bad=copy.deepcopy(moving);bad['samples'][3]['scenario'][key]=value;cases.append(('sample '+key+' '+str(value),bad))
        for name,t in [('stalled',2.),('reversed',1.),('after bracket',100.)]:
            bad=copy.deepcopy(moving);bad['samples'][3]['scenario']['physical_time']=t;cases.append((name+' clock',bad))
        bad=copy.deepcopy(moving);bad['scenario_after']['physical_time']=10.;cases.append(('final before samples',bad))
        bad=copy.deepcopy(moving);bad['scenario_before']['physical_time']=float('nan');cases.append(('nonfinite initial',bad))
        bad=copy.deepcopy(paused);bad['samples'][3]['scenario']['physical_time']=1.;cases.append(('paused clock advanced',bad))
        bad=copy.deepcopy(moving);bad['samples'][3]['scenario']['unknown']=1;cases.append(('extra scenario field',bad))
        bad=copy.deepcopy(moving);bad['inventory_after'][0]['created_filetime']+=100;cases.append(('changed process identity',bad))
        for name,bad in cases:
            try:audit.audit(bad,expected_samples=66)
            except (ValueError,KeyError):result['refusals'].append(name)
            else:raise AssertionError('Accepted bad adapter metadata: '+name)
        assert all(sha(ROOT/n)==s for n,s in hashes.items())
        result.update(accepted=True,completed=True);persist()
    except Exception:result['failure']=traceback.format_exc();persist();raise
    print(json.dumps(dict(accepted=result['accepted'],refusals=len(result['refusals']),new_measurement=False)),flush=True)


if __name__=='__main__':main()
