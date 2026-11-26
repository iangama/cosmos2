"""Own one frozen magnetic scene sample without changing the physical solution."""
import copy
import json

from body_field_scene import prepare
from body_field_map_layer import MapSelection


def lua(value):return json.dumps(value,ensure_ascii=False)


def vec(value):return '{'+','.join(format(v,'.17g') for v in value)+'}'


class BodyFieldLayer(MapSelection):
    def __init__(self,lab):
        self.lab=lab;self.preview=None;self.label_restore=None

    @property
    def public(self):
        return copy.deepcopy(self.preview)

    @property
    def masked_body_id(self):
        return self.preview['reading']['body_id'] if self.preview and self.preview.get('visible',True) else None

    def _remove_code(self):
        if not self.preview:return ''
        render=self.preview['render'];code=self.lab._freeze_anchor(render['frame_node'])
        code+=''.join('if openspace.hasSceneGraphNode('+lua(node)+') then openspace.removeSceneGraphNode('+lua(node)+') end;' for node in reversed(render['nodes']))
        node,enabled=self.label_restore
        code+='if openspace.hasSceneGraphNode('+lua(node)+') then openspace.setPropertyValueSingle("Scene.'+node+'.Renderable.Enabled",'+str(enabled).lower()+') end;'
        return code

    def clear(self,render=True):
        if self.preview:
            identifier=self.masked_body_id
            if self.lab._lua(self._remove_code()+'return {cleared=true}',True).get('cleared') is not True:
                raise RuntimeError('O motor não confirmou a remoção do vetor magnético.')
            with self.lab.lock:self.preview=None;self.label_restore=None
            self.lab.rendered_attributes.pop(identifier,None);self.lab.rendered_sequence=None
            if render and self.lab.mode=='experiment':self.lab._render()

    def expect(self,action):
        if set(action)!={'command','layer_id'} or not self.preview or action.get('layer_id')!=self.preview['render']['id']:
            raise ValueError('A camada magnética mudou; consulte o estado atual.')

    def view(self):
        r=self.preview['render'];view=r['view']
        self.lab._lua('openspace.navigation.setNavigationState({Anchor='+lua(r['frame_node'])+',ReferenceFrame="LabRoot",Position='+vec(view['position_render_relative_m'])+',Up='+vec(view['up_render'])+'});return {queued=true}',True)

    def show(self,reading,representation='vector',restored=False):
        code,result=prepare(reading,representation);r,g=result['render'],result['geometry']
        with self.lab.lock:state=copy.deepcopy(self.lab.latest)
        if not state['paused'] or any(reading[k]!=state[k] for k in (['system_id'] if restored else ['system_id','edit_token','revision','time'])):
            raise ValueError('Pause e confirme a fase antes de desenhar o vetor.')
        body=next(b for b in state['bodies'] if b['id']==reading['body_id'])
        old_id=self.masked_body_id
        if old_id==body['id']:label_restore=self.label_restore
        else:
            value=self.lab._lua('return {enabled=openspace.propertyValue("Scene.'+body['label_node']+'.Renderable.Enabled")}',True)
            label_restore=(body['label_node'],value['enabled'])
        cleanup=''.join('if openspace.hasSceneGraphNode('+lua(node)+') then openspace.removeSceneGraphNode('+lua(node)+') end;' for node in reversed(r['nodes']))
        transaction='local ok,err=pcall(function() '+code+' end);if not ok then '+cleanup+'error(err) end;'
        # Verify local coordinates before replacing any previous accepted layer.
        transaction+='local c=openspace.propertyValue("Scene.'+r['frame_node']+'.Translation.Position");local p=openspace.propertyValue("Scene.'+r['label_node']+'.Translation.Position");local ec='+vec(g['center_render_m'])+';local ep='+vec(r['label_position_render_relative_m'])+';'
        transaction+='for k=1,3 do if math.abs(c[k]-ec[k])>0.001 or math.abs(p[k]-ep[k])>0.001 then '+cleanup+'error("Magnetic local coordinates not confirmed") end end;'
        transaction+=self._remove_code()
        # Restore the former body's marker using the CURRENT display policy.
        if old_id and old_id!=body['id']:
            previous=next((b for b in state['bodies'] if b['id']==old_id),None)
            if previous:
                transaction+='openspace.setPropertyValueSingle("Scene.'+previous['scene_node']+'.Renderable.Enabled",'+str(not self.lab.physical_radii).lower()+');'
                transaction+='if openspace.hasSceneGraphNode('+lua(previous['shape_node'])+') then openspace.setPropertyValueSingle("Scene.'+previous['shape_node']+'.Renderable.Enabled",'+str(self.lab.physical_radii and bool(previous['attributes']['radius_m'])).lower()+') end;'
        transaction+='openspace.setPropertyValueSingle("Scene.'+body['scene_node']+'.Renderable.Enabled",false);openspace.setPropertyValueSingle("Scene.'+body['label_node']+'.Renderable.Enabled",false);'
        transaction+='if openspace.hasSceneGraphNode('+lua(body['shape_node'])+') then openspace.setPropertyValueSingle("Scene.'+body['shape_node']+'.Renderable.Enabled",false) end;return {ready=true}'
        if self.lab._lua(transaction,True).get('ready') is not True:
            raise RuntimeError('O motor não confirmou o vetor magnético.')
        public={'schema':1,'reading':reading,'render':r,'reference':g['reference'],
            'arrow_length_m':g['arrow'].get('length_m'),'arrow_drawn':g['arrow']['drawn'],
            'policy':g['policy'],'native_local_coordinates_confirmed':True,
            'persistence':'Configuration, visibility and frozen SI reading saved atomically with checkpoint/branch. Native node IDs are rebuilt on restore.'}
        public['visible']=True;public['restored_from_checkpoint']=restored
        public['representation']=representation
        if representation=='lines':
            traced=g['field_lines']
            public['line_summary']={'curves':len(traced['lines']),'degree':traced['degree'],'domain':traced['domain'],
                'vertices':sum(len(line['points_m']) for line in traced['lines']),
                'ends':[[line[side]['termination'] for side in ['negative','positive']] for line in traced['lines']],
                'SI_vertices_and_fields_receipt':r['receipt'],'observational_uncertainty':None}
        public['map_probe']=None
        if representation in ('shell','cut'):
            display=g['map_display']
            public['map_summary']={k:display[k] for k in ['shape','minimum_sampled_T','maximum_sampled_T','palette_rgb','sample_count','drawn_symbols','glyph_half_length_m','legend']}
        with self.lab.lock:self.preview=public;self.label_restore=label_restore
        for identifier in [old_id,body['id']]:self.lab.rendered_attributes.pop(identifier,None)
        self.lab.rendered_sequence=None
        self.view()
        return self.public


    def set_visible(self,visible):
        if type(visible) is not bool or self.preview is None:raise ValueError('Visibilidade da camada magnética inválida.')
        r=self.preview['render'];body=next(b for b in self.lab.latest['bodies'] if b['id']==self.preview['reading']['body_id'])
        nodes=[m['node'] for m in r['meshes']]+[r['label_node']]
        if self.preview.get('map_probe'):nodes.append(self.preview['map_probe']['native_node'])
        code=''.join('openspace.setPropertyValueSingle("Scene.'+n+'.Renderable.Enabled",'+str(visible).lower()+');' for n in nodes)
        code+='openspace.setPropertyValueSingle("Scene.'+body['label_node']+'.Renderable.Enabled",'+str(False if visible else self.label_restore[1]).lower()+');'
        if self.lab._lua(code+'return {ready=true}',True).get('ready') is not True:raise RuntimeError('Visibilidade magnética não confirmada pelo motor.')
        with self.lab.lock:self.preview['visible']=visible
        self.lab.rendered_attributes.pop(body['id'],None);self.lab.rendered_sequence=None;self.lab._render()
        return self.public

    def checkpoint(self,configuration=None):
        import body_field_view
        state=self.lab.latest
        if configuration is None:
            configuration={'selected_body_id':self.preview['reading']['body_id'] if self.preview else state['bodies'][0]['id'],
                'representation':self.preview['representation'] if self.preview else 'vector',
                'earth':[-23.55,-46.63,1000.],'jupiter':[1.5*71492000.,0.,0.,13]}
        return body_field_view.capture(state,configuration,self.public)

    def restore(self,value):
        if value and value['layer']:
            layer=value['layer'];self.show(layer['reading'],layer['representation'],restored=True)
            if layer.get('map_probe'):self.select_map_cell(layer['map_probe']['row'],layer['map_probe']['column'])
            if not layer['visible']:self.set_visible(False)

    def export(self,configuration):
        import hashlib
        from pathlib import Path
        from artifacts import export_json
        if self.preview is None:raise ValueError('Mostre uma camada antes de exportar.')
        data=self.checkpoint(configuration);render=self.preview['render'];path=Path(render['receipt'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=render['receipt_sha256']:raise ValueError('Recibo de geometria magnética alterado.')
        geometry=json.loads(path.read_text(encoding='utf-8'))['geometry']
        if geometry['reading']!=self.preview['reading']:raise ValueError('Geometria e leitura magnética divergiram.')
        stale=any(self.preview['reading'][k]!=self.lab.latest[k] for k in ['system_id','edit_token','revision','time'])
        return export_json('body-magnetic-field',{'schema':1,'view':data,'geometry':geometry,'reading_is_stale':stale,
            'scope':'Frozen internal-model sample/curves; no total magnetosphere, particle trajectories or observational uncertainty propagation.'})
