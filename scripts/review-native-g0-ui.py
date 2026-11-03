"""Native navigation/search/pause captures accompanying the G0 evidence review."""
from pathlib import Path
import json
import runpy
import subprocess
import time
import urllib.request
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
engine=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
errors=[]
report={'runtime_receipt':json.loads((ROOT/'evidence/built-runtime.json').read_text()),'routes':[]}
def command(name,**values):
    request=urllib.request.Request('http://127.0.0.1:4700/api/command',
        data=json.dumps({'command':name,**values}).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(request,timeout=20))
def capture(name):
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)

command('atlas')
with Page() as page:
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:4700/')
    page.wait_for_function('socket && socket.readyState===WebSocket.OPEN')
    page.evaluate('document.getElementById("search").value="Lua";document.getElementById("search").dispatchEvent(new Event("input",{bubbles:true}))')
    assert page.evaluate('document.querySelector("[data-target=Moon]").offsetHeight>0')
    assert page.evaluate('document.querySelector("[data-target=Earth]").offsetHeight===0')
    page.evaluate('document.getElementById("search").value="";document.getElementById("search").dispatchEvent(new Event("input",{bubbles:true}))')
    for target,anchor in [('Earth','Earth'),('Moon','Moon'),('Galaxy','MilkyWayVolume')]:
        page.locator(f'[data-target="{target}"]').click()
        time.sleep(1)
        camera=engine('return {camera=openspace.navigation.getNavigationState()}')['payload']['1']['camera']
        assert camera['Anchor']==anchor
        image=f'cosmos2-g0bulk-{target.lower()}.png';capture(image)
        report['routes'].append({'target':target,'camera':camera,'capture':f'evidence/{image}'})
    command('enter',count=128);command('resume');time.sleep(.2)
    began=time.perf_counter();command('pause');report['p128_pause_http_ms']=(time.perf_counter()-began)*1000
    assert report['p128_pause_http_ms']<250
    command('reset',count=32);command('atlas')
    page.locator('[data-target="Earth"]').click()
    assert not errors,errors
report.update(search_filter=True,native_click_navigation=True,page_errors=errors,
              scope='Existing native CEF and actual window captures; visual acceptance recorded separately after inspection.')
(ROOT/'evidence/native-g0bulk-ui-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('runtime_receipt','routes')},indent=2))
