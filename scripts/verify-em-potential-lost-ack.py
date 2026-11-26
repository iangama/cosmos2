"""Execute real native publication, discard its ACK, verify bounded recovery."""
from pathlib import Path
import hashlib
import json
import sys
import urllib.request
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];CANDIDATE=ROOT/'output/c212-em-potential-product'
sys.path.insert(0,str(CANDIDATE/'app'));from em_native import NativeEM
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state'))
def guard():
    s=state()['state'];return {k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
def command(name,**values):
    req=urllib.request.Request('http://127.0.0.1:4700/api/em/command',data=json.dumps({'command':name,**values}).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req,timeout=20))
host=NativeEM();nodes=[];completed=False
try:
    with Page() as page:
        page.goto('http://127.0.0.1:4700/');page.wait_for_function('typeof appState!=="undefined"&&appState!==null');page.locator('#em-lab').click()
        page.wait_for_function('nativeState?.confirmation?.state==="accepted"&&!pending',timeout=30000)
        command('load_preset',**guard(),preset='electric');command('configure_potential',**guard(),changes={'visible':True,'count_axis':17})
        layer=command('sample_potential',**guard())['result'];snapshot=state()['state'];science=snapshot['experiment'];editor=snapshot['editor']
        # Separate test-owned transaction manager and node UUIDs share only the
        # existing root. No camera, body, server-owned potential or worker edits.
        host.active=True;host.potential.configure({'visible':True});first=host.potential.show(layer,snapshot)
        old=[m['node'] for m in first['meshes']];nodes.extend(old);real_call=host._call
        def lost_reply(code):
            real_call(code)
            raise TimeoutError('Injected lost acknowledgement after actual native execution')
        host._call=lost_reply
        try:host.potential.show(layer,snapshot)
        except TimeoutError:pass
        else:raise AssertionError('Lost native ACK reported as confirmed')
        host._call=real_call;pending=[m['node'] for m in host.potential.pending['meshes']];nodes.extend(pending)
        status=host.potential.status();assert status['confirmation_uncertain'] and status['pending_node_count']==len(pending)>0
        def presence(names):
            code='local values={};'
            for name in names:code+='values['+json.dumps(name)+']=openspace.hasSceneGraphNode('+json.dumps(name)+');'
            return real_call(code+'return {values=values}')['values']
        assert not any(presence(old).values()) and all(presence(pending).values())
        for action in (lambda:host.potential.show(layer,snapshot),lambda:host.potential.configure({'visible':False})):
            try:action()
            except RuntimeError:pass
            else:raise AssertionError('Uncertain transaction repeated without cleanup')
        assert all(presence(pending).values()) and host.potential.config['visible']
        host.potential.clear();assert not any(presence(nodes).values()) and not host.potential.status()['confirmation_uncertain']
        recovered=host.potential.show(layer,snapshot);nodes.extend(m['node'] for m in recovered['meshes']);assert all(presence([m['node'] for m in recovered['meshes']]).values())
        host.potential.clear();assert not any(presence(nodes).values())
        assert state()['state']['experiment']==science and state()['state']['editor']==editor and owner.read_bytes()==original
        completed=True
        report={'status':'real_native_potential_lost_ACK_does_not_repeat_or_leak_nodes_after_confirmed_cleanup',
                'old_nodes_replaced_before_injected_ACK_loss':len(old),'pending_nodes_observed_independently':len(pending),
                'uncertain_show_and_visibility_blocked_until_cleanup':True,'all_old_pending_and_recovered_nodes_removed':True,
                'same_layer_can_be_published_after_confirmed_cleanup':True,'science_editor_owner_unchanged':True,
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CANDIDATE/'app/em_potential_native.py',CANDIDATE/'app/em_potential_mesh.py',Path(__file__))},
                'scope':'Injected ACK loss after real engine execution using isolated test-owned mesh UUIDs under an existing EM root. No physical mutation or full transport/engine crash guarantee.'}
        (ROOT/'evidence/em-potential-lost-ack-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
    try:
        if 'real_call' in locals():host._call=real_call
        if host.active:host.potential.clear()
    finally:
        host.close()
        with Page() as page:page.call('Page.navigate',{'url':'http://127.0.0.1:4700/'})
        assert owner.read_bytes()==original
