"""Static source-relative SPECK mesh; no changes to accepted native/runtime code."""
from pathlib import Path
import hashlib
import json
import math
import struct
import sys
import time
import uuid

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
sys.path.insert(0,str(ROOT/'output/is6-spatial-artifact-staging'))
import is6_spatial_artifact as artifact
from is4_stream_scene import lua

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
FILES=[Path(__file__),ROOT/'IS-6-CENA-PROTOTIPO-CONTRATO.md',
       ROOT/'.upstream/openspace/modules/space/rendering/renderableconstellationlines.cpp',
       ROOT/'.upstream/openspace/modules/space/rendering/renderableconstellationlines.h',
       ROOT/'evidence/built-runtime-is4-stream.json',ROOT/'evidence/is6-spatial-artifact-20261101a.json']
IMPORTED={p.relative_to(ROOT).as_posix():sha(p) for p in FILES}


def generation():
    if any(sha(ROOT/n)!=v for n,v in IMPORTED.items()):raise ValueError('Restart after spatial scene-source changes')
    accepted=json.loads((ROOT/'evidence/is6-spatial-artifact-20261101a.json').read_text())
    gen=artifact.generation()
    if not accepted['accepted'] or accepted['generation']!=gen:raise ValueError('Accepted spatial artifact required')
    runtime=json.loads((ROOT/'evidence/built-runtime-is4-stream.json').read_text())
    for p in FILES[2:4]:
        if sha(p)!=runtime['source_sha256'][p.relative_to(ROOT).as_posix()]:raise ValueError('Native renderer source differs')
    return dict(schema=1,id='cosmos2:is6-static-SPECK-spatial-mesh',version='0.1.0',
                source_sha256=dict(IMPORTED),artifact=gen,engine_sha256=runtime['engine_sha256'])


def lines(payload):
    mesh=payload['mesh'];nr,na=mesh['radial_count'],mesh['azimuth_sectors'];vertices=mesh['display_vertices_relative_m']
    unit=payload['binding']['source_configuration']['material_radius_m']
    for i in range(nr):
        yield 'ring_'+str(i),1,[[x/unit for x in v] for v in vertices[i*(na+1):(i+1)*(na+1)]]
    for j in range(na):
        yield 'meridian_'+str(j),2,[[x/unit for x in vertices[i*(na+1)+j]] for i in range(nr)]


def prepare(run,folder):
    if not isinstance(run,artifact.Run):raise ValueError('Spatial Run required')
    gen=generation();payload=run.payload
    if payload['generation']!=gen['artifact']:raise ValueError('Spatial scene artifact generation differs')
    folder=Path(folder).resolve()
    if not folder.is_relative_to((ROOT/'output').resolve()):raise ValueError('Spatial scene files must remain under output')
    if folder.exists():raise FileExistsError('Use a new spatial scene binding directory')
    folder.mkdir(parents=True)
    text=[];names=[];count=0;maximum=0.;bounds=[[],[],[]]
    for identifier,color,points in lines(payload):
        text.extend(['mesh -c '+str(color)+' {','id '+identifier,str(len(points))])
        for point in points:
            words=[format(x,'.17g') for x in point];text.append(' '.join(words))
            converted=[struct.unpack('<f',struct.pack('<f',float(x)))[0] for x in words]
            maximum=max(maximum,math.dist(point,converted));count+=1
            for k in range(3):bounds[k].append(point[k])
        text.append('}');names.append(identifier+' '+identifier)
    wire=folder/'wire.speck';labels=folder/'wire.names'
    wire.write_text('\n'.join(text)+'\n',encoding='utf-8',newline='\n')
    labels.write_text('\n'.join(names)+'\n',encoding='utf-8',newline='\n')
    center=[(min(v)+max(v))*.5 for v in bounds]
    radius=max(math.hypot(*[p[k]-center[k] for k in range(3)]) for _,_,points in lines(payload) for p in points)
    unit=payload['binding']['source_configuration']['material_radius_m']
    record=dict(schema=1,kind='is6_static_spatial_scene_files',generation=gen,artifact_id=run.id,
        artifact_sha256=artifact.digest(payload),source_binding_sha256=payload['binding']['binding_sha256'],
        wire_sha256=sha(wire),names_sha256=sha(labels),normalization_unit_m=unit,
        line_count=len(names),vertex_instances=count,maximum_predicted_float32_error_normalized=maximum,
        maximum_predicted_float32_error_m=maximum*unit,plot_focus_normalized=center,plot_radius_normalized=radius,
        quantization_scope='Predicted static-parser GL_FLOAT conversion; not a GPU readback measurement.')
    (folder/'binding.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert generation()==gen
    return record


class Scene:
    def __init__(self,native,run,folder):
        self.native=native;self.run=run;self.payload=run.payload;self.folder=Path(folder)
        self.prepared=prepare(run,folder);token=uuid.uuid4().hex
        self.frame='IS6SpatialFrame_'+token;self.wire='IS6SpatialWire_'+token;self.focus='IS6SpatialFocus_'+token
        self.camera=None;self.hidden={};self.attached=False;self.visible=True

    def attach(self):
        if self.attached:raise ValueError('Spatial scene already attached')
        p=self.payload;bound=p['binding'];unit=self.prepared['normalization_unit_m']
        self.camera=self.native('return {camera=openspace.navigation.getNavigationState("Root")}')['camera']
        names=['LabGrid','LabBarycenter','LabProbe']
        for b in p['phase']['bodies']:names.extend(b[k] for k in ['scene_node','label_node','shape_node','spin_node'] if b.get(k))
        self.hidden=self.native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v;openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",false) end end end;return {flags=f}')['flags']
        nodes=[dict(Identifier=self.frame,Parent='LabRoot',Transform=dict(Translation=dict(Type='StaticTranslation',Position=bound['center_render_m']),Scale=dict(Type='StaticScale',Scale=unit)),GUI=dict(Name='Corte espacial de referência · '+bound['name'],Focusable=False)),
               dict(Identifier=self.wire,Parent=self.frame,Renderable=dict(Type='RenderableConstellationLines',File=(self.folder/'wire.speck').as_posix(),NamesFile=(self.folder/'wire.names').as_posix(),Unit='m',Colors=[[.36,.87,1.],[.74,.53,1.]],LineWidth=1.5,DrawElements=True),GUI=dict(Name='Anéis e meridianos da malha',Focusable=False)),
               dict(Identifier=self.focus,Parent=self.frame,Transform=dict(Translation=dict(Type='StaticTranslation',Position=self.prepared['plot_focus_normalized'])),GUI=dict(Name='Foco da malha espacial'))]
        self.attached=True;began=time.monotonic()
        try:
            self.native(''.join('openspace.addSceneGraphNode('+lua(n)+');' for n in nodes)+'return {queued=true}')
            while self.native('return openspace.cosmos2SceneInitialization()')['cpu_initializing']:
                if time.monotonic()-began>15:raise TimeoutError('Spatial scene initialization exceeded15s')
                time.sleep(.025)
            self.frame_camera();state=self.read_native()
            if not state['exists'] or not state['draw'] or state['center']!=bound['center_render_m'] or state['scale']!=unit:
                raise ValueError('Native spatial transform was not confirmed')
            self.ready_s=time.monotonic()-began;return state
        except Exception:
            self.close();raise

    def frame_camera(self):
        unit=self.prepared['normalization_unit_m'];extent=max(1.,self.prepared['plot_radius_normalized'])
        camera=dict(Anchor=self.focus,ReferenceFrame='Root',Position=[0.,-2.6*extent*unit,1.7*extent*unit],Up=[0.,0.,1.])
        self.native('openspace.navigation.setNavigationState('+lua(camera)+');return {ready=true}')

    def read_native(self):
        return self.native('return {exists=openspace.hasSceneGraphNode('+lua(self.wire)+'),draw=openspace.propertyValue("Scene.'+self.wire+'.Renderable.DrawElements"),center=openspace.propertyValue("Scene.'+self.frame+'.Translation.Position"),scale=openspace.propertyValue("Scene.'+self.frame+'.Scale.Scale"),file=openspace.propertyValue("Scene.'+self.wire+'.Renderable.File")}')

    def set_visible(self,value):
        if type(value) is not bool:raise ValueError('Explicit mesh visibility required')
        self.native('openspace.setPropertyValueSingle("Scene.'+self.wire+'.Renderable.DrawElements",'+lua(value)+');return {ready=true}')
        self.visible=value

    def close(self):
        if self.camera is not None:self.native('openspace.navigation.setNavigationState('+lua(self.camera)+');return {restored=true}')
        if self.attached:
            self.native('if openspace.hasSceneGraphNode('+lua(self.frame)+') then openspace.removeSceneGraphNode('+lua(self.frame)+') end;return {removed=true}')
        if self.hidden:self.native('for n,v in pairs('+lua(self.hidden)+') do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end end;return {restored=true}')
        self.attached=False;self.camera=None;self.hidden={}
