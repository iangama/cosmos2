"""Actual native magnetic map cells, visibility, immutable SI samples and persistence."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import subprocess
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-body-maps-product/app'
h=SourceFileLoader('body_maps_native_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
phase=lambda p:{k:copy.deepcopy(p[k]) for k in ['system_id','time','revision','bodies','interventions','atlas_initial']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-native-body-maps-'+args.label);receipt=ROOT/('evidence/is3-native-body-maps-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native map evidence.')
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('bodyMapsCandidate') and launch.get('nodeLifecycleV2Candidate')
    assert json.loads((ROOT/'evidence/is3-map-checkpoints-20261024a.json').read_text(encoding='utf-8'))['accepted']
    folder.mkdir();paths=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [Path(__file__).resolve(),ROOT/'scripts/cef_page.py',ROOT/'IS-3-MAPAS-NATIVOS-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths};owner=sha(ROOT/'user/sessions/latest.json')
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'session':launch,'cases':[],'captures':[]}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    persist();topic=0
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                reply=json.loads(ws.recv(timeout=180));assert reply.get('topic')==topic;return reply['payload']['1']
            def ready():
                deadline=time.monotonic()+240
                while native('return openspace.cosmos2SceneInitialization()')['cpu_initializing']:
                    if time.monotonic()>deadline:raise TimeoutError('Map CPU initialization never drained.')
                    time.sleep(.1)
                native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<3:
                    if time.monotonic()>deadline:raise TimeoutError('No GL/rendered frames after CPU idle.')
                    time.sleep(.05)
                native('openspace.cosmos2EndFrameCapture();return {ok=true}')
            def capture(name):
                ready()
                native('openspace.cosmos2BeginFrameCapture(240);return {ready=true}')
                deadline=time.monotonic()+5
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<10:
                    if time.monotonic()>deadline:raise TimeoutError('No rendered map frames.')
                    time.sleep(.05)
                native('openspace.cosmos2EndFrameCapture();return {ready=true}')
                filename='cosmos2-is3-body-maps-'+args.label+'-'+name+'.png'
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',filename],check=True,capture_output=True)
                report['captures'].append({'name':name,'path':'evidence/'+filename,'sha256':sha(ROOT/'evidence'/filename)})
            def native_probe(probe):
                p=native('return {p=openspace.propertyValue("Scene.'+probe['native_node']+'.Translation.Position"),enabled=openspace.propertyValue("Scene.'+probe['native_node']+'.Renderable.Enabled")}')
                assert max(abs(a-b) for a,b in zip(p['p'],probe['position_render_relative_m']))<=.001
                return p
            with Page() as page:
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.mode==="atlas"&&!pending')
                atlas=h.get('/api/atlas/state');h.click(page,'#copy-solar')
                page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                def open_panels():
                    for name in ['solar-panel','body-field-vector-panel']:
                        if not page.evaluate('document.getElementById('+json.dumps(name)+').open'):h.click(page,'#'+name+' > summary')
                first=h.get('/api/state')['physics'];initial_phase=phase(first);old_nodes=[]
                for target in ['599']:
                    body=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:'+target)
                    for representation in ['cut']:
                        open_panels();page.locator('#solar-body').select_option(body['id'])
                        page.locator('#body-field-representation').select_option(representation);h.click(page,'#body-field-show')
                        ready();state=h.get('/api/state');layer=state['body_field_preview'];render=layer['render']
                        assert layer['representation']==representation and phase(state['physics'])==initial_phase
                        assert layer['map_summary']['shape']==([19,37] if representation=='shell' else [65,65])
                        assert layer['map_summary']['drawn_symbols']>600
                        assert all(native('local f={};for _,n in ipairs({'+','.join(json.dumps(n) for n in render['nodes'])+'}) do f[n]=openspace.hasSceneGraphNode(n) end;return {f=f}')['f'].values())
                        if old_nodes:
                            assert not any(native('local f={};for _,n in ipairs({'+','.join(json.dumps(n) for n in old_nodes)+'}) do f[n]=openspace.hasSceneGraphNode(n) end;return {f=f}')['f'].values())
                        row,column=(9,9) if representation=='shell' else (32,61 if target=='399' else 48)
                        page.locator('#body-map-row').select_option(str(row));page.locator('#body-map-column').select_option(str(column));h.click(page,'#body-map-sample')
                        layer=h.get('/api/state')['body_field_preview'];probe=copy.deepcopy(layer['map_probe']);native_probe(probe)
                        geometry=json.loads(Path(render['receipt']).read_text(encoding='utf-8'))['geometry']
                        expected=geometry['field_maps'][representation]['samples'][row][column]
                        assert probe['sample']==expected and probe['epoch']==layer['reading']['epoch']
                        assert 'Mesmo dado' in page.locator('#body-map-reading').inner_text()
                        request={'command':'select_body_field_map_cell','layer_id':render['id'],'row':row,'column':column}
                        for changes in [{'row':True},{'row':99},{'layer_id':'stale'},*([{'row':32,'column':32}] if representation=='cut' else [])]:
                            assert not h.post('/api/command',{**request,**changes},400)['ok']
                            assert h.get('/api/state')['body_field_preview']['map_probe']==probe
                            assert phase(h.get('/api/state')['physics'])==initial_phase
                        for scale in ['1','1.5']:
                            page.locator('#ui-scale').select_option(scale);page.evaluate('document.getElementById("body-map-reading").scrollIntoView({block:"center"})')
                            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                            capture(target+'-'+representation+'-'+str(int(float(scale)*100)))
                        page.locator('#ui-scale').select_option('1')
                        page.locator('#body-field-visible').set_checked(False);page.wait_for_function('!pending&&!appState.body_field_preview.visible')
                        assert not native_probe(probe)['enabled'] and phase(h.get('/api/state')['physics'])==initial_phase
                        # Selecting another valid cell while hidden must preserve
                        # its hidden native label and use a stored SI value.
                        other_column=column+1
                        h.post('/api/command',{**request,'column':other_column})
                        layer=h.get('/api/state')['body_field_preview'];assert not native_probe(layer['map_probe'])['enabled']
                        h.click(page,'#save');saved=h.get('/api/state')['physics'];saved_cell=saved['body_field_view']['layer']['map_probe']
                        h.click(page,'#body-field-clear');h.click(page,'#load');ready();state=h.get('/api/state');layer=state['body_field_preview']
                        assert phase(state['physics'])==phase(saved) and not layer['visible'] and layer['restored_from_checkpoint']
                        assert {k:layer['map_probe'][k] for k in ['row','column']}==saved_cell
                        assert not native_probe(layer['map_probe'])['enabled']
                        original_id=layer['render']['id'];page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.body_field_preview&&!pending')
                        assert h.get('/api/state')['body_field_preview']['render']['id']==original_id
                        open_panels();assert page.evaluate('document.getElementById("body-map-column").value')==str(other_column)
                        page.locator('#body-field-visible').set_checked(True);page.wait_for_function('!pending&&appState.body_field_preview.visible')
                        layer=h.get('/api/state')['body_field_preview'];assert native_probe(layer['map_probe'])['enabled']
                        old_nodes=layer['render']['nodes'];initial_phase=phase(h.get('/api/state')['physics'])
                        report['cases'].append({'target':target,'representation':representation,'map_id':layer['render']['id'],
                            'same_SI_probe_native_position_confirmed':True,'invalid_cells_transactional':True,
                            'hidden_probe_checkpoint_reload_reattach':True})
                        persist()
                # Last case is the Jovian cut with a selected cell. Persist an
                # evolved phase while keeping the earlier sampled map/cell.
                reading=copy.deepcopy(layer['reading']);sample=copy.deepcopy(layer['map_probe']['sample'])
                h.post('/api/command',{'command':'rate','value':.1});h.click(page,'#play');page.wait_for_function('appState.physics.time>0&&!pending');h.click(page,'#play')
                h.click(page,'#save');saved=h.get('/api/state')['physics'];h.click(page,'#load');state=h.get('/api/state');layer=state['body_field_preview']
                assert phase(state['physics'])==phase(saved) and layer['reading']==reading and layer['map_probe']['sample']==sample
                open_panels()
                if not page.evaluate('document.getElementById("simulation-branches").open'):h.click(page,'#simulation-branches > summary')
                page.evaluate('document.getElementById("branch-name").value="Mapa joviano com sonda"');h.click(page,'#branch-create')
                branch=h.get('/api/state')['physics']['branches']['active_id'];page.locator('#branch-first').select_option(branch);h.click(page,'#branch-load')
                ready();state=h.get('/api/state');layer=state['body_field_preview'];assert layer['map_probe']['sample']==sample and layer['reading']==reading
                open_panels();before_exports=set((ROOT/'user/exports').glob('cosmos2-body-magnetic-field-*.json'));h.click(page,'#body-field-export')
                exports=set((ROOT/'user/exports').glob('cosmos2-body-magnetic-field-*.json'))-before_exports;assert len(exports)==1
                path=exports.pop();payload=json.loads(path.read_text(encoding='utf-8'))
                cell=payload['view']['layer']['map_probe'];assert payload['geometry']['field_maps']['cut']['samples'][cell['row']][cell['column']]==sample
                assert payload['reading_is_stale'];report['export']={'path':str(path),'sha256':sha(path)}
                report['restart_expected']={'physics':state['physics'],'reading':reading,'sample':sample,'cell':cell,
                                            'configuration':state['physics']['body_field_view']['configuration']}
                h.click(page,'#atlas');assert h.get('/api/state')['body_field_preview'] is None
                after=h.get('/api/atlas/state');assert after['epoch']==atlas['epoch'] and after['bodies']==atlas['bodies']
        assert all(sha(ROOT/name)==value for name,value in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        report.update(accepted=True,completed=True,scope='Focused Jovian cut replay on lifecyclev2, CPU idle and subsequent rendered frames observed; exact SI cell lookup, probe placement/visibility, invalid cells, checkpoint/CEF reload/branch/export/Atlas. Manual image review, full process restart and sustained performance separate.')
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
