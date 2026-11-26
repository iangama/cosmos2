"""Check tide dispatch, phase guards and historical checkpoint compatibility."""
from pathlib import Path
import argparse
import copy
import datetime as dt
from decimal import Decimal, localcontext
import hashlib
import json
import shutil
import subprocess
import sys
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-tides-product/app'
sys.path.insert(0,str(APP))
from solar_catalog import states
from solar_import import prepare


class Worker:
    def __init__(self,folder):
        self.errors=(folder/'worker-stderr.log').open('w',encoding='utf-8')
        self.process=subprocess.Popen([sys.executable,'-u',str(APP/'worker.py'),'--storage',str(folder)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.errors,text=True,encoding='utf-8')
        self.serial=0;self.latest=None
        assert json.loads(self.process.stdout.readline())['type']=='ready'
        self.latest=json.loads(self.process.stdout.readline())

    def call(self,name,expect_error=False,**fields):
        self.serial+=1
        self.process.stdin.write(json.dumps({'command':name,'id':self.serial,**fields})+'\n');self.process.stdin.flush()
        while True:
            line=self.process.stdout.readline()
            if not line:raise RuntimeError('Worker stopped unexpectedly.')
            response=json.loads(line)
            if response['type']=='snapshot':self.latest=response
            if response.get('id')==self.serial and response['type'] in ('ack','error'):
                assert (response['type']=='error')==expect_error,response
                return response

    def close(self):
        if self.process.poll() is None:self.call('quit')
        self.process.wait(timeout=10);self.errors.close()


def guard(p):
    return {k:p[k] for k in ['system_id','edit_token','revision']}|{'expected_time':p['time'],'frame':p['contract']['frame']}


def physical(p):
    return {k:copy.deepcopy(p[k]) for k in ['system_id','edit_token','revision','time','bodies','atlas_initial','interventions']}


def independent(snapshot,center,offset):
    rows={}
    with localcontext() as context:
        context.prec=70;D=Decimal.from_float
        length=D(snapshot['physical_scale']['length_unit_m']);gm_unit=D(snapshot['physical_scale']['nominal_GM_unit_m3_s2'])
        for b in snapshot['bodies']:
            if b['id']==center['id']:continue
            r=[(D(b['position'][k])-D(center['position'][k]))*length for k in range(3)]
            q=[r[k]-D(float(offset[k])) for k in range(3)]
            radius=sum(v*v for v in r).sqrt();local=sum(v*v for v in q).sqrt();gm=D(b['mass'])*gm_unit
            rows[b['id']]=[float(gm*(q[k]/local**3-r[k]/radius**3)) for k in range(3)]
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-tide-worker-'+args.label);receipt=ROOT/('evidence/is3-tide-worker-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve previous evidence.')
    folder.mkdir();storage=folder/'sessions';storage.mkdir()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    paths=sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)+[Path(__file__).resolve(),ROOT/'IS-3-MARES-VALIDACAO-PREVIA.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    prepared=json.loads((ROOT/'evidence/is3-tides-candidate-prepared-20261023.json').read_text(encoding='utf-8'))
    owner=ROOT/'user/sessions/latest.json';owner_before=sha(owner)
    report={'schema':1,'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source_sha256':hashes,
            'limits_before_execution':{'absolute_component_m_s2':2e-15,'relative_component':1e-10},
            'completed':False,'accepted':False,'checks':{},'scope':'New isolated worker dispatch and checkpoint compatibility; no native UI or performance acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();worker=None
    try:
        worker=Worker(storage)
        catalog=states('2026-10-11T12:00:00Z');initial=prepare(catalog)
        worker.call('import_atlas',initial_state=initial)
        first=copy.deepcopy(worker.latest);assert first['paused'] and first['time']==0
        readings=[]
        for body in first['bodies']:
            request={**guard(first),'body_id':body['id'],'offset_m':[6378137.,0,0]}
            before=physical(worker.latest)
            result=worker.call('solar_tide',**request)['result']
            assert physical(worker.latest)==before
            oracle=independent(first,body,request['offset_m']);error=0.
            for row in result['sources']:
                for actual,expected in zip(row['exact_m_s2'],oracle[row['id']]):
                    error=max(error,abs(actual-expected));assert abs(actual-expected)<=2e-15
                    if abs(expected)>1e-12:assert abs(actual-expected)/abs(expected)<=1e-10
            assert result['scientific_generation']==first['scientific_generation']
            assert result['epoch_et_tdb_s']==initial['source']['epoch']['et_tdb_s']
            readings.append({'id':body['reference_id'],'max_component_error_m_s2':error})
        report['checks']['four_body_readings_against_Decimal']=readings
        request={**guard(first),'body_id':first['bodies'][1]['id'],'offset_m':[6378137.,0,0]}
        variants=[]
        for key in request:
            bad=copy.deepcopy(request);del bad[key];variants.append(('missing_'+key,bad))
        for key,value in [('unknown',1),('system_id','stale'),('edit_token','stale'),('revision',1),('revision',True),
            ('expected_time',1),('expected_time',True),('frame','SSB'),('body_id','unknown'),
            ('offset_m',[True,0,0]),('offset_m',[float('nan'),0,0]),('offset_m',[1e13,0,0])]:
            bad=copy.deepcopy(request);bad[key]=value;variants.append((key+'_'+str(value),bad))
        for label,payload in variants:
            before=physical(worker.latest);worker.call('solar_tide',expect_error=True,**payload)
            worker.call('snapshot');assert physical(worker.latest)==before,label
        report['checks']['transactional_worker_refusals']=[label for label,_ in variants]
        worker.call('save');saved=copy.deepcopy(worker.latest)
        worker.call('resume');time.sleep(.1);worker.call('pause')
        evolved=copy.deepcopy(worker.latest);assert evolved['time']>0
        worker.call('solar_tide',expect_error=True,**request)
        worker.call('snapshot');assert physical(worker.latest)==physical(evolved)
        request_evolved={**guard(evolved),'body_id':evolved['bodies'][1]['id'],'offset_m':[0,0,0]}
        zero=worker.call('solar_tide',**request_evolved)['result'];assert zero['exact_m_s2']==[0.,0.,0.]
        worker.call('load');loaded=copy.deepcopy(worker.latest)
        assert loaded['bodies']==saved['bodies'] and loaded['atlas_initial']==initial and loaded['restoration']['status']=='same_generation'
        assert loaded['edit_token']!=saved['edit_token']
        worker.call('solar_tide',expect_error=True,**request)
        fresh=worker.call('solar_tide',**{**guard(loaded),'body_id':loaded['bodies'][1]['id'],'offset_m':[6378137.,0,0]})['result']
        assert fresh['edit_token']==loaded['edit_token']
        report['checks']['evolution_restore_and_stale_token_refusals']=True
        worker.close();worker=None

        # Read a real older IS12 checkpoint from a copied namespace, preserving the original.
        old=ROOT/'output/is12-solar-product/gravity-sessions';copied=folder/'older-is12';copied.mkdir()
        manifest=json.loads((old/'latest.json').read_text(encoding='utf-8'))
        for name in ['latest.json',manifest['binary']]:shutil.copy2(old/name,copied/name)
        old_checkpoint_hash=sha(old/'latest.json')
        worker=Worker(copied);worker.call('load');older=copy.deepcopy(worker.latest)
        assert older['restoration']['status']=='changed_generation'
        assert older['atlas_initial']==manifest['atlas_initial']
        result=worker.call('solar_tide',**{**guard(older),'body_id':older['bodies'][1]['id'],'offset_m':[6378137.,0,0]})['result']
        assert len(result['sources'])==3 and sha(old/'latest.json')==old_checkpoint_hash
        report['checks']['older_IS12_checkpoint_read_without_rewriting_source']=True
        assert all(sha(ROOT/name)==digest for name,digest in prepared['base_source_sha256'].items())
        assert sha(owner)==owner_before==prepared['owner_pointer_sha256']
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        report['checks']['audited_IS12_and_owner_preserved']=True
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if worker is not None:worker.close()
        persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
