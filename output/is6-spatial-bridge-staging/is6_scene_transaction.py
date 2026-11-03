"""Hidden native candidates and acknowledged atomic swaps of spatial views."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import time

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
sys.path.insert(0,str(ROOT/'output/is6-spatial-scene-staging'))
import is6_spatial_scene as base
lua=base.lua
FILES=[Path(__file__),ROOT/'IS-6-PONTE-CENA-CONTRATO.md',ROOT/'evidence/is6-spatial-native-20261101a.json',ROOT/'evidence/is6-spatial-prototype-visual-20261101a.json']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
IMPORTED={p.relative_to(ROOT).as_posix():sha(p) for p in FILES}


def generation():
    if any(sha(ROOT/n)!=v for n,v in IMPORTED.items()):raise ValueError('Restart after spatial transaction source changes')
    for p in FILES[-2:]:
        if not json.loads(p.read_text())['accepted']:raise ValueError('Accepted spatial native prototype required')
    return dict(schema=1,id='cosmos2:is6-hidden-candidate-scene-owner',version='0.1.0',source_sha256=dict(IMPORTED),renderer=base.generation())


def check_cancel(event):
    if event is not None and event.is_set():raise ValueError('Preparação da malha cancelada; vista anterior preservada.')


class Candidate(base.Scene):
    def attach(self,cancel=None):
        check_cancel(cancel)
        if self.attached:raise ValueError('Spatial candidate already attached')
        bound=self.payload['binding'];unit=self.prepared['normalization_unit_m']
        nodes=[dict(Identifier=self.frame,Parent='LabRoot',Transform=dict(Translation=dict(Type='StaticTranslation',Position=bound['center_render_m']),Scale=dict(Type='StaticScale',Scale=unit)),GUI=dict(Name='Corte espacial pendente',Focusable=False)),
            dict(Identifier=self.wire,Parent=self.frame,Renderable=dict(Type='RenderableConstellationLines',File=(self.folder/'wire.speck').as_posix(),NamesFile=(self.folder/'wire.names').as_posix(),Unit='m',Colors=[[.36,.87,1.],[.74,.53,1.]],LineWidth=1.5,DrawElements=False),GUI=dict(Name='Malha candidata oculta',Focusable=False)),
            dict(Identifier=self.focus,Parent=self.frame,Transform=dict(Translation=dict(Type='StaticTranslation',Position=self.prepared['plot_focus_normalized'])),GUI=dict(Name='Foco da malha candidata'))]
        self.attached=True;self.visible=False;began=time.monotonic()
        try:
            self.native(''.join('openspace.addSceneGraphNode('+lua(n)+');' for n in nodes)+'return {queued=true}')
            check_cancel(cancel)
            while self.native('return openspace.cosmos2SceneInitialization()')['cpu_initializing']:
                check_cancel(cancel)
                if time.monotonic()-began>15:raise TimeoutError('Spatial candidate initialization exceeded15s')
                time.sleep(.025)
            check_cancel(cancel);state=self.read_native()
            if not state['exists'] or state['draw'] or state['center']!=bound['center_render_m'] or state['scale']!=unit:raise ValueError('Hidden native candidate differs')
            self.ready_s=time.monotonic()-began;return state
        except Exception:
            self.close();raise

    def desired_camera(self):
        unit=self.prepared['normalization_unit_m'];extent=max(1.,self.prepared['plot_radius_normalized'])
        return dict(Anchor=self.focus,ReferenceFrame='Root',Position=[0.,-2.6*extent*unit,1.7*extent*unit],Up=[0.,0.,1.])


class Owner:
    def __init__(self,native,current_phase):
        self.native=native;self.current_phase=copy.deepcopy(current_phase);self.active=None;self.context=None;self.error=None
        self.scientific_generation=generation()

    def prepare(self,run,folder,cancel=None):
        check_cancel(cancel);candidate=Candidate(self.native,run,folder)
        try:candidate.attach(cancel);return candidate
        except Exception:
            candidate.close();raise

    def _capture(self):
        names=['LabGrid','LabBarycenter','LabProbe']
        for b in self.current_phase['bodies']:names.extend(b[k] for k in ['scene_node','label_node','shape_node','spin_node'] if b.get(k))
        result=self.native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')
        return result

    def commit(self,candidate,visible=True,cancel=None):
        check_cancel(cancel)
        if type(visible) is not bool or not isinstance(candidate,Candidate) or not candidate.attached:raise ValueError('Ready hidden spatial candidate required')
        state=candidate.read_native()
        if state['draw']:raise ValueError('Candidate became visible before confirmation')
        old=self.active;context=self.context or self._capture()
        before=self.native('return {camera=openspace.navigation.getNavigationState("Root")}')['camera']
        prior_draw=False if old is None else old.visible
        old_wire=None if old is None else old.wire
        hide='for n,v in pairs('+lua(context['flags'])+') do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",false) end end;'
        rollback='openspace.navigation.setNavigationState('+lua(before)+');'
        rollback+='if openspace.hasSceneGraphNode('+lua(candidate.wire)+') then openspace.setPropertyValueSingle("Scene.'+candidate.wire+'.Renderable.DrawElements",false) end;'
        if old:
            rollback+='openspace.setPropertyValueSingle("Scene.'+old.wire+'.Renderable.DrawElements",'+lua(prior_draw)+');'
        else:
            rollback+='for n,v in pairs('+lua(context['flags'])+') do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end end;'
        # Validate every node before any mutation. One Lua request performs the
        # visible swap; Python publishes ownership only after its acknowledgement.
        script='local is6_commit_candidate='+lua(candidate.wire)+';'
        for name in [candidate.wire,candidate.focus,candidate.frame]+([old_wire] if old else []):
            script+='if not openspace.hasSceneGraphNode('+lua(name)+') then error("Spatial commit node unavailable") end;'
        apply=hide
        if old:apply+='openspace.setPropertyValueSingle("Scene.'+old.wire+'.Renderable.DrawElements",false);'
        apply+='openspace.setPropertyValueSingle("Scene.'+candidate.wire+'.Renderable.DrawElements",'+lua(visible)+');openspace.navigation.setNavigationState('+lua(candidate.desired_camera())+');'
        script+='local ok,err=pcall(function() '+apply+' end);if not ok then '+rollback+' error(tostring(err)) end;return {committed=true}'
        check_cancel(cancel)
        try:
            reply=self.native(script)
            if reply.get('committed') is not True:raise ValueError('Spatial scene acknowledgement differs')
        except Exception:
            try:self.native(rollback+'return {restored=true}')
            except Exception as error:self.error='Rollback da cena não confirmado: '+str(error)
            raise
        candidate.visible=visible;self.active=candidate;self.context=context;self.error=None
        if old:
            try:old.close()
            except Exception as error:self.error='Nova malha confirmada; limpeza anterior pendente: '+str(error)
        return candidate.read_native()

    def close(self):
        if self.context:
            self.native('openspace.navigation.setNavigationState('+lua(self.context['camera'])+');return {restored=true}')
        if self.active:self.active.close();self.active=None
        if self.context:
            self.native('for n,v in pairs('+lua(self.context['flags'])+') do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end end;return {restored=true}')
        self.context=None
