"""Real CEF regression for a hidden, already confirmed trajectory's status."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time
import traceback
from cef_page import Page
from importlib.machinery import SourceFileLoader

ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'output/is4-solar-wind-product0.9.1/app'
h=SourceFileLoader('wind_hidden_test',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
    if not a.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.label):p.error('Invalid label')
    path=ROOT/('evidence/is4-wind-hidden-label-'+a.label+'.json')
    if path.exists():raise FileExistsError('Preserve regression')
    files=[*APP.rglob('*.py'),APP/'ui/is4-particle.js',Path(__file__)];hashes={f.relative_to(ROOT).as_posix():sha(f) for f in files}
    r=dict(schema=1,accepted=False,source_sha256=hashes,page_errors=[])
    try:
        for file in APP.glob('*.py'):assert sha(file)==sha(ROOT/'output/is4-solar-wind-product0.9.0/app'/file.name)
        with Page() as page:
            page.on('pageerror',lambda e:r['page_errors'].append(e));page.goto(h.BASE+'/');page.wait_for_function('particleState!==null&&appState?.mode==="atlas"&&!pending')
            h.click(page,'#copy-solar');page.wait_for_function('!pending&&appState?.physics?.paused&&appState?.physics?.bodies.length===4',timeout=70000)
            page.evaluate('document.getElementById("wind-setup").open=true');page.wait_for_function('!document.getElementById("wind-create").disabled');page.locator('#wind-create').click()
            page.wait_for_function('!particlePending&&particleState?.active&&particleState?.view?.confirmed_phase?.time_s===0',timeout=25000)
            page.evaluate('particleCommand("advance",{steps:64})');page.wait_for_function('!particlePending&&!particleState.view.pending_sequence&&particleState.view.confirmed_phase.time_s===particleState.worker.experiment.phase.time_s')
            before=h.get('/api/particles/state')['worker']['experiment']['phase']
            page.evaluate('particleCommand("visible",{visible:false})');page.wait_for_function('!particlePending&&!particleState.view.visible')
            text=page.evaluate('document.getElementById("particle-provenance").textContent')
            assert 'Trajetória oculta; dados confirmados até' in text and 'Orientação IAU_SUN' in text and 'Aguardando' not in text,text
            assert h.get('/api/particles/state')['worker']['experiment']['phase']==before
            page.locator('#ui-scale').select_option('1.5');page.evaluate('document.getElementById("particle-provenance").parentElement.open=true;document.getElementById("particle-provenance").scrollIntoView({block:"start"})');time.sleep(.3)
            name='cosmos2-is4-wind-hidden-label-'+a.label+'-150.png';subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
            r.update(capture='evidence/'+name,capture_sha256=sha(ROOT/'evidence'/name),status_text=text)
            assert not r['page_errors']
        assert all(sha(ROOT/n)==v for n,v in hashes.items());r.update(accepted=True,scope='UI hidden-status regression and unchanged Python sources only; no new numerical or performance claim.')
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            with Page() as page:
                if h.get('/api/particles/state')['active']:page.evaluate('particleCommand("leave")');page.wait_for_function('!particlePending&&!particleState.active')
                page.locator('#ui-scale').select_option('1')
                if h.get('/api/state')['mode']=='experiment':h.click(page,'#atlas')
        except Exception:r['cleanup_failure']=traceback.format_exc()
        path.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(accepted=r['accepted'],failure=r.get('failure'))));return 0 if r['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
