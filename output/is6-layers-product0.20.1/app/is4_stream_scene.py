"""Single pending trajectory upload; line and endpoint are drawn from the same VBO."""
from pathlib import Path
import copy
import json
import math
import time
import uuid
from is4_trajectory_transport import encode,decode,publish
from is4_particle_scene import GRAPHIC_UNIT_M


def lua(value):
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False)
    if type(value) is bool:return str(value).lower()
    if type(value) in (int,float):return format(value,'.17g')
    if isinstance(value,list):return '{'+','.join(lua(v) for v in value)+'}'
    if isinstance(value,dict):return '{'+','.join('['+lua(k)+']='+lua(v) for k,v in value.items())+'}'
    raise ValueError('Unsupported native literal')


class Stream:
    @staticmethod
    def plot_focus(g):
        points=g['vertices_normalized']
        center=[(min(p[k] for p in points)+max(p[k] for p in points))*.5 for k in range(3)]
        radius=max(math.dist(p,center) for p in points)
        return center,max(1.,.55*radius)

    def __init__(self,native,folder,physical_unit_m,initial_field_T):
        self.native=native;self.folder=Path(folder);self.unit=physical_unit_m;self.field=initial_field_T
        if self.folder.exists():raise FileExistsError('Use a new trajectory binding directory')
        self.folder.mkdir(parents=True)
        token=uuid.uuid4().hex;self.frame='LabIS4StreamFrame_'+token;self.trail='LabIS4StreamTrail_'+token;self.focus='LabIS4StreamFocus_'+token;self.axes='LabIS4StreamAxes_'+token
        self.path=self.folder/'trajectory.bin';self.binding=None;self.pending=None;self.confirmed=None;self.latest_native=None;self.attached=False;self.visible=True;self.last_phase=None;self.pending_since=None

    def attach(self,state):
        if self.attached:raise ValueError('Trajectory already attached')
        packet,record=encode(state,self.unit,self.field);g=record['geometry'];self.binding=record['metadata']['binding_sha256']
        publish(self.path,packet,self.binding)
        (self.folder/'binding.json').write_text(json.dumps(record['descriptor'],indent=2)+'\n',encoding='utf-8')
        seed=self.folder/'seed.speck';names=self.folder/'seed.names'
        seed.write_text('mesh -c 1 {\nid trajectory\n1\n0 0 0\n}\n',encoding='utf-8');names.write_text('trajectory trajectory\n',encoding='utf-8')
        nodes=[{'Identifier':self.frame,'Parent':'LabRoot','Transform':{
            'Translation':{'Type':'StaticTranslation','Position':g['anchor_relative_LabRoot_m']},
            'Rotation':{'Type':'StaticRotation','Rotation':g['rotation_euler_rad']},'Scale':{'Type':'StaticScale','Scale':GRAPHIC_UNIT_M}},
            'GUI':{'Name':'Vista ampliada da trajetória','Focusable':False}},
            {'Identifier':self.trail,'Parent':self.frame,'Renderable':{'Type':'RenderableConstellationLines','File':seed.as_posix(),'NamesFile':names.as_posix(),
                'ConfirmedTrajectoryFile':self.path.as_posix(),'TrajectoryBinding':self.binding,'Unit':'m','Colors':[[.3,.9,1.]],'LineWidth':3,'DrawElements':self.visible},'GUI':{'Name':'Trajetória e marcador sincronizados','Focusable':False}},
            {'Identifier':self.focus,'Parent':self.frame,'Transform':{'Translation':{'Type':'StaticTranslation','Position':self.plot_focus(g)[0]}},'GUI':{'Name':'Foco da trajetória ampliada'}},
            {'Identifier':self.axes,'Parent':self.frame,'Transform':{'Scale':{'Type':'StaticScale','Scale':.6}},'Renderable':{'Type':'RenderableCartesianAxes'},'GUI':{'Name':'Eixos congelados','Focusable':False}}]
        self.attached=True
        self.native(''.join('openspace.addSceneGraphNode('+lua(n)+');' for n in nodes)+'return {queued=true}')
        self.pending=record;self.pending_since=time.monotonic();self.last_phase=(copy.deepcopy(state['experiment']['phase']),state['experiment']['revision'])

    def frame_camera(self):
        record=self.confirmed or self.pending
        if record is None:raise ValueError('No trajectory to frame')
        g=record['geometry']
        center,factor=self.plot_focus(g)
        self.native('openspace.setPropertyValueSingle("Scene.'+self.focus+'.Translation.Position",'+lua(center)+');openspace.navigation.setNavigationState('+lua({'Anchor':self.focus,'ReferenceFrame':'LabRoot','Position':[v*factor for v in g['camera_offset_render_m']],'Up':g['camera_up_render']})+');return {ready=true}')

    def poll(self):
        if not self.attached:return None
        response=self.native('return {status=openspace.propertyValue("Scene.'+self.trail+'.Renderable.ConfirmedTrajectoryStatus")}')
        native=json.loads(response['status']);self.latest_native=native
        if native.get('state')=='rejected':raise RuntimeError('Native trajectory rejected: '+str(native))
        if self.pending and native.get('state')=='accepted' and native.get('gpu_buffer_uploaded') and native.get('metadata')==self.pending['metadata']:
            g=self.pending['geometry'];error=native['maximum_gpu_quantization_normalized']*self.unit
            if error+g['global_frame_conservative_error_m']>g['adopted_total_error_bound_m']:raise ValueError('Confirmed plot quantization exceeded scientific budget')
            self.confirmed=self.pending;self.pending=None;self.pending_since=None
            self.native('openspace.setPropertyValueSingle("Scene.'+self.focus+'.Translation.Position",'+lua(self.plot_focus(g)[0])+');return {ready=true}')
        if self.pending and self.pending_since is not None and time.monotonic()-self.pending_since>2.:raise TimeoutError('A vista não confirmou a fase em2s; partícula pausada para preservar a última vista confirmada.')
        return native

    def update(self,state):
        self.poll()
        if self.pending:return False
        phase=(state['experiment']['phase'],state['experiment']['revision'])
        if phase==self.last_phase:return False
        packet,record=encode(state,self.unit,self.field)
        if record['metadata']['binding_sha256']!=self.binding:raise ValueError('Trajectory rebind required after worker/experiment/token/frame changes')
        old=self.confirmed['metadata']
        decode(packet,self.binding,old['sequence']+1,old['time_s'],old['revision'])
        publish(self.path,packet,self.binding,old['sequence']+1,old['time_s'],old['revision'])
        self.pending=record;self.pending_since=time.monotonic();self.last_phase=copy.deepcopy(phase)
        return True

    def set_visible(self,value):
        if type(value) is not bool:raise ValueError('Explicit trajectory visibility required')
        # Keep the receiver updating while hidden; hide draw submission only.
        self.native('openspace.setPropertyValueSingle("Scene.'+self.trail+'.Renderable.DrawElements",'+lua(value)+');return {ready=true}')
        self.visible=value

    def close(self):
        if self.attached:
            # Freeze a camera anchored to this frame before deleting its subtree.
            code='local n=openspace.navigation.getNavigationState("Root");if n.Anchor=='+lua(self.focus)+' then local p=openspace.worldPosition(n.Anchor);local r=openspace.worldPosition("LabRoot");openspace.setPropertyValueSingle("Scene.LabCameraAnchor.Translation.Position",{p[1]-r[1],p[2]-r[2],p[3]-r[3]});n.Anchor="LabCameraAnchor";openspace.navigation.setNavigationState(n) end;'
            self.native(code+'if openspace.hasSceneGraphNode('+lua(self.frame)+') then openspace.removeSceneGraphNode('+lua(self.frame)+') end;return {removed=true}')
        self.attached=False
