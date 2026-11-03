"""Native scene Earth-field journey, including time linkage and unavailable domains."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import subprocess
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-tides-product/app'
helper=SourceFileLoader('earth_native_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
get,post,click,guard,physical=helper.get,helper.post,helper.click,helper.guard,helper.physical
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-native-earth-'+args.label);receipt=ROOT/('evidence/is3-native-earth-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native field evidence.')
    folder.mkdir()
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('earthFieldCandidate')
    paths=sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths += [Path(__file__).resolve(),ROOT/'scripts/cef_page.py',ROOT/'IS-3-IGRF-CONTRATO.md',ROOT/'scripts/start-is3-tides-candidate.ps1']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    baseline=json.loads((ROOT/'evidence/is3-tides-candidate-prepared-20261023.json').read_text(encoding='utf-8'))
    owner=ROOT/'user/sessions/latest.json'
    report={'schema':1,'session':launch,'source_sha256':hashes,'source_archive_sha256':sha(archive),
        'checks':{},'captures':[],'completed':False,'accepted':False,
        'scope':'Actual CEF/API/worker scene-field point binding, guards and checkpoints. No native field geometry, Lorentz dynamics, external magnetosphere or final visual acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();topic=0
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                result=json.loads(ws.recv(timeout=15));assert result.get('topic')==topic;return result['payload']['1']

            def capture(name):
                native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
                deadline=time.monotonic()+5
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<10:
                    if time.monotonic()>deadline:raise TimeoutError('Rendered frames not confirmed.')
                    time.sleep(.05)
                native('return openspace.cosmos2EndFrameCapture()')
                filename='cosmos2-is3-earth-'+args.label+'-'+name+'.png'
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/capture-window.ps1'),'-Name',filename],check=True,capture_output=True)
                p=ROOT/'evidence'/filename;report['captures'].append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)})

            errors=[]
            with Page() as page:
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending')
                original_atlas=get('/api/atlas/state')
                click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                first=get('/api/state')['physics'];earth=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:399')
                if not page.evaluate('document.getElementById("solar-panel").open'):click(page,'#solar-panel > summary')
                if not page.evaluate('document.getElementById("earth-field-panel").open'):click(page,'#earth-field-panel > summary')
                page.locator('#solar-body').select_option(earth['id'])
                click(page,'#earth-field-sample');page.wait_for_function('earthFieldReading?.body_id==='+json.dumps(earth['id'])+'&&!pending')
                reading=page.evaluate('earthFieldReading')
                request={**guard(first),'body_id':earth['id'],'latitude_deg':-23.55,'longitude_deg':-46.63,'altitude_m':1000}
                assert post('/api/solar/earth-field',request)['ack']['result']==reading
                assert physical(get('/api/state')['physics'])==physical(first)
                assert reading['epoch']['et_tdb_s']==first['atlas_initial']['source']['epoch']['et_tdb_s']
                assert reading['earth_center_inertial_m']==[v*first['physical_scale']['length_unit_m'] for v in earth['position']]
                assert reading['orientation']['frame']=='ITRF93' and reading['orientation']['status']=='EOP_supported_region'
                report['checks']['same_CEF_API_reading_bound_to_evolved_center_and_epoch']=reading
                for scale in ['1','1.5']:
                    page.locator('#ui-scale').select_option(scale);click(page,'#solar-view-body')
                    assert native('return {anchor=openspace.navigation.getNavigationState().Anchor}')['anchor']==earth['scene_node']
                    page.evaluate('document.getElementById("earth-field-reading").scrollIntoView({block:"center"})')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    assert 'IGRF2025' in page.locator('#earth-field-reading').inner_text()
                    capture('scale-'+str(int(float(scale)*100)))
                page.locator('#ui-scale').select_option('1')
                report['checks']['real_selection_readout_100_150']=True
                persist()
                # Coordinates are editable while the old reading keeps its explicit sample identity.
                page.evaluate('const e=document.getElementById("earth-field-latitude");e.value="90";e.dispatchEvent(new Event("input",{bubbles:true}))')
                assert 'Coordenadas alteradas' in page.locator('#earth-field-reading').inner_text()
                click(page,'#earth-field-sample');page.wait_for_function('earthFieldReading?.coordinates.latitude_deg===90&&!pending')
                pole=page.evaluate('earthFieldReading');assert all(abs(v)<1e-3 for v in pole['field_J2000_T'])
                jupiter=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:599')
                page.locator('#solar-body').select_option(jupiter['id'])
                assert page.evaluate('document.getElementById("earth-field-sample").disabled')
                assert 'associado à Terra' in page.locator('#earth-field-reading').inner_text()
                page.locator('#solar-body').select_option(earth['id'])
                report['checks']['coordinate_staleness_pole_and_wrong_body_UI']=True
                refusals=[]
                for change in [{'year':2020},{'body_id':jupiter['id']},{'revision':1},{'edit_token':'stale'},
                    {'expected_time':1},{'frame':'SSB'},{'latitude_deg':True},{'latitude_deg':91},
                    {'longitude_deg':float('nan')},{'altitude_m':1000001}]:
                    assert post('/api/solar/earth-field',{**request,**change},400)['ok'] is False
                    assert physical(get('/api/state')['physics'])==physical(first)
                    refusals.append(next(iter(change)))
                report['checks']['API_transactional_refusals']=refusals
                click(page,'#play');page.wait_for_function('appState.physics.time>0&&!pending');time.sleep(.15);click(page,'#play')
                page.wait_for_function('appState.physics.paused&&!pending')
                assert 'Amostra fixa' in page.locator('#earth-field-reading').inner_text()
                click(page,'#earth-field-sample');page.wait_for_function('earthFieldReading?.time===appState.physics.time&&!pending')
                evolved=page.evaluate('earthFieldReading');assert evolved['epoch']['et_tdb_s']>reading['epoch']['et_tdb_s']
                click(page,'#save');saved=get('/api/state')['physics'];click(page,'#load');loaded=get('/api/state')['physics']
                assert loaded['bodies']==saved['bodies'] and loaded['restoration']['status']=='same_generation'
                assert 'Amostra fixa' in page.locator('#earth-field-reading').inner_text()
                click(page,'#earth-field-sample');page.wait_for_function('earthFieldReading?.edit_token===appState.physics.edit_token&&!pending')
                report['checks']['evolution_and_checkpoint_invalidate_derived_reading']=True
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.physics?.atlas_initial&&!pending')
                assert page.evaluate('earthFieldReading===null')
                assert get('/api/state')['physics']['bodies']==loaded['bodies']
                report['checks']['CEF_reload_clears_derived_field']=True

                for utc,prediction in [('2026-11-10T12:00:00Z',True),('2027-01-19T00:00:00Z',None)]:
                    click(page,'#atlas');page.wait_for_function('appState.mode==="atlas"&&!pending')
                    post('/api/atlas/epoch',{'utc':utc})
                    page.goto('http://127.0.0.1:4700/');page.wait_for_function('atlasState&&appState?.mode==="atlas"&&!pending')
                    click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                    current=get('/api/state')['physics'];identifier=next(b['id'] for b in current['bodies'] if b['reference_id']=='sol:naif:399')
                    payload={**guard(current),'body_id':identifier,'latitude_deg':0,'longitude_deg':0,'altitude_m':0}
                    if prediction:
                        result=post('/api/solar/earth-field',payload)['ack']['result']
                        assert result['orientation']['status']=='prediction'
                    else:
                        assert post('/api/solar/earth-field',payload,400)['ok'] is False
                        assert physical(get('/api/state')['physics'])==physical(current)
                report['checks']['predicted_orientation_label_and_outside_coverage_refusal']=True
                click(page,'#atlas');page.wait_for_function('appState.mode==="atlas"&&!pending')
                post('/api/atlas/epoch',{'utc':original_atlas['epoch']['utc']})
                after=get('/api/atlas/state');assert after['epoch']==original_atlas['epoch'] and after['bodies']==original_atlas['bodies']
                assert not errors,errors;report['checks']['page_errors']=errors
        assert sha(owner)==baseline['owner_pointer_sha256']
        assert all(sha(ROOT/name)==digest for name,digest in baseline['base_source_sha256'].items())
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        report['checks']['Atlas_IS12_and_owner_preserved']=True
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
