"""Native JRM33 point journey: confirmed scene phase, model limits and stale readings."""
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
helper=SourceFileLoader('jupiter_native_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
get,post,click,guard,physical=helper.get,helper.post,helper.click,helper.guard,helper.physical
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-native-jupiter-'+args.label);receipt=ROOT/('evidence/is3-native-jupiter-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native evidence.')
    folder.mkdir()
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('jupiterFieldCandidate')
    paths=sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths += [Path(__file__).resolve(),ROOT/'scripts/cef_page.py',ROOT/'IS-3-JRM33-ORIENTACAO-CONTRATO.md',
        ROOT/'scripts/start-is3-tides-candidate.ps1',ROOT/'scripts/verify-native-solar-tide.py',ROOT/'scripts/verify-native-solar-integration.py']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    baseline=json.loads((ROOT/'evidence/is3-tides-candidate-prepared-20261023.json').read_text(encoding='utf-8'))
    owner=ROOT/'user/sessions/latest.json'
    report={'schema':1,'session':launch,'source_sha256':hashes,'source_archive_sha256':sha(archive),
        'checks':{},'captures':[],'completed':False,'accepted':False,
        'scope':'CEF/API/worker passive JRM33 point binding and native controls. Captures need review; no native field geometry, plasma/Lorentz or final visual acceptance.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();topic=0
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                reply=json.loads(ws.recv(timeout=15));assert reply.get('topic')==topic;return reply['payload']['1']
            def capture(name):
                native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
                deadline=time.monotonic()+5
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<10:
                    if time.monotonic()>deadline:raise TimeoutError('Rendered frames not confirmed.')
                    time.sleep(.05)
                native('return openspace.cosmos2EndFrameCapture()')
                filename='cosmos2-is3-jupiter-'+args.label+'-'+name+'.png'
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/capture-window.ps1'),'-Name',filename],check=True,capture_output=True)
                p=ROOT/'evidence'/filename;report['captures'].append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)})
            errors=[]
            with Page() as page:
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending')
                original_atlas=get('/api/atlas/state')
                click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                first=get('/api/state')['physics'];jupiter=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:599')
                earth=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:399')
                if not page.evaluate('document.getElementById("solar-panel").open'):click(page,'#solar-panel > summary')
                if not page.evaluate('document.getElementById("jupiter-field-panel").open'):click(page,'#jupiter-field-panel > summary')
                page.locator('#solar-body').select_option(jupiter['id'])
                click(page,'#jupiter-field-sample');page.wait_for_function('jupiterFieldReading?.body_id==='+json.dumps(jupiter['id'])+'&&!pending')
                reading=page.evaluate('jupiterFieldReading')
                request={**guard(first),'body_id':jupiter['id'],'radius_m':1.5*71492000.,'latitude_deg':0.,'east_longitude_deg':0.,'degree':13}
                assert post('/api/solar/jupiter-field',request)['ack']['result']==reading
                assert physical(get('/api/state')['physics'])==physical(first)
                assert reading['epoch']['et_tdb_s']==first['atlas_initial']['source']['epoch']['et_tdb_s']
                assert reading['jupiter_center_inertial_m']==[v*first['physical_scale']['length_unit_m'] for v in jupiter['position']]
                assert reading['orientation']['frame']=='IAU_JUPITER' and reading['coefficient_epoch_decimal_year']==2019
                report['checks']['identical_CEF_API_reading_bound_to_current_center_and_epoch']=reading
                for scale in ['1','1.5']:
                    page.locator('#ui-scale').select_option(scale);click(page,'#solar-view-body')
                    actual=native('return {anchor=openspace.navigation.getNavigationState().Anchor,text=openspace.propertyValue("Scene.'+jupiter['label_node']+'.Renderable.Text")}')
                    assert actual['anchor']==jupiter['scene_node'] and actual['text']=='Júpiter',actual
                    page.evaluate('document.getElementById("jupiter-field-reading").scrollIntoView({block:"center"})')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    assert page.evaluate('getComputedStyle(document.getElementById("jupiter-field-reading")).whiteSpace')=='pre-line'
                    assert 'Coeficientes estáticos da época 2019' in page.locator('#jupiter-field-reading').inner_text()
                    capture('scale-'+str(int(float(scale)*100)))
                page.locator('#ui-scale').select_option('1')
                report['checks']['selection_readout_100_150_and_model_scope']=True;persist()
                page.locator('#jupiter-field-degree').select_option('18')
                assert 'Coordenadas ou grau alterados' in page.locator('#jupiter-field-reading').inner_text()
                click(page,'#jupiter-field-sample');page.wait_for_function('jupiterFieldReading?.degree===18&&!pending')
                assert 'exploratório' in page.locator('#jupiter-field-reading').inner_text()
                page.evaluate('const e=document.getElementById("jupiter-field-latitude");e.value="90";e.dispatchEvent(new Event("input",{bubbles:true}))')
                click(page,'#jupiter-field-sample');page.wait_for_function('jupiterFieldReading?.coordinates.latitude_planetocentric_deg===90&&!pending')
                pole=page.evaluate('jupiterFieldReading');assert 0<pole['field_norm_T']<.01
                page.locator('#solar-body').select_option(earth['id'])
                assert page.evaluate('document.getElementById("jupiter-field-sample").disabled')
                assert 'associado a Júpiter' in page.locator('#jupiter-field-reading').inner_text()
                old_earth=post('/api/solar/earth-field',{**guard(first),'body_id':earth['id'],'latitude_deg':0.,'longitude_deg':0.,'altitude_m':0.})['ack']['result']
                assert old_earth['orientation']['frame']=='ITRF93'
                page.locator('#solar-body').select_option(jupiter['id'])
                report['checks']['degree_staleness_pole_wrong_body_and_Earth_regression']=True
                refusals=[]
                for change in [{'year':2020},{'body_id':earth['id']},{'revision':True},{'edit_token':'stale'},
                    {'expected_time':1},{'frame':'SSB'},{'latitude_deg':True},{'latitude_deg':91},
                    {'east_longitude_deg':float('nan')},{'east_longitude_deg':361},{'radius_m':71492000.-1},
                    {'radius_m':21*71492000.},{'degree':30},{'degree':True}]:
                    assert post('/api/solar/jupiter-field',{**request,**change},400)['ok'] is False
                    assert physical(get('/api/state')['physics'])==physical(first)
                    refusals.append(next(iter(change)))
                missing=copy.deepcopy(request);del missing['degree']
                assert post('/api/solar/jupiter-field',missing,400)['ok'] is False;refusals.append('missing_degree')
                report['checks']['HTTP_transactional_refusals']=refusals
                click(page,'#play');page.wait_for_function('appState.physics.time>0&&!pending');time.sleep(.15);click(page,'#play')
                page.wait_for_function('appState.physics.paused&&!pending')
                assert 'Amostra fixa' in page.locator('#jupiter-field-reading').inner_text()
                click(page,'#jupiter-field-sample');page.wait_for_function('jupiterFieldReading?.time===appState.physics.time&&!pending')
                evolved=page.evaluate('jupiterFieldReading');assert evolved['epoch']['et_tdb_s']>reading['epoch']['et_tdb_s']
                click(page,'#save');saved=get('/api/state')['physics'];click(page,'#load');loaded=get('/api/state')['physics']
                assert loaded['bodies']==saved['bodies'] and loaded['restoration']['status']=='same_generation'
                assert 'Amostra fixa' in page.locator('#jupiter-field-reading').inner_text()
                click(page,'#jupiter-field-sample');page.wait_for_function('jupiterFieldReading?.edit_token===appState.physics.edit_token&&!pending')
                report['checks']['evolution_and_exact_restore_mark_old_reading']=True
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.physics?.atlas_initial&&!pending')
                assert page.evaluate('jupiterFieldReading===null') and get('/api/state')['physics']['bodies']==loaded['bodies']
                report['checks']['CEF_reload_clears_derived_field']=True
                for utc,available in [('2030-01-01T00:00:00Z',True),('2030-01-01T00:00:01Z',False)]:
                    click(page,'#atlas');page.wait_for_function('appState.mode==="atlas"&&!pending');post('/api/atlas/epoch',{'utc':utc})
                    page.goto('http://127.0.0.1:4700/');page.wait_for_function('atlasState&&appState?.mode==="atlas"&&!pending')
                    click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                    current=get('/api/state')['physics'];identifier=next(b['id'] for b in current['bodies'] if b['reference_id']=='sol:naif:599')
                    payload={**request,**guard(current),'body_id':identifier}
                    if available:
                        result=post('/api/solar/jupiter-field',payload)['ack']['result']
                        assert result['coefficient_epoch_decimal_year']==2019 and not result['secular_variation_applied']
                    else:
                        assert post('/api/solar/jupiter-field',payload,400)['ok'] is False
                        assert physical(get('/api/state')['physics'])==physical(current)
                report['checks']['static_2019_at_later_scene_epoch_and_application_boundary_refusal']=True
                # Restore the candidate's healthy saved phase before returning to the original Atlas.
                click(page,'#load');restored=get('/api/state')['physics'];assert restored['bodies']==saved['bodies']
                click(page,'#atlas');page.wait_for_function('appState.mode==="atlas"&&!pending')
                post('/api/atlas/epoch',{'utc':original_atlas['epoch']['utc']})
                after=get('/api/atlas/state');assert after['epoch']==original_atlas['epoch'] and after['bodies']==original_atlas['bodies']
                assert not errors,errors;report['checks']['page_errors']=errors
        assert sha(owner)==baseline['owner_pointer_sha256']
        assert all(sha(ROOT/name)==digest for name,digest in baseline['base_source_sha256'].items())
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        report['checks']['healthy_candidate_phase_Atlas_IS12_owner_and_sources_preserved']=True
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
