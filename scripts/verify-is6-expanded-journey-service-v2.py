"""Preliminary real-worker16->4->16 admission; renderer and downstream instruments remain pending."""
import argparse
import copy
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import shutil
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-expanded-journey-product0.27.0/app'
helpers=SourceFileLoader('expanded_service_worker_helpers',str(ROOT/'scripts/verify-is6-dynamics16-service-v3.py')).load_module()
# The helper only owns the line protocol; the launched child executes this packet.
helpers.APP=APP
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


class ExpandedWorker(helpers.Worker):
    def call(self,command_name,expect_error=False,**fields):
        self.serial+=1
        self.process.stdin.write(json.dumps(dict(command=command_name,id=self.serial,**fields),allow_nan=False)+'\n')
        self.process.stdin.flush()
        import time
        deadline=time.monotonic()+40
        while True:
            response=self.events.get(timeout=max(.001,deadline-time.monotonic()))
            assert response['type'] not in ('eof','invalid'),response
            if response['type']=='snapshot':self.latest=response
            if response.get('id')==self.serial and response['type'] in ('ack','error'):
                assert (response['type']=='error')==expect_error,response
                return response


def physical(p):
    return {k:copy.deepcopy(p[k]) for k in ['system_id','edit_token','revision','time','bodies','atlas_initial','interventions','dynamics16']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);label=parser.parse_args().label
    assert label and len(label)<=24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    folder=ROOT/f'output/is6-expanded-journey-service-{label}';out=ROOT/f'evidence/is6-expanded-journey-service-{label}.json'
    assert not folder.exists() and not out.exists(),'Preserve admission evidence'
    packet=json.loads((APP.parent/'build-manifest.json').read_text(encoding='utf8'))
    assert packet['candidate']=='0.27.0' and packet['changed']==[] and packet['promoted'] is False
    assert {p.relative_to(APP).as_posix():sha(p) for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts}==packet['files_sha256']
    inventory_path=APP.parent/'journey-inventory.json';assert sha(inventory_path)==packet['journey_inventory_sha256']
    inventory=json.loads(inventory_path.read_text())
    folder.mkdir();storage=folder/'worker';protected={n:sha(ROOT/n) for n in ['output/session.json','user/sessions/latest.json','Abrir-Dinamica16.cmd']}
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__),Path(helpers.__file__),inventory_path,APP.parent/'build-manifest.json',ROOT/'IS-6-PERCURSO-AMPLIADO16-CONTRATO.md']
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in sources:z.write(ROOT/name,name)
    report=dict(accepted=False,completed=False,source_sha256=sources,source_archive_sha256=sha(folder/'executed-sources.zip'),protected_sha256=protected,
        steps=[],refusals=[],scope='Preliminary actual0.27.0 worker transition and phase-domain guards. HTTP/native, particles, layers, solar nuclear journey, captures and residency remain pending.')
    def persist():out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    worker=None;persist()
    try:
        import system16_import
        import solar_import
        import solar_catalog
        utc='2026-10-11T12:00:00Z'
        sixteen=system16_import.prepare(system16_import.catalog.states(utc=utc))
        four=solar_import.prepare(solar_catalog.states(utc))
        assert sixteen['source']['epoch']['et_tdb_s']==four['source']['epoch']['et_tdb_s']
        worker=ExpandedWorker(storage);worker.call('import_atlas',initial_state=sixteen)
        original=copy.deepcopy(worker.latest);assert len(original['bodies'])==16 and original['paused']
        worker.call('save');saved16=folder/'saved-sixteen';shutil.copytree(storage,saved16)
        branch=worker.call('create_branch',**helpers.guard(original),name='Origem16 do percurso ampliado')['result']
        assert branch['system_id']==original['system_id']
        for b in [original['bodies'][3],original['bodies'][6],original['bodies'][-1]]:
            assert len(worker.call('dynamics16_reading',**helpers.guard(original),body_id=b['id'])['result']['sources'])==15
        report['steps'].append(dict(name='sixteen_saved_and_branched',bodies=16,branch=branch['id']))
        worker.call('import_atlas',initial_state=four);phase=copy.deepcopy(worker.latest)
        assert len(phase['bodies'])==4 and phase['paused'] and phase['system_id']!=original['system_id']
        assert phase['dynamics16'] is None
        def refused(name,command,**fields):
            before=physical(worker.latest);answer=worker.call(command,expect_error=True,**fields)
            worker.call('snapshot');assert physical(worker.latest)==before
            report['refusals'].append(dict(name=name,error=answer['message']))
        refused('sixteen guard in four','dynamics16_reading',**helpers.guard(original),body_id=original['bodies'][3]['id'])
        common=physical(phase);points=inventory['legacy_recipe']['magnetic_points'];reads=[]
        for naif,command in [('399','earth_field'),('599','jupiter_field')]:
            body=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:'+naif);point=points[naif]
            fields=dict(latitude_deg=point['latitude'])
            if naif=='399':fields.update(longitude_deg=point['longitude'],altitude_m=point['altitude'])
            else:fields.update(east_longitude_deg=point['longitude'],radius_m=point['radius'],degree=inventory['legacy_recipe']['jovian_degree'])
            reading=worker.call(command,**helpers.guard(phase),body_id=body['id'],**fields)['result']
            assert reading['body_id']==body['id'] and reading['system_id']==phase['system_id']
            assert physical(worker.latest)==common
            reads.append(dict(body=body['reference_id'],command=command,reading=reading))
        earth=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:399')
        assert len(worker.call('solar_reading',**helpers.guard(phase),body_id=earth['id'])['result']['sources'])==3
        assert len(worker.call('solar_tide',**helpers.guard(phase),body_id=earth['id'],offset_m=[6378137.,0.,0.])['result']['sources'])==3
        assert physical(worker.latest)==common
        worker.call('save');saved4=folder/'saved-four';shutil.copytree(storage,saved4)
        report['steps'].append(dict(name='four_common_phase_readonly_fields',bodies=4,magnetic_readings=reads,phase_unchanged=True))
        # Restore the explicit sixteen archive in this temporary namespace only.
        shutil.copy2(saved16/'latest.json',storage/'latest.json');worker.call('load');restored=copy.deepcopy(worker.latest)
        assert restored['bodies']==original['bodies'] and restored['time']==original['time'] and restored['atlas_initial']==sixteen
        assert restored['dynamics16']==original['dynamics16'] and restored['edit_token']!=original['edit_token']
        refused('old sixteen token after restore','dynamics16_reading',**helpers.guard(original),body_id=original['bodies'][3]['id'])
        refused('four guard after sixteen restore','solar_reading',**helpers.guard(phase),body_id=earth['id'])
        target=restored['bodies'][3]
        refused('magnetic provider outside sixteen domain','earth_field',**helpers.guard(restored),body_id=target['id'])
        assert len(worker.call('dynamics16_reading',**helpers.guard(restored),body_id=target['id'])['result']['sources'])==15
        report['steps'].append(dict(name='exact_sixteen_restore',bodies=16,new_token=True,origin_separated=True))
        worker.close();worker=None
        assert all(sha(ROOT/n)==s for n,s in protected.items()) and all(sha(ROOT/n)==s for n,s in sources.items())
        report.update(accepted=True,completed=True,worker_exit=0,owner_app_unchanged=True)
        persist();print(json.dumps(dict(accepted=True,steps=len(report['steps']),refusals=len(report['refusals']),owner_app_unchanged=True)),flush=True)
    except Exception:report['failure']=traceback.format_exc();persist();raise
    finally:
        if worker:
            try:worker.close()
            except Exception:pass


if __name__=='__main__':main()
