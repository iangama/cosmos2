"""Load the local CEF GUI once after the native scene begins processing Lua.

Initial CEF navigation during scene initialization can remain about:blank.
Reissue the project's URL after normal frame processing, before user input.
"""
from pathlib import Path
import json
import time
from websockets.sync.client import connect
from websockets.exceptions import WebSocketException

ROOT = Path(__file__).resolve().parents[1]
start = time.monotonic()
deadline=start+120
attempts=0
while time.monotonic()-start < 120:
    try:
        # Server::preSync starts pending WebSocket streams only after scene
        # initialization. Early HTTP upgrade retries leave cancelled sockets
        # queued for that first frame, delaying the real GUI connection.
        with (ROOT/'output/engine.log').open('rb') as log:
            log.seek(0,2)
            log.seek(max(0,log.tell()-65536))
            if b'Running Global initialization scripts' not in log.read():
                time.sleep(.05)
                continue
        attempts+=1
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.1,ping_interval=None) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'return':True,'script':
                               'return openspace.navigation.getNavigationState()'}}))
            # Keep the first accepted connection while scene initialization is
            # running; retrying queued Lua requests creates a startup backlog.
            while time.monotonic()<deadline:
                try:
                    answer=json.loads(ws.recv(timeout=min(1,max(.05,deadline-time.monotonic()))))
                    if answer.get('topic')==1:
                        break
                except TimeoutError:
                    continue
            else:
                raise TimeoutError('A cena não respondeu antes do prazo de abertura.')
            value=answer.get('payload',{}).get('1',{})
            if value.get('Anchor') != 'Earth':
                raise ValueError('A cena inicial ainda não está pronta.')
            script='openspace.setPropertyValueSingle("Modules.CefWebGui.GuiUrl", ""); openspace.setPropertyValueSingle("Modules.CefWebGui.GuiUrl", "http://127.0.0.1:4700/")'
            ws.send(json.dumps({'topic':2,'type':'luascript','payload':{'return':True,'script':script}}))
            reply=json.loads(ws.recv(timeout=3))
            if reply.get('topic') != 2: raise ValueError('Resposta fora da ordem de inicialização.')
        report={'gui_url_reissued_after_scene_ready':True,'elapsed_s':time.monotonic()-start,
                'connection_attempts':attempts,'kept_connection_during_scene_initialization':True,
                'scope':'One startup navigation; does not run after user navigation'}
        (ROOT/'output/bootstrap-ui.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
        break
    except (OSError,TimeoutError,ValueError,WebSocketException):
        time.sleep(.1)
else:
    raise RuntimeError('Motor não ficou pronto para inicializar GUI em120s.')
