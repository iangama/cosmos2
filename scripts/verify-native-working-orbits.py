"""Use the original header and ordinary mouse controls for the newly delivered orbit bench."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import urllib.request
from cef_page_v2 import Page
from ordinary_option_input_v3 import OptionInput

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'output/original-flow-hotfix-product0.28.4'
FOLDER=ROOT/'output/native-working-orbits-20261121a'
OUT=ROOT/'evidence/native-working-orbits-20261121a.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def get():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=30))
def material(p):return {k:p.get(k) for k in ['system_id','revision','time','paused','bodies','atlas_initial','interventions']}


def main():
    assert not FOLDER.exists() and not OUT.exists();FOLDER.mkdir()
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    entry=json.loads((ROOT/'evidence/original-flow-entry-orbits-20261121a.json').read_text());assert entry['accepted'] and entry['session']['app']==session['app']
    saved=json.loads((ROOT/'evidence/orbits-session-preservation-20261121a.json').read_text());assert saved['accepted']
    manifest=json.loads((PRODUCT/'build-manifest.json').read_text());assert all(sha(PRODUCT/n)==seal for n,seal in manifest['files_sha256'].items())
    proof=dict(accepted=False,completed=False,checks=[],captures=[],actions=[],session=session,
      script_sha256=sha(Path(__file__)),manifest_sha256=sha(PRODUCT/'build-manifest.json'),
      scope='Original launcher/header, ordinary Windows clicks/typing and visible option lists at100%/150%. Discover and use timelike orbits, circular choice, clock view, playback, clock operator, invalid conditions and recovery, return to saved owner experiment/Atlas. DOM/HTTP observe only. No transferred0.28.2 performance or whole C2-14 acceptance; no claim of native calculation-cancellation timing.')
    def persist():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with Page() as page:
        window=OptionInput(session['app'],page)
        def wait(expr):page.wait_for_function(expr,timeout=60000)
        def click(selector,ready=None):
            proof['step']=selector;persist();window.click(selector)
            if ready:wait(ready)
        def capture(name):
            path=FOLDER/(name+'.png');assert not path.exists();time.sleep(.3)
            row=window.capture(path);row['sha256']=sha(path);proof['captures'].append(row);persist()
        def check(name,**values):proof['checks'].append(dict(name=name,**values));persist()
        def phase_stable():assert material(get()['physics'])==phase
        def complete():wait('!pending&&response?.result.timelike&&!byId("force-status").classList.contains("error")')
        try:
            assert page.evaluate('location.pathname==="/"&&!pending&&appState.mode==="atlas"')
            click('#experiment','!pending&&appState.mode==="experiment"')
            click('#load','!pending&&appState.physics?.paused')
            phase=material(get()['physics']);assert phase=={k:saved['physical_after'].get(k) for k in phase}
            click('#atlas','!pending&&appState.mode==="atlas"')
            click('#forces','location.pathname==="/forces.html"&&typeof response!=="undefined"&&response&&!pending')
            click('[data-scenario="timelike-orbits"]');complete()
            assert page.evaluate('response.result.time_s.length')==1025
            assert page.evaluate('config.scenario')=='timelike-orbits'
            click('#scene-title');capture('orbit-discovered-from-original-header')
            check('original-launcher-header-and-scenario-open-complete-timelike-result')
            window.select('#parameters [name="orbit_kind"]','circular')
            assert page.evaluate('document.querySelector("[data-parameter=eccentricity]").hidden')
            click('#calculate');complete()
            assert page.evaluate('config.parameters.orbit_kind')=='circular'
            check('mouse-selects-circular-and-applies-its-analytic-reference')
            window.select('#timelike-view','clocks')
            click('#timelike-view');capture('clock-view-selected-by-mouse')
            click('#animate','animating')
            wait('Number(byId("time-index").value)>0&&Number(byId("time-index").value)<1024')
            click('#animate','!animating')
            assert page.evaluate('byId("timelike-readings").textContent.includes("Atraso aplicado")')
            check('clock-view-and-native-playback-show-current-readings')
            click('[data-effect="proper_clock_rate"]');complete()
            assert page.evaluate('response.result.timelike.clock_effect_applied') is False
            assert page.evaluate('response.result.timelike.readings.every(r=>r.applied_lag_s===0)')
            check('clock-operator-changes-the-applied-clock-while-owner-phase-stays-intact');phase_stable()
            before=page.evaluate('JSON.stringify(response)')
            window.fill('#parameters [name="radial_cycles"]','1.5')
            click('#calculate','!pending&&byId("force-status").classList.contains("error")')
            assert page.evaluate('JSON.stringify(response)')==before
            assert page.evaluate('!byId("result-draft-note").hidden')
            click('#restore-result-conditions','!pending&&draftConfig.parameters.radial_cycles===8')
            assert page.evaluate('JSON.stringify(response)')==before
            check('invalid-fractional-cycle-keeps-confirmed-result-and-recovers-with-ordinary-button')
            click('a.back','location.pathname==="/"&&typeof appState!=="undefined"&&appState&&!pending');phase_stable()
            window.select('#ui-scale','1.5')
            click('#forces','location.pathname==="/forces.html"&&typeof response!=="undefined"&&response&&!pending')
            assert page.evaluate('Number(getComputedStyle(document.body).zoom)')==1.5
            click('[data-scenario="timelike-orbits"]');complete()
            window.select('#timelike-view','clocks')
            click('#timelike-readings');capture('clock-readings-at150')
            window.select('#parameters [name="orientation"]','negative')
            click('#calculate');complete()
            assert page.evaluate('config.parameters.orientation')=='negative'
            check('ordinary-view-and-orientation-options-work-at150');phase_stable()
            click('a.back','location.pathname==="/"&&typeof appState!=="undefined"&&appState&&!pending')
            window.select('#ui-scale','1');phase_stable()
            assert all(sha(PRODUCT/n)==seal for n,seal in manifest['files_sha256'].items())
            proof['owner_phase_preserved']=True;proof.update(accepted=True,completed=True)
        except Exception:proof['failure']=traceback.format_exc()
        finally:proof['actions']=list(window.actions);persist()
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','step','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
