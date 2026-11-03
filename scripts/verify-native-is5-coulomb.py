"""Own0.15.0 CEF/native acceptance; long calculations use explicit bounded waits."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import hashlib
import json
import subprocess
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from PIL import Image
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is5-coulomb-zone-product0.15.0/app'
h=SourceFileLoader('coulomb_native_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def post(route,payload,expected=200):
    req=urllib.request.Request(h.BASE+route,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    try:response=urllib.request.urlopen(req,timeout=390)
    except urllib.error.HTTPError as error:
        assert error.code==expected,(error.code,error.read().decode())
        return json.load(error)
    assert response.status==expected,response.status
    return json.load(response)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    path=ROOT/f'evidence/is5-native-coulomb-{args.label}.json'
    archive=ROOT/f'output/is5-native-coulomb-{args.label}.zip'
    if path.exists() or archive.exists():raise FileExistsError('Preserve native evidence')
    worker=ROOT/'evidence/is5-coulomb-worker-artifact-20261029b.json'
    accepted=json.loads(worker.read_text(encoding='utf-8'));assert accepted['accepted']
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve()==(APP/'server.py').resolve()
    assert session.get('is5CoulombZoneCandidate') is True
    hashes={**accepted['source_sha256'],worker.relative_to(ROOT).as_posix():sha(worker)}
    for p in [*[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts],Path(__file__),
              ROOT/'IS-5-COULOMB-PRODUTO-CONTRATO.md',ROOT/'scripts/prepare-is5-coulomb-product.py',
              ROOT/'scripts/launch-is5-coulomb-candidate.py']:
        hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),
           checks=[],refusals=0,captures=[],page_errors=[],limits_before_execution=dict(calculation_CEF_wait_ms=380000,busy_rejection_s=2.))
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def zone():return h.get('/api/solar-zone/state')
    def guard(q):return {k:q['worker'][k] for k in ['worker_id','artifact_id','edit_token','revision']}
    def command(action,**extra):
        request=dict(command=action,**extra)
        if action not in ['create','load_saved']:request['guard']=guard(zone())
        return post('/api/solar-zone/command',request)
    def settled(page,condition='true'):
        page.wait_for_function('!solarZonePending&&solarZoneState?.active&&solarZoneCurveId===solarZoneState.worker.artifact_id&&('+condition+')',timeout=380000)
    def capture(page,name,scale='1',section='coulomb'):
        page.locator('#ui-scale').select_option(scale)
        page.evaluate('document.getElementById("zone-panel").scrollTop=0;document.getElementById("zone-charts").scrollTop=0')
        if section=='coulomb':page.evaluate('document.getElementById("zone-coulomb-chart").scrollIntoView({block:"center"});document.getElementById("zone-probe").scrollIntoView({block:"start"})')
        elif section=='factors':page.evaluate('document.getElementById("zone-screening-table").parentElement.open=true;document.getElementById("zone-screening-reading").scrollIntoView({block:"start"})')
        elif section=='controls':page.evaluate('document.getElementById("zone-config-form").parentElement.open=true;document.getElementById("zone-coulomb").scrollIntoView({block:"center"})')
        elif section=='cno':page.evaluate('document.getElementById("zone-cno-chart").scrollIntoView({block:"center"});document.getElementById("zone-panel").scrollTop=580')
        time.sleep(.3)
        file=ROOT/f'evidence/cosmos2-is5-coulomb-{args.label}-{name}.png'
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',file.name],check=True,capture_output=True)
        pixels=Image.open(file).convert('RGB').crop((700,460,1200,650))
        count=sum(red>225 and 140<green<210 and 50<blue<130 for red,green,blue in pixels.get_flattened_data())
        assert count>12000,(file.name,count)
        r['captures'].append(dict(path=file.relative_to(ROOT).as_posix(),sha256=sha(file),marker_pixels=count))
        persist()
    def check(name):r['checks'].append(name);persist();print(json.dumps(dict(check=name,passed=True)),flush=True)
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.BASE+'/')
            page.wait_for_function('solarZoneState!==null&&!pending&&!solarZonePending')
            if zone()['active']:command('leave')
            if h.get('/api/state')['mode']=='experiment':post('/api/command',dict(command='atlas'))
            page.wait_for_function('appState?.mode==="atlas"&&!pending');h.click(page,'#copy-solar')
            page.wait_for_function('!pending&&appState?.physics?.paused&&appState?.physics?.bodies.length===4',timeout=70000)
            orbital=h.phase(h.get('/api/state')['physics'])
            page.evaluate('document.getElementById("zone-setup").open=true');page.locator('#zone-create').click()
            page.wait_for_function('solarZonePending',timeout=20000)
            deadline=time.monotonic()+10
            while not zone()['busy'] and time.monotonic()<deadline:time.sleep(.025)
            assert zone()['busy']
            began=time.perf_counter();post('/api/solar-zone/command',dict(command='create'),expected=400)
            r['busy_rejection_s']=time.perf_counter()-began;assert r['busy_rejection_s']<=2.;r['refusals']+=1
            assert 'Calculando' in page.evaluate('document.getElementById("zone-setup-status").textContent')
            settled(page)
            first=command('get_result')['result'];assert first['actual']==first['reference']
            assert first['configuration']['include_coulomb'] and first['configuration']['include_screening']
            assert page.evaluate('document.querySelectorAll("#zone-channels input").length')==18
            assert page.evaluate('document.querySelectorAll(".zone-factor-row").length')==18
            assert h.phase(h.get('/api/state')['physics'])==orbital and zone()['scene']['confirmed']
            check('CEF default creation, responsive state/busy admission,18channels/factors, archived marker and frozen orbit')
            page.evaluate('document.getElementById("zone-config-form").parentElement.open=true')
            page.locator('#zone-coulomb').set_checked(False)
            assert page.evaluate('document.getElementById("zone-screening").disabled&&!document.getElementById("zone-screening").checked')
            page.locator('#zone-recompute').click();settled(page,'!solarZoneState.worker.configuration.include_coulomb')
            ideal=command('get_result')['result'];assert set(ideal['actual']['Coulomb_internal_energy_J_m3'])=={0.}
            assert all(set(row)=={1.} for row in ideal['actual']['screening_factors'])
            capture(page,'ideal-controls-150','1.5','controls')
            page.locator('#ui-scale').select_option('1');page.locator('#zone-coulomb').set_checked(True)
            assert not page.evaluate('document.getElementById("zone-screening").checked')
            page.locator('#zone-recompute').click();settled(page,'solarZoneState.worker.configuration.include_coulomb&&!solarZoneState.worker.configuration.include_screening')
            reservoir=command('get_result')['result'];assert max(reservoir['actual']['Coulomb_internal_energy_J_m3'])<0
            assert all(set(row)=={1.} for row in reservoir['actual']['screening_factors'])
            capture(page,'EOS-only-100')
            page.locator('#zone-screening').set_checked(True);page.locator('#zone-seed').select_option('o16')
            page.locator('#zone-recompute').click();settled(page,'solarZoneState.worker.configuration.include_screening&&solarZoneState.worker.configuration.parameters.catalyst_seed==="o16"')
            command('sample',index=240);settled(page,'solarZoneState.worker.view.selected_index===240')
            full=command('get_result')['result'];probe=zone()['worker']['sample']['actual']
            assert probe['Coulomb_internal_energy_J_m3']<0 and probe['screening_factors']['pp']>1
            assert probe['screening_factors']['be7ec']==probe['screening_factors']['f17beta']==1.
            assert 'Correlação de Coulomb:' in page.evaluate('document.getElementById("zone-probe").textContent')
            assert probe['mass_fractions']['o16']>0 and probe['mass_fractions']['f17']>0 and probe['mass_fractions']['o17']>0
            for scale in ['1','1.5']:
                tag='100' if scale=='1' else '150'
                capture(page,'Coulomb-'+tag,scale);capture(page,'factors-'+tag,scale,'factors');capture(page,'CNO-'+tag,scale,'cno')
            check('Separate EOS/screening controls, negative Coulomb reservoir,18factors and O16 CNO through the form')
            page.locator('#ui-scale').select_option('1');page.evaluate('document.getElementById("zone-config-form").parentElement.open=true')
            page.locator('#zone-channel-n15pg').set_checked(False);page.locator('#zone-recompute').click()
            settled(page,'!solarZoneState.worker.configuration.channel_switches.n15pg')
            command('sample',index=120);changed=command('get_result')['result']
            assert changed['actual']['event_rates_m3_s'][-1][14]==0 and changed['reference']==full['reference']
            before=zone();oldguard=guard(before)
            for alteration in ['mode','flags','old_decay','type']:
                bad=copy.deepcopy(changed['configuration'])
                if alteration=='mode':bad['mode']='prescribed'
                elif alteration=='flags':bad['include_coulomb']=False
                elif alteration=='old_decay':bad['decay_basis']='reaclib_wc12'
                else:bad['parameters']['temperature_K']=True
                post('/api/solar-zone/command',dict(command='configure',configuration=bad,guard=guard(zone())),expected=400)
                assert zone()['worker']['artifact_id']==before['worker']['artifact_id'] and zone()['scene']==before['scene'];r['refusals']+=1
            post('/api/solar-zone/command',dict(command='sample',index=1,guard={**oldguard,'revision':True}),expected=400);r['refusals']+=1
            held=zone()['worker']['artifact_sha256']
            command('set_view',view=dict(selected_index=120,visible=dict(composition=False,energy=False,neutrinos=True,reference=False)))
            page.wait_for_function('document.getElementById("zone-coulomb-chart").hidden&&document.getElementById("zone-cno-chart").hidden')
            assert zone()['worker']['artifact_sha256']==held
            command('set_view',view=dict(selected_index=120,visible=dict(composition=True,energy=True,neutrinos=False,reference=True)))
            command('save');saved_state=zone();branch=command('branch_create',name='Coulomb · captura N15 desligada')['result']['branch']['id']
            command('sample',index=240);second=command('branch_create',name='Mesmo cenário · instante final')['result']['branch']['id']
            assert next(v for v in zone()['worker']['branches'] if v['id']==second)['parent']==branch
            command('branch_load',branch_id=branch);assert zone()['worker']['view']==saved_state['worker']['view']
            oldworker=zone()['worker']['worker_id'];command('new_worker')
            assert zone()['worker']['worker_id']!=oldworker and command('get_result')['result']==changed
            exported=command('export')['result'];record=json.loads(Path(exported['path']).read_text(encoding='utf-8'))
            assert record['run']==changed and record['record_sha256']==exported['record_sha256']
            check('Channel gate/reference, invalid models/types, independent visibility, sealed save/branches/newprocess/export')
            saved=APP.parent/'solar-zone-checkpoints/saved.json';original=saved.read_bytes()
            bad=json.loads(original);bad['record_sha256']='0'*64;before=zone()
            try:
                saved.write_text(json.dumps(bad),encoding='utf-8')
                post('/api/solar-zone/command',dict(command='load',guard=guard(before)),expected=400)
                assert zone()['worker']['artifact_id']==before['worker']['artifact_id'] and zone()['scene']==before['scene'];r['refusals']+=1
            finally:saved.write_bytes(original)
            archived=zone()['worker']['source'];node=zone()['scene']['node'];command('leave')
            assert not h.native('return {exists=openspace.hasSceneGraphNode('+json.dumps(node)+')}')['exists']
            assert h.phase(h.get('/api/state')['physics'])==orbital
            post('/api/command',dict(command='resume'));time.sleep(.35);post('/api/command',dict(command='pause'))
            moved=h.phase(h.get('/api/state')['physics']);assert moved['time']>orbital['time']
            command('load_saved');assert zone()['worker']['source']==archived and h.phase(h.get('/api/state')['physics'])==moved
            settled(page);capture(page,'archived-source-150','1.5','top')
            assert not r['page_errors'],r['page_errors']
            assert all(sha(ROOT/n)==v for n,v in hashes.items())
            check('Corrupt load preserves actor/scene; later orbital phase preserves archived source; native nodes clean up')
            r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            if zone()['active']:command('leave')
            with Page() as page:page.locator('#ui-scale').select_option('1')
            if h.get('/api/state')['mode']=='experiment':post('/api/command',dict(command='atlas'))
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        persist()
        r['normal_shutdown_requested']=True
        try:h.native('openspace.toggleShutdown();return {requested=true}')
        except Exception as error:r['shutdown_response']=str(error)
        persist()
    print(json.dumps(dict(accepted=r['accepted'],checks=len(r['checks']),captures=len(r['captures']),refusals=r['refusals'],
                         failure=r.get('failure'),cleanup_failure=r.get('cleanup_failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
