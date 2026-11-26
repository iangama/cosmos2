"""Native experimental coexistence; no product endpoint or performance claim."""
from pathlib import Path
import argparse
import copy
import hashlib
import itertools
import json
import subprocess
import sys
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-spatial-product0.18.5/app'
sys.path[:0]=[str(ROOT/'output/is6-layer-coordination-staging'),str(APP)]
from cef_page import Page
import is6_layer_contract as c
import is6_layer_scene_v3 as scene
h=SourceFileLoader('layer_pair_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(x not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for x in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is6-native-layer-pair-'+args.label);out=ROOT/('evidence/is6-native-layer-pair-'+args.label+'.json')
    if folder.exists() or out.exists():raise FileExistsError('Preserve native evidence')
    anchor=ROOT/'evidence/is6-layer-admission-boundaries-20261102a.json';a=json.loads(anchor.read_text());assert a['accepted']
    hashes=dict(a['source_sha256'])
    for p in [Path(__file__),Path(scene.__file__),anchor,ROOT/'IS-6-COEXISTENCIA-CENA-K1-CONTRATO.md',ROOT/'IS-6-COEXISTENCIA-CENA-K1-REVISAO-B.md',ROOT/'IS-6-COEXISTENCIA-CENA-K1-REVISAO-C.md',ROOT/'evidence/is6-magnetic-transform-diagnostic-20261103a.json',ROOT/'scripts/cef_page.py',ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/engine-command.py',ROOT/'scripts/capture-window.ps1']:
        hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,cases=[],captures=[],faults=[],page_errors=[],owner_sha256=sha(ROOT/'user/sessions/latest.json'),
           limits_before_execution=dict(native_initialization_s=15,native_local_error_m=.001,world_difference_policy="ulp(point_world)+ulp(center_world)+0.001m",graphic_rotation_policy='Native float angles exact; graphic point within existing generator display bound plus world ULPs',camera_up_absolute_error=1e-12),
           scope='Experimental native pair only; independent frozen models. Captures need review. No product UI, composite checkpoint or performance acceptance.')
    owner=None
    def persist():out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def restored(before,after):
        assert before['flags']==after['flags']
        assert before['camera'].keys()==after['camera'].keys()
        for k,v in before['camera'].items():
            if k=='Up':assert all(abs(x-y)<=1e-12 for x,y in zip(v,after['camera'][k]))
            else:assert after['camera'][k]==v,(k,v,after['camera'][k])
    def capture(page,target,scale):
        page.locator('#ui-scale').select_option(scale);time.sleep(.2)
        name='cosmos2-is6-pair-'+args.label+'-'+target+'-'+str(int(float(scale)*100))+'.png';path=ROOT/'evidence'/name
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
        im=Image.open(path);assert im.size==(1920,1080);rgb=folder/name;im.convert('RGB').save(rgb)
        r['captures'].append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),RGB=rgb.relative_to(ROOT).as_posix(),RGB_sha256=sha(rgb)));persist()
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda e:r['page_errors'].append(e));page.goto(h.BASE+'/');page.wait_for_function('appState&&atlasState&&!pending')
            for module in ['spatial','particles','solar-zone']:assert not h.get('/api/'+module+'/state')['active']
            page.locator('#copy-solar').click();page.wait_for_function('appState.physics?.bodies.length===4&&!pending',timeout=70000)
            phase=h.get('/api/state')['physics'];held=h.phase(copy.deepcopy(phase));r['source_phase']=phase
            owner=scene.Owner(h.native,phase);base=owner.context_now()
            page.evaluate('(()=>{const s=document.createElement("style");s.textContent="aside,#lab-details,#object-panel,#scene-targets{display:none!important}#pair-note{position:absolute;top:124px;left:28px;width:340px;padding:20px;pointer-events:auto;white-space:pre-line;font:13px/1.7 Segoe UI;color:#d9edf1}#pair-note h1{font-size:23px}#pair-note p{white-space:pre-line;overflow-wrap:anywhere}";document.head.append(s);const p=document.createElement("div");p.id="pair-note";p.className="glass";document.body.append(p);})()')
            for target in ['399','599']:
                b=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:'+target)
                options={**c.artifact.DEFAULT_CONFIGURATION,'outer_radius_boundary_units':3.}
                run=c.artifact.Run.create(phase,dict(body_id=b['id'],source_guard=c.artifact.body.guard(phase)),options)
                reading=c.earth_magnetism.read(phase,b['id'],-23.55,-46.63,1000.) if target=='399' else c.jupiter_magnetism.read(phase,b['id'],1.5*71492000.,0.,0.,13)
                before=owner.context_now();pair=owner.prepare(run,reading,folder/(target+'-mesh'))
                prepared=pair.read();assert not prepared['spatial']['draw'] and not any(prepared['magnetic']['draw'].values())
                confirmed=owner.commit(pair,dict(spatial=True,magnetic=True));assert not owner.error
                item=dict(body=target,plan=pair.plan,hidden_preparation=prepared,confirmed=confirmed,combinations=[])
                for spatial,magnetic in itertools.product([False,True],repeat=2):
                    s=owner.visibility(dict(spatial=spatial,magnetic=magnetic));assert h.phase(h.get('/api/state')['physics'])==held
                    item['combinations'].append(dict(spatial=spatial,magnetic=magnetic,readback=s))
                text='Protótipo de camadas independentes\n'+b['name']+' · '+reading['provenance']['model']+'\nÉpoca: '+reading['epoch']['utc']+'\nMalha exterior:1–3 Rref · altura gráfica×200\nCiano/violeta: corte de Schwarzschild\nVerde: B em tesla · seta de tamanho gráfico\nOuro: ponto da amostra\nPosições: metros · referencial GALACTIC\nModelos sem acoplamentoGR–EM\nAmostraB não se limita ao domínio exterior da malha.'
                page.evaluate('document.getElementById("pair-note").textContent='+json.dumps(text)+';document.getElementById("notice").textContent="Protótipo nativo · mesma fase orbital pausada"')
                for scale in ['1','1.5']:capture(page,target,scale)
                page.locator('#ui-scale').select_option('1')
                remaining=owner.remove_magnetic();assert remaining['spatial']['draw'] and remaining['magnetic'] is None
                try:owner.visibility(dict(spatial=True,magnetic=True))
                except ValueError:item['removed_layer_refusal']=True
                else:raise AssertionError('Removed layer shown')
                owner.close();after=owner.context_now();restored(before,after)
                nodes=[pair.spatial.frame,pair.spatial.wire,pair.spatial.focus,*pair.magnetic.nodes]
                absent=h.native('local r={};for _,n in ipairs('+scene.lua(nodes)+') do r[n]=openspace.hasSceneGraphNode(n) end;return r');assert not any(absent.values())
                item['cleanup']=dict(before=before,after=after,nodes=absent);r['cases'].append(item);persist()
            restored(base,owner.context_now())
            # Failures use real prepared nodes and actual native commits.
            # The injected transport faults do not replace any physics.
            old=owner.prepare(run,reading,folder/'fault-base');owner.commit(old,dict(spatial=True,magnetic=True))
            before=owner.context_now();old_state=old.read()
            native=owner.native
            def prepare_fault(code):
                if 'openspace.addSceneGraphNode' in code and 'IS6MagneticFrame_' in code:raise ConnectionError('Injected magnetic preparation failure')
                return native(code)
            owner.native=prepare_fault
            try:owner.prepare(run,reading,folder/'fault-prepare')
            except ConnectionError:pass
            else:raise AssertionError('Preparation failure not observed')
            owner.native=native;assert owner.active is old and old.read()==old_state;restored(before,owner.context_now())
            r['faults'].append('Real_hidden_preparation_refusal_kept_previous_pair');persist()
            for kind in ['lost_ack','readback']:
                candidate=owner.prepare(run,reading,folder/('fault-'+kind))
                if kind=='lost_ack':
                    def lose_ack(code):
                        answer=native(code)
                        if 'return {committed=true}' in code:raise ConnectionError('Injected ACK loss after real native commit')
                        return answer
                    owner.native=lose_ack
                else:
                    original_read=candidate.read;calls=[0]
                    def bad_readback():
                        calls[0]+=1
                        if calls[0]==2:raise ConnectionError('Injected committed readback failure')
                        return original_read()
                    candidate.read=bad_readback
                try:owner.commit(candidate,dict(spatial=True,magnetic=True))
                except ConnectionError:pass
                else:raise AssertionError('Commit fault not observed')
                owner.native=native
                if kind=='readback':candidate.read=original_read
                assert owner.active is old and not owner.faulted and old.read()==old_state
                restored(before,owner.context_now());hidden=candidate.read()
                assert not hidden['spatial']['draw'] and not any(hidden['magnetic']['draw'].values())
                r['faults'].append('Real_'+kind+'_rolled_back_before_publication');persist()
            candidate=owner.prepare(run,reading,folder/'fault-rollback');committed=[False]
            def broken_transport(code):
                if committed[0] and 'return {restored=true}' in code:raise ConnectionError('Injected rollback connection failure')
                answer=native(code)
                if 'return {committed=true}' in code:committed[0]=True;raise ConnectionError('Injected committed ACK loss')
                return answer
            owner.native=broken_transport
            try:owner.commit(candidate,dict(spatial=True,magnetic=True))
            except ConnectionError:pass
            else:raise AssertionError('Rollback fault not observed')
            assert owner.active is old and owner.faulted
            try:owner.visibility(dict(spatial=False,magnetic=False))
            except ValueError:pass
            else:raise AssertionError('Faulted owner admitted visibility')
            owner.native=native;owner.close();restored(base,owner.context_now())
            r['faults'].append('Failed_rollback_blocked_commands_then_recovered_all_owned_nodes');persist()
            assert h.phase(h.get('/api/state')['physics'])==held and not r['page_errors']
            assert sha(ROOT/'user/sessions/latest.json')==r['owner_sha256'] and all(sha(ROOT/n)==v for n,v in hashes.items())
            r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            if owner:owner.close()
            h.post('/api/command',dict(command='atlas'));h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        persist()
    print(json.dumps(dict(accepted=r['accepted'],cases=len(r['cases']),captures=len(r['captures']),failure=r.get('failure','').splitlines()[-1:])))
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
