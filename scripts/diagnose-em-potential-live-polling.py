"""Same paused H fixture, alternating original CEF polling and quiesced refresh."""
from pathlib import Path
import hashlib
import json
import time
import urllib.request
import urllib.error
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];H=ROOT/'output/c212-em-cloud-editor-product'
dest=ROOT/'evidence/em-cloud-editor-potential-live-polling-diagnostic.json';assert not dest.exists()
owner=(ROOT/'user/sessions/latest.json').read_bytes();runs=[]
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))
def command(name,**values):
    s=state()['state'];guard={k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
    request=urllib.request.Request('http://127.0.0.1:4700/api/em/command',data=json.dumps({'command':name,**guard,**values}).encode(),headers={'Content-Type':'application/json'})
    began=time.perf_counter()
    try:
        response=json.load(urllib.request.urlopen(request,timeout=20))
        return {'status':200,'response':response,'wall_ms':(time.perf_counter()-began)*1000}
    except urllib.error.HTTPError as e:return {'status':e.code,'error':json.load(e),'wall_ms':(time.perf_counter()-began)*1000}
with Page() as page:
    page.goto('http://127.0.0.1:4700/em.html');page.wait_for_function('state&&state.paused&&!pending&&nativeState.active&&!nativeState.error',timeout=30000)
    initial=state()['state'];assert initial['experiment']['mode']=='mutual_electrostatic' and len(initial['experiment']['system']['ids'])==128 and initial['time_s']==0
    assert command('configure_potential',changes={'visible':True,'count_axis':33,'levels_V':None})['status']==200
    page.evaluate('window.originalDiagnosticRefresh=refresh')
    try:
        for index,enabled in enumerate((True,False,True,False,True)):
            page.evaluate('refresh=window.originalDiagnosticRefresh' if enabled else 'refresh=async()=>{}')
            time.sleep(.3)
            result=command('sample_potential');after=state()['state'];assert after['experiment']==initial['experiment']
            if result['status']==200:
                response=result.pop('response');result.update(numeric_ms=response['result']['batch_protocol']['elapsed_wall_ms'],segments=len(response['result']['geometry']['segments']),display=response.get('display'))
            result.update(order=index+1,CEF_polling=enabled);runs.append(result);print(json.dumps(result),flush=True)
    finally:
        page.evaluate('refresh=window.originalDiagnosticRefresh;delete window.originalDiagnosticRefresh;refresh(true)')
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"')
assert owner==(ROOT/'user/sessions/latest.json').read_bytes()
report={'status':'H_live_paused_sampling_alternating_CEF_refresh_diagnostic','runs':runs,'scientific_phase_preserved':True,'owner_pointer_preserved':True,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),H/'app/em_slice.py',H/'app/em_potential.py',H/'app/ui/em/app.js']},
        'scope':'Original2s budget and unchanged product files; CEF runtime refresh temporarily replaced then restored. Order fixed, aging/load uncontrolled; diagnostic only, not formal performance acceptance or A attribution.'}
dest.write_text(json.dumps(report,indent=2)+'\n')
