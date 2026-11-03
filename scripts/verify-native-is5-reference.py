"""Native CEF acceptance for the read-only B23 reference browser."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import hashlib
import json
import subprocess
import time
import traceback
import urllib.request
import urllib.error
import zipfile
from PIL import Image
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is5-reference-product0.16.0/app'
h=SourceFileLoader('reference_native_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def request(route,payload=None,expected=200):
    req=urllib.request.Request(h.BASE+route,data=None if payload is None else json.dumps(payload).encode(),
                              headers={'Content-Type':'application/json'})
    try:response=urllib.request.urlopen(req,timeout=390)
    except urllib.error.HTTPError as error:
        assert error.code==expected,(error.code,error.read().decode())
        return json.load(error)
    assert response.status==expected,response.status
    return json.load(response)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    path=ROOT/f'evidence/is5-native-reference-{args.label}.json'
    archive=ROOT/f'output/is5-native-reference-{args.label}.zip'
    if path.exists() or archive.exists():raise FileExistsError('Preserve native reference evidence')
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert session.get('is5ReferenceCandidate') is True and Path(session['serverScript']).resolve()==(APP/'server.py').resolve()
    anchor=ROOT/'evidence/is5-solar-reference-browser-20261029a.json'
    accepted=json.loads(anchor.read_text());assert accepted['accepted']
    hashes={**accepted['source_sha256'],anchor.relative_to(ROOT).as_posix():sha(anchor)}
    for name in ['evidence/is5-native-coulomb-20261029c.json','evidence/is5-coulomb-visual-review-20261029c.json',
                 'evidence/is5-coulomb-zone-profile-audit-20261029c.json']:
        prior=ROOT/name;evidence=json.loads(prior.read_text());assert evidence['accepted']
        hashes.update(evidence.get('source_sha256',{}));hashes[name]=sha(prior)
        if 'profile' in evidence:
            measured=ROOT/evidence['profile'];assert sha(measured)==evidence['profile_sha256']
            hashes.update(json.loads(measured.read_text())['source_sha256']);hashes[evidence['profile']]=sha(measured)
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__),ROOT/'scripts/prepare-is5-reference-product.py',ROOT/'scripts/launch-is5-reference-candidate.py',
              ROOT/'IS-5-REFERENCIAS-SOLARES-PRODUTO-CONTRATO.md',APP.parent/'build-manifest.json',
              ROOT/'scripts/cef_page.py',ROOT/'scripts/verify-native-solar-integration.py',
              ROOT/'scripts/engine-command.py',ROOT/'scripts/capture-window.ps1',
              ROOT/'scripts/revise-is5-reference-navigation.py',
              ROOT/'evidence/is5-native-reference-20261029a.json',
              ROOT/'evidence/is5-reference-visual-review-20261029a.json',
              ROOT/'output/is5-reference-navigation-revision-20261029b/stellar-reference-before.css',
              ROOT/'output/is5-reference-navigation-revision-20261029b/build-manifest-before.json']
    hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),
           owner_sha256=sha(ROOT/'user/sessions/latest.json'),checks=[],refusals=0,captures=[],page_errors=[])
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def check(name):r['checks'].append(name);persist();print(json.dumps(dict(check=name,passed=True)),flush=True)
    def zone():return request('/api/solar-zone/state')
    def command(action,**extra):
        payload=dict(command=action,**extra)
        if action not in ['create','load_saved']:
            payload['guard']={k:zone()['worker'][k] for k in ['worker_id','artifact_id','edit_token','revision']}
        return request('/api/solar-zone/command',payload)
    def select(page,model,index):
        if page.evaluate('document.getElementById("stellar-reference-model").value')!=model:
            page.locator('#stellar-reference-model').select_option(model)
            page.wait_for_function('stellarReferenceState.sample?.model==='+json.dumps(model))
        page.evaluate('document.getElementById("stellar-reference-number").value='+str(index)+';document.getElementById("stellar-reference-number").dispatchEvent(new Event("change"))')
        page.wait_for_function('stellarReferenceState.sample?.model==='+json.dumps(model)+'&&stellarReferenceState.sample.index==='+str(index))
    def key(page,name,code):
        for kind in ['keyDown','keyUp']:
            page.call('Input.dispatchKeyEvent',dict(type=kind,key=name,code=name,windowsVirtualKeyCode=code,nativeVirtualKeyCode=code))
    def capture(page,name,scale='1',pressure=False,focus=None):
        page.locator('#stellar-reference-scale').select_option(scale)
        page.evaluate('document.getElementById("stellar-reference-panel").scrollTop=0')
        if pressure:page.evaluate('document.getElementById("stellar-reference-pressure").scrollIntoView({block:"end"})')
        elif focus:page.evaluate('document.getElementById('+json.dumps('stellar-reference-'+focus)+').scrollIntoView({block:"center"})')
        time.sleep(.3)
        image=ROOT/f'evidence/cosmos2-is5-reference-{args.label}-{name}.png'
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',image.name],check=True,capture_output=True)
        assert Image.open(image).size==(1920,1080)
        r['captures'].append(dict(path=image.relative_to(ROOT).as_posix(),sha256=sha(image)));persist()
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.BASE+'/')
            page.wait_for_function('appState!==null&&solarZoneState!==null&&!pending')
            if zone()['active']:command('leave')
            if request('/api/state')['mode']=='experiment':request('/api/command',dict(command='atlas'))
            page.wait_for_function('appState?.mode==="atlas"&&!pending')
            before=request('/api/state');h.click(page,'#open-stellar-reference')
            page.wait_for_function('stellarReferenceState.sample?.model==="GS98"&&stellarReferenceState.sample.index===3')
            assert request('/api/stellar-reference/catalog')['models']==['GS98','AGSS09','AAG21','C11','MB22m','MB22p']
            for model in ['GS98','AGSS09','AAG21','C11','MB22m','MB22p']:
                select(page,model,100)
                expected=request(f'/api/stellar-reference/sample?model={model}&index=100')
                assert page.evaluate('stellarReferenceState.sample')==expected
                assert len(page.evaluate('stellarReferenceState.series.r_over_Rsun'))==2001
            stable=lambda p:None if p is None else {k:p.get(k) for k in ['system_id','edit_token','revision','time','bodies','atlas_initial','interventions']}
            after=request('/api/state')
            assert after['mode']==before['mode'] and stable(after['physics'])==stable(before['physics'])
            check('Six offline model selectors and exact radial probes preserve Atlas/laboratory state')
            for route in ['sample?model=GS98&index=true','sample?model=GS98&index=2001','sample?model=GS98&index=1&index=2',
                          'series?model=unknown','catalog?x=1','sample?model=GS98']:
                assert request('/api/stellar-reference/'+route,expected=400)['ok'] is False;r['refusals']+=1
            select(page,'GS98',3)
            page.evaluate('document.getElementById("stellar-reference-model").focus()');key(page,'Tab',9)
            assert page.evaluate('document.activeElement.id')=='stellar-reference-reload'
            page.evaluate('document.getElementById("stellar-reference-index").focus()');key(page,'ArrowRight',39)
            page.wait_for_function('stellarReferenceState.sample?.index===4')
            select(page,'GS98',3)
            assert page.evaluate('stellarReferenceState.sample.ideal_comparison.upper_mass_number_bound')==1
            for scale in ['1','1.5']:
                tag='100' if scale=='1' else '150';capture(page,'GS98-core-'+tag,scale);capture(page,'GS98-pressure-'+tag,scale,True)
            capture(page,'GS98-ideal-bracket-150','1.5',focus='comparison')
            select(page,'GS98',0)
            assert 'central_interpolation_residue' in page.evaluate('stellarReferenceState.sample.quality_flags')
            assert page.evaluate('stellarReferenceState.sample.ideal_comparison') is None
            capture(page,'central-flags-150','1.5',focus='quality')
            select(page,'AGSS09',350);capture(page,'AGSS09-core-100')
            select(page,'MB22p',2000)
            assert page.evaluate('stellarReferenceState.sample.ideal_comparison') is None
            capture(page,'MB22p-surface-150','1.5',True)
            assert page.evaluate('document.getElementById("stellar-reference-source").href')=='https://zenodo.org/records/10822316'
            check('Strict read-only queries, keyboard navigation, A>=1 bracket, central flags, uncomputed cases and100/150% curves')
            page.evaluate('document.getElementById("stellar-reference-close").focus()');key(page,'Escape',27)
            assert page.evaluate('document.getElementById("stellar-reference-panel").hidden')
            page.locator('#ui-scale').select_option('1');h.click(page,'#copy-solar')
            page.wait_for_function('!pending&&appState?.physics?.paused&&appState.physics.bodies.length===4',timeout=70000)
            source=request('/api/state')['physics'];orbital=h.phase(source)
            sg={k:source[k] for k in ['system_id','edit_token','revision','time']}|{'frame':source['contract']['frame']}
            command('create',source_guard=sg,configuration=page.evaluate('zoneConfiguration()'))
            page.wait_for_function('solarZoneState?.active&&!solarZoneCurvePending&&solarZoneCurveId===solarZoneState.worker.artifact_id',timeout=380000)
            held=zone()['worker']
            page.wait_for_function('getComputedStyle(document.getElementById("open-stellar-reference")).pointerEvents!=="none"')
            h.click(page,'#open-stellar-reference')
            page.wait_for_function('!document.getElementById("stellar-reference-panel").hidden')
            select(page,'GS98',100)
            capture(page,'with-calculated-zone-150','1.5')
            current=zone()['worker']
            assert all(current[k]==held[k] for k in ['worker_id','artifact_id','artifact_sha256','edit_token','revision','configuration','source','view'])
            assert h.phase(request('/api/state')['physics'])==orbital
            check('Reference consultation preserves calculated Coulomb artifact, archived source and orbital phase')
            assert not r['page_errors'],r['page_errors']
            assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
            assert all(sha(ROOT/n)==v for n,v in hashes.items())
            r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            with Page() as page:
                page.evaluate('document.getElementById("stellar-reference-panel").hidden=true')
                page.locator('#ui-scale').select_option('1')
            if zone()['active']:command('leave')
            if request('/api/state')['mode']=='experiment':request('/api/command',dict(command='atlas'))
            h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        persist()
    print(json.dumps({k:r.get(k) for k in ['accepted','checks','refusals','failure','cleanup_failure']}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
