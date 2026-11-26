"""Reproduce a failed recalculation exporting another scenario through ordinary native controls."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import urllib.request

from cef_page_v2 import Page
from ordinary_native_input_v5 import NativeInput

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'output/forces-confirmed-result-before-20261120a'
OUT = ROOT / 'evidence/forces-confirmed-result-before-20261120a.json'


def get(route):
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700'+route, timeout=20))


def phase():
    value = get('/api/state')['physics']
    return None if value is None else {key:value.get(key) for key in ['system_id','edit_token','revision','time','paused','bodies','atlas_initial','interventions']}


def main():
    assert not OUT.exists() and not FOLDER.exists()
    FOLDER.mkdir()
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    product = Path(session['serverScript']).parent.parent
    proof = dict(completed=False, reproduced=False, feature_working=False, session=session, actions=[],
                 scope='Native error-state reproduction only. Original header and Windows mouse controls; CDP blocks the evaluate request only as a declared transport fault. DOM/HTTP readback observes results.')
    for name in ['forces.js','forces.html','forces.css']:
        proof.setdefault('source_sha256', {})[(product / 'app/ui' / name).relative_to(ROOT).as_posix()] = hashlib.sha256((product / 'app/ui' / name).read_bytes()).hexdigest()
    before = phase()
    with Page() as page:
        window = NativeInput(session['app'], page)
        try:
            page.wait_for_function('location.pathname==="/"&&appState&&!pending')
            window.click('#forces')
            page.wait_for_function('location.pathname==="/forces.html"&&typeof response!=="undefined"&&response?.ok&&!pending')
            proof['confirmed_before'] = page.evaluate('({configuration:response.configuration,physics_sha256:response.physics_sha256,title:document.getElementById("scene-title").textContent})')
            assert proof['confirmed_before']['configuration']['scenario'] == 'gravity'
            page.call('Network.setBlockedURLs', {'urls':['http://127.0.0.1:4700/api/forces/evaluate']})
            window.click('[data-scenario="strong"]')
            page.wait_for_function('!pending&&document.getElementById("force-status").classList.contains("error")')
            proof['after_rejected_recalculation'] = page.evaluate('({editing_configuration:config,shown_configuration:response.configuration,shown_physics_sha256:response.physics_sha256,title:document.getElementById("scene-title").textContent,error:document.getElementById("force-status").textContent})')
            shown = proof['after_rejected_recalculation']
            assert shown['editing_configuration']['scenario'] == 'strong' and shown['shown_configuration']['scenario'] == 'gravity'
            assert shown['shown_physics_sha256'] == proof['confirmed_before']['physics_sha256']
            time.sleep(.3)
            capture = FOLDER / 'rejected-recalculation.png'
            proof['capture'] = window.capture(capture)
            proof['capture']['sha256'] = hashlib.sha256(capture.read_bytes()).hexdigest()
            page.call('Network.setBlockedURLs', {'urls':[]})
            window.click('#export-forces')
            page.wait_for_function('!pending&&typeof lastForcesExport!=="undefined"&&lastForcesExport?.ok')
            proof['export'] = page.evaluate('({scenario:lastForcesExport.configuration.scenario,physics_sha256:lastForcesExport.physics_sha256,path:lastForcesExport.export_file})')
            assert proof['export']['scenario'] == 'strong'
            assert proof['export']['physics_sha256'] != shown['shown_physics_sha256']
            exported = Path(proof['export']['path'])
            assert exported.is_relative_to(product)
            proof['export']['sha256'] = hashlib.sha256(exported.read_bytes()).hexdigest()
            window.click('a.back')
            page.wait_for_function('location.pathname==="/"&&appState&&!pending')
            assert phase() == before
            assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest for name,digest in proof['source_sha256'].items())
            proof.update(completed=True, reproduced=True, physical_phase_preserved=True)
        except Exception:
            proof['failure'] = traceback.format_exc()
        finally:
            page.call('Network.setBlockedURLs', {'urls':[]})
            proof['actions'] = window.actions
            OUT.write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({key:proof.get(key) for key in ['completed','reproduced','export','physical_phase_preserved','failure']}, ensure_ascii=False))
    return 0 if proof['reproduced'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
