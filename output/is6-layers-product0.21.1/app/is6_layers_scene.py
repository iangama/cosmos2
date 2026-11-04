"""Experimental native pair owner; deliberately separate from product services."""
import copy
import hashlib
import math
from pathlib import Path
import struct
import time
import uuid

from is6_product_scene import Candidate, lua
from is6_layer_contract import compose, digest
import body_field_scene


class Magnetic:
    def __init__(self,native,reading):
        self.native=native
        _,self.prepared=body_field_scene.prepare(reading,'vector')
        self.render=self.prepared['render'];self.geometry=self.prepared['geometry']
        self.frame='IS6MagneticFrame_'+uuid.uuid4().hex
        self.probe_frame=self.frame+'_basis';self.probe=self.frame+'_probe';self.display_probe=self.frame+'_display_probe'
        self.meshes=[dict(m,node=self.frame+'_'+str(i)) for i,m in enumerate(self.render['meshes'])]
        self.nodes=[self.frame,*[m['node'] for m in self.meshes],self.probe_frame,self.display_probe,self.probe]
        self.attached=False

    @property
    def draw_nodes(self):return [m['node'] for m in self.meshes] if self.attached else []

    def attach(self):
        g=self.geometry;unit=g['reference_radius_m']
        nodes=[dict(Identifier=self.frame,Parent='LabRoot',Transform=dict(Translation=dict(Type='StaticTranslation',Position=g['center_render_m'])),GUI=dict(Name='Referência magnética independente',Focusable=False))]
        for m in self.meshes:
            nodes.append(dict(Identifier=m['node'],Parent=self.frame,Transform=dict(Rotation=dict(Type='StaticRotation',Rotation=m['rotation_euler_rad']),Scale=dict(Type='StaticScale',Scale=m['scale_m'])),
                Renderable=dict(Type='RenderableConstellationLines',File=m['file'],NamesFile=m['names_file'],Unit='m',Colors=[m['color_rgb']],LineWidth=2,DrawElements=False),GUI=dict(Name=m['quantity'],Focusable=False)))
        nodes.extend([dict(Identifier=self.probe_frame,Parent=self.frame,Transform=dict(Rotation=dict(Type='StaticRotation',Rotation=self.render['model_to_render_rotation_euler_rad']),Scale=dict(Type='StaticScale',Scale=unit)),GUI=dict(Focusable=False)),
                      dict(Identifier=self.display_probe,Parent=self.probe_frame,Transform=dict(Translation=dict(Type='StaticTranslation',Position=[x/unit for x in g['point_model_m']])),GUI=dict(Focusable=False)),
                      dict(Identifier=self.probe,Parent=self.frame,Transform=dict(Translation=dict(Type='StaticTranslation',Position=self.render['label_position_render_relative_m'])),GUI=dict(Focusable=False))])
        self.attached=True
        try:
            self.native(''.join('openspace.addSceneGraphNode('+lua(n)+');' for n in nodes)+'return {queued=true}')
            began=time.monotonic()
            while self.native('return openspace.cosmos2SceneInitialization()')['cpu_initializing']:
                if time.monotonic()-began>15:raise TimeoutError('Magnetic hidden initialization exceeded15s')
                time.sleep(.025)
            actual=self.read()
            if any(actual['draw'].values()):raise ValueError('Magnetic candidate was not hidden')
            return actual
        except Exception:
            self.close();raise

    def read(self):
        for m in self.meshes:
            for path,seal in [(m['file'],m['file_sha256']),(m['names_file'],m['names_sha256'])]:
                if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=seal:raise ValueError('Magnetic scene file seal differs')
        r=self.native('local d,t={},{};for _,n in ipairs('+lua(self.draw_nodes)+') do d[n]=openspace.propertyValue("Scene."..n..".Renderable.DrawElements");t[n]={scale=openspace.propertyValue("Scene."..n..".Scale.Scale"),file=openspace.propertyValue("Scene."..n..".Renderable.File"),rotation=openspace.propertyValue("Scene."..n..".Rotation.Rotation")} end;return {draw=d,transforms=t,point_world=openspace.worldPosition('+lua(self.probe)+'),point_local=openspace.propertyValue("Scene.'+self.probe+'.Translation.Position"),display_point_world=openspace.worldPosition('+lua(self.display_probe)+'),center_world=openspace.worldPosition('+lua(self.frame)+'),center_local=openspace.propertyValue("Scene.'+self.frame+'.Translation.Position")}')
        if len(r['draw'])!=len(self.meshes):raise ValueError('Magnetic mesh set differs')
        for m in self.meshes:
            angles=[struct.unpack('f',struct.pack('f',a))[0] for a in m['rotation_euler_rad']]
            if r['transforms'][m['node']]!=dict(scale=m['scale_m'],file=m['file'],rotation=angles):raise ValueError('Magnetic native scale/file/float rotation differs')
        if max(abs(x-y) for x,y in zip(r['center_local'],self.geometry['center_render_m'],strict=True))>.001:raise ValueError('Magnetic local center differs: '+str(r))
        r['point_relative_m']=[x-y for x,y in zip(r['point_world'],r['center_world'],strict=True)]
        r['expected_relative_m']=body_field_scene.product(self.geometry['body_to_render'],self.geometry['point_model_m'])
        if max(abs(x-y) for x,y in zip(r['point_local'],r['expected_relative_m'],strict=True))>.001:raise ValueError('Magnetic SI point local position differs')
        r['world_difference_limits_m']=[math.ulp(x)+math.ulp(y)+.001 for x,y in zip(r['point_world'],r['center_world'],strict=True)]
        if any(abs(x-y)>limit for x,y,limit in zip(r['point_relative_m'],r['expected_relative_m'],r['world_difference_limits_m'],strict=True)):raise ValueError('Magnetic native relative point differs: '+str(r))
        # StaticRotation is a Vec3Property and builds a float quaternion. The
        # scientific point therefore uses the same direct double translation
        # as the accepted body-field label. Check the graphic transform
        # independently against the generator's already declared bounds.
        r['display_point_relative_m']=[x-y for x,y in zip(r['display_point_world'],r['center_world'],strict=True)]
        r['display_position_error_bound_m']=max(m['conservative_display_position_error_bound_m'] for m in self.meshes)
        r['display_world_difference_limits_m']=[math.ulp(x)+math.ulp(y)+r['display_position_error_bound_m'] for x,y in zip(r['display_point_world'],r['center_world'],strict=True)]
        if any(abs(x-y)>limit for x,y,limit in zip(r['display_point_relative_m'],r['expected_relative_m'],r['display_world_difference_limits_m'],strict=True)):raise ValueError('Magnetic graphic point exceeds declared display bound')
        return r

    def close(self):
        if not self.attached:return
        self.native(''.join('if openspace.hasSceneGraphNode('+lua(n)+') then openspace.removeSceneGraphNode('+lua(n)+') end;' for n in reversed(self.nodes))+'return {removed=true}')
        remaining=self.native('local r={};for _,n in ipairs('+lua(self.nodes)+') do r[n]=openspace.hasSceneGraphNode(n) end;return r')
        if any(remaining.values()):raise ValueError('Magnetic native removal not confirmed')
        self.attached=False


class Pair:
    def __init__(self,native,run,reading,folder):
        self.native=native
        self.plan=compose(run.payload['phase'],run.payload,reading,dict(spatial=True,magnetic=True))
        self.spatial=Candidate(native,run,folder);self.magnetic=Magnetic(native,reading)
        self.visible=dict(spatial=False,magnetic=False);self.magnetic_removed=False

    def attach(self):
        try:self.spatial.attach();self.magnetic.attach()
        except Exception:self.close();raise
        return self.read()

    def settings(self,visible):
        if set(visible)!={'spatial','magnetic'} or any(type(v) is not bool for v in visible.values()):raise ValueError('Explicit pair visibilities required')
        if self.magnetic_removed and visible['magnetic']:raise ValueError('Removed magnetic layer cannot be shown')
        return {self.spatial.wire:visible['spatial'],**{n:visible['magnetic'] for n in self.magnetic.draw_nodes}}

    def read(self):
        return dict(spatial=self.spatial.read_native(),magnetic=None if self.magnetic_removed else self.magnetic.read())

    def close(self):
        errors=[]
        for component in [self.magnetic,self.spatial]:
            try:component.close()
            except Exception as error:errors.append(str(error))
        if errors:raise RuntimeError('; '.join(errors))


class Owner:
    def __init__(self,native,phase):
        self.native=native;self.phase=copy.deepcopy(phase)
        self.active=None;self.context=None;self.faulted=False;self.retired=[];self.prepared=[];self.error=None

    def context_now(self):
        names=['LabGrid','LabBarycenter','LabProbe']
        for b in self.phase['bodies']:names.extend(b[k] for k in ['scene_node','label_node','shape_node','spin_node'] if b.get(k))
        return self.native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')

    def prepare(self,run,reading,folder):
        if self.faulted:raise ValueError('Native recovery required')
        if digest(run.payload['phase'])!=digest(self.phase):raise ValueError('Pair belongs to another owner source phase')
        pair=Pair(self.native,run,reading,folder);self.prepared.append(pair)
        try:pair.attach()
        except Exception:
            # Retain ownership if removal itself failed.
            pair.close();self.prepared.remove(pair);raise
        return pair

    @staticmethod
    def draw_code(settings):
        return ''.join('openspace.setPropertyValueSingle("Scene.'+n+'.Renderable.DrawElements",'+lua(v)+');' for n,v in settings.items())

    @staticmethod
    def flag_code(flags):
        return 'for n,v in pairs('+lua(flags)+') do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end end;'

    def commit(self,pair,visible):
        if self.faulted:raise ValueError('Native recovery required')
        if pair not in self.prepared:raise ValueError('Pair was not prepared by this owner')
        if pair is self.active:raise ValueError('Use independent visibility operation')
        hidden=pair.read()
        if hidden['spatial']['draw'] or any(hidden['magnetic']['draw'].values()):raise ValueError('Prepared pair must remain hidden')
        desired=pair.settings(visible)
        old=self.active;context=self.context or self.context_now();before=self.context_now()
        prior={} if old is None else old.settings(old.visible)
        rollback=self.draw_code({n:False for n in desired})+self.draw_code(prior)
        if old is None:rollback+=self.flag_code(context['flags'])
        rollback+='openspace.navigation.setNavigationState('+lua(before['camera'])+');'
        code='for _,n in ipairs('+lua(list(desired)+list(prior))+') do if not openspace.hasSceneGraphNode(n) then error("Missing composite node") end end;'
        apply=self.flag_code({n:False for n in context['flags']})+self.draw_code({n:False for n in prior})+self.draw_code(desired)+'openspace.navigation.setNavigationState('+lua(pair.spatial.desired_camera())+');'
        try:
            reply=self.native(code+'local ok,err=pcall(function() '+apply+' end);if not ok then '+rollback+'error(tostring(err)) end;return {committed=true}')
            if reply.get('committed') is not True:raise ValueError('Composite ACK absent')
            actual=pair.read()
            if actual['spatial']['draw'] is not visible['spatial'] or any(v is not visible['magnetic'] for v in actual['magnetic']['draw'].values()):raise ValueError('Composite readback differs')
        except Exception:
            try:
                if self.native(rollback+'return {restored=true}').get('restored') is not True:raise ValueError('Composite rollback ACK absent')
            except Exception:self.context=context;self.faulted=True
            raise
        self.context=context;self.active=pair;pair.visible=dict(visible);self.prepared.remove(pair)
        if old:
            self.retired.append(old)
            try:old.close();self.retired.remove(old)
            except Exception as error:self.error='Previous pair cleanup pending: '+str(error)
        return actual

    def visibility(self,visible):
        if self.faulted or self.active is None:raise ValueError('Confirmed pair required')
        pair=self.active;prior=pair.settings(pair.visible);desired=pair.settings(visible)
        try:
            if self.native(self.draw_code(desired)+'return {changed=true}').get('changed') is not True:raise ValueError('Visibility ACK absent')
            state=pair.read()
            if state['spatial']['draw'] is not visible['spatial'] or state['magnetic'] and any(v is not visible['magnetic'] for v in state['magnetic']['draw'].values()):raise ValueError('Visibility readback differs')
        except Exception:
            try:
                if self.native(self.draw_code(prior)+'return {restored=true}').get('restored') is not True:raise ValueError('Visibility rollback ACK absent')
            except Exception:self.faulted=True
            raise
        pair.visible=dict(visible);return state

    def remove_magnetic(self):
        if self.faulted or self.active is None:raise ValueError('Confirmed pair required')
        try:self.active.magnetic.close()
        except Exception:self.faulted=True;raise
        self.active.magnetic_removed=True;self.active.visible['magnetic']=False
        return self.active.read()

    def close(self):
        if self.context:self.native('openspace.navigation.setNavigationState('+lua(self.context['camera'])+');return {restored=true}')
        for pair in [*self.prepared,*self.retired,*([self.active] if self.active else [])]:pair.close()
        if self.context:self.native(self.flag_code(self.context['flags'])+'return {restored=true}')
        self.prepared=[];self.retired=[];self.active=None;self.context=None;self.faulted=False;self.error=None
