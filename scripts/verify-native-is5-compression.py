"""Own CEF/native acceptance of the prescribed-density instrument revision."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import hashlib
import json
import math
import subprocess
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from PIL import Image
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is5-compression-product0.17.1/app'
h=SourceFileLoader('compression_native_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def request(route,payload=None,expected=200):
    req=urllib.request.Request(h.BASE+route,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    try:response=urllib.request.urlopen(req,timeout=750)
    except urllib.error.HTTPError as error:
        assert error.code==expected,(error.code,error.read().decode())
        return json.load(error)
    assert response.status==expected,response.status
    return json.load(response)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    path=ROOT/f'evidence/is5-native-compression-{args.label}.json'
    archive=ROOT/f'output/is5-native-compression-{args.label}.zip'
    if path.exists() or archive.exists():raise FileExistsError('Preserve evidence')
    manifest=json.loads((APP.parent/'build-manifest.json').read_text())
    assert manifest['candidate']=='0.17.1' and not manifest['promoted']
    assert all(sha(APP/n)==v for n,v in manifest['files_sha256'].items())
    worker=ROOT/manifest['worker_receipt'];accepted=json.loads(worker.read_text());assert accepted['accepted']
    hashes={**accepted['source_sha256'],**manifest['source_sha256']}
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__),APP.parent/'build-manifest.json',worker,ROOT/'scripts/cef_page.py',
              ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/engine-command.py',ROOT/'scripts/capture-window.ps1']
    hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert session.get('is5CompressionZoneCandidate') and Path(session['serverScript']).resolve()==(APP/'server.py').resolve()
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),
           session=session,owner_sha256=sha(ROOT/'user/sessions/latest.json'),checks=[],refusals=0,captures=[],page_errors=[],
           limits_before_execution=dict(calculation_CEF_wait_ms=750000,busy_rejection_s=2.,cancel_s=6.,cancel_control_visible_s=2.),
           scope='Real CEF form, HTTP, worker, native scene, exact probes and persistence; visual review and performance require separate receipts.')
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def check(name,**extra):r['checks'].append(dict(name=name,**extra));persist();print(json.dumps(r['checks'][-1]),flush=True)
    def zone():return request('/api/solar-zone/state')
    def guard(z):return {k:z['worker'][k] for k in ['worker_id','artifact_id','edit_token','revision']}
    def command(action,**extra):
        payload=dict(command=action,**extra)
        if action not in ['create','load_saved']:payload['guard']=guard(zone())
        return request('/api/solar-zone/command',payload)
    def settled(page,condition='true'):
        page.wait_for_function('!solarZonePending&&!solarZoneState?.busy&&solarZoneState?.active&&!solarZoneCurvePending&&solarZoneCurveId===solarZoneState.worker.artifact_id&&('+condition+')',timeout=750000)
    def field(page,key,value):
        page.evaluate('(()=>{const e=document.getElementById('+json.dumps('zone-'+key)+');e.value='+json.dumps(str(value))+';e.dispatchEvent(new Event("change",{bubbles:true}));})()')
    def recompute(page):
        page.evaluate('document.getElementById("zone-config-holder").open=true')
        h.click(page,'#zone-recompute');settled(page)
        assert not page.evaluate('solarZoneError'),page.evaluate('solarZoneError')
    def capture(page,name,scale='1',chart=None,panel=None,setup=False,reference=False):
        page.locator('#ui-scale').select_option(scale)
        if not setup and not reference:
            page.evaluate('document.getElementById("zone-panel").scrollTop=0;document.getElementById("zone-charts").scrollTop=0')
        if chart:page.evaluate('document.getElementById('+json.dumps('zone-'+chart+'-chart')+').scrollIntoView({block:"start"})')
        if panel:
            page.evaluate('(()=>{const e=document.getElementById('+json.dumps(panel)+');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;e.scrollIntoView({block:"start"});})()')
        time.sleep(.3)
        file=ROOT/f'evidence/cosmos2-is5-compression-{args.label}-{name}.png'
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',file.name],check=True,capture_output=True)
        assert Image.open(file).size==(1920,1080)
        r['captures'].append(dict(path=file.relative_to(ROOT).as_posix(),sha256=sha(file)));persist()
    def stable(z):
        return dict(worker=None if z['worker'] is None else {k:z['worker'][k] for k in ['worker_id','artifact_id','artifact_sha256','edit_token','revision','sample','configuration','source','view','branch_parent']},scene=z['scene'])
    def cancel_from_CEF(page,button,before):
        page.wait_for_function('solarZonePending')
        deadline=time.monotonic()+15
        while not zone()['calculation'] and time.monotonic()<deadline:time.sleep(.025)
        tx=zone()['calculation'];assert tx and tx['cancellable']
        began=time.perf_counter()
        page.wait_for_function('!document.getElementById('+json.dumps(button)+').hidden',timeout=2000)
        visible_s=time.perf_counter()-began
        assert stable(zone())==stable(before)
        began=time.perf_counter();request('/api/solar-zone/command',dict(command='create'),expected=400)
        busy_s=time.perf_counter()-began;assert busy_s<=2.;r['refusals']+=1
        request('/api/solar-zone/cancel',dict(transaction_id='0'*32),expected=400);r['refusals']+=1
        page.locator('#'+button).click();began=time.perf_counter()
        page.wait_for_function('!solarZonePending&&!zoneCancelPending&&!solarZoneState?.busy&&!solarZoneState?.calculation',timeout=6000)
        elapsed=time.perf_counter()-began
        assert elapsed<=6. and stable(zone())==stable(before)
        time.sleep(.5);assert stable(zone())==stable(before)
        return dict(cancel_s=elapsed,control_visible_s=visible_s,busy_rejection_s=busy_s)
    def check_run(run):
        assert run['kind']=='is5_compression_calculated_solar_scenario'
        for name in ['actual','reference']:
            a=run[name];assert len(a['time_s'])==241
            for i in range(241):
                rho,v,e,u,w,q=[a[k][i] for k in ['density_kg_m3','volume_m3','internal_energy_J','internal_energy_J_m3','external_pressure_work_J','non_neutrino_energy_available_J']]
                assert math.isclose(rho*v,a['density_kg_m3'][0]*a['volume_m3'][0],rel_tol=1e-14)
                assert math.isclose(e,v*u,rel_tol=1e-14)
                assert abs(e-a['internal_energy_J'][0]-w-q)/max(a['initial_internal_energy_J'],abs(e),abs(w))<=1e-8
        for key in ['parameters','density_history','include_coulomb','include_screening','density_kg_m3','volume_m3','time_s','baryon_count']:
            assert run['actual'][key]==run['reference'][key],key
    def probes(page,run):
        for i in [0,120,240]:
            command('sample',index=i);settled(page,'solarZoneState.worker.view.selected_index==='+str(i))
            w=zone()['worker']
            for name in ['actual','reference']:
                for key in ['density_kg_m3','volume_m3','internal_energy_J','external_pressure_work_J','non_neutrino_energy_available_J','neutrino_count','nuclear_power_W','external_pressure_power_W']:
                    assert w['sample'][name][key]==run[name][key][i],(name,key,i)
            assert page.evaluate('solarZoneCurves')==run
            assert page.evaluate('solarZoneState.worker.sample')==w['sample']
            text=page.evaluate('document.getElementById("zone-thermodynamic-reading").textContent')
            for key in ['density_kg_m3','volume_m3','baryon_count','external_pressure_work_J','non_neutrino_energy_available_J']:
                assert page.evaluate('zoneNumber(solarZoneState.worker.sample.actual['+json.dumps(key)+'])') in text,key
            assert ' J/m³' in page.evaluate('document.getElementById("zone-probe").textContent')
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.BASE+'/')
            page.wait_for_function('solarZoneState!==null&&!pending&&!solarZonePending')
            if zone()['active']:command('leave')
            if request('/api/state')['mode']=='experiment':request('/api/command',dict(command='atlas'))
            page.wait_for_function('appState?.mode==="atlas"&&!pending');h.click(page,'#copy-solar')
            page.wait_for_function('!pending&&appState?.physics?.paused&&appState.physics.bodies.length===4',timeout=70000)
            orbital=h.phase(request('/api/state')['physics'])
            page.evaluate('document.getElementById("zone-setup").open=true')
            initial=page.evaluate('zoneConfiguration()')
            assert initial['parameters']==dict(temperature_K=15e6,density_kg_m3=150000.,hydrogen_fraction=.34,catalyst_fraction=.01,catalyst_seed='n14',duration_s=31557600000.,volume_m3=1.)
            assert initial['density_history']==dict(kind='exponential',ratio=1.05)
            for scale in ['1','1.5']:
                capture(page,'initial-form-'+('100' if scale=='1' else '150'),scale,panel='zone-history',setup=True)
            page.locator('#ui-scale').select_option('1');before=zone();h.click(page,'#zone-create')
            metrics=cancel_from_CEF(page,'zone-cancel-setup',before)
            assert h.phase(request('/api/state')['physics'])==orbital
            check('CEF_initial_creation_cancel_visible_and_responsive_no_scene_or_late_commit',**metrics)
            h.click(page,'#zone-create');settled(page)
            first=command('get_result')['result'];check_run(first)
            assert first['configuration']==initial and first['actual']==first['reference']
            assert first['actual']['external_pressure_work_J'][-1]>0 and zone()['scene']['confirmed']
            assert page.evaluate('document.querySelectorAll("#zone-channels input").length')==18
            probes(page,first)
            for scale in ['1','1.5']:
                capture(page,'compression-work-'+('100' if scale=='1' else '150'),scale,chart='work')
                capture(page,'probe-'+('100' if scale=='1' else '150'),scale,panel='zone-probe',chart='energy')
            check('Default_exact_configuration_241knots_positive_work_global_units_and_exact0_120_240probes')
            page.locator('#ui-scale').select_option('1')
            command('set_view',view=dict(selected_index=120,visible=dict(composition=False,energy=True,neutrinos=False,reference=True)));settled(page,'solarZoneState.worker.view.selected_index===120')
            before=zone();field(page,'ratio',.98)
            page.evaluate('document.getElementById("zone-config-holder").open=true');h.click(page,'#zone-recompute')
            metrics=cancel_from_CEF(page,'zone-cancel',before)
            assert command('get_result')['result']==first and h.phase(request('/api/state')['physics'])==orbital
            check('CEF_recalculation_cancel_preserves_exact_actor_scene_source_view_probe_and_curves',**metrics)
            field(page,'ratio',.95);field(page,'volume',2.5);page.locator('#zone-seed').select_option('o16');recompute(page)
            expansion=command('get_result')['result'];check_run(expansion)
            assert expansion['configuration']['density_history']==dict(kind='exponential',ratio=.95)
            assert expansion['configuration']['parameters']['volume_m3']==2.5 and expansion['configuration']['parameters']['catalyst_seed']=='o16'
            assert expansion['actual']['external_pressure_work_J'][-1]<0
            probes(page,expansion);capture(page,'expansion-negative-work-150','1.5',chart='work')
            page.locator('#ui-scale').select_option('1');page.locator('#zone-history').select_option('constant')
            assert page.evaluate('document.getElementById("zone-ratio").disabled')
            page.locator('#zone-coulomb').set_checked(False)
            assert page.evaluate('document.getElementById("zone-screening").disabled&&!document.getElementById("zone-screening").checked')
            recompute(page);constant=command('get_result')['result'];check_run(constant)
            assert constant['configuration']['density_history']==dict(kind='constant')
            assert set(constant['actual']['external_pressure_work_J'])=={0.} and set(constant['actual']['Coulomb_internal_energy_J_m3'])=={0.}
            page.locator('#zone-history').select_option('cycle');field(page,'ratio',1.03)
            page.locator('#zone-coulomb').set_checked(True)
            assert not page.evaluate('document.getElementById("zone-screening").checked')
            recompute(page);cycle=command('get_result')['result'];check_run(cycle)
            assert cycle['configuration']['density_history']==dict(kind='cycle',ratio=1.03)
            assert cycle['actual']['density_kg_m3'][-1]==cycle['actual']['density_kg_m3'][0]
            assert max(cycle['actual']['Coulomb_internal_energy_J_m3'])<0 and all(set(row)=={1.} for row in cycle['actual']['screening_factors'])
            command('sample',index=120);settled(page,'solarZoneState.worker.view.selected_index===120')
            capture(page,'cycle-density-volume-100',chart='density',panel='zone-thermodynamic-reading')
            check('Expansion_global_volume2p5_negative_work_constant_ideal_limit_and_cycle_EOS_without_screening')
            page.locator('#zone-screening').set_checked(True);page.locator('#zone-weak').set_checked(False);recompute(page)
            gated=command('get_result')['result'];check_run(gated)
            assert gated['actual']['neutrino_count']==[0.]*241 and gated['reference']['neutrino_count'][-1]>0
            assert gated['reference']!=gated['actual'] and gated['configuration']['include_screening']
            for i,c in enumerate(gated['actual']['channels']):
                if c in ['pp','n13beta','o15beta','be7ec','b8beta2a','f17beta']:assert all(row[i]==0 for row in gated['actual']['event_rates_m3_s'])
            probes(page,gated)
            capture(page,'weak-off-reference-150','1.5',chart='neutrinos',panel='zone-reference-reading')
            page.locator('#ui-scale').select_option('1')
            before=zone()
            for kind in ['old_mode','wrong_bool','invalid_ratio','trajectory_guard','EOS_mismatch','old_decay','extra_field']:
                bad=copy.deepcopy(gated['configuration'])
                if kind=='old_mode':bad['mode']='isochoric'
                elif kind=='wrong_bool':bad['parameters']['temperature_K']=True
                elif kind=='invalid_ratio':bad['density_history']['ratio']=1.3
                elif kind=='trajectory_guard':bad['parameters']['density_kg_m3']=300000.;bad['density_history']=dict(kind='exponential',ratio=1.2)
                elif kind=='EOS_mismatch':bad['include_coulomb']=False
                elif kind=='old_decay':bad['decay_basis']='reaclib_wc12'
                else:bad['unknown']=1
                began=time.perf_counter();request('/api/solar-zone/command',dict(command='configure',configuration=bad,guard=guard(zone())),expected=400)
                assert time.perf_counter()-began<=2. and stable(zone())==stable(before),kind;r['refusals']+=1
            request('/api/solar-zone/command',dict(command='sample',index=1,guard={**guard(zone()),'revision':True}),expected=400);r['refusals']+=1
            command('set_view',view=dict(selected_index=120,visible=dict(composition=True,energy=True,neutrinos=True,reference=True)))
            command('save');saved=zone();branch=command('branch_create',name='Ciclo · fraca desligada')['result']['branch']['id']
            command('sample',index=240);child=command('branch_create',name='Final do ciclo')['result']['branch']['id']
            assert next(b for b in zone()['worker']['branches'] if b['id']==child)['parent']==branch
            command('branch_load',branch_id=branch);assert zone()['worker']['view']==saved['worker']['view']
            old=zone()['worker']['worker_id'];command('new_worker')
            assert zone()['worker']['worker_id']!=old and command('get_result')['result']==gated
            export=command('export')['result'];record=json.loads(Path(export['path']).read_text(encoding='utf-8'))
            assert record['run']==gated and record['record_sha256']==export['record_sha256']
            checkpoint=APP.parent/'solar-zone-checkpoints/saved.json';original=checkpoint.read_bytes()
            try:
                for kind in ['seal','old_type']:
                    bad=json.loads(original)
                    if kind=='seal':bad['record_sha256']='0'*64
                    else:bad['kind']='is5_coulomb_solar_checkpoint'
                    checkpoint.write_text(json.dumps(bad),encoding='utf-8');before=zone()
                    request('/api/solar-zone/command',dict(command='load',guard=guard(before)),expected=400)
                    assert stable(zone())==stable(before);r['refusals']+=1
            finally:checkpoint.write_bytes(original)
            check('Weak_gate_reference_neutrinos_strict_refusals_corrupt_old_checkpoints_branches_new_process_and_export')
            settled(page);held=stable(zone());h.click(page,'#open-stellar-reference')
            page.wait_for_function('!document.getElementById("stellar-reference-panel").hidden&&stellarReferenceState.sample?.model==="GS98"')
            capture(page,'B23-over-paused-zone-150','1.5',reference=True)
            assert stable(zone())==held and h.phase(request('/api/state')['physics'])==orbital
            page.locator('#stellar-reference-close').click();page.locator('#ui-scale').select_option('1')
            capture(page,'controls-100',panel='zone-config-fields');capture(page,'limits-150','1.5',panel='zone-provenance')
            archived=zone()['worker']['source'];node=zone()['scene']['node'];command('leave')
            assert not h.native('return {exists=openspace.hasSceneGraphNode('+json.dumps(node)+')}')['exists']
            assert h.phase(request('/api/state')['physics'])==orbital
            request('/api/command',dict(command='resume'));time.sleep(.35);request('/api/command',dict(command='pause'))
            moved=h.phase(request('/api/state')['physics']);assert moved['time']>orbital['time']
            command('load_saved');settled(page)
            assert zone()['worker']['source']==archived and h.phase(request('/api/state')['physics'])==moved
            check('B23_read_only_over_paused_zone_native_cleanup_return_orbit_and_archived_source_restore')
            assert not r['page_errors'],r['page_errors']
            assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
            assert all(sha(ROOT/n)==v for n,v in hashes.items())
            r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            state=zone()
            if state['calculation']:request('/api/solar-zone/cancel',dict(transaction_id=state['calculation']['transaction_id']))
            if zone()['active']:command('leave')
            with Page() as page:
                page.locator('#ui-scale').select_option('1');page.evaluate('document.getElementById("stellar-reference-panel").hidden=true')
            if request('/api/state')['mode']=='experiment':request('/api/command',dict(command='atlas'))
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        try:h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception as error:r['shutdown_response']=str(error)
        persist()
    print(json.dumps(dict(accepted=r['accepted'],checks=len(r['checks']),captures=len(r['captures']),refusals=r['refusals'],failure=r.get('failure'),cleanup_failure=r.get('cleanup_failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
