"""Bounded owner-entry journeys: actual Windows input; CDP/HTTP only observe or inject a named transport fault."""
from pathlib import Path
import hashlib
import json
import os
import time
import traceback
import urllib.request

import psutil
from cef_page_v2 import Page
from ordinary_native_input_v4 import NativeInput

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / 'output/original-flow-hotfix-product0.27.1'
FOLDER = ROOT / 'output/original-flow-native-20261120e'
OUT = ROOT / 'evidence/original-flow-native-journey-20261120e.json'


def get(route):
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+route, timeout=30))


def physical(value):
    if value is None:
        return None
    return {key:value.get(key) for key in ['system_id', 'edit_token', 'revision', 'time', 'paused', 'bodies', 'atlas_initial', 'interventions']}


def main():
    assert not OUT.exists(), 'Preserve previous attempts'
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve() == PRODUCT / 'app/server.py'
    manifest = json.loads((PRODUCT / 'build-manifest.json').read_text(encoding='utf8'))
    proof = dict(accepted=False, completed=False, original_entry=True, session=session,
                 whole_user_workflow_accepted=False, final_visual_integration_accepted=False,
                 checks=[], captures=[], findings=[], step='initial', actions=[],
                 source_sha256={str((PRODUCT / name).relative_to(ROOT)).replace('\\', '/'):digest for name, digest in manifest['files_sha256'].items()},
                 scope='Bounded native Forces/Mesh/Layers journeys through original .cmd and header buttons. Ordinary Windows mouse/keyboard only; DOM/HTTP readback is supplementary. Explicit Network blocking is transport fault injection only. Import, cancellation races and overall milestone acceptance are outside this receipt.')
    for name in ['scripts/verify-ordinary-native-journey-v4.py', 'scripts/ordinary_native_input_v4.py', 'scripts/cef_page_v2.py',
                 'scripts/open-working-cosmos2.py', 'scripts/launch-working-cosmos2.py', 'Iniciar-Cosmos2.cmd',
                 'Abrir-Planetas.cmd', 'Abrir-Planetas-e-Luas.cmd', 'config/local-working-product.json']:
        proof['source_sha256'][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    def persist():
        OUT.write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    def check(name, **values):
        proof['checks'].append(dict(name=name, **values))
        proof['actions'] = list(window.actions)
        persist()
    persist()
    with Page() as page:
        window = NativeInput(session['app'], page)
        def wait(expression, timeout=90000):
            page.wait_for_function(expression, timeout=timeout)
        def click(selector, ready=None):
            proof['step'] = selector
            persist()
            wait('(()=>{const e=document.querySelector('+json.dumps(selector)+');return e&&!e.matches(":disabled");})()')
            window.click(selector)
            if ready:
                wait(ready)
        def capture(name):
            time.sleep(.4)
            path = FOLDER / (name+'.png')
            assert not path.exists()
            row = window.capture(path)
            row['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            proof['captures'].append(row)
            persist()
        def settled(kind):
            return '!window.'+('spatialInstrument' if kind=='spatial' else 'layerInstrument')+'.pending&&!window.'+('spatialInstrument' if kind=='spatial' else 'layerInstrument')+'.snapshot?.busy'
        def state(kind):
            return get('/api/'+kind+'/state')
        try:
            wait('location.pathname==="/"&&appState&&atlasState&&!pending&&spatialInstrument.online&&layerInstrument.online')
            for shortcut in ['Abrir-Planetas.cmd', 'Abrir-Planetas-e-Luas.cmd']:
                os.startfile(str(ROOT / shortcut))
                time.sleep(1)
                current = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
                assert current['app'] == session['app'] and current['serverScript'] == session['serverScript']
                engines = [p for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() == 'openspace.exe']
                assert len(engines) == 1
                check('original-shortcut-reuses-selected-session', shortcut=shortcut, app_pid=current['app'])
            for scale in ['1', '1.5']:
                proof['step'] = 'scale-'+scale
                window.select('#ui-scale', scale)
                wait('Number(getComputedStyle(document.body).zoom)==='+scale)
                before = physical(get('/api/state')['physics'])
                click('#forces', 'location.pathname==="/forces.html"&&typeof response!=="undefined"&&response?.ok&&!pending')
                assert page.evaluate('document.querySelectorAll("#scenarios button").length') == 12
                assert page.evaluate('document.querySelectorAll("#measurements .measurement").length') > 0
                actual_zoom = page.evaluate('Number(getComputedStyle(document.body).zoom)')
                if actual_zoom != float(scale):
                    proof['findings'].append(dict(kind='forces-scale-not-inherited', requested=scale, actual=actual_zoom))
                click('[data-scenario="strong"]', 'config.scenario==="strong"&&response.configuration.scenario==="strong"&&!pending')
                capture('forces-strong-'+scale.replace('.', '-'))
                check('forces-real-entry-and-strong-result', scale=scale, scenarios=12, physics_sha256=page.evaluate('response.physics_sha256'), actual_page_zoom=actual_zoom)
                click('a.back', 'location.pathname==="/"&&appState&&!pending&&spatialInstrument.online&&layerInstrument.online')
                assert physical(get('/api/state')['physics']) == before
                check('forces-return-preserves-physical-phase', scale=scale)
                click('#open-spatial', '!document.getElementById("spatial-panel").hidden')
                if get('/api/state')['mode'] == 'atlas':
                    click('#spatial-copy', 'appState.mode==="experiment"&&appState.physics?.paused&&appState.physics.bodies.length===4&&!pending')
                phase = physical(get('/api/state')['physics'])
                body = next(row['id'] for row in phase['bodies'] if row.get('reference_id') == 'sol:naif:399')
                proof['step'] = 'select-spatial-body'; persist()
                window.select('#spatial-body', body)
                click('#spatial-create', 'spatialInstrument.snapshot?.active&&!spatialInstrument.pending&&!spatialInstrument.snapshot.busy')
                s = state('spatial')
                assert s['artifact']['source']['reference_id'] == 'sol:naif:399' and not s['error']
                digest = s['artifact']['sha256']
                click('#spatial-visible', settled('spatial'))
                assert state('spatial')['artifact']['view']['visible'] is False
                click('#spatial-visible', settled('spatial'))
                proof['step']='fill-spatial-radial'; persist()
                window.fill('#spatial-radial', '1')
                click('#spatial-sample', settled('spatial'))
                assert state('spatial')['artifact']['view']['selected_radial_index'] == 1
                click('#spatial-active details:nth-of-type(2)>summary')
                click('#spatial-save', settled('spatial'))
                assert state('spatial')['checkpoint_available']
                click('#spatial-export', settled('spatial'))
                assert 'Exportado' in page.evaluate('document.getElementById("spatial-storage-status").textContent')
                assert state('spatial')['artifact']['sha256'] == digest
                assert physical(get('/api/state')['physics']) == phase
                capture('mesh-earth-'+scale.replace('.', '-'))
                click('#spatial-leave', '!spatialInstrument.snapshot.active&&!spatialInstrument.snapshot.recovery_required&&!spatialInstrument.pending')
                assert physical(get('/api/state')['physics']) == phase
                check('mesh-earth-visibility-probe-save-export-leave', scale=scale, sha256=digest)
                click('#open-layers', '!document.getElementById("layers-panel").hidden')
                assert page.evaluate('document.getElementById("spatial-panel").hidden')
                click('#layers-create', 'layerInstrument.snapshot?.active&&!layerInstrument.pending&&!layerInstrument.snapshot.busy')
                s = state('layers')
                assert s['artifact']['magnetic']['provenance']['model'] and not s['error']
                digest = s['artifact']['sha256']
                for selector, key in [('#layers-spatial-visible', 'spatial'), ('#layers-magnetic-visible', 'magnetic')]:
                    click(selector, settled('layers'))
                    assert state('layers')['artifact']['visible'][key] is False
                click('#layers-storage>summary')
                click('#layers-save', settled('layers'))
                click('#layers-export', settled('layers'))
                assert 'Exportado' in page.evaluate('document.getElementById("layers-storage-status").textContent')
                assert state('layers')['artifact']['sha256'] == digest
                assert physical(get('/api/state')['physics']) == phase
                capture('layers-earth-'+scale.replace('.', '-'))
                click('#layers-leave', '!layerInstrument.snapshot.active&&!layerInstrument.snapshot.recovery_required&&!layerInstrument.pending')
                assert physical(get('/api/state')['physics']) == phase
                check('layers-earth-visibility-save-export-leave', scale=scale, sha256=digest)
                click('#layers-panel-close')
            window.select('#ui-scale', '1')
            click('#open-spatial')
            page.call('Network.setBlockedURLs', {'urls':['http://127.0.0.1:4700/api/spatial/state']})
            wait('!spatialInstrument.online&&spatialInstrument.transportError')
            assert page.evaluate('document.getElementById("spatial-create").matches(":disabled")')
            capture('mesh-transport-error')
            page.call('Network.setBlockedURLs', {'urls':[]})
            click('#spatial-retry', 'spatialInstrument.online&&!spatialInstrument.transportError')
            check('mesh-transport-recovery-real-retry', fault_injection='CDP Network request blocking only; normal Windows click on retry')
            click('#spatial-panel-close')
            assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest()==digest for name,digest in proof['source_sha256'].items())
            proof['accepted'] = proof['completed'] = True
        except Exception:
            proof['failure'] = traceback.format_exc()
            try:
                capture('journey-failure')
            except Exception as error:
                proof['capture_failure'] = str(error)
        finally:
            page.call('Network.setBlockedURLs', {'urls':[]})
            proof['actions'] = window.actions
            proof['final_spatial'] = state('spatial')
            proof['final_layers'] = state('layers')
            proof['final_laboratory'] = get('/api/state')
            persist()
    print(json.dumps(dict(accepted=proof['accepted'], completed=proof['completed'], checks=len(proof['checks']),
                          findings=proof['findings'], step=proof['step'], failure=proof.get('failure')), ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
