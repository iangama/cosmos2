"""Wait for the real scene and native CEF before starting a local verification."""
import json
import time
import urllib.request
from websockets.sync.client import connect
from cef_page import Page

began=time.perf_counter();attempts=0;last=None
while time.perf_counter()-began<45:
    attempts+=1
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=2,close_timeout=.2,ping_interval=None) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'return':True,'script':
                'return {earth=openspace.hasSceneGraphNode("Earth"),gui=openspace.propertyValue("Modules.CefWebGui.GuiUrl")}'}}))
            result=json.loads(ws.recv(timeout=2)).get('payload',{}).get('1',{})
            if result.get('earth') and result.get('gui')=='http://127.0.0.1:4700/':
                targets=json.load(urllib.request.urlopen('http://127.0.0.1:8088/json/list',timeout=2))
                if any(t['url'].startswith('http://127.0.0.1:4700') for t in targets):
                    api=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=2))
                    if not isinstance(api,dict) or api.get('error'):raise ValueError('Backend state did not confirm readiness')
                    with Page() as page:
                        page.goto('http://127.0.0.1:4700/',timeout=5000)
                        page.wait_for_function('typeof appState!=="undefined"&&appState!==null&&document.readyState==="complete"',timeout=5000)
                    print(json.dumps({'native_scene_and_CEF_ready':True,'backend_HTTP_ready':True,'CEF_appState_ready':True,'elapsed_s':time.perf_counter()-began,'attempts':attempts}),flush=True)
                    break
    except (OSError,TimeoutError,ValueError) as error:last=str(error)
    time.sleep(.25)
else:raise TimeoutError('A cena e a CEF não ficaram prontas em45s: '+str(last))
