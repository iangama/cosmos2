"""Isolated dynamic10k GPU receiver, binding guards and confirmed SI selection."""
from pathlib import Path
import copy
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import time
from websockets.sync.client import connect
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/c211-cloud-product/app'))
from session import Session
from cloud_scene import selected_nodes
from physics import PHYSICAL_SCALE as U
import cloud_transport as wire
from cef_page import Page

session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(session['runtime']).resolve()==(ROOT/'.runtime-cloud').resolve()
engine_receipt=json.loads((ROOT/'evidence/built-runtime-cloud.json').read_text())
assert hashlib.sha256((Path(session['runtime'])/'bin/OpenSpace.exe').read_bytes()).hexdigest()==engine_receipt['built_files']['OpenSpace.exe']
pointer=ROOT/'user/sessions/latest.json';original=pointer.read_bytes()
ws=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=1,ping_interval=None)
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}));topic=0
def lua(script):
    global topic
    topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':script,'return':True}}))
    r=json.loads(ws.recv(timeout=20));assert r.get('topic')==topic,r
    v=r.get('payload',{}).get('1');assert v is not None,r
    return v
def literal(value):
    if isinstance(value,bool):return str(value).lower()
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False)
    if isinstance(value,(int,float)):return repr(value)
    if isinstance(value,list):return '{'+','.join(literal(x) for x in value)+'}'
    if isinstance(value,dict):return '{'+','.join(k+'='+literal(v) for k,v in value.items())+'}'
    raise TypeError(value)
def status():
    r=lua('return {count=openspace.propertyValue("Scene.C2CloudStream.Renderable.NumberOfDataPoints"),status=openspace.propertyValue("Scene.C2CloudStream.Renderable.ConfirmedCloudStatus")}')
    if 'status' in r:r['status']=json.loads(r['status'])
    return r
def wait_status(state,sequence):
    deadline=time.perf_counter()+15
    while time.perf_counter()<deadline:
        r=status();v=r.get('status',{})
        if v.get('state')==state and (v.get('metadata',{}).get('sequence') if state=='accepted' else v.get('last_accepted_sequence'))==sequence:
            assert r['count']==10000,r
            return v
        time.sleep(.05)
    raise AssertionError(r)

nav=lua('return openspace.navigation.getNavigationState()')
created=False;overlay=False
with tempfile.TemporaryDirectory(prefix='cosmos2-native-cloud-stream-') as folder:
    s=Session(folder,2)
    s.load_cloud_experiment({'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,
        'expected_time':s.sim.t,'frame':s.contract()['frame'],'parameters':{'count':10000}})
    path=Path(folder)/'packet.bin'
    packet,meta=wire.encode(s._cloud,s.system_id,s.edit_token,1,s.contract()['frame']);wire.publish(path,packet)
    node={'Identifier':'C2CloudStream','Transform':{'Translation':{'Type':'StaticTranslation','Position':[1e14,0,0]}},
        'Renderable':{'Type':'RenderablePointCloud','ConfirmedCloud':{'File':path.as_posix(),
            'SystemId':s.system_id,'EditToken':s.edit_token,'CloudId':s._cloud.id,'SourceId':s.registry[0]['id'],
            'Frame':s.contract()['frame'],'Count':10000,'TimeUnitS':U['time_unit_s']},
            'Unit':'m','UseCaching':False,'Texture':{'Enabled':False},
            'SizeSettings':{'ScaleExponent':7.1,'ScaleFactor':1.,'EnableMaxSizeControl':True,'MaxSize':.15},
            'Coloring':{'FixedColor':[.35,.8,.88]},'UseAdditiveBlending':False},
        'GUI':{'Name':'Candidata: dez mil partículas de teste'}}
    try:
        lua('openspace.addSceneGraphNode('+literal(node)+');return {queued=true}');created=True
        first=wait_status('accepted',1);assert first['metadata']==meta and first['gpu_buffer_uploaded']
        accepted=[];seq=1;selection_created=False;selection_error=0.
        for target in (.1,.2,.35,.5,.8,1.):
            s.integrate(target);seq+=1
            packet,meta=wire.encode(s._cloud,s.system_id,s.edit_token,seq,s.contract()['frame']);wire.publish(path,packet)
            current=wait_status('accepted',seq)
            assert current['metadata']==meta and current['maximum_gpu_position_quantization_m']<1000.
            selected=s.cloud_point({'system_id':s.system_id,'edit_token':s.edit_token,'cloud_id':s._cloud.id,'index':9999})
            selection=selected_nodes(current,selected,'C2CloudStream')
            if not selection_created:
                lua(''.join('openspace.addSceneGraphNode('+literal(n)+');' for n in selection)+'return {ready=true}')
                selection_created=True
            else:
                lua('openspace.setPropertyValueSingle("Scene.C2CloudSelection.Translation.Position",'+literal(selected['position_m'])+');return {ready=true}')
            rendered=lua('return {position=openspace.propertyValue("Scene.C2CloudSelection.Translation.Position")}')['position']
            selection_error=max(selection_error,math.dist(rendered,selected['position_m']))
            assert selection_error==0.
            accepted.append({'sequence':seq,'time_model':target,'maximum_gpu_position_quantization_m':current['maximum_gpu_position_quantization_m']})
        point=s.cloud_point({'system_id':s.system_id,'edit_token':s.edit_token,'cloud_id':s._cloud.id,'index':9999})
        _,xyz=wire.decode(packet,s.system_id,s.edit_token,s._cloud.id,s.registry[0]['id'],s.contract()['frame'],10000,seq)
        assert xyz[9999].tolist()==point['position_m']
        _,size=wire.HEADER.unpack_from(packet);payload=packet[12+size:]
        rejected=[]
        def rewrite(m,raw=payload):
            header=json.dumps(m,separators=(',',':'),allow_nan=True).encode('ascii')
            return wire.HEADER.pack(wire.MAGIC,len(header))+header+raw
        for key,bad in [('cloud_id','0'*32),('system_id','0'*32),('edit_token','0'*32),
            ('source_id','other'),('frame','other'),('count',9999),('count',True),
            ('sequence',seq-1),('sequence',True),('time_model',-1.),('time_unit_s',1.),('length_unit_m',1.)]:
            m=copy.deepcopy(meta);m['sequence']=seq+1;m[key]=bad
            wire.publish(path,rewrite(m));rejection=wait_status('rejected',seq)
            assert rejection['previous_buffer_preserved'];rejected.append(key+':'+str(bad))
        m=copy.deepcopy(meta);m['sequence']=seq+1
        corrupt_payload=payload[:-1]+bytes([payload[-1]^1])
        wire.publish(path,rewrite(m,corrupt_payload));wait_status('rejected',seq);rejected.append('payload-bitflip')
        # Revalidating checksums must still reject a NaN coordinate before GPU mutation.
        import zlib
        points=xyz.copy();points[9999,0]=float('nan');raw=points.astype('<f8').tobytes();m=copy.deepcopy(meta)
        m.update(sequence=seq+1,payload_sha256=hashlib.sha256(raw).hexdigest(),payload_crc32=zlib.crc32(raw))
        wire.publish(path,rewrite(m,raw));wait_status('rejected',seq);rejected.append('resealed-NaN')
        seq+=1;packet,meta=wire.encode(s._cloud,s.system_id,s.edit_token,seq,s.contract()['frame']);wire.publish(path,packet)
        last=wait_status('accepted',seq)
        lua('openspace.navigation.setNavigationState({Anchor="C2CloudSelection",Position={0,-1e9,6e8},Up={0,0,1}});return {ready=true}')
        assert lua('return openspace.navigation.getNavigationState()')['Anchor']=='C2CloudSelection'
        lua('openspace.navigation.setNavigationState({Anchor="C2CloudStream",Position={0,-8e9,6e9},Up={0,0,1}});return {ready=true}')
        with Page() as page:
            page.evaluate('(() => {const e=document.createElement("div");e.id="cloud-stream-note";e.style="position:fixed;top:120px;right:35px;max-width:420px;padding:18px;background:#0b1925;color:#b4d5df;z-index:9999;border:1px solid #456174;font:16px sans-serif";e.textContent="Candidata: 10.000 partículas de teste sem massa, um buffer gráfico. Instante confirmado t=1 do modelo. Evolução e seleção SI conferidas nesta prova; integração ao produto e perfil de desempenho ainda pendentes.";document.body.append(e)})()')
            overlay=True
        time.sleep(1)
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),
            '-Name','cosmos2-cloud-stream-native.png'],check=True,capture_output=True)
        report={'status':'isolated_dynamic_10k_native_receiver_verified_not_installed','runtime':session['runtime'],
            'engine_sha256':engine_receipt['built_files']['OpenSpace.exe'],'count':10000,
            'single_aggregate_buffer':True,'six_evolved_packets_confirmed':accepted,
            'invalid_packets_refused_before_buffer_mutation':rejected,'SI_selection_matches_confirmed_packet':True,
            'one_selection_anchor_tracks_six_confirmed_instants':True,'selection_native_max_position_error_m':selection_error,
            'individual_camera_focus_verified':True,
            'last_native_confirmation':last,'owner_pointer_preserved':pointer.read_bytes()==original,
            'scope':'Isolated evolving native receiver. Product Session/worker/CEF integration and formal10k performance remain pending.'}
        (ROOT/'evidence/cloud-stream-native-check.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='last_native_confirmation'},indent=2),flush=True)
    finally:
        if overlay:
            with Page() as page:page.evaluate('document.getElementById("cloud-stream-note")?.remove()')
        restore={k:nav[k] for k in ('Anchor','Position','Up')}
        if created:lua('openspace.navigation.setNavigationState('+literal(restore)+');if openspace.hasSceneGraphNode("C2CloudSelectionLabel") then openspace.removeSceneGraphNode("C2CloudSelectionLabel") end;if openspace.hasSceneGraphNode("C2CloudSelection") then openspace.removeSceneGraphNode("C2CloudSelection") end;if openspace.hasSceneGraphNode("C2CloudStream") then openspace.removeSceneGraphNode("C2CloudStream") end;return {clean=true}')
        ws.close()
assert pointer.read_bytes()==original
