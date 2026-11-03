"""Native installed forks: archive, overlay, export and atomic scene restore."""
from pathlib import Path
import copy
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700'
latest=ROOT/'user/sessions/latest.json';saved=latest.read_bytes() if latest.exists() else None
created=[];cases=[];errors=[]
LARGE='--large' in sys.argv

def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=35))
def post(body,path='command'):
    request=urllib.request.Request(BASE+'/api/'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(request,timeout=35))
def guard(p):return {k:p[k] for k in ('system_id','edit_token','revision')}|{'expected_time':p['time'],'frame':p['contract']['frame']}
def physical(p):return {k:copy.deepcopy(p[k]) for k in ('bodies','time','revision','system_id','edit_token','conservation','scientific_generation','instruments','instrument_history')}
def idle(page,condition='true'):
    page.wait_for_function('!pending&&('+condition+')',timeout=35000);time.sleep(.07)
def fill(page,key,value):page.evaluate('document.getElementById('+json.dumps(key)+').value='+json.dumps(str(value)))
def create(page,name):
    fill(page,'branch-name',name);page.locator('#branch-create').click();idle(page)
    p=get('state')['physics'];identifier=p['branches']['active_id']
    assert identifier and p['branches']['branches'][-1]['name']==name
    created.append(identifier);return identifier
def compare(page,a,b):
    page.locator('#branch-first').select_option(a);page.locator('#branch-second').select_option(b)
    page.wait_for_function('!document.getElementById("branch-compare").disabled')
    page.locator('#branch-compare').click();idle(page)
    page.wait_for_function('branchComparison?.first.id==='+json.dumps(a)+'&&branchComparison?.second.id==='+json.dumps(b),timeout=35000)
    return page.evaluate('branchComparison')

socket=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None)
socket.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));serial=0
def lua(code):
    global serial
    serial+=1;socket.send(json.dumps({'topic':serial,'type':'luascript','payload':{'script':code,'return':True}}))
    reply=json.loads(socket.recv(timeout=15));assert reply.get('topic')==serial and '1' in reply.get('payload',{}),reply
    return reply['payload']['1']

atlas=get('atlas/state')
existing={p.name:hashlib.sha256((p/'branch.json').read_bytes()).hexdigest() for p in (ROOT/'user/sessions/branches').glob('*') if p.is_dir() and (p/'branch.json').exists()}
try:
    with Page() as page:
        page.on('pageerror',lambda error:errors.append(str(error)));page.goto(BASE+'/')
        page.wait_for_function('appState!==null');page.locator('#ui-scale').select_option('1')
        for kind in (('fixture',) if LARGE else ('fixture','atlas')):
            post({'command':'atlas'})
            if kind=='atlas':post({'utc':atlas['epoch']['utc']},'atlas/experiment')
            else:post({'command':'enter'});post({'command':'reset','count':128 if LARGE else 32})
            post({'command':'rate','value':1});page.evaluate('updateState()');idle(page)
            p=get('state')['physics'];assert p['scientific_generation']['model_version']=='3.8.0'
            for i in range(16 if LARGE else 2):
                p=get('state')['physics']
                post({'command':'configure_instruments',**guard(p),'instruments_revision':p['instruments']['revision'],
                    'operation':'create','definition':{'name':'Sonda de ramo '+str(i),'mode':'fixed','position_m':[1.7e10+i*1e6,-9e9,3e9]}})
            p=get('state')['physics'];post({'command':'configure_history',**guard(p),'instruments_revision':p['instruments']['revision'],
                'history_revision':p['instrument_history']['revision'],'recording':True,'cadence_wall_s':.25})
            post({'command':'resume'});page.evaluate('updateState()')
            page.wait_for_function('appState.physics.instrument_history.next_sequence>='+str(132 if LARGE else 8),timeout=60000)
            post({'command':'pause'});page.evaluate('updateState()');idle(page)
            if not page.evaluate('document.getElementById("simulation-branches").open'):
                page.locator('#simulation-branches summary').click()
            baseline=get('state')['physics'];pointer=latest.read_bytes() if latest.exists() else None
            checkpoint_save_ms=None
            if LARGE:
                began=time.perf_counter();page.locator('#save').click();idle(page)
                checkpoint_save_ms=(time.perf_counter()-began)*1000
                assert page.locator('#notice').inner_text()=='Sessão salva em user/sessions.'
                assert len(json.loads(latest.read_text())['instrument_history']['samples'])==128
                assert physical(get('state')['physics'])==physical(baseline)
                pointer=latest.read_bytes()
            a=create(page,'QA '+kind+' · Base "A" \\')
            assert physical(get('state')['physics'])==physical(baseline)
            assert (latest.read_bytes() if latest.exists() else None)==pointer
            p=get('state')['physics'];post({'command':'set_mass','body':p['bodies'][0]['id'],'mass':p['bodies'][0]['mass']*1.1})
            page.evaluate('updateState()');idle(page)
            c=create(page,'QA '+kind+' · Massa maior')
            frozen=get('state')['physics'];same=compare(page,a,c)
            assert same['same_physical_instant'] and same['body_differences'][0]['delta_mass_kg']>0
            assert physical(get('state')['physics'])==physical(frozen)
            assert 'mesmo instante físico' in page.locator('#branch-comparison-status').inner_text()
            post({'command':'resume'});page.evaluate('updateState()')
            page.wait_for_function('appState.physics.instrument_history.next_sequence>='+str(frozen['instrument_history']['next_sequence']+8))
            post({'command':'pause'});page.evaluate('updateState()');idle(page)
            b=create(page,'QA '+kind+' · Evolução alterada')
            evolved=get('state')['physics'];different=compare(page,a,b)
            assert not different['same_physical_instant'] and all('delta_position_m' not in row for row in different['body_differences'])
            assert different['second']['parent_id']==c and different['first']['time']<different['second']['time']
            assert physical(get('state')['physics'])==physical(evolved)
            assert 'não são subtraídos' in page.locator('#branch-comparison-status').inner_text()
            assert 'Sem interpolar' in page.locator('#branch-chart-legend').inner_text()
            assert any('state_or_instrument_definition_changed' in row['break_before'] for row in different['second_curves']['samples'])
            page.locator('#branch-export').click();idle(page)
            page.wait_for_function('document.getElementById("notice").textContent.startsWith("Exportado:")')
            export=Path(page.locator('#notice').inner_text().removeprefix('Exportado: '))
            exported=json.loads(export.read_text(encoding='utf8'))
            assert exported['first_curves']==different['first_curves'] and exported['second_curves']==different['second_curves']
            assert physical(get('state')['physics'])==physical(evolved)
            page.evaluate('document.getElementById("branch-chart").scrollIntoView({block:"center"})');time.sleep(.3)
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-branches-'+kind+'.png'],check=True,capture_output=True)
            # Archive restoration rebuilds the native scene with the original
            # phase and frees old overlays before replacing anchors.
            page.locator('#branch-first').select_option(a);page.locator('#branch-load').click();idle(page)
            restored=get('state')['physics']
            assert restored['bodies']==baseline['bodies'] and restored['time']==baseline['time'] and restored['conservation']==baseline['conservation']
            assert restored['instruments']==baseline['instruments'] and restored['instrument_history']==baseline['instrument_history']
            assert restored['branches']['active_id']==a and restored['edit_token']!=baseline['edit_token']
            assert restored['paused'] and (latest.read_bytes() if latest.exists() else None)==pointer
            native_difference=0.
            for body in restored['bodies']:
                actual=lua('return openspace.propertyValue('+json.dumps('Scene.'+body['scene_node']+'.Translation.Position')+')')
                if isinstance(actual,dict):actual=[actual[str(k)] for k in (1,2,3)]
                expected=[v*restored['physical_scale']['length_unit_m'] for v in body['position']]
                if kind=='atlas':
                    matrix=restored['atlas_initial']['j2000_to_render_frame']
                    expected=[math.fsum(row[k]*expected[k] for k in range(3)) for row in matrix]
                native_difference=max(native_difference,max(abs(a-b) for a,b in zip(actual,expected)))
                assert all(abs(v)<float('inf') for v in actual)
            assert native_difference<.01
            before_old=physical(restored)
            try:post({'command':'load_branch',**guard(baseline),'branch_id':b})
            except urllib.error.HTTPError as error:assert error.code==400
            else:raise AssertionError('Pre-switch editor identity accepted')
            assert physical(get('state')['physics'])==before_old
            cases.append({'kind':kind,'same_time_mass_difference_and_different_time_no_subtraction':True,
                'mass_count':len(baseline['bodies']),'probe_count':len(baseline['instruments']['probes']),
                'original_window_samples':baseline['instrument_history']['sample_count'],'native_UI_save_wall_ms':checkpoint_save_ms,
                'fork_compare_export_preserve_phase_and_owner_pointer':True,'original_timestamp_curves_and_intervention_gaps':True,
                'native_restore_phase_reference_history_definitions_and_parent':True,'native_position_max_component_difference_m':native_difference,
                'old_pre_switch_identity_rejected_atomically':True,'export_original_curves_and_generation':True})
finally:
    try:post({'command':'atlas'})
    finally:
        socket.close()
        if saved is None:latest.unlink(missing_ok=True)
        else:latest.write_bytes(saved)
        # Move only archives created by this test to retained evidence; owner
        # branch files remain byte-exact. Restart backend to refresh its catalog.
        target=ROOT/'output/c211-branches-native-fixtures';target.mkdir(exist_ok=True)
        for identifier in created:
            folder=ROOT/'user/sessions/branches'/identifier.split(':')[1]
            if folder.exists():shutil.move(str(folder),str(target/folder.name))
assert get('atlas/state')['epoch']==atlas['epoch'] and not errors
assert (latest.read_bytes() if latest.exists() else None)==saved
assert all(hashlib.sha256((ROOT/'user/sessions/branches'/name/'branch.json').read_bytes()).hexdigest()==checksum for name,checksum in existing.items())
report={'status':'installed3_8_native_branches_verified','browser':'native CEF','cases':cases,'page_errors':errors,
    'owner_pointer_restored':True,'existing_branch_receipts_untouched':True,'atlas_epoch_preserved':True,
    'test_archives_retained_in':'output/c211-branches-native-fixtures','backend_catalog_refresh_required_after_fixture_move':True,
    'scope':'Partial C2-11 branch slice; J2/material tides/resonances/256/10k pending'}
(ROOT/('evidence/branches-ui-large-check.json' if LARGE else 'evidence/branches-ui-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
