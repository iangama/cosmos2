"""CEF product journey: physical/visual controls, exact checkpoints, own worker and source clock."""
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
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];PRODUCT=ROOT/'output/is4-solar-wind-product0.9.0';APP=PRODUCT/'app'
h=SourceFileLoader('is4_product_solar_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
phase=lambda p:{k:copy.deepcopy(p[k]) for k in ['system_id','edit_token','time','revision','bodies','interventions','atlas_initial']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is4-native-wind-product-'+args.label);receipt=ROOT/('evidence/is4-native-wind-product-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve product journey evidence')
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert session.get('is4ParticleProductCandidate')
    folder.mkdir();paths=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[Path(__file__),ROOT/'scripts/cef_page.py',ROOT/'IS-4-VENTO-SOLAR-PRODUTO-CONTRATO.md',ROOT/'IS-4-VENTO-SOLAR-CEF-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths};owner=sha(ROOT/'user/sessions/latest.json')
    base=json.loads((PRODUCT/'base-manifest.json').read_text());assert all(sha(ROOT/n)==v for n,v in base['base_sha256'].items())
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'session':session,'source_sha256':hashes,'checks':[],'captures':[],'page_errors':[]}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda value:report['page_errors'].append(value))
            page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState!==null&&particleState!==null&&!pending')
            if page.evaluate('particleState.active'):
                page.evaluate('particleCommand("leave")');page.wait_for_function('!particlePending&&!particleState.active')
            if page.evaluate('appState.mode==="experiment"'):h.click(page,'#atlas')
            h.click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
            original=phase(h.get('/api/state')['physics'])
            def settled():
                page.wait_for_function('!particlePending&&particleState?.active&&particleState.worker.paused&&particleState.view?.confirmed_phase?.time_s===particleState.worker.experiment.phase.time_s&&!particleState.view.pending_sequence',timeout=25000)
                state=h.get('/api/particles/state');assert not state['error'],state['error'];return state
            def click(selector,check=True):
                page.evaluate('(() => {let p=document.querySelector('+json.dumps(selector)+');for(let a=p?.parentElement;a;a=a.parentElement)if(a.tagName==="DETAILS")a.open=true;})()')
                page.wait_for_function('document.querySelector('+json.dumps(selector)+')&&!document.querySelector('+json.dumps(selector)+').disabled',timeout=25000)
                page.locator(selector).click();page.wait_for_function('!particlePending',timeout=35000)
                if check:assert not page.evaluate('particleError'),page.evaluate('particleError')
            def getguard(state):
                s=state['worker'];e=s['experiment'];return {'worker_id':s['worker_id'],'experiment_id':e['id'],'edit_token':e['edit_token'],'revision':e['revision'],'expected_time_s':e['phase']['time_s'],'frame':s['frame']}
            # A point in the masked HCS band must refuse before creating a worker.
            page.evaluate('document.getElementById("wind-latitude").value=0')
            click('#wind-create',check=False);assert not h.get('/api/particles/state')['active']
            assert page.evaluate('Boolean(particleError)') and phase(h.get('/api/state')['physics'])==original
            report['HCS_refusal']=True
            for target,kind,degree,radius,latitude in [('north','proton',1,1.,30.),('outer-south','electron',-1,5.,-60.),('inner','neutral',1,.3,10.),('south','proton',-1,1.,-30.)]:
                page.locator('#wind-species').select_option(kind);page.locator('#wind-polarity').select_option(str(degree))
                for selector,value in [('#wind-radius',radius),('#wind-latitude',latitude),('#wind-relative-speed',1000000. if kind=='electron' else 100000.)]:page.evaluate('document.querySelector('+json.dumps(selector)+').value='+str(value))
                click('#wind-create');state=settled();assert state['worker']['experiment']['phase']['time_s']==0.
                assert state['worker']['experiment']['degree'] is None and state['worker']['experiment']['model'].startswith('Parker')
                assert 'prescrito' in page.evaluate('document.getElementById("particle-title").textContent')
                for _ in range(8):click('#particle-step');settled()
                page.locator('#particle-rate').select_option('200');page.wait_for_function('!particlePending');settled()
                click('#particle-play');page.wait_for_function('particleState.worker.paused===false');time.sleep(.8)
                began=time.perf_counter();click('#particle-play');pause_ms=(time.perf_counter()-began)*1000;state=settled();assert pause_ms<=500.,pause_ms
                before=copy.deepcopy(state['worker']['experiment']['phase']);sample_time=before['time_s']
                click('#particle-visible');state=settled();assert not state['view']['visible'] and state['worker']['experiment']['phase']==before
                click('#particle-step');state=settled();time.sleep(2.2);state=settled()
                assert not state['view']['visible']
                before=copy.deepcopy(state['worker']['experiment']['phase']);sample_time=before['time_s']
                click('#particle-visible');state=settled();assert state['view']['visible'] and state['worker']['experiment']['phase']==before
                click('#particle-sample');state=settled();field_before=copy.deepcopy(state['sample']['field'])
                click('#particle-gravity');state=settled();assert not state['worker']['experiment']['controls']['gravity'] and state['worker']['experiment']['phase']==before
                click('#particle-sample');state=settled();assert state['sample']['field']==field_before and state['sample']['reference_time_s']==sample_time
                click('#particle-magnetic');state=settled();assert not state['worker']['experiment']['controls']['magnetic'] and state['worker']['experiment']['phase']==before
                click('#particle-magnetic');settled();click('#particle-gravity');state=settled()
                click('#particle-electric');state=settled();assert not state['worker']['experiment']['controls']['electric'] and state['worker']['experiment']['phase']==before
                click('#particle-sample');state=settled();assert state['sample']['field']==field_before and state['sample']['electric_work_J']==0.
                click('#particle-electric');settled()
                oldguard=getguard(state);refusals=0
                for edit in [{'edit_token':'0'*32},{'revision':True},{'expected_time_s':True}]:
                    result=h.post('/api/particles/command',{'command':'advance','steps':1,'guard':{**oldguard,**edit}},400);assert not result['ok'];refusals+=1
                    assert h.get('/api/particles/state')['worker']['experiment']['phase']==before
                h.post('/api/command',{'command':'resume'},400);assert phase(h.get('/api/state')['physics'])==original
                click('#particle-save');saved=settled();saved_phase=copy.deepcopy(saved['worker']['experiment']['phase']);old_token=saved['worker']['experiment']['edit_token'];old_worker=saved['worker']['worker_id']
                click('#particle-step');future=copy.deepcopy(settled()['worker']['experiment']['phase'])
                click('#particle-load');loaded=settled();assert loaded['worker']['experiment']['phase']==saved_phase and loaded['worker']['experiment']['edit_token']!=old_token
                click('#particle-step');state=settled();assert state['worker']['experiment']['phase']==future
                click('#particle-visible');saved=settled();assert not saved['view']['visible']
                click('#particle-save');saved=settled();saved_phase=copy.deepcopy(saved['worker']['experiment']['phase']);saved_unit=saved['view']['physical_unit_m']
                page.evaluate('document.getElementById("particle-branch-name").value="Ramo A"')
                click('#particle-branch-create');state=settled();branch_a=state['branch_parent'];assert branch_a
                click('#particle-visible');settled();click('#particle-step');future=copy.deepcopy(settled()['worker']['experiment']['phase'])
                page.evaluate('document.getElementById("particle-branch-name").value="Ramo B"')
                click('#particle-branch-create');state=settled();branch_b=state['branch_parent'];assert branch_b!=branch_a
                parent=next(b for b in state['branches'] if b['id']==branch_b);assert parent['parent']==branch_a
                page.locator('#particle-branch-select').select_option(branch_a);click('#particle-branch-load');state=settled()
                assert state['worker']['experiment']['phase']==saved_phase and not state['view']['visible'] and state['view']['physical_unit_m']==saved_unit
                click('#particle-step');state=settled();assert state['worker']['experiment']['phase']==future and not state['view']['visible']
                click('#particle-visible');settled()
                exported=page.evaluate('particleCommand("export")');assert exported['ok'];path=Path(exported['result']['export_file']);data=json.loads(path.read_text(encoding='utf-8'))
                assert sha(path)==exported['result']['sha256'] and data['particle']['phase']==future and data['view']['geometry']['phase']==future
                click('#particle-frame');settled()
                if kind!='neutral':
                    for scale in ['1','1.5']:
                        page.locator('#ui-scale').select_option(scale);page.evaluate('document.getElementById("particle-panel").scrollTop=0')
                        page.wait_for_function('document.documentElement.scrollWidth<=innerWidth+1')
                        # CEF paint plus real native frames; no wall-time inference about GPU phases.
                        time.sleep(.25)
                        name='cosmos2-is4-wind-product-'+args.label+'-'+target+'-'+kind+'-'+str(degree)+'-'+str(int(float(scale)*100))+'.png'
                        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
                        report['captures'].append({'path':'evidence/'+name,'sha256':sha(ROOT/'evidence'/name)})
                    page.locator('#ui-scale').select_option('1')
                click('#particle-restart');state=settled();assert state['worker']['experiment']['phase']['time_s']==0. and state['worker']['experiment']['step_index']==0
                click('#particle-leave');page.wait_for_function('!particleState.active')
                assert phase(h.get('/api/state')['physics'])==original
                click('#particle-load-saved');state=settled();assert state['worker']['worker_id']!=old_worker and state['worker']['experiment']['phase']==saved_phase and not state['view']['visible'] and state['view']['physical_unit_m']==saved_unit
                click('#particle-step');state=settled();assert state['worker']['experiment']['phase']==future
                click('#particle-leave');page.wait_for_function('!particleState.active')
                report['checks'].append({'target':target,'kind':kind,'polarity':degree,'radius_AU':radius,'latitude_deg':latitude,'pause_UI_wall_ms':pause_ms,'physical_visual_controls_and_fields_separate':True,
                    'save_load_and_new_worker_future_exact':True,'SI_origin_and_offset_preserved':True,'hidden_receiver_confirmed':True,'view_sealed_and_branch_future_exact':True,'restart_export':True,'guard_refusals':refusals,'orbital_phase_unchanged':True});persist()
            # Inject an update stall in this experiment's own trajectory node.
            click('#wind-create');state=settled();node=state['view']['native_nodes']['trajectory']
            confirmed=copy.deepcopy(state['view']['confirmed_phase']);prop='Scene.'+node+'.Renderable.Enabled'
            h.native('openspace.setPropertyValueSingle('+json.dumps(prop)+',false);return {ready=true}')
            try:
                click('#particle-play');deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    state=h.get('/api/particles/state')
                    if state['error'] and state['worker']['paused']:break
                    time.sleep(.1)
                assert state['worker']['paused'] and '2s' in state['error'],state
                assert state['view']['confirmed_phase']==confirmed
                report['native_stall']={'paused':True,'last_confirmed_preserved':True,'error':state['error']}
            finally:h.native('openspace.setPropertyValueSingle('+json.dumps(prop)+',true);return {ready=true}')
            page.wait_for_function('particleState.worker.paused&&particleState.view.confirmed_phase.time_s===particleState.worker.experiment.phase.time_s',timeout=10000)
            click('#particle-frame');settled();click('#particle-leave');page.wait_for_function('!particleState.active')
            assert phase(h.get('/api/state')['physics'])==original
            page.locator('#ui-scale').select_option('1');h.click(page,'#atlas')
            assert not report['page_errors'],report['page_errors']
        assert all(sha(ROOT/n)==v for n,v in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        assert all(sha(ROOT/n)==v for n,v in base['base_sha256'].items())
        report.update(accepted=True,completed=True,scope='CEF product journey with own worker/native scene: four wind species/hemisphere/polarity/radius cases, guarded physical and visual controls, SI probe, checkpoint/rebind/new worker exact future, restart/export/source clock and PNG100/150. Sealed view preferences, branches and native stall recovery included. Image review/profile separate.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        try:
            state=h.get('/api/particles/state')
            if state['active']:h.post('/api/particles/command',{'command':'leave'})
            with Page() as page:page.locator('#ui-scale').select_option('1')
        except Exception:report['cleanup_failure']=traceback.format_exc()
        persist()
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['checks']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
