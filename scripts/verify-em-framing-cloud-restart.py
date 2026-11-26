"""H fresh normal restart, sealed-view refusal and exact frozen-G continuation."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import sys
import urllib.request
import urllib.error
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];H=ROOT/'output/c212-em-framing-product'
sys.path.insert(0,str(ROOT/'output/c212-em-integration-product/em-cloud'))
from cloud_checkpoint import load
dest=ROOT/'evidence/em-framing-cloud-restart-check.json';assert not dest.exists()
expected=json.loads((ROOT/'output/em-framing-cloud-restart-expected.json').read_bytes());storage=H/'c212-em-cloud-worker/product'
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert session['emFramingCandidate']
assert Path(session['serverScript']).resolve()==(H/'app/server.py').resolve()
owner=(ROOT/'user/sessions/latest.json').read_bytes();errors=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def idle(p):p.wait_for_function('state&&state.paused&&!pending&&!native.error&&native.confirmation?.metadata.time_s===state.time_s',timeout=30000)
assert all(sha(storage/('ui-phase'+s))==d for s,d in expected['files_sha256'].items())
system,phase,dt,controls=load(storage/'ui-phase.json')
for _ in range(777):phase,_=system.step(phase,dt,**controls)
with Page() as p:
    p.on('pageerror',lambda e:errors.append(e));p.goto('http://127.0.0.1:4700/')
    p.wait_for_function('typeof appState!=="undefined"&&appState');p.locator('#em-cloud-lab').click();idle(p)
    actual=p.evaluate('JSON.parse(JSON.stringify(state))')
    for key in ('phase_sha256','time_s','model','dt_s','controls','count','selected_particle','requested_model_s_per_wall_s'):
        assert actual[key]==expected['state'][key],key
    assert p.evaluate('visual')==expected['visual'] and p.evaluate('$("count").value')==str(actual['count'])
    # Invalid, correctly resealed preferences must be refused before phase load.
    base=json.loads((storage/'ui-phase.view.json').read_bytes());refusals=[]
    for suffix in ('.json','.view.json'):(storage/('h-invalid'+suffix)).write_bytes((storage/('ui-phase'+suffix)).read_bytes())
    for change in ({'selected_source_id':'absent'},{'selected_source_id':False},{'unexpected':True}):
        env=deepcopy(base);env['payload']['visual'].update(change)
        env['sha256']=hashlib.sha256(json.dumps(env['payload'],sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
        (storage/'h-invalid.view.json').write_text(json.dumps(env)+'\n')
        result=p.evaluate('(async()=>{const r=await fetch("/api/em-cloud/command",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:"load",file:"h-invalid",...guard()})});return {status:r.status,body:await r.json()};})()')
        assert result['status']==400,result;refusals.append(result['body']['error']);p.evaluate('refresh(true)')
        assert p.evaluate('state.phase_sha256')==actual['phase_sha256']
        assert p.evaluate('visual')==expected['visual']
    p.evaluate('(async()=>{for(let n=0;n<777;n+=32)await command("advance",{steps:Math.min(32,777-n)});return true;})()');idle(p)
    assert p.evaluate('state.phase_sha256')==hashlib.sha256(phase._x+phase._v).hexdigest()
    assert p.evaluate('state.time_s')==phase.time_s
    assert all(sha(storage/('ui-phase'+s))==d for s,d in expected['files_sha256'].items())
    p.locator('#return').click();p.wait_for_function('location.pathname==="/"')
assert not errors and (ROOT/'user/sessions/latest.json').read_bytes()==owner
report={'status':'I_cloud_normal_restart_source_selection_and777_step_future_verified','scientific_future_exact':True,
        'saved_files_preserved':True,'source_and_particle_selection_restored':True,'resealed_view_refusals':refusals,
        'JS_errors':errors,'owner_pointer_preserved':True,'session':session,
        'source_sha256':{str(f.relative_to(ROOT)):sha(f) for f in [Path(__file__),ROOT/'output/em-framing-cloud-restart-expected.json',*sorted((H/'app').rglob('*'))] if f.is_file() and '__pycache__' not in f.parts},
        'scope':'Fresh native restart, auto-restored phase/view preferences and exact777-step frozen-G continuation. No final visual/performance acceptance.'}
dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'JS_errors':errors}),flush=True)
