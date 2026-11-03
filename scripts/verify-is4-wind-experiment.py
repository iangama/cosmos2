"""Own0.9 worker/checkpoint, actual new process continuation and body replay."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import copy
import hashlib
import json
import sys
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1];PRODUCT=ROOT/'output/is4-solar-wind-product0.9.0';APP=PRODUCT/'app'
sys.path.insert(0,str(APP))
from is4_experiment import Experiment
from is4_body_snapshot import digest
from is4_client import Client
from is4_laboratory import ParticleLaboratory
from is4_product_store import Store
from is4_trajectory_transport import encode,decode
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def payload(client):
    p=client.call('export_payload')['result'];p.pop('edit_token');return p

def advance(client,count):
    while count:
        n=min(256,count);client.call('advance',{'steps':n});count-=n

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is4-wind-experiment-'+args.label);receipt=ROOT/('evidence/is4-wind-experiment-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve experiment evidence')
    folder.mkdir();fixture=ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json';phase=json.loads(fixture.read_text())['phase']
    base=json.loads((PRODUCT/'base-manifest.json').read_text());assert all(sha(ROOT/n)==v for n,v in base['base_sha256'].items())
    files=[*APP.glob('is4*.py'),Path(__file__),fixture,ROOT/'IS-4-VENTO-SOLAR-PRODUTO-CONTRATO.md'];hashes={f.relative_to(ROOT).as_posix():sha(f) for f in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,f.relative_to(ROOT).as_posix())
    report=dict(schema=1,accepted=False,completed=False,source_sha256=hashes,cases=[],refusals=0)
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    client=None;persist()
    try:
        lab=SimpleNamespace(lab=SimpleNamespace(status=lambda:dict(mode='experiment',physics=phase)))
        source_guard={k:phase[k] for k in ['system_id','edit_token','revision','time']}|{'frame':phase['contract']['frame']}
        from is4_wind_field import DEFAULT,AU_M
        for species,radius,lat,polarity in [('proton',1.,30.,1),('electron',5.,-60.,-1),('neutral',.3,10.,1)]:
            request=dict(source_guard=source_guard,species=species,relative_speed_m_s=1e6 if species=='electron' else 1e5,pitch_deg=60.,coordinates=dict(radius_m=radius*AU_M,latitude_deg=lat,east_longitude_deg=20.),wind_parameters={**DEFAULT,'polarity':polarity})
            p,r,parameters,unit,B=ParticleLaboratory._initial_wind(lab,request);storage=folder/species;client=Client(storage)
            client.call('create',dict(source_phase=p,source_reading=r,parameters=parameters,controls=dict(electric=True,magnetic=True,gravity=True)))
            advance(client,1024);sample=client.call('sample')['result'];assert 'wind_velocity_m_s' in sample['field']
            assert any(v!=0. for v in sample['field']['electric_field_V_m']) and 'total_static_energy_change_J' in sample
            if species!='neutral':assert sample['electric_work_J']!=0.
            state=client.snapshot();packet,record=encode(state,unit,B);decode(packet,record['metadata']['binding_sha256'])
            assert json.loads(json.dumps(record['geometry']['phase']))==state['experiment']['phase'] and state['experiment']['degree'] is None
            client.call('set_rate',{'value':200*parameters['dt_s']});client.call('resume');time.sleep(.4);began=time.perf_counter();client.call('pause');pause_ms=(time.perf_counter()-began)*1000
            assert client.snapshot()['paused'] and pause_ms<=500.
            client.call('save');saved=payload(client);old_worker=client.snapshot()['worker_id'];old_token=client.snapshot()['experiment']['edit_token']
            raw=json.loads((storage/'latest.json').read_text());store=Store(storage/'product');store.save(raw,dict(physical_unit_m=unit,visible=False));a=store.save(raw,dict(physical_unit_m=unit,visible=False),name='Ramo vento A')
            advance(client,77);future=payload(client);client.call('load');assert client.snapshot()['experiment']['edit_token']!=old_token and payload(client)==saved
            advance(client,77);assert payload(client)==future;client.close();client=None
            view,validated=store.restore_to(storage);assert view==dict(physical_unit_m=unit,visible=False)
            client=Client(storage);client.call('load');assert client.snapshot()['worker_id']!=old_worker;advance(client,77);assert payload(client)==future
            now=client.call('export_payload')['result'];b=store.save({**now,'manifest_sha256':digest(now)},dict(physical_unit_m=unit,visible=True),name='Ramo vento B',parent=a['branch']['id'])
            assert store.load(b['branch']['id'])[0]['branch']['parent']==a['branch']['id']
            old=copy.deepcopy(client.snapshot()['experiment']['phase']);guard=Client.guard(client.snapshot())
            try:client.call('advance',{'steps':1},guard={**guard,'edit_token':'0'*32})
            except ValueError:report['refusals']+=1
            else:raise AssertionError('Stale mutation accepted')
            assert client.snapshot()['experiment']['phase']==old
            client.close();client=None
            for field,value in [('electric_field_model_V_m',[0.,0.,0.]),('epoch',{'et_tdb_s':True}),('wind_parameters',{**DEFAULT,'polarity':True})]:
                bad=copy.deepcopy(raw);bad['source_reading'][field]=value;bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'})
                test=storage/('bad-'+field);test.mkdir();(test/'latest.json').write_text(json.dumps(bad))
                try:Experiment.load(test)
                except (ValueError,TypeError):report['refusals']+=1
                else:raise AssertionError(field)
            report['cases'].append(dict(kind='wind',species=species,pause_ms=pause_ms,electric_work_J=sample['electric_work_J'],save_load_new_worker_future77_exact=True,view_branch_sealed=True));persist()
        # Recreate accepted body trajectories using the unchanged solver/providers.
        exports=[]
        for file in (ROOT/'output/is4-body-particle-product0.8.1/particle-exports').glob('*.json'):
            data=json.loads(file.read_text())['particle']
            if data['source_reading']['body_reference_id'] in ['sol:naif:399','sol:naif:599'] and data['parameters']['charge_C']>0:
                if data['source_reading']['body_reference_id'] not in [x[1]['source_reading']['body_reference_id'] for x in exports]:exports.append((file,data))
        assert len(exports)==2
        for file,old in exports:
            storage=folder/file.stem;e=Experiment(storage,old['source_phase'],old['source_reading'],old['parameters'],old['controls'])
            remaining=old['step_index']
            while remaining:
                n=min(256,remaining);e.advance_steps(n);remaining-=n
            assert json.loads(json.dumps(e.payload()['phase']))==old['phase'] and json.loads(json.dumps(e.payload()['trail']))==old['trail']
            old={**old,'manifest_sha256':digest(old)};(storage/'latest.json').write_text(json.dumps(old))
            try:Experiment.load(storage)
            except ValueError:report['refusals']+=1
            else:raise AssertionError('Old schema silently migrated')
            report['cases'].append(dict(kind='body_replay',source=file.relative_to(ROOT).as_posix(),steps=e.step_index,phase_and_trail_exact=True))
        assert all(sha(ROOT/n)==v for n,v in hashes.items()) and all(sha(ROOT/n)==v for n,v in base['base_sha256'].items())
        report.update(accepted=True,completed=True,scope='0.9 science/worker/checkpoint: three wind species with nonzero E, exact future77 on load/new worker, view/branches, guard/source corruption refusals and two accepted body phase/trail replays. Native/UI/performance remain separate.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if client:client.close()
        persist()
    print(json.dumps(dict(accepted=report['accepted'],cases=len(report['cases']),refusals=report['refusals'],failure=report.get('failure'))),flush=True)
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
