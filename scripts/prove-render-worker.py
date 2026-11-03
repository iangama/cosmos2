"""Short native proof: feed 32 independently integrated bodies to OpenSpace.

Requires the local Cosmos2 window to be running. Restores atlas camera and
removes experiment nodes on completion. Marker radii are display-only.
"""
from pathlib import Path
import importlib.util
import json
import queue
import subprocess
import sys
import threading
import time
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
process = subprocess.Popen([sys.executable,'-u',str(ROOT/'app'/'worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
messages=queue.Queue()
def read():
    for line in process.stdout: messages.put(json.loads(line))
threading.Thread(target=read,daemon=True).start()
assert messages.get(timeout=10)['type']=='ready'

with connect('ws://127.0.0.1:4682',open_timeout=5) as socket:
    topic=0
    socket.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
    def send(code,wait=False):
        global topic
        topic+=1
        socket.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':wait}}))
        if wait: return json.loads(socket.recv(timeout=20))
    old=send('return openspace.navigation.getNavigationState()',True)['payload']['1']
    created=False
    try:
        # Render position scale 1e9 m/unit, fixed offset avoids mixing atlas coordinates.
        code='openspace.addSceneGraphNode({Identifier="C2Experiment",Transform={Translation={Type="StaticTranslation",Position={1e14,0,0}}}});'
        for i in range(32):
            code+=f'openspace.addSceneGraphNode({{Identifier="C2Body{i}",Parent="C2Experiment",Transform={{Translation={{Type="StaticTranslation",Position={{0,0,0}}}}}},Renderable={{Type="RenderableSphereImageLocal",Size={4e8 if i==0 else 1.5e8},Segments=16,Texture=openspace.absPath("${{DATA}}/test.jpg")}},GUI={{Name="P32: corpo {i}"}}}});'
        code+='openspace.navigation.setNavigationState({Anchor="C2Experiment",Position={0,-5e10,6e10},Up={0,0,1}});return {created=true}'
        send(code,True);created=True
        # UI is hidden only during this automated visualization/throughput proof.
        send('openspace.setPropertyValueSingle("Modules.CefWebGui.Visible",false)')
        process.stdin.write('{"command":"resume","id":1}\n');process.stdin.flush()
        started=time.perf_counter();frames=0;last=None;capture=False
        while time.perf_counter()-started < 10:
            message=messages.get(timeout=10)
            if message['type']!='snapshot':continue
            last=message
            code=''
            for i,body in enumerate(message['bodies']):
                xyz=','.join(format(v*1e9,'.17g') for v in body['position'])
                code+=f'openspace.setPropertyValueSingle("Scene.C2Body{i}.Translation.Position",{{{xyz}}});'
            send(code);frames+=1
            if not capture and time.perf_counter()-started>2:
                send('openspace.takeScreenshot()');capture=True
        elapsed=time.perf_counter()-started
        # Barrier confirms scripts before it were consumed, then inspect actual node state.
        rendered=send('return {position=openspace.propertyValue("Scene.C2Body1.Translation.Position")}',True)
        expected=[v*1e9 for v in last['bodies'][1]['position']]
        actual=rendered['payload']['1']['position']
        assert max(abs(a-b) for a,b in zip(expected,actual)) < 1e-4,(expected,actual)
        result={'duration_seconds':elapsed,'snapshots_sent':frames,'snapshots_per_second':frames/elapsed,'physical_time':last['time'],'requested_physical_rate':1,'effective_physical_rate':last['time']/elapsed,'last_energy_error':last['energy_error'],'renderer_position_verified':True,'display_scale_m_per_unit':1e9,'marker_radii_exaggerated':True,'scope':'10-second smoke check, not sustained performance acceptance'}
        (ROOT/'evidence'/'renderer-worker-check.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally:
        process.stdin.write('{"command":"quit"}\n');process.stdin.flush()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        if created:
            cleanup='openspace.navigation.setNavigationState({Anchor="'+old['Anchor']+'",Position={'+','.join(map(str,old['Position']))+'},Up={'+','.join(map(str,old['Up']))+'}});'
            cleanup+='openspace.setPropertyValueSingle("Modules.CefWebGui.Visible",true);'
            for i in range(32):cleanup+=f'openspace.removeSceneGraphNode("C2Body{i}");'
            cleanup+='openspace.removeSceneGraphNode("C2Experiment");return {clean=true}'
            send(cleanup,True)
