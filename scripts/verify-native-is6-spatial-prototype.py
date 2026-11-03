"""Own diagnostic native mesh proof hosted by the preserved0.17.2 application."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import time
import traceback
import zipfile
from PIL import Image
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is6-spatial-scene-staging'
h=SourceFileLoader('is6_native_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is6-spatial-native-{args.label}';receipt=ROOT/f'evidence/is6-spatial-native-{args.label}.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native mesh evidence')
    anchor=ROOT/'evidence/is6-spatial-scene-files-20261101a.json';accepted=json.loads(anchor.read_text());assert accepted['accepted']
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve()==(ROOT/'output/is5-compression-product0.17.2/app/server.py').resolve()
    files=[Path(__file__),anchor,ROOT/'scripts/cef_page.py',ROOT/'scripts/engine-command.py',
           ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/capture-window.ps1',
           ROOT/'scripts/launch-is5-compression-admission.py',ROOT/'config/window-1080.json',ROOT/'config/cosmos2.cfg']
    hashes=dict(accepted['source_sha256']);hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    assert all(sha(ROOT/n)==v for n,v in hashes.items());folder.mkdir();archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),session=session,
           owner_sha256=sha(ROOT/'user/sessions/latest.json'),limits_before_execution=dict(scene_ready_s=15.),
           cases=[],captures=[],page_errors=[],
           scope='Temporary native prototype only. Diagnostic caption is not a product0.18 UI; captures need separate visual review. No performance or promotion acceptance.')
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def capture(name):
        path=ROOT/f'evidence/cosmos2-is6-spatial-{args.label}-{name}.png'
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',path.name],check=True,capture_output=True)
        pixels=Image.open(path);assert pixels.size==(1920,1080)
        rgb=folder/path.name;pixels.convert('RGB').save(rgb)
        roi=pixels.convert('RGB').crop((600,220,1300,820))
        count=sum((red<190 and green>120 and blue>160) or (red>100 and green<190 and blue>170) for red,green,blue in roi.get_flattened_data())
        row=dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),RGB_inspection=rgb.relative_to(ROOT).as_posix(),RGB_sha256=sha(rgb),wire_color_pixels_in_fixed_ROI=count)
        r['captures'].append(row);persist();return count
    persist();scene=None
    try:
        sys.path.insert(0,str(STAGE));import is6_spatial_scene as renderer
        gen=renderer.generation();assert sha(Path(session['runtime'])/'bin/OpenSpace.exe')==gen['engine_sha256']
        r['generation']=gen
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.BASE+'/')
            page.wait_for_function('appState!==null&&!pending&&solarZoneState!==null')
            assert not h.get('/api/solar-zone/state')['active']
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            page.wait_for_function('appState?.mode==="atlas"&&!pending');h.click(page,'#copy-solar')
            page.wait_for_function('!pending&&appState?.physics?.paused&&appState.physics.bodies.length===4',timeout=70000)
            phase=h.get('/api/state')['physics'];held=h.phase(copy.deepcopy(phase))
            page.evaluate('(()=>{const s=document.createElement("style");s.id="is6-diagnostic-style";s.textContent="#lab-panel,#lab-details,#scene-targets{display:none!important}#is6-diagnostic-caption{position:absolute;right:28px;top:124px;width:330px;padding:20px;pointer-events:none;white-space:pre-line;font-size:14px;line-height:1.6;color:#daedf1;background:#08151ef2;border:1px solid #385868;border-radius:12px}";document.head.append(s);const p=document.createElement("aside");p.id="is6-diagnostic-caption";document.body.append(p);})()')
            for body in phase['bodies']:
                config=copy.deepcopy(renderer.artifact.DEFAULT_CONFIGURATION)
                run=renderer.artifact.Run.create(phase,dict(body_id=body['id'],source_guard=renderer.artifact.body.guard(phase)),config)
                payload=run.payload;before=renderer.artifact.digest(payload);code=body['reference_id'].split(':')[-1]
                saved=folder/('artifact-'+code+'.json');saved.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                scene=renderer.Scene(h.native,run,folder/('scene-'+code));native=scene.attach();assert scene.ready_s<=15.
                assert Path(native['file']).resolve()==(scene.folder/'wire.speck').resolve()
                bound=payload['binding'];configuration=bound['source_configuration']
                caption=('PROTÓTIPO · MALHA ESPAÇO-TEMPORAL\nCorte espacial do modelo\n\n'+bound['name']+' · época '+bound['epoch']['utc']+'\nPlano: GALACTIC XY\nRref = '+format(configuration['material_radius_m'],'.9g')+' m\nGM = '+format(configuration['GM_m3_s2'],'.9g')+' m³/s²\nAltura do desenho ×200\n\nCiano: anéis · violeta: meridianos\nInterior fora do modelo.\nReferência esférica isolada; órbita pausada.\nSondas usam a métrica sem ampliação.')
                page.evaluate('document.getElementById("is6-diagnostic-caption").textContent='+json.dumps(caption));time.sleep(.4)
                visible_pixels=capture(code+'-visible')
                for visible in [False,True]:
                    scene.set_visible(visible);assert scene.read_native()['draw'] is visible
                    assert h.phase(h.get('/api/state')['physics'])==held and renderer.artifact.digest(run.payload)==before
                    if not visible and code=='10':
                        time.sleep(.3);hidden_pixels=capture(code+'-hidden');assert visible_pixels-hidden_pixels>2000,(visible_pixels,hidden_pixels)
                frame=scene.frame;focus=scene.focus;wire=scene.wire;ready=scene.ready_s
                scene.close();scene=None
                absence=h.native('return {frame=openspace.hasSceneGraphNode('+json.dumps(frame)+'),focus=openspace.hasSceneGraphNode('+json.dumps(focus)+'),wire=openspace.hasSceneGraphNode('+json.dumps(wire)+')}')
                assert not any(absence.values()) and h.phase(h.get('/api/state')['physics'])==held
                r['cases'].append(dict(reference_id=body['reference_id'],scene_ready_s=ready,native=native,visible_color_pixels=visible_pixels,
                    artifact=saved.relative_to(ROOT).as_posix(),artifact_sha256=sha(saved),restored_scene_and_orbit=True))
                persist();print(json.dumps(r['cases'][-1]),flush=True)
            page.evaluate('document.getElementById("is6-diagnostic-style").remove();document.getElementById("is6-diagnostic-caption").remove()')
            assert not r['page_errors'] and sha(ROOT/'user/sessions/latest.json')==r['owner_sha256']
            assert renderer.generation()==gen and all(sha(ROOT/n)==v for n,v in hashes.items())
            r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            if scene:scene.close()
            with Page() as page:page.evaluate('document.getElementById("is6-diagnostic-style")?.remove();document.getElementById("is6-diagnostic-caption")?.remove()')
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        try:h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception as error:r['shutdown_response']=str(error)
        persist()
    print(json.dumps(dict(accepted=r['accepted'],completed=r['completed'],cases=len(r['cases']),captures=len(r['captures']),failure=r.get('failure'),cleanup_failure=r.get('cleanup_failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
