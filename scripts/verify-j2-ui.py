"""Installed native J2 form, exterior maps, saved history and branch hypotheses."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import subprocess
import time
import urllib.request

from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700'
pointer=ROOT/'user/sessions/latest.json';saved=pointer.read_bytes() if pointer.exists() else None
created=[];cases=[];errors=[]

def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=35))
def post(body,path='command'):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=35))
def physics():return get('state')['physics']
def guard(p):return {k:p[k] for k in ('system_id','edit_token','revision')}|{'expected_time':p['time'],'frame':p['contract']['frame']}
def phase(p):return {k:p[k] for k in ('time','revision','system_id','edit_token','conservation','gravity_effects','instruments','instrument_history','bodies')}
def idle(page):page.wait_for_function('!pending',timeout=35000);time.sleep(.07)
def refresh(page):page.evaluate('updateState()');idle(page)
def fill(page,key,value):page.evaluate('document.getElementById('+json.dumps(key)+').value='+json.dumps(str(value)))
def archive(page,name):
    fill(page,'branch-name',name);page.locator('#branch-create').click();idle(page)
    result=physics()['branches']['active_id'];assert result;created.append(result);return result

atlas=get('atlas/state')
existing={p.name:hashlib.sha256((p/'branch.json').read_bytes()).hexdigest() for p in (ROOT/'user/sessions/branches').glob('*') if p.is_dir() and (p/'branch.json').exists()}
try:
    with Page() as page:
        page.on('pageerror',lambda error:errors.append(str(error)));page.goto(BASE+'/');page.wait_for_function('appState!==null')
        page.locator('#ui-scale').select_option('1')
        for kind in ('fixture','atlas'):
            post({'command':'atlas'})
            if kind=='atlas':post({'utc':atlas['epoch']['utc']},'atlas/experiment')
            else:post({'command':'enter'});post({'command':'reset','count':32})
            post({'command':'rate','value':1});refresh(page);p=physics()
            assert p['scientific_generation']['model_version']=='3.9.1' and not p['gravity_effects']
            source=next((b for b in p['bodies'] if b.get('reference_id')=='sol:naif:399'),p['bodies'][0]);radius=6e6 if kind=='atlas' else 1e8
            page.evaluate('document.getElementById("gravity-harmonics").open=true')
            page.locator('#j2-body').select_option(source['id']);page.locator('#prepare-j2').click();idle(page)
            page.locator('#j2-active').set_checked(True)
            fill(page,'j2-coefficient',.002);fill(page,'j2-radius',radius);fill(page,'j2-provenance','Parâmetros sintéticos QA · não valor observado')
            for i,value in enumerate([.3,-.4,.5]):fill(page,'j2-axis-'+str(i),value)
            before=physics();page.locator('#apply-j2').click();idle(page);p=physics()
            assert p['revision']==before['revision']+1 and source['id'] in p['gravity_effects']
            assert p['time']==before['time'] and all(a['position']==b['position'] and a['velocity']==b['velocity'] for a,b in zip(before['bodies'],p['bodies']))
            assert p['conservation']['angular_momentum_error_normalized'] is None and 'J2' in page.locator('#unit-note').inner_text()
            if kind=='atlas':assert 'J2 e deformações de maré' not in p['contract']['excluded_influences']
            for i in range(2):
                p=physics();post({'command':'configure_instruments',**guard(p),'instruments_revision':p['instruments']['revision'],
                    'operation':'create','definition':{'name':'J2 '+str(i),'mode':'follow','body_id':source['id'],
                    'offset_m':[radius*2+i*1000,0.,0.],'exclude_followed_source':False}})
            p=physics();post({'command':'configure_history',**guard(p),'instruments_revision':p['instruments']['revision'],
                'history_revision':p['instrument_history']['revision'],'recording':True,'cadence_wall_s':.25})
            post({'command':'resume'});refresh(page);page.wait_for_function('appState.physics.instrument_history.sample_count>=8')
            post({'command':'pause'});refresh(page)
            assert page.evaluate('document.getElementById("apply-j2").disabled')
            p=physics();reading=post({'command':'sample_instruments',**guard(p),'instruments_revision':p['instruments']['revision']})['ack']['result']
            assert all(row['available'] for row in reading['readings']) and any('j2' in row for row in reading['source_snapshot_si'])
            p=physics();cfg=copy.deepcopy(p['field_layers']['settings']);cfg.update(center_mode='follow',body_id=source['id'],
                shell_radius_m=radius*2,shell_count=48,cut_half_width_m=radius*.5,cut_offset_m=radius*2,
                cut_orientation_deg=[0.,0.,0.],cut_resolution=17)
            post({'command':'configure_fields',**guard(p),'fields_revision':p['field_layers']['revision'],'settings':cfg})
            p=physics();post({'command':'sample_fields',**guard(p),'fields_revision':p['field_layers']['revision']});refresh(page)
            assert get('state')['fields_preview']['sample_count']==337
            recorded=get('instruments/history');assert recorded['sample_count']>=8
            frozen=phase(physics());page.locator('#save').click();idle(page)
            assert page.locator('#notice').inner_text()=='Sessão salva em user/sessions.'
            manifest=json.loads(pointer.read_text());assert manifest['gravity_effects'] and any('j2' in source for source in manifest['instrument_history']['samples'][0]['reading']['source_snapshot_si'])
            assert phase(physics())==frozen
            page.evaluate('document.getElementById("simulation-branches").open=true')
            a=archive(page,'QA J2 '+kind);page.locator('#prepare-j2').click();idle(page)
            page.locator('#j2-active').set_checked(False);page.locator('#apply-j2').click();idle(page)
            assert not physics()['gravity_effects'];b=archive(page,'QA monopolo '+kind)
            page.locator('#branch-first').select_option(a);page.locator('#branch-second').select_option(b)
            page.wait_for_function('!document.getElementById("branch-compare").disabled');page.locator('#branch-compare').click();idle(page)
            page.wait_for_function('branchComparison?.gravity_definition_changed===true')
            assert 'Hipóteses J2 distintas' in page.locator('#branch-comparison-status').inner_text()
            page.locator('#branch-first').select_option(a);page.locator('#branch-load').click();idle(page)
            restored=physics();assert restored['gravity_effects']==frozen['gravity_effects'] and restored['bodies']==frozen['bodies']
            assert restored['conservation']==frozen['conservation'] and restored['instrument_history']==frozen['instrument_history']
            # Native saved-session load also reconnects forces, without needing
            # to recreate definitions or silently changing the symmetry axis.
            page.locator('#load').click();idle(page);assert physics()['gravity_effects']==frozen['gravity_effects']
            page.locator('#prepare-j2').click();idle(page)
            page.evaluate('document.getElementById("gravity-harmonics").scrollIntoView({block:"start"})')
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-j2-'+kind+'.png'],check=True,capture_output=True)
            cases.append({'kind':kind,'explicit_source_axis_radius_provenance_form':True,'no_automatic_planet_activation':True,
                'toggle_preserves_phase_and_registers_energy_intervention':True,'native_exterior_map_samples':337,
                'live_history_includes_J2_sources':True,'stale_form_blocked':True,
                'save_load_and_branch_restore_phase_model_history_reference_exact':True,
                'branch_J2_vs_monopole_hypotheses_labeled':True})
finally:
    try:post({'command':'atlas'})
    finally:
        if saved is None:pointer.unlink(missing_ok=True)
        else:pointer.write_bytes(saved)
        target=ROOT/'output/c211-j2-native-fixtures';target.mkdir(exist_ok=True)
        for identifier in created:
            folder=ROOT/'user/sessions/branches'/identifier.split(':')[1]
            if folder.exists():shutil.move(str(folder),str(target/folder.name))
assert get('atlas/state')['epoch']==atlas['epoch'] and not errors,errors
assert (pointer.read_bytes() if pointer.exists() else None)==saved
assert all(hashlib.sha256((ROOT/'user/sessions/branches'/name/'branch.json').read_bytes()).hexdigest()==sha for name,sha in existing.items())
report={'status':'installed3_9_native_exterior_J2_verified','cases':cases,'page_errors':errors,
        'owner_pointer_and_branch_files_preserved':True,'atlas_epoch_preserved':True,'catalog_refresh_required':True,
        'scope':'Exterior fixed-axis J2 only; no spin torque/material tides/full C2-11 acceptance'}
(ROOT/'evidence/j2-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
