"""Preserve the first candidate's actual CEF cancellation admission evidence."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import hashlib
import json
import subprocess
import time
import traceback
import urllib.request
import zipfile
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is5-compression-product0.17.0/app'
h=SourceFileLoader('compression_cancel_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    path=ROOT/'evidence/is5-compression-cancel-cef-20261101b.json'
    archive=ROOT/'output/is5-compression-cancel-cef-20261101b.zip'
    if path.exists() or archive.exists():raise FileExistsError('Preserve diagnostic')
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__),APP.parent/'build-manifest.json',ROOT/'scripts/cef_page.py',
              ROOT/'scripts/launch-is5-compression-candidate.py']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),
           scope='CEF cancellation control admission diagnostic; not native/visual/profile acceptance.')
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def zone():return h.get('/api/solar-zone/state')
    try:
        session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        assert Path(session['serverScript']).resolve()==(APP/'server.py').resolve()
        with Page() as page:
            page.goto(h.BASE+'/');page.wait_for_function('solarZoneState!==null&&!pending')
            assert not zone()['active']
            h.click(page,'#copy-solar')
            page.wait_for_function('!pending&&appState?.physics?.paused&&appState.physics.bodies.length===4',timeout=70000)
            page.evaluate('document.getElementById("zone-setup").open=true')
            h.click(page,'#zone-create')
            page.wait_for_function('solarZonePending')
            deadline=time.monotonic()+10
            while not zone()['calculation'] and time.monotonic()<deadline:time.sleep(.05)
            assert zone()['calculation']['cancellable']
            # More than five normal state polling periods; calculation remains real.
            time.sleep(1.2)
            r['server_state']=zone()
            r['CEF']=page.evaluate('({pending:solarZonePending,calculation:solarZoneState.calculation??null,hidden:document.getElementById("zone-cancel-setup").hidden,status:document.getElementById("zone-setup-status").textContent})')
            capture=ROOT/'evidence/cosmos2-is5-compression-20261101b-missing-cancel.png'
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',capture.name],check=True,capture_output=True)
            r['capture']=dict(path=capture.relative_to(ROOT).as_posix(),sha256=sha(capture))
            r['completed']=True
            r['accepted']=not r['CEF']['hidden'] and r['CEF']['calculation'] is not None
            if not r['accepted']:r['failure']='Server publishes cancellable transaction; CEF polling discards state while command is pending, leaving the cancel button hidden.'
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            state=zone()
            if state['calculation']:
                payload=json.dumps(dict(transaction_id=state['calculation']['transaction_id'])).encode()
                request=urllib.request.Request(h.BASE+'/api/solar-zone/cancel',data=payload,headers={'Content-Type':'application/json'})
                began=time.perf_counter()
                with urllib.request.urlopen(request,timeout=10) as reply:r['diagnostic_direct_cancel']=json.load(reply)
                r['direct_cancel_s']=time.perf_counter()-began
            h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception:r['cleanup_failure']=traceback.format_exc()
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        persist()
    print(json.dumps({k:r.get(k) for k in ['accepted','completed','failure','direct_cancel_s','cleanup_failure']}),flush=True)


if __name__=='__main__':main()
