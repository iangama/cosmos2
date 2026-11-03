"""Additional native setup/probe/model close-ups; source clock must remain unchanged."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time
import traceback
from importlib.machinery import SourceFileLoader
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('wind_detail_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
phase=lambda s:{k:s[k] for k in ['system_id','edit_token','revision','time','bodies','interventions','atlas_initial']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);args=p.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):p.error('Invalid label')
    path=ROOT/('evidence/is4-wind-detail-captures-'+args.label+'.json')
    if path.exists():raise FileExistsError('Preserve detail captures')
    report=dict(schema=1,completed=False,accepted=False,captures=[],page_errors=[])
    try:
        with Page() as page:
            page.on('pageerror',lambda e:report['page_errors'].append(e));page.goto(h.BASE+'/');page.wait_for_function('appState!==null&&particleState!==null&&!pending')
            assert not h.get('/api/particles/state')['active'],'Wait for active native journey/profile to finish'
            if h.get('/api/state')['mode']=='atlas':h.click(page,'#copy-solar');page.wait_for_function('!pending&&appState?.physics?.bodies.length===4',timeout=70000)
            before=phase(h.get('/api/state')['physics'])
            def capture(name,selector,scale,block='start'):
                page.locator('#ui-scale').select_option(scale)
                page.evaluate('(() => {const e=document.querySelector('+json.dumps(selector)+');for(let a=e;a;a=a.parentElement)if(a.tagName==="DETAILS")a.open=true;e.scrollIntoView({block:'+json.dumps(block)+'});})()')
                page.wait_for_function('document.documentElement.scrollWidth<=innerWidth+1');time.sleep(.3)
                filename='cosmos2-is4-wind-details-'+args.label+'-'+name+'-'+str(int(float(scale)*100))+'.png'
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',filename],check=True,capture_output=True)
                report['captures'].append(dict(path='evidence/'+filename,sha256=sha(ROOT/'evidence'/filename)))
            for scale in ['1','1.5']:capture('setup','#wind-setup',scale)
            page.locator('#ui-scale').select_option('1')
            page.evaluate('particleCommand("load_saved")');page.wait_for_function('!particlePending&&particleState.active&&particleState.view.confirmed_phase.time_s===particleState.worker.experiment.phase.time_s',timeout=25000)
            page.evaluate('particleCommand("sample")');page.wait_for_function('!particlePending&&particleState.sample')
            assert not page.evaluate('particleError')
            for scale in ['1','1.5']:
                capture('probe-top','#particle-reading',scale)
                capture('probe-energy','#particle-reading',scale,'end')
            capture('model','#particle-provenance','1.5')
            assert phase(h.get('/api/state')['physics'])==before and not report['page_errors']
            report.update(completed=True,particle=h.get('/api/particles/state'),source_phase_unchanged=True,scope='Close-up native PNG for manual review only; acceptance remains false until images reviewed separately.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        try:
            with Page() as page:
                if h.get('/api/particles/state')['active']:page.evaluate('particleCommand("leave")');page.wait_for_function('!particlePending&&!particleState.active')
                page.locator('#ui-scale').select_option('1')
                if h.get('/api/state')['mode']=='experiment':h.click(page,'#atlas')
        except Exception:report['cleanup_failure']=traceback.format_exc()
        path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=report['completed'],captures=len(report['captures']),failure=report.get('failure'))))
    return 0 if report['completed'] else 1

if __name__=='__main__':raise SystemExit(main())
