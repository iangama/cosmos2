"""Verify native scaled probes and confirmed save/export after a rejected draft; ordinary Windows controls."""
from pathlib import Path
import hashlib
import json
import math
import re
import time
import traceback
import urllib.request

from cef_page_v2 import Page
from ordinary_native_input_v5 import NativeInput

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.2'
FOLDER=ROOT/'output/forces-confirmed-native-after-20261120a'
OUT=ROOT/'evidence/forces-confirmed-native-after-20261120a.json'


def phase():
    value=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=20))['physics']
    return None if value is None else {k:value.get(k) for k in ['system_id','edit_token','revision','time','paused','bodies','atlas_initial','interventions']}


def main():
    assert not OUT.exists() and not FOLDER.exists()
    FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).parent.parent==PRODUCT
    saved_path=PRODUCT/'user/forces/latest.json'
    saved_before=saved_path.read_bytes() if saved_path.exists() else None
    if saved_before is not None:(FOLDER/'saved-conditions-before.json').write_bytes(saved_before)
    proof=dict(accepted=False,completed=False,cases=[],captures=[],actions=[],
               scope='Native original-header Forces journeys using Windows mouse/keyboard at100/150%. Network blocking injects only the declared recalc fault; DOM/HTTP observe. Save/load/export use the real private backend; the prior saved file is restored after the test. No whole-project or performance acceptance.')
    before=phase()
    with Page() as page:
        window=NativeInput(session['app'],page)
        def wait(expression):page.wait_for_function(expression,timeout=60000)
        def click(selector,condition=None):
            proof['step']=selector
            OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            window.click(selector)
            if condition:wait(condition)
        def capture(name):
            time.sleep(.3)
            file=FOLDER/(name+'.png');assert not file.exists()
            row=window.capture(file);row['sha256']=hashlib.sha256(file.read_bytes()).hexdigest();proof['captures'].append(row)
        try:
            wait('location.pathname==="/"&&appState&&!pending')
            original_scale=page.evaluate('document.getElementById("ui-scale").value')
            for scale in ['1','1.5']:
                window.select('#ui-scale',scale)
                click('#forces','location.pathname==="/forces.html"&&typeof response!=="undefined"&&response?.ok&&!pending')
                assert page.evaluate('Number(getComputedStyle(document.body).zoom)')==float(scale)
                initial=page.evaluate('({configuration:response.configuration,physics_sha256:response.physics_sha256})')
                assert initial['configuration']['scenario']=='gravity'
                point=page.evaluate('''(()=>{const r=canvas.getBoundingClientRect(),body=document.body.getBoundingClientRect(),layout=parseFloat(getComputedStyle(document.body).width),z=Number(getComputedStyle(document.body).zoom)||1,factor=Math.abs(body.width/layout-1)<.02?z:1;
                  const all=projectedArrows,candidates=all.filter(a=>a.field&&a.x>20&&a.x<r.width-20&&a.y>35&&a.y<r.height-45).map(a=>({...a,separation:Math.min(...all.filter(b=>b!==a).map(b=>Math.hypot(a.x-b.x,a.y-b.y)))})).sort((a,b)=>b.separation-a.separation);const a=candidates[0];if(!a)return null;
                  return {x:(r.left+a.x)*factor,y:(r.top+a.y)*factor,field:a.field,separation:a.separation};})()''')
                assert point and point['separation']>0
                window.click_at(point['x'],point['y'],'gravity reference vector')
                wait('document.getElementById("probe").textContent.includes("Campo de referência:")')
                reading=page.evaluate('document.getElementById("probe").textContent')
                token=re.search(r'Campo de referência:\s*([^\s]+)',reading).group(1)
                measured=float(token) if 'e' in token.lower() else float(token.replace('.','').replace(',','.'))
                expected=float(format(math.hypot(*point['field']['vector']),'.6g'))
                assert measured==expected,(measured,expected,reading)
                page.call('Network.setBlockedURLs',{'urls':['http://127.0.0.1:4700/api/forces/evaluate']})
                click('[data-scenario="strong"]','!pending&&document.getElementById("force-status").classList.contains("error")')
                rejected=page.evaluate('({shown:response.configuration.scenario,confirmed:config.scenario,draft:draftConfig.scenario,physics:response.physics_sha256,note:!document.getElementById("result-draft-note").hidden})')
                assert rejected==dict(shown='gravity',confirmed='gravity',draft='strong',physics=initial['physics_sha256'],note=True)
                capture('rejected-draft-'+scale.replace('.','-'))
                page.call('Network.setBlockedURLs',{'urls':[]})
                click('#save-forces','!pending&&document.getElementById("force-status").textContent.includes("salvas")')
                saved=json.loads(saved_path.read_text(encoding='utf8'))
                assert saved['configuration']==initial['configuration']
                click('#export-forces','!pending&&typeof lastForcesExport!=="undefined"&&lastForcesExport?.ok')
                exported=page.evaluate('({configuration:lastForcesExport.configuration,physics_sha256:lastForcesExport.physics_sha256,path:lastForcesExport.export_file})')
                assert exported['configuration']==initial['configuration'] and exported['physics_sha256']==initial['physics_sha256']
                export_path=Path(exported['path']);assert export_path.is_relative_to(PRODUCT) and export_path.is_file()
                click('#restore-result-conditions','draftConfig.scenario==="gravity"&&document.getElementById("result-draft-note").hidden')
                field=page.evaluate('(()=>{const e=document.querySelector("#parameters input[type=number]");return {name:e.name,value:Number(e.value),max:Number(e.max)}})()')
                changed=field['value']*1.1 if field['value'] else 1
                assert changed<=field['max']
                window.fill('#parameters [name="'+field['name']+'"]',str(changed))
                wait('!document.getElementById("result-draft-note").hidden')
                click('#calculate','!pending&&document.getElementById("result-draft-note").hidden')
                assert page.evaluate('response.physics_sha256')!=initial['physics_sha256']
                assert page.evaluate('config.parameters['+json.dumps(field['name'])+']')==changed
                click('#load-forces','!pending&&!document.getElementById("restoration-note").hidden')
                assert page.evaluate('response.physics_sha256')==initial['physics_sha256']
                assert page.evaluate('document.getElementById("restoration-note").dataset.state')=='same_generation'
                capture('restored-result-'+scale.replace('.','-'))
                click('a.back','location.pathname==="/"&&appState&&!pending')
                assert phase()==before
                proof['cases'].append(dict(scale=scale,probe_reading=reading,expected_magnitude_6_significant_digits=expected,
                                          rejected=rejected,export=exported,export_sha256=hashlib.sha256(export_path.read_bytes()).hexdigest(),
                                          changed_parameter=field['name'],changed_value=changed,restored_physics_sha256=initial['physics_sha256']))
            window.select('#ui-scale',original_scale)
            proof.update(accepted=True,completed=True,physical_phase_preserved=True)
        except Exception:
            proof['failure']=traceback.format_exc()
            try:capture('failure')
            except Exception as error:proof['capture_failure']=str(error)
        finally:
            page.call('Network.setBlockedURLs',{'urls':[]})
            if saved_before is not None:
                temporary=saved_path.with_suffix('.preserved.tmp');temporary.write_bytes(saved_before);temporary.replace(saved_path)
                assert saved_path.read_bytes()==saved_before
                proof['previous_save_restored_sha256']=hashlib.sha256(saved_before).hexdigest()
            proof['actions']=window.actions
            OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','physical_phase_preserved','step','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
