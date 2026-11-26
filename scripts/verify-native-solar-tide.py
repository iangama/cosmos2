"""Real CEF tide API/UI journey in the isolated IS3 candidate."""
from pathlib import Path
import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import subprocess
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-tides-product/app'
base=SourceFileLoader('solar_native_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
get,post,click,guard=base.get,base.post,base.click,base.guard
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def physical(p):
    return {k:copy.deepcopy(p[k]) for k in ['system_id','edit_token','revision','time','bodies','atlas_initial','interventions']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-native-tide-'+args.label);receipt=ROOT/('evidence/is3-native-tide-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native evidence.')
    folder.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert session.get('solarTidesCandidate') and session['storage'].replace('\\','/').endswith('/output/is3-tides-product/gravity-sessions')
    paths=sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths += [Path(__file__).resolve(),ROOT/'scripts/cef_page.py',ROOT/'scripts/start-is3-tides-candidate.ps1',ROOT/'IS-3-MARES-VALIDACAO-PREVIA.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    archive=folder/'executed-sources-and-recipe.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    preparation=json.loads((ROOT/'evidence/is3-tides-candidate-prepared-20261023.json').read_text(encoding='utf-8'))
    owner=ROOT/'user/sessions/latest.json'
    report={'schema':1,'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'session':session,
        'source_sha256':hashes,'source_archive_sha256':sha(archive),'checks':{},'captures':[],
        'completed':False,'accepted':False,'scope':'Dedicated tide API/worker/CEF/native journey. Captures require review; no ocean/deformation/EM/nuclear integration acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();topic=0
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                reply=json.loads(ws.recv(timeout=15));assert reply.get('topic')==topic,reply
                return reply['payload']['1']

            def capture(name):
                # Confirm subsequent rendered frames, not just changed scene properties.
                native('openspace.cosmos2BeginFrameCapture(240);return {ready=true}')
                until=time.monotonic()+5
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<10:
                    if time.monotonic()>until:raise TimeoutError('No subsequent rendered frames.')
                    time.sleep(.05)
                native('return openspace.cosmos2EndFrameCapture()')
                filename='cosmos2-is3-tide-'+args.label+'-'+name+'.png'
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/capture-window.ps1'),'-Name',filename],check=True,capture_output=True)
                p=ROOT/'evidence'/filename
                report['captures'].append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'rendered_frames_after_action':10})

            errors=[]
            with Page() as page:
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(base.BASE+'/')
                page.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending')
                atlas=get('/api/atlas/state')
                before=get('/api/state')['physics']
                bad={'system_id':'missing','edit_token':'missing','revision':0,'expected_time':0,
                     'frame':'initial_subset_barycenter_inertial_axes_J2000','body_id':'missing','offset_m':[0,0,0]}
                assert post('/api/solar/tide',bad,400)['ok'] is False
                assert get('/api/state')['physics']==before and get('/api/state')['mode']=='atlas'
                click(page,'#copy-solar')
                page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                first=get('/api/state')['physics'];earth=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:399')
                if not page.evaluate('document.getElementById("solar-panel").open'):click(page,'#solar-panel > summary')
                if not page.evaluate('document.getElementById("solar-tide-panel").open'):click(page,'#solar-tide-panel > summary')
                page.locator('#solar-body').select_option(earth['id'])
                click(page,'#solar-tide-sample')
                page.wait_for_function('solarTideReading?.body_id==='+json.dumps(earth['id'])+'&&!pending')
                reading=page.evaluate('solarTideReading')
                request={**guard(first),'body_id':earth['id'],'offset_m':[6378137.,0,0]}
                api=post('/api/solar/tide',request)['ack']['result']
                assert api==reading
                assert physical(get('/api/state')['physics'])==physical(first)
                assert len(reading['sources'])==3 and earth['id'] in reading['excluded_source_ids']
                assert all(earth['id']!=r['id'] for r in reading['sources'])
                for k in range(3):assert reading['exact_m_s2'][k]==math.fsum(r['exact_m_s2'][k] for r in reading['sources'])
                assert page.locator('[data-solar-tide-source]').count()==3
                report['checks']['CEF_API_same_passive_reading']=reading
                persist()

                for scale in ['1','1.5']:
                    page.locator('#ui-scale').select_option(scale)
                    click(page,'#solar-view-body')
                    status=native('return {anchor=openspace.navigation.getNavigationState().Anchor,text=openspace.propertyValue("Scene.'+earth['label_node']+'.Renderable.Text"),enabled=openspace.propertyValue("Scene.'+earth['label_node']+'.Renderable.Enabled")}')
                    assert status['anchor']==earth['scene_node'] and status['text']=='Terra' and status['enabled'],status
                    page.evaluate('document.getElementById("solar-tide-reading").scrollIntoView({block:"center"})')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    assert page.evaluate('getComputedStyle(document.getElementById("solar-tide-reading")).whiteSpace')=='pre-line'
                    capture('scale-'+str(int(float(scale)*100)))
                page.locator('#ui-scale').select_option('1')
                report['checks']['native_selection_and_readable_100_150_layout']=True

                page.evaluate('const e=document.getElementById("solar-tide-offset-0");e.value="1000";e.dispatchEvent(new Event("input",{bubbles:true}))')
                assert 'Deslocamento alterado' in page.locator('#solar-tide-reading').inner_text()
                assert page.evaluate('solarTideReading')==reading
                assert physical(get('/api/state')['physics'])==physical(first)
                for k in range(3):page.evaluate('document.getElementById("solar-tide-offset-'+str(k)+'").value="0"')
                click(page,'#solar-tide-sample')
                page.wait_for_function('solarTideReading?.offset_m.every(v=>v===0)&&!pending')
                assert page.evaluate('solarTideReading.exact_m_s2')==[0,0,0]
                report['checks']['changed_input_marked_and_zero_offset_exact']=True

                refusals=[]
                for change in [{'revision':1},{'edit_token':'stale'},{'expected_time':1},{'frame':'SSB'},
                               {'body_id':'missing'},{'offset_m':[True,0,0]},{'offset_m':[float('nan'),0,0]},
                               {'unknown':1}]:
                    assert post('/api/solar/tide',{**request,**change},400)['ok'] is False
                    assert physical(get('/api/state')['physics'])==physical(first)
                    refusals.append(next(iter(change)))
                missing=copy.deepcopy(request);del missing['frame']
                assert post('/api/solar/tide',missing,400)['ok'] is False
                report['checks']['API_transactional_refusals']=refusals+['missing_frame']
                click(page,'#play');page.wait_for_function('appState.physics.time>0&&!pending')
                time.sleep(.15);click(page,'#play');page.wait_for_function('appState.physics.paused&&!pending')
                page.wait_for_function('document.getElementById("solar-tide-reading").textContent.includes("Amostra fixa")')
                evolved=get('/api/state')['physics'];assert evolved['time']>0
                click(page,'#save');saved=get('/api/state')['physics']
                click(page,'#load');loaded=get('/api/state')['physics']
                assert loaded['bodies']==saved['bodies'] and loaded['atlas_initial']==saved['atlas_initial']
                assert loaded['restoration']['status']=='same_generation' and loaded['edit_token']!=saved['edit_token']
                assert 'Amostra fixa' in page.locator('#solar-tide-reading').inner_text()
                click(page,'#solar-tide-sample')
                page.wait_for_function('solarTideReading?.edit_token===appState.physics.edit_token&&!pending')
                report['checks']['evolution_checkpoint_and_fresh_read_after_restore']=True
                page.goto(base.BASE+'/');page.wait_for_function('appState?.physics?.atlas_initial&&!pending')
                assert page.evaluate('solarTideReading===null')
                assert get('/api/state')['physics']['bodies']==loaded['bodies']
                report['checks']['derived_reading_cleared_on_CEF_reload']=True
                click(page,'#atlas');page.wait_for_function('appState.mode==="atlas"&&!pending')
                after=get('/api/atlas/state');assert after['epoch']==atlas['epoch'] and after['bodies']==atlas['bodies']
                report['checks']['reference_Atlas_preserved']=True
                assert not errors,errors;report['checks']['page_errors']=errors
        assert sha(owner)==preparation['owner_pointer_sha256']
        assert all(sha(ROOT/name)==digest for name,digest in preparation['base_source_sha256'].items())
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        report['checks']['IS12_and_owner_preserved']=True
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
