"""Real CEF time controls, frozen layers, HTTP refusals and save/restore."""
from pathlib import Path
from copy import deepcopy
import hashlib
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];CANDIDATE=ROOT/'output/c212-em-time-product'
STORAGE=CANDIDATE/'c212-em-worker/product'
sys.path[:0]=[str(CANDIDATE/'em'),str(CANDIDATE/'app')]
from em_experiment import Experiment
from em_timing import execution_generation
import em_time_laboratory as adjunct

parser=argparse.ArgumentParser();parser.add_argument('--label',default='initial');args=parser.parse_args()
assert args.label.isalnum() and len(args.label)<=20
label_suffix='' if args.label=='initial' else '-'+args.label
destination=ROOT/f'evidence/em-time-native-ui{label_suffix}-check.json';assert not destination.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(session['serverScript']).resolve()==(CANDIDATE/'app/server.py').resolve()
owner=(ROOT/'user/sessions/latest.json').read_bytes();errors=[];refusals=[];pauses=[]
def current():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))
def stable():
    s=current()['state']
    return {k:s[k]for k in ('system_id','edit_token','revision','experiment','editor','time_preferences','paused')}
def request(name,**parameters):
    s=current()['state'];guard={k:s[k]for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
    req=urllib.request.Request('http://127.0.0.1:4700/api/em/command',data=json.dumps({'command':name,**guard,**parameters}).encode(),headers={'Content-Type':'application/json'})
    try:return json.load(urllib.request.urlopen(req,timeout=20))
    except urllib.error.HTTPError as error:return {'HTTP_error':error.code,'response':json.load(error)}
def idle(page):page.wait_for_function('state&&nativeState?.confirmation?.state==="accepted"&&!pending&&!nativeState.error&&nativeState.confirmation.metadata.time_s===state.time_s',timeout=30000)
def snapshot(page):return page.evaluate('JSON.parse(JSON.stringify(state))')
def click(page,name):page.locator('#'+name).click();idle(page)
def change_dt(page,value):
    page.evaluate('document.getElementById("integration-step").value='+json.dumps(str(value)))
    click(page,'apply-timestep')
    assert snapshot(page)['experiment']['dt_s']==value
def rate(page,value):page.locator('#model-rate').select_option(str(value));idle(page);assert snapshot(page)['requested_model_s_per_wall_s']==value

original_timing=None
try:
    with Page() as page:
        page.on('pageerror',lambda value:errors.append(value));page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('typeof appState!=="undefined"&&appState!==null');page.locator('#em-lab').click();idle(page)
        assert snapshot(page)['execution_generation']==execution_generation()
        click(page,'load-preset')
        click(page,'measure');frozen=page.evaluate('JSON.stringify(map)');before=snapshot(page)
        change_dt(page,.0005);after=snapshot(page)
        assert before['experiment']['phase']==after['experiment']['phase'] and before['editor']==after['editor']
        assert before['revision']==after['revision'] and before['edit_token']==after['edit_token']
        assert page.evaluate('JSON.stringify(map)')==frozen
        expected=Experiment.from_payload(after['experiment']);expected.advance()
        click(page,'one-step');assert snapshot(page)['experiment']==json.loads(json.dumps(expected.payload()))
        assert page.evaluate('JSON.stringify(map)')==frozen and 'CONGELADO' in page.locator('#map-state').inner_text()
        for requested in (.1,.5,2):
            before=snapshot(page);rate(page,requested);assert snapshot(page)['experiment']==before['experiment'] and snapshot(page)['editor']==before['editor']
            click(page,'play');page.wait_for_function('!state.paused&&state.time_s>'+repr(before['time_s']+.01))
            page.wait_for_function('document.getElementById("integration-step").disabled&&document.getElementById("one-step").disabled')
            began=time.perf_counter();click(page,'play');pauses.append((time.perf_counter()-began)*1000)
        rate(page,.5);click(page,'save');saved=snapshot(page)
        original_timing=(STORAGE/'ui-phase.timing.json').read_bytes()
        saved_core=(STORAGE/'ui-phase.json').read_bytes();saved_view=(STORAGE/'ui-phase.view.json').read_bytes()
        change_dt(page,.00025);rate(page,2);click(page,'restore')
        restored=snapshot(page);assert restored['experiment']==saved['experiment'] and restored['editor']==saved['editor'] and restored['time_preferences']==saved['time_preferences']
        assert (STORAGE/'ui-phase.json').read_bytes()==saved_core and (STORAGE/'ui-phase.view.json').read_bytes()==saved_view
        envelope=json.loads(original_timing)
        bad_cases=[('invalid seal',None),('rate bool',lambda b:b['preferences'].update(rate=True)),
                   ('extra preference',lambda b:b['preferences'].update(extra=0)),('generation',lambda b:b['execution_generation'].update(protocol=99)),
                   ('wrong checkpoint',lambda b:b.update(checkpoint_sha256='0'*64)),('schema bool',lambda b:b.update(schema=True)),
                   ('future history',lambda b:b['preferences']['timestep_changes'][-1].update(time_s=1e12)),
                   ('wrong step',lambda b:b['preferences']['timestep_changes'][-1].update(dt_after_s=.003))]
        for label,mutate in bad_cases:
            bad=deepcopy(envelope)
            if mutate:mutate(bad['payload']);bad['sha256']=hashlib.sha256(adjunct.canonical(bad['payload'])).hexdigest()
            else:bad['sha256']='0'*64
            (STORAGE/'ui-phase.timing.json').write_text(json.dumps(bad));before=stable();result=request('load',file='ui-phase')
            assert result.get('HTTP_error')==400 and stable()==before,(label,result);refusals.append(label)
        for label,raw in [('not object',b'[]'),('duplicate key',b'{"payload":{},"payload":{},"sha256":"0"}'),('oversize',b' '*32769)]:
            (STORAGE/'ui-phase.timing.json').write_bytes(raw);before=stable();result=request('load',file='ui-phase')
            assert result.get('HTTP_error')==400 and stable()==before,(label,result);refusals.append(label)
        (STORAGE/'ui-phase.timing.json').write_bytes(original_timing)
        for key in ('time_preferences','checkpoint_sha256'):
            before=stable();result=request('load',file='ui-phase',**{key:{}})
            assert result.get('HTTP_error')==400 and stable()==before;refusals.append('browser internal '+key)
        # A core0.4 save from the frozen base remains exact; missing time adjunct defaults explicitly.
        legacy=ROOT/'output/c212-em-cloud-native-product/c212-em-worker/product'
        legacy_hash={suffix:hashlib.sha256((legacy/('ui-phase'+suffix)).read_bytes()).hexdigest()for suffix in ('.json','.view.json')}
        for suffix in ('.json','.view.json'):shutil.copyfile(legacy/('ui-phase'+suffix),STORAGE/('legacy-time'+suffix))
        old=Experiment.load(STORAGE/'legacy-time.json');result=request('load',file='legacy-time')
        assert result.get('timing_preferences_source')=='legacy_default_rate1' and not result.get('display')
        s=current()['state'];assert s['requested_model_s_per_wall_s']==1 and s['experiment']==json.loads(json.dumps(old.payload())) and not s['time_preferences']['timestep_changes']
        assert all(hashlib.sha256((legacy/('ui-phase'+suffix)).read_bytes()).hexdigest()==digest for suffix,digest in legacy_hash.items())
        page.evaluate('refresh(true)');idle(page);click(page,'restore');s=snapshot(page)
        assert s['experiment']==saved['experiment'] and s['time_preferences']==saved['time_preferences']
        expected={'experiment':s['experiment'],'editor':s['editor'],'time_preferences':s['time_preferences'],
                  'scientific_generation':s['scientific_generation'],'execution_generation':s['execution_generation'],
                  'files_sha256':{suffix:hashlib.sha256((STORAGE/('ui-phase'+suffix)).read_bytes()).hexdigest()for suffix in ('.json','.view.json','.timing.json')}}
        (ROOT/'output/c212-em-time-restart-expected.json').write_text(json.dumps(expected,indent=2)+'\n')
        page.evaluate('document.querySelectorAll("aside").forEach(e=>e.scrollTop=0)')
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-em-time-controls-ui'+label_suffix+'.png'],check=True,capture_output=True)
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"')
        assert not errors and (ROOT/'user/sessions/latest.json').read_bytes()==owner
        report={'status':'real_CEF_numeric_timing_step_rate_save_restore_and_HTTP_preflight_verified',
                'requested_rates': [.1,.5,2.],'UI_pause_wall_ms':pauses,'one_manual_step_matches_core':True,
                'timestep_preserves_phase_editor_conservation_reference_and_frozen_map':True,
                'rate_preserves_phase_editor_and_dt':True,'save_restore_preferences_exact':True,
                'legacy_core04_checkpoint_exact_with_explicit_default_rate1':True,
                'malformed_loads_refused_before_any_mutation':refusals,'restart_expected_prepared':True,
                'JS_errors':errors,'owner_pointer_preserved':True,'execution_generation':execution_generation(),
                'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()for p in [
                    Path(__file__),CANDIDATE/'em/em_worker.py',CANDIDATE/'em/em_timing.py',CANDIDATE/'app/em_laboratory.py',
                    CANDIDATE/'app/em_time_laboratory.py',CANDIDATE/'app/ui/em.html',CANDIDATE/'app/ui/em/app.js',CANDIDATE/'app/ui/em/timing.js',CANDIDATE/'app/ui/em/style.css']},
                'scope':'Functional native CEF journey; screenshot awaits visual review. No fresh restart or formal128 throughput approval yet.'}
        destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'refusals':len(refusals),'JS_errors':errors}),flush=True)
finally:
    if original_timing is not None:(STORAGE/'ui-phase.timing.json').write_bytes(original_timing)
    assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
