"""Restore the saved experiment through normal controls, then restore its recorded view as supplementary state recovery."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import hashlib
import json
import math
import time
import traceback
import urllib.request

from cef_page_v2 import Page
from ordinary_native_input_v5 import NativeInput

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/working-session-restored-20261120a.json'
FOLDER=ROOT/'output/working-session-restored-20261120a'
helper=SourceFileLoader('restore_working_state_helpers',str(ROOT/'scripts/preserve-working-session-for-upgrade.py')).load_module()


def post(route,value):
    req=urllib.request.Request('http://127.0.0.1:4700'+route,data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req,timeout=30))


def lua(value):
    if value is None:return 'nil'
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False)
    if isinstance(value,(int,float)):
        assert math.isfinite(value)
        return format(value,'.17g')
    if isinstance(value,list):return '{'+','.join(lua(v) for v in value)+'}'
    if isinstance(value,dict):return '{'+','.join('['+lua(k)+']='+lua(v) for k,v in value.items())+'}'
    raise ValueError('Unsupported saved native value')


def main():
    assert not OUT.exists() and not FOLDER.exists()
    FOLDER.mkdir()
    migration=json.loads((ROOT/'evidence/working-product-switch-20261120a.json').read_text(encoding='utf8'))
    assert migration['accepted'] and migration['completed']
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    product=Path(session['serverScript']).parent.parent
    assert product==ROOT/'output/original-flow-hotfix-product0.27.2'
    context=migration['context'];expected=migration['physical_before']
    proof=dict(accepted=False,completed=False,session=session,actions=[],
               scope='Ordinary Windows controls restore the saved experiment. Explicit API epoch/clock restoration and native camera restoration are supplementary preservation, not feature acceptance. Edit-token renewal is required by the existing session contract.')
    try:
        with Page() as page:
            page.wait_for_function('location.pathname==="/"&&appState&&atlasState&&!pending')
            assert helper.get('/api/state')['mode']=='atlas'
            post('/api/atlas/epoch',{'utc':context['utc']})
            post('/api/navigation/clock',{'paused':True,'rate':context['rate'] if context['rate'] else 1})
            window=NativeInput(session['app'],page)
            window.click('#experiment')
            page.wait_for_function('appState.mode==="experiment"&&appState.physics&&!pending',timeout=60000)
            if not helper.get('/api/state')['physics']['paused']:
                window.click('#play')
                page.wait_for_function('appState.physics.paused&&!pending')
            window.click('#load')
            page.wait_for_function('!pending&&appState.physics.system_id==='+json.dumps(expected['system_id']),timeout=90000)
            actual=helper.material(helper.get('/api/state')['physics'])
            assert actual['edit_token']!=expected['edit_token'],'Restoration must renew the stale-edit guard'
            assert {k:v for k,v in actual.items() if k!='edit_token'}=={k:v for k,v in expected.items() if k!='edit_token'}
            ready=helper.native_read('return {present=openspace.hasSceneGraphNode('+lua(context['navigation']['Anchor'])+')}')
            assert ready['present']
            script='openspace.time.setPause(true);openspace.time.setTime('+lua(context['et'])+');openspace.navigation.setNavigationState('+lua(context['navigation'])+');return {restored=true}'
            assert helper.native_read(script)['restored']
            deadline=time.monotonic()+10
            while True:
                observed=helper.native_read('return {navigation=openspace.navigation.getNavigationState("Root"),et=openspace.time.currentTime(),paused=openspace.time.isPaused()}')
                if abs(observed['et']-context['et'])<=1e-6:break
                assert time.monotonic()<deadline
                time.sleep(.05)
            a,b=context['navigation'],observed['navigation']
            assert a['Anchor']==b['Anchor'] and a['ReferenceFrame']==b['ReferenceFrame'] and a['Position']==b['Position']
            assert all(abs(x-y)<=1e-12 for x,y in zip(a['Up'],b['Up'],strict=True))
            assert observed['paused'] is True
            proof.update(physical_before=expected,physical_after=actual,native_context_after=observed,
                         native_context_before=context,edit_token_renewed=True)
            proof['actions']=window.actions
            capture=FOLDER/'restored-live-session.png'
            proof['capture']=window.capture(capture)
            proof['capture']['sha256']=hashlib.sha256(capture.read_bytes()).hexdigest()
            proof['notice']=page.evaluate('document.getElementById("notice").textContent')
        proof.update(accepted=True,completed=True)
    except Exception:
        proof['failure']=traceback.format_exc()
    finally:
        OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','edit_token_renewed','notice','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
