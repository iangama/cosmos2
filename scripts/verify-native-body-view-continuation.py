"""Native persisted magnetic views: independent visibility, checkpoints, branches and export."""
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
APP=ROOT/'output/is3-body-view-product/app'
h=SourceFileLoader('body_view_native_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-native-body-view-'+args.label);receipt=ROOT/('evidence/is3-native-body-view-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve native evidence.')
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('bodyViewCandidate')
    assert json.loads((ROOT/'evidence/is3-view-checkpoints-summary-20261024.json').read_text())['accepted']
    paths=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [Path(__file__).resolve(),ROOT/'scripts/cef_page.py',ROOT/'IS-3-VISUAL-PERSISTENCIA-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths};folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    owner=sha(ROOT/'user/sessions/latest.json')
    prepared=json.loads((ROOT/'evidence/is3-body-view-candidate-prepared-20261024.json').read_text())
    report={'schema':1,'session':launch,'source_sha256':hashes,'checks':{},'captures':[],'completed':False,'accepted':False}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist();topic=0
    try:
        with connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=4*1024*1024) as ws:
            ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            def native(code):
                nonlocal topic
                topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}))
                answer=json.loads(ws.recv(timeout=15));assert answer.get('topic')==topic;return answer['payload']['1']
            def visibility(layer,body):
                nodes=[m['node'] for m in layer['render']['meshes']]+[layer['render']['label_node']]
                return native('local flags={};for _,n in ipairs({'+','.join(json.dumps(n) for n in nodes)+'}) do flags[n]=openspace.propertyValue("Scene."..n..".Renderable.Enabled") end;return {flags=flags,marker=openspace.propertyValue("Scene.'+body['scene_node']+'.Renderable.Enabled")}')
            def capture(name):
                native('openspace.cosmos2BeginFrameCapture(240);return {ok=true}')
                until=time.monotonic()+5
                while native('return openspace.cosmos2MemoryMetrics()')['capture_samples']<10:
                    if time.monotonic()>until:raise TimeoutError('No rendered frames.')
                    time.sleep(.05)
                native('openspace.cosmos2EndFrameCapture();return {ok=true}')
                filename='cosmos2-is3-body-view-'+args.label+'-'+name+'.png'
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',filename],check=True,capture_output=True)
                report['captures'].append({'name':name,'path':'evidence/'+filename,'sha256':sha(ROOT/'evidence'/filename)})
            with Page() as page:
                prior=json.loads((ROOT/'evidence/is3-native-body-view-20261024a.json').read_text())
                assert prior['checks']['Earth_lines_visibility_save_clear_load_preserves_phase_and_sample']
                for name,digest in prior['source_sha256'].items():
                    if name.startswith('output/is3-body-view-product/app/'):assert sha(ROOT/name)==digest
                report['continuation_of']='evidence/is3-native-body-view-20261024a.json'
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.body_field_preview&&!pending')
                atlas=h.get('/api/atlas/state');first=h.get('/api/state')['physics']
                def open_panel():
                    for name in ['solar-panel','body-field-vector-panel']:
                        if not page.evaluate('document.getElementById('+json.dumps(name)+').open'):h.click(page,'#'+name+' > summary')
                open_panel();earth=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:399')
                jupiter=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:599')
                layer=h.get('/api/state')['body_field_preview'];reading=layer['reading'];saved=first
                assert not layer['visible'] and reading['body_reference_id']=='sol:naif:399'
                page.locator('#ui-scale').select_option('1')
                if not page.evaluate('document.getElementById("simulation-branches").open'):
                    page.evaluate('document.querySelector("#branch-create").closest("details").open=true')
                page.evaluate('document.getElementById("branch-name").value="Camada oculta Terra"');h.click(page,'#branch-create')
                branch=h.get('/api/state')['physics']['branches']['active_id'];assert branch
                open_panel();page.locator('#body-field-visible').set_checked(True);page.wait_for_function('!pending&&appState.body_field_preview.visible')
                if not page.evaluate('document.querySelector("#branch-create").closest("details").open'):page.evaluate('document.querySelector("#branch-create").closest("details").open=true')
                page.locator('#branch-first').select_option(branch);h.click(page,'#branch-load')
                loaded=h.get('/api/state');assert loaded['body_field_preview']['reading']==reading and not loaded['body_field_preview']['visible']
                assert loaded['physics']['bodies']==saved['bodies']
                report['checks']['native_branch_restores_hidden_Earth_sample']=True
                open_panel();h.click(page,'#body-field-clear');page.locator('#solar-body').select_option(jupiter['id'])
                page.locator('#body-field-representation').select_option('vector');h.click(page,'#body-field-show')
                assert h.get('/api/state')['body_field_preview']['representation']=='vector'
                page.locator('#body-field-representation').select_option('lines')
                page.evaluate('document.getElementById("jupiter-field-radius").value="2";document.getElementById("jupiter-field-latitude").value="30";document.getElementById("jupiter-field-longitude").value="90";document.getElementById("jupiter-field-degree").value="18"')
                h.click(page,'#body-field-show');layer=h.get('/api/state')['body_field_preview'];reading=copy.deepcopy(layer['reading'])
                assert layer['reading']['degree']==18
                h.post('/api/command',{'command':'rate','value':.1});h.click(page,'#play');page.wait_for_function('appState.physics.time>0&&!pending');h.click(page,'#play');page.wait_for_function('appState.physics.paused&&!pending')
                h.click(page,'#save');saved=h.get('/api/state')['physics'];h.click(page,'#body-field-clear');h.click(page,'#load')
                loaded=h.get('/api/state');layer=loaded['body_field_preview'];assert layer['reading']==reading and layer['visible']
                assert loaded['physics']['bodies']==saved['bodies'] and loaded['physics']['time']==saved['time']
                assert page.evaluate('bodyFieldConfiguration()')==saved['body_field_view']['configuration']
                open_panel();assert 'Amostra fixa' in page.locator('#body-field-status').inner_text()
                for scale in ['1','1.5']:
                    page.locator('#ui-scale').select_option(scale);page.evaluate('document.getElementById("body-field-status").scrollIntoView({block:"center"})')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');capture('jupiter-restored-'+str(int(float(scale)*100)))
                page.locator('#ui-scale').select_option('1')
                export_before=set((ROOT/'user/exports').glob('cosmos2-body-magnetic-field-*.json'));h.click(page,'#body-field-export')
                exported=set((ROOT/'user/exports').glob('cosmos2-body-magnetic-field-*.json'))-export_before;assert len(exported)==1
                path=exported.pop();payload=json.loads(path.read_text(encoding='utf-8'))
                assert payload['view']['layer']['reading']==reading and payload['geometry']['reading']==reading
                assert payload['reading_is_stale'] and len(payload['geometry']['field_lines']['lines'])==5
                report['export']={'path':str(path),'sha256':sha(path)}
                before=h.physical(h.get('/api/state')['physics']);manifest=Path(launch['storage'])/'latest.json';manifest_sha=sha(manifest)
                for value in [1,None,'false']:
                    assert not h.post('/api/command',{'command':'set_body_field_visible','layer_id':layer['render']['id'],'visible':value},400)['ok']
                    assert h.physical(h.get('/api/state')['physics'])==before
                bad=copy.deepcopy(saved['body_field_view']['configuration']);bad['earth'][2]=-1
                assert not h.post('/api/command',{'command':'save','body_field_configuration':bad},400)['ok']
                assert sha(manifest)==manifest_sha and h.physical(h.get('/api/state')['physics'])==before
                report['checks']['Jupiter_degree18_stale_sample_forms_export_and_transactional_refusals']=True
                report['restart_expected']={'physics':h.get('/api/state')['physics'],'reading':reading,'configuration':saved['body_field_view']['configuration']}
                h.click(page,'#atlas');assert h.get('/api/state')['body_field_preview'] is None
                after=h.get('/api/atlas/state');assert after['epoch']==atlas['epoch'] and after['bodies']==atlas['bodies']
                report['checks']['Atlas_clears_active_view_preserves_reference']=True
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        assert all(sha(ROOT/name)==value for name,value in prepared['base_source_sha256'].items())
        assert sha(ROOT/'user/sessions/latest.json')==owner
        report.update(accepted=True,completed=True,scope='Native view persistence/visibility/branches/export; native process restart, image review and performance require separate receipts.')
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'accepted':report['accepted'],'checks':report['checks'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
