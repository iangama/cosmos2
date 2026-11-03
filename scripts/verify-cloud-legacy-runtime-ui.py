"""Candidate backend on the preserved query/baseline engine: massive flows stay usable."""
from pathlib import Path
import json
import time
import urllib.error
import urllib.request
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert launch['cloudCandidate'] and launch['runtimeVariant'] in ('query','baseline')
owner=ROOT/'user/sessions/latest.json';before_owner=owner.read_bytes()
candidate=ROOT/'output/c211-cloud-candidate/sessions/latest.json'
before_candidate=candidate.read_bytes()
assert json.loads(before_candidate)['test_particle_cloud'] is not None
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=5))
def command(action,**data):
    request=urllib.request.Request('http://127.0.0.1:4700/api/command',data=json.dumps({'command':action,**data}).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(request,timeout=65))
def guard(p):return {k:p[k] for k in ('system_id','edit_token','revision')}|{'expected_time':p['time'],'frame':p['contract']['frame']}
errors=[];refused=[]
try:
    with Page() as page:
        page.on('pageerror',lambda e:errors.append(e));page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('appState!==null');page.locator('#experiment').click()
        page.wait_for_function('!pending&&appState.mode==="experiment"',timeout=60000)
        s=state();assert s['cloud_supported'] is False and len(s['physics']['bodies'])==32
        page.evaluate('document.getElementById("test-cloud").open=true')
        page.wait_for_function('document.getElementById("cloud-status").textContent.includes("indisponíveis")')
        assert page.evaluate('document.getElementById("cloud-create").disabled')
        assert 'indisponíveis' in page.locator('#cloud-status').inner_text()
        before=s['physics']
        for name,data in [('load_cloud_experiment',{'parameters':{'count':10000}}),
                ('set_cloud',{'parameters':{'count':128}}),('load',{})]:
            try:command(name,**guard(before),**data)
            except urllib.error.HTTPError as e:
                assert e.code==400
                refused.append({'command':name,'error':json.load(e)['error']})
            else:raise AssertionError('Unsupported cloud load/activation accepted: '+name)
            assert state()['physics']==before
        command('create_body',**guard(before),name='Compatibilidade',mass_kg=1e20,
            position_m=[1e11,2e11,3e11],velocity_m_s=[0.,0.,0.])
        p=state()['physics'];assert len(p['bodies'])==33
        added=p['bodies'][-1]['id'];command('remove_body',**guard(p),body=added)
        command('resume');time.sleep(.25);command('pause')
        p=state()['physics'];assert p['time']>0 and len(p['bodies'])==32
        command('save');command('reset',count=32);command('load')
        loaded=state()['physics'];assert loaded['time']==p['time'] and loaded['bodies']==p['bodies']
        assert loaded['test_particle_cloud'] is None
        page.evaluate('updateState()');page.wait_for_function('appState.physics.time>0')
        assert not errors,errors
        report={'status':'candidate_massive_flows_on_preserved_legacy_runtime_verified',
            'runtime':launch['runtimeVariant'],'cloud_controls_disabled':True,
            'cloud_activation_and_checkpoint_refused_before_mutation':refused,
            'create_remove_massive_body':True,'real_32_body_evolution':True,'plain_save_reset_load_exact':True,
            'javascript_errors':errors,'owner_pointer_preserved':owner.read_bytes()==before_owner}
        (ROOT/('evidence/cloud-legacy-'+launch['runtimeVariant']+'-ui-check.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
finally:
    candidate.write_bytes(before_candidate)
    try:command('pause');command('atlas')
    finally:assert owner.read_bytes()==before_owner
