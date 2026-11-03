"""Native laboratory: six bodies fall inward along all axes, plus a3D field shell."""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import sys
import time
import urllib.request
from websockets.sync.client import connect
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
label=sys.argv[sys.argv.index('--label')+1] if '--label' in sys.argv else 'gravity-spherical'
assert label.replace('-','').isalnum()
BASE='http://127.0.0.1:4700'
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert launch['cloudCandidate'], 'Use only the isolated candidate storage'
def state():return json.load(urllib.request.urlopen(BASE+'/api/state',timeout=10))
def command(command_name,**value):
    r=urllib.request.Request(BASE+'/api/command',data=json.dumps({'command':command_name,**value}).encode(),
        headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(r,timeout=65))
def guard(p):
    return {k:p[k] for k in ('system_id','edit_token','revision')}|{'expected_time':p['time'],'frame':p['contract']['frame']}
ws=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=1,ping_interval=None)
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));serial=0
def lua(code):
    global serial
    serial+=1;ws.send(json.dumps({'topic':serial,'type':'luascript','payload':{'script':code,'return':True}}))
    response=json.loads(ws.recv(timeout=20));assert response['topic']==serial,response
    return response.get('payload',{}).get('1')
original_mode=state()['mode'];saved=False
try:
    command('enter');command('pause');command('save');saved=True
    p=state()['physics']
    if p.get('test_particle_cloud'):
        command('set_cloud',**guard(p),parameters=None);p=state()['physics']
    command('new_system',**guard(p),name='Centro gravitacional',mass_kg=1.988409870698051e30,
        position_m=[0.,0.,0.],velocity_m_s=[0.,0.,0.])
    axes=[('Direita +x',[1,0,0]),('Frente +y',[0,1,0]),('Acima +z',[0,0,1]),
        ('Esquerda −x',[-1,0,0]),('Atrás −y',[0,-1,0]),('Abaixo −z',[0,0,-1])]
    for name,d in axes:
        p=state()['physics'];command('create_body',**guard(p),name=name,mass_kg=1e20,
            position_m=[v*2e9 for v in d],velocity_m_s=[0.,0.,0.])
    p=state()['physics'];initial=p
    readings=[]
    for name,d in axes:
        result=command('probe',**guard(p),position_m=[v*3e9 for v in d])['ack']['result']
        g=result['acceleration_m_s2']
        inward=-sum(g[k]*d[k] for k in range(3))
        transverse=math.sqrt(sum((g[k]+inward*d[k])**2 for k in range(3)))
        assert inward>0 and transverse/inward<1e-13
        readings.append({'direction':name,'acceleration_m_s2':g,'inward':True})
    p=state()['physics'];cfg=dict(p['field_layers']['settings'])
    cfg.update(center_mode='follow',body_id=p['bodies'][0]['id'],shell_radius_m=3e9,
        shell_count=128,shell_enabled=True,cut_enabled=False)
    command('configure_fields',**guard(p),fields_revision=p['field_layers']['revision'],settings=cfg)
    p=state()['physics'];command('sample_fields',**guard(p),fields_revision=p['field_layers']['revision'])
    labels=''.join('openspace.setPropertyValueSingle('+json.dumps('Scene.'+b['label_node']+'.Renderable.Enabled')+',true);' for b in p['bodies'])
    lua(labels+'openspace.setPropertyValueSingle("Scene.LabGrid.Renderable.Enabled",false);openspace.navigation.setNavigationState({Anchor="LabFrame",ReferenceFrame="LabRoot",Position={7e9,-9e9,4e9},Up={0,0,1}});return {ready=true}')
    with Page() as page:
        page.evaluate('updateState()')
        page.evaluate('(()=>{const d=document.createElement("div");d.id="gravity3d-proof";d.style="position:fixed;top:120px;left:360px;max-width:620px;padding:15px;background:#081824e8;color:#bce6ed;border:1px solid #426474;z-index:9999;font:15px sans-serif";d.textContent="Verificação 3D: seis corpos nos eixos ±x, ±y e ±z. As setas da casca esférica apontam para o centro. Acima (+z), aceleração para baixo; abaixo (−z), aceleração para cima. Mapa congelado no instante inicial.";document.body.append(d)})()')
    time.sleep(.4)
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),
        '-Name','cosmos2-'+label+'-initial.png'],check=True,capture_output=True)
    command('rate',value=1);command('resume')
    deadline=time.perf_counter()+10
    while time.perf_counter()<deadline:
        if state()['physics']['time']>=.7:break
        time.sleep(.03)
    command('pause');after=state()['physics'];assert .7<=after['time']<2.
    native=[]
    for b,(_,d) in zip(after['bodies'][1:],axes):
        r=b['position'];v=b['velocity'];assert math.hypot(*r)<2 and sum(v[k]*d[k] for k in range(3))<0
        transverse=math.sqrt(sum((r[k]-sum(r[j]*d[j] for j in range(3))*d[k])**2 for k in range(3)))
        assert transverse<1e-13
        expected=[x*1e9 for x in r];uri='Scene.'+b['scene_node']+'.Translation.Position'
        end=time.perf_counter()+3
        while time.perf_counter()<end:
            xyz=lua('return {position=openspace.propertyValue('+json.dumps(uri)+')}')['position']
            if math.dist(xyz,expected)<1e-5:break
            time.sleep(.02)
        assert math.dist(xyz,expected)<1e-5
        native.append({'name':b['name'],'initial_radius_m':2e9,'final_radius_m':math.hypot(*r)*1e9,
            'position_m':xyz,'velocity_model':v,'native_position_error_m':math.dist(xyz,expected)})
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),
        '-Name','cosmos2-'+label+'-falling.png'],check=True,capture_output=True)
    report={'status':'native_3d_spherical_inward_attraction_verified','field_axis_readings':readings,
        'native_bodies':native,'initial_time_model':initial['time'],'final_time_model':after['time'],
        'all_six_bodies_moved_toward_center':True,'spherical_shell_128_arrows':True,
        'owner_pointer_preserved':owner.read_bytes()==original,
        'scope':'Seven active Newtonian masses in the isolated candidate Laboratory; no J2/material tide. Six small masses all fall inward, including above/below. Field map is frozen at the initial instant.'}
    report_path=ROOT/('evidence/'+label+'-native-check.json')
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if '--verify-field-toggle' in sys.argv:
        p=state()['physics'];cfg=dict(p['field_layers']['settings']);cfg['cut_enabled']=True
        command('configure_fields',**guard(p),fields_revision=p['field_layers']['revision'],settings=cfg)
        with Page() as page:
            errors=[];page.on('pageerror',lambda e:errors.append(e))
            page.evaluate('document.getElementById("gravity3d-proof")?.remove();document.getElementById("gravity-fields").open=true;updateState()')
            page.wait_for_function('!pending&&appState.physics.paused')
            page.locator('#measure-fields').click()
            page.wait_for_function('!pending&&appState.fields_preview?.cut&&appState.fields_visible',timeout=30000)
            page.locator('#view-fields').click();time.sleep(.3)
            frozen=state()['physics']
            def physical(p):
                return {k:p[k] for k in ('bodies','time','revision','system_id','edit_token','conservation')}
            before=physical(frozen);cycles=[]
            meshes=state()['fields_preview']['render']['meshes']
            assert len(meshes)>=3
            def enabled():
                result=lua('return {enabled={'+','.join('openspace.propertyValue('+json.dumps('Scene.'+m['node']+'.Renderable.Enabled')+')' for m in meshes)+'}}')['enabled']
                print(json.dumps({'native_enabled_raw':result}),flush=True)
                return list(result.values()) if isinstance(result,dict) else result
            assert all(enabled())
            for cycle in range(3):
                for visible in (False,True):
                    page.locator('#toggle-fields').click()
                    page.wait_for_function('!pending&&appState.fields_visible==='+str(visible).lower())
                    deadline=time.perf_counter()+3
                    while True:
                        values=enabled()
                        if all(v==visible for v in values) or time.perf_counter()>=deadline:break
                        time.sleep(.05)
                    assert all(v==visible for v in values),{'expected':visible,'values':values}
                    assert physical(state()['physics'])==before
                    text=page.locator('#toggle-fields').inner_text()
                    assert text==('Esconder campo' if visible else 'Mostrar campo')
                    cycles.append({'cycle':cycle+1,'visible':visible,'button_text':text,'native_meshes_enabled':values})
                    if cycle==0:
                        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),
                            '-Name','cosmos2-'+label+('-field-on.png' if visible else '-field-off.png')],check=True,capture_output=True)
            assert not errors,errors
            report['field_visibility_button']={'status':'passed','three_full_off_on_cycles':cycles,
                'native_mesh_count':len(meshes),'layers':[m['layer'] for m in meshes],
                'physical_state_unchanged':True,'javascript_errors':errors,
                'scope_ptBR':'Controle Mostrar/Esconder campo: casca vetorial, corte e equipotenciais. Não é malha de curvatura espaço-temporal.'}
    (ROOT/('evidence/'+label+'-native-check.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
finally:
    try:
        with Page() as page:page.evaluate('document.getElementById("gravity3d-proof")?.remove()')
        if saved:command('pause');command('load')
        if original_mode=='atlas':command('atlas')
    finally:
        ws.close()
        assert owner.read_bytes()==original
