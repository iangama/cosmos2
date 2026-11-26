"""Use the original panels to select Jupiter and prepare the advertised references."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import urllib.request

from cef_page_v2 import Page
from ordinary_option_input_v2 import OptionInput

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.27.4'
FOLDER=ROOT/'output/option-controls-native-reference-20261120b'
OUT=ROOT/'evidence/option-controls-native-reference-20261120b.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get(route):return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+route,timeout=30))
def physical(value):return {key:value.get(key) for key in ['system_id','edit_token','revision','time','paused','bodies','atlas_initial','interventions']}


def main():
    assert not OUT.exists() and not FOLDER.exists()
    FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).parent.parent==PRODUCT
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
    saved=PRODUCT/'gravity-sessions/latest.json'
    proof=dict(accepted=False,completed=False,session=session,checks=[],captures=[],actions=[],
      saved_session_sha256=sha(saved),source_manifest_sha256=sha(PRODUCT/'build-manifest.json'),
      source_sha256={name:sha(ROOT/name) for name in ['scripts/verify-native-reference-options-v2.py','scripts/ordinary_option_input_v2.py','scripts/ordinary_native_input_v8.py','scripts/cef_page_v2.py']},
      scope='Original header/panels, genuine Windows clicks and wheel to select body, resolution and plane, then prepare Jupiter Mesh/Layers and close them. Restore the existing four-body saved experiment through its button; no overwrite of that save. HTTP/DOM readback observes selected models and preservation. No import, branch, cancellation-race, benchmark or scientific milestone acceptance.')
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with Page() as page:
        window=OptionInput(session['app'],page)
        def wait(expression):page.wait_for_function(expression,timeout=90000)
        def click(selector,ready=None):
            proof['step']=selector;persist();window.click(selector)
            if ready:wait(ready)
        def capture(name):
            time.sleep(.25);target=FOLDER/(name+'.png');assert not target.exists()
            row=window.capture(target);row['sha256']=sha(target);proof['captures'].append(row);persist()
        def check(name,**values):
            proof['checks'].append(dict(name=name,**values));proof['actions']=list(window.actions);persist()
        try:
            wait('location.pathname==="/"&&appState&&!pending&&spatialInstrument.online&&layerInstrument.online')
            current=get('/api/state')
            if current['mode']=='atlas':
                click('#experiment','appState.mode==="experiment"&&!pending')
                click('#load','!pending&&appState.physics?.paused&&appState.physics.bodies.length===4')
            else:
                assert current['mode']=='experiment' and current['physics']['paused'] and len(current['physics']['bodies'])==4
                previous=json.loads((ROOT/'evidence/option-controls-native-reference-20261120a.json').read_text(encoding='utf8'))
                assert physical(current['physics'])==previous['restored_phase']
                proof['restoration_context_receipt']='evidence/option-controls-native-reference-20261120a.json'
            phase=physical(get('/api/state')['physics'])
            assert phase['system_id']==json.loads(saved.read_text(encoding='utf8'))['system_id']
            proof['restored_phase']=phase
            jupiter=next(body['id'] for body in phase['bodies'] if body.get('reference_id')=='sol:naif:599')
            check('uses-preserved-paused-four-body-session',system_id=phase['system_id'],bodies=4)
            for scale in ['1','1.5']:
                proof['step']='scale-'+scale;persist();window.select('#ui-scale',scale)
                wait('Number(getComputedStyle(document.body).zoom)==='+scale)
                click('#open-spatial','!document.getElementById("spatial-panel").hidden')
                window.open_options('#spatial-body');capture('mesh-body-options-'+scale.replace('.','-'))
                window.select('#spatial-body',jupiter)
                window.select('#spatial-resolution','33')
                window.select('#spatial-plane','XZ')
                assert physical(get('/api/state')['physics'])==phase
                click('#spatial-create','spatialInstrument.snapshot?.active&&!spatialInstrument.pending&&!spatialInstrument.snapshot.busy')
                spatial=get('/api/spatial/state');artifact=spatial['artifact']
                assert artifact['source']['reference_id']=='sol:naif:599'
                assert artifact['configuration']['radial_count']==33
                assert artifact['configuration']['orientation']==[[1,0,0],[0,0,1],[0,-1,0]]
                assert not spatial['error'] and physical(get('/api/state')['physics'])==phase
                capture('mesh-jupiter-result-'+scale.replace('.','-'))
                check('mesh-jupiter-body-resolution-plane-prepare',scale=scale,radial_count=33,plane='XZ',sha256=artifact['sha256'])
                click('#spatial-leave','!spatialInstrument.pending&&!spatialInstrument.snapshot.active&&!spatialInstrument.snapshot.recovery_required')
                assert physical(get('/api/state')['physics'])==phase
                click('#open-layers','!document.getElementById("layers-panel").hidden')
                window.open_options('#layers-body');capture('layers-body-options-'+scale.replace('.','-'))
                window.select('#layers-body',jupiter)
                wait('!document.getElementById("layers-radius-label").hidden&&document.getElementById("layers-altitude-label").hidden')
                click('#layers-create','layerInstrument.snapshot?.active&&!layerInstrument.pending&&!layerInstrument.snapshot.busy')
                layers=get('/api/layers/state');artifact=layers['artifact'];magnetic=artifact['magnetic']
                assert magnetic['body_reference_id']=='sol:naif:599' and magnetic['degree']==13
                assert 'JRM33' in magnetic['provenance']['model']
                assert not layers['error'] and physical(get('/api/state')['physics'])==phase
                capture('layers-jupiter-result-'+scale.replace('.','-'))
                check('layers-jupiter-model-choice-and-prepare',scale=scale,model=magnetic['provenance']['model'],degree=13,sha256=artifact['sha256'])
                click('#layers-leave','!layerInstrument.pending&&!layerInstrument.snapshot.active&&!layerInstrument.snapshot.recovery_required')
                assert physical(get('/api/state')['physics'])==phase
                click('#layers-panel-close','document.getElementById("layers-panel").hidden')
            window.select('#ui-scale','1')
            assert sha(saved)==proof['saved_session_sha256']
            proof['physical_phase_preserved']=physical(get('/api/state')['physics'])==phase
            assert proof['physical_phase_preserved']
            click('#atlas','!pending&&appState.mode==="atlas"')
            assert all(sha(PRODUCT/name)==digest for name,digest in manifest['files_sha256'].items())
            proof.update(accepted=True,completed=True)
        except Exception:proof['failure']=traceback.format_exc()
        finally:proof['actions']=list(window.actions);persist()
    print(json.dumps({key:proof.get(key) for key in ['accepted','completed','step','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
