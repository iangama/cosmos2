"""Verify saved magnetic view in a newly launched OpenSpace and server process."""
from pathlib import Path
import argparse
import hashlib
import json
import traceback
import time
import zipfile
from importlib.machinery import SourceFileLoader
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('view_restart_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    receipt=ROOT/('evidence/is3-native-body-points-restart-'+args.label+'.json')
    folder=ROOT/('output/is3-native-body-points-restart-'+args.label)
    if receipt.exists() or folder.exists():raise FileExistsError('Preserve restart evidence.')
    prior_path=ROOT/'evidence/is3-native-body-points-20261024a.json';prior=json.loads(prior_path.read_text(encoding='utf-8'));assert prior['accepted']
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert launch['bodyPointsCandidate'] and all(launch[k]!=prior['session'][k] for k in ['app','server'])
    paths=[p for p in (ROOT/'output/is3-body-points-product/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [Path(__file__).resolve(),ROOT/'scripts/cef_page.py',prior_path]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    for name,digest in prior['source_sha256'].items():
        if name.startswith('output/is3-body-points-product/app/'):assert sha(ROOT/name)==digest
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'session':launch,'source_sha256':hashes}
    try:
        with Page() as page:
            page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.mode&&!pending')
            if page.evaluate('appState.mode==="atlas"'):
                h.click(page,'#experiment');h.click(page,'#load')
            page.wait_for_function('appState?.body_field_preview?.restored_from_checkpoint&&!pending')
            state=h.get('/api/state');expected=prior['restart_expected'];layer=state['body_field_preview']
            assert all(state['physics'][k]==expected['physics'][k] for k in ['system_id','time','revision','bodies','interventions','atlas_initial'])
            assert layer['reading']==expected['reading'] and layer['representation']=='cut' and layer['visible']
            assert layer['map_probe']['sample']==expected['sample']
            assert {k:layer['map_probe'][k] for k in ['row','column']}==expected['cell']
            assert page.evaluate('bodyFieldConfiguration()')==expected['configuration']
            for name in ['solar-panel','body-field-vector-panel']:
                if not page.evaluate('document.getElementById('+json.dumps(name)+').open'):h.click(page,'#'+name+' > summary')
            assert 'Amostra original restaurada' in page.locator('#body-field-status').inner_text()
            with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None) as ws:
                ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
                topic=0
                def native(code):
                    nonlocal topic
                    topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                    reply=json.loads(ws.recv(timeout=15));assert reply.get('topic')==topic;return reply['payload']['1']
                deadline=time.monotonic()+15
                while native('return openspace.cosmos2SceneInitialization()')['cpu_initializing']:
                    if time.monotonic()>deadline:raise TimeoutError('Restart CPU did not initialize.')
                    time.sleep(.05)
                native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<5:
                    if time.monotonic()>deadline:raise TimeoutError('Restart did not render after CPU idle.')
                    time.sleep(.05)
                native('openspace.cosmos2EndFrameCapture();return {ok=true}')
                flags=native('local flags={};for _,n in ipairs({'+','.join(json.dumps(n) for n in layer['render']['nodes'])+'}) do flags[n]=openspace.hasSceneGraphNode(n) end;return {flags=flags}')['flags'];assert all(flags.values())
                probe=layer['map_probe'];position=native('return {p=openspace.propertyValue("Scene.'+probe['native_node']+'.Translation.Position")}')['p']
                assert max(abs(a-b) for a,b in zip(position,probe['position_render_relative_m']))<=.001
            report.update(accepted=True,completed=True,phase_reading_configuration_and_native_nodes_restored=True,
                          scope='New OpenSpace/server/worker processes with actual CEF load; saved frozen Jovian cut/cell sample preserved. No performance inheritance.')
            h.click(page,'#atlas')
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
