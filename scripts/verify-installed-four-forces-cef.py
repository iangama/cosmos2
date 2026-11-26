"""Post-promotion smoke of all existing force pages in the default installed CEF."""
from pathlib import Path
import hashlib
import json
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert launch['runtimeVariant']=='cloud' and not launch['cloudCandidate']
assert Path(launch['serverScript']).resolve()==(ROOT/'app/server.py').resolve()
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
errors=[];checks=[]
with Page() as page:
    previous=page.evaluate('location.href')
    page.on('pageerror',lambda e:errors.append(e))
    def go(url):
        page.call('Page.navigate',{'url':url})
        page.wait_for_function('location.href==='+json.dumps(url)+'&&document.readyState==="complete"')
    try:
        go('http://127.0.0.1:4700/forces.html')
        page.wait_for_function('typeof response!=="undefined"&&response&&!pending',timeout=30000)
        for force in ('gravity','electromagnetic','strong','weak'):
            page.locator('[data-scenario="'+force+'"]').click()
            page.wait_for_function('!pending&&config.scenario==='+json.dumps(force))
            for act in (False,True):
                page.locator('[data-force="'+force+'"][data-control="acting"]').set_checked(act)
                page.wait_for_function('!pending')
                physical=None
                for visible in (False,True):
                    page.locator('[data-force="'+force+'"][data-control="visible"]').set_checked(visible)
                    page.wait_for_function('!pending')
                    value=page.evaluate('({control:config.controls['+json.dumps(force)+'],result:response.result,counterfactual:response.counterfactual})')
                    assert value['control']['acting']==act and value['control']['visible']==visible
                    assert value['counterfactual']==(not act)
                    measure=value['result']['measurements'][1]['value']
                    assert (measure>0) if act else (measure==0)
                    if physical is None:physical=value['result']
                    else:assert value['result']==physical
                    if force in ('gravity','electromagnetic'):
                        assert (page.evaluate('projectedArrows.length')>0)==visible
                    checks.append({'force':force,'acting':act,'visible':visible,'passed':True})
            print(force+' four combinations passed',flush=True)
        assert not errors,errors
        assert owner.read_bytes()==original
    finally:go(previous)
report={'status':'all_four_existing_force_pages_verified_on_installed_default_CEF','checks':checks,
    'visibility_preserves_physical_result':True,'javascript_errors':errors,'owner_pointer_preserved':True,
    'installed_server_sha256':hashlib.sha256((ROOT/'app/server.py').read_bytes()).hexdigest(),
    'scope':'Sixteen acting/visibility combinations on existing scientific stages; does not accept the future mesh or body-associated EM layers.'}
(ROOT/'evidence/cloud-installed-four-forces-cef-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
