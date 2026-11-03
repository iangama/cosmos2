"""Short real-J collector checks with complete refusal snapshots and unchanged criteria."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import traceback
import urllib.error
import urllib.request
import zipfile
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
J=ROOT/'output/c212-em-viewport-product'
sys.path.insert(0,str(J/'em'))
from em_experiment import Experiment
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def get(path):return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+path,timeout=10))


def command(family,name,**fields):
    s=get('/api/'+family+'/state')['state']
    guard={} if name in ('pause','snapshot') else {k:s[k] for k in ['system_id','edit_token','revision','frame']}|{'expected_time_s':s['time_s']}
    request=urllib.request.Request('http://127.0.0.1:4700/api/'+family+'/command',
        data=json.dumps({'command':name,**guard,**fields}).encode(),headers={'Content-Type':'application/json'})
    try:result=json.load(urllib.request.urlopen(request,timeout=25))
    except urllib.error.HTTPError as error:raise RuntimeError(str(error.code)+' '+error.read().decode('utf-8',errors='replace')) from error
    assert not result.get('display'),result
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    parser.add_argument('--family',choices=['both','potential','cloud'],default='both');args=parser.parse_args()
    if not 1<=len(args.label)<=18 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/em-native-preflight-'+args.label);receipt=ROOT/('evidence/em-native-preflight-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve evidence.')
    folder.mkdir()
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert launch.get('emViewportCandidate') and Path(launch['serverScript']).resolve()==(J/'app/server.py').resolve()
    prior=json.loads((ROOT/'evidence/native-em128-c212jpotb.json').read_text())
    cloud=json.loads((ROOT/'evidence/native-emcloud-c212jsrca.json').read_text())
    immutable={p:h for p,h in prior['configuration_sha256'].items() if p.startswith('output/c212-em-viewport-product/')}
    assert all(sha(ROOT/p)==h for p,h in immutable.items())
    assert sha(Path(launch['runtime'])/'bin/OpenSpace.exe')==prior['engine_sha256']
    paths=[p for family in ['app','em','em-cloud'] for p in (J/family).rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix in ['.py','.json','.js','.html','.css','.cpp','.dll','.txt']]
    paths += [Path(__file__).resolve(),ROOT/'scripts/cef_page.py',ROOT/'scripts/collect-em-potential-gpu-memory-diagnostic.ps1',
        ROOT/'scripts/collect-em-cloud-gpu-memory-diagnostic.ps1',ROOT/'C2-12-DIAGNOSTICO-J-20261022.md']
    owner=ROOT/'user/sessions/latest.json';owner_sha=sha(owner)
    paths += [p for storage in ['c212-em-worker/product','c212-em-cloud-worker/product'] for p in (J/storage).glob('ui-phase*')]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources-and-before-UI-state.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    name='diagnostic-'+args.label
    Experiment.from_payload(prior['fixture']).save(J/'c212-em-worker/product'/(name+'.json'))
    cloud_fixture=ROOT/Path(cloud['fixture_checkpoint']);assert sha(cloud_fixture)==cloud['fixture_sha256']
    shutil.copy2(cloud_fixture,J/'c212-em-cloud-worker/product'/(name+'.json'))
    report={'schema':1,'families_requested':args.family,'session':launch,'source_sha256':hashes,'checks':{},'runs':[],
        'completed':False,'accepted':False,'scope':'Three WDDM samples per route and deliberately mismatched worker expectation on real J. Criteria unchanged; diagnostic readiness only, no sustained frame/rate/latency acceptance or retrospective explanation of c212jpotb.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();active=None
    def collect(family,route,worker,potential=True,electric=True,expected_refusal=False):
        label=args.label+'-'+family+'-'+str(route)
        script=ROOT/('scripts/collect-em-'+('potential' if family=='em' else 'cloud')+'-gpu-memory-diagnostic.ps1')
        arguments=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),'-Label',label,
            '-Samples','3','-ExpectedMode',family.replace('-',''),'-ExpectedWorker',worker]
        if family=='em':arguments += ['-ExpectedPotential','visible' if potential else 'hidden','-ExpectedElectric','visible' if electric else 'hidden']
        run=subprocess.run(arguments,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=50)
        (folder/(label+'-collector.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
        refused=sorted((ROOT/'output').glob('em-scenario-refusal-'+label+'-*.json'))
        result={'family':family,'route':route,'collector_sha256':sha(script),'returncode':run.returncode,
            'expected_refusal':expected_refusal,'refusal_receipts':[p.relative_to(ROOT).as_posix() for p in refused]}
        report['runs'].append(result);persist()
        if expected_refusal:
            assert run.returncode!=0 and len(refused)==1,result
            details=json.loads(refused[0].read_text(encoding='utf-8-sig'))
            assert details['snapshot'] is not None and details['failed_predicates']==['expected_worker'],details['failed_predicates']
            assert details['session']['app']==launch['app'] and details['collector_sha256']==sha(script)
            result['failed_predicates']=details['failed_predicates'];result['snapshot_preserved']=True
        else:
            assert run.returncode==0 and not refused,result
            gpu=ROOT/('evidence/gpu-memory-'+label+'.json');raw=json.loads(gpu.read_text(encoding='utf-8-sig'))
            assert len(raw['samples'])==3 and raw['collector_sha256']==sha(script)
            result['GPU_receipt']=gpu.relative_to(ROOT).as_posix();result['GPU_receipt_sha256']=sha(gpu)
        persist()
    try:
        with Page() as page:
            if args.family in ('both','potential'):
                page.goto('http://127.0.0.1:4700/em.html');active='em'
                page.wait_for_function('state&&nativeState?.active&&!pending',timeout=30000)
                page.locator('#interface-scale').select_option('1');page.locator('[data-panel="layers"]').click()
                for route,(potential,electric) in enumerate([(True,True),(False,True),(True,False)],1):
                    command('em','pause');command('em','load',file=name)
                    for i in range(64):
                        current=get('/api/em/state')['state']
                        command('em','set_timestep',dt_s=.0005 if i%2==0 else .001,expected_dt_s=current['experiment']['dt_s'])
                    page.wait_for_function('state.experiment.mode==="mutual_electrostatic"&&state.experiment.system.ids.length===128&&!pending')
                    page.locator('#measure').click();page.wait_for_function('!pending&&map?.samples.length===97',timeout=30000)
                    command('em','set_visual',changes={'electric_visible':electric,'magnetic_visible':True})
                    command('em','configure_potential',changes={'visible':potential,'count_axis':33,'levels_V':None})
                    command('em','sample_potential')
                    if route==1:collect('em','refusal','running',expected_refusal=True)
                    command('em','resume');collect('em',route,'running',potential,electric);command('em','pause')
                report['checks']['potential_three_routes_and_real_refusal_snapshot']=True;persist()
                page.goto('http://127.0.0.1:4700/');active=None
            if args.family in ('both','cloud'):
                page.goto('http://127.0.0.1:4700/em-cloud.html');active='em-cloud'
                page.wait_for_function('state&&native?.active&&!pending',timeout=30000)
                page.locator('#interface-scale').select_option('1');page.locator('[data-cloud-panel="layers"]').click()
                for route,(particles,magnetic) in enumerate([(True,True),(False,True),(True,False)],1):
                    command('em-cloud','pause');command('em-cloud','load',file=name);command('em-cloud','set_rate',value=1.)
                    command('em-cloud','set_visual',changes={'cloud_visible':particles,'electric_visible':True,'magnetic_visible':magnetic})
                    points=[]
                    for k in range(48):
                        z=1-2*(k+.5)/48;a=k*math.pi*(3-math.sqrt(5));rad=math.sqrt(1-z*z)
                        points.append([3*rad*math.cos(a),3*rad*math.sin(a),3*z])
                    points += [[a,b,0] for a in range(-3,4) for b in range(-3,4)]
                    command('em-cloud','field_map',points_m=points)
                    if route==1:collect('em-cloud','refusal','running',expected_refusal=True)
                    command('em-cloud','resume');collect('em-cloud',route,'running');command('em-cloud','pause')
                report['checks']['cloud_three_routes_and_real_refusal_snapshot']=True
                page.goto('http://127.0.0.1:4700/');active=None
        assert sha(owner)==owner_sha and all(sha(ROOT/p)==h for p,h in immutable.items())
        report['checks']['J_sources_runtime_and_owner_preserved']=True
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if active:
            try:
                command(active,'pause')
                with Page() as page:page.goto('http://127.0.0.1:4700/')
            except Exception as error:report['cleanup_error']=str(error)
        persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
