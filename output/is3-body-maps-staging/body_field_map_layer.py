"""Read a cell from the immutable geometry that colored its native sample glyph."""
from pathlib import Path
import copy
import hashlib
import json
import math

from body_field_geometry import product


class MapSelection:
    def select_map_cell(self,row,column):
        if not self.preview or self.preview['representation'] not in ('shell','cut'):
            raise ValueError('Mostre um mapa corporal antes de selecionar a célula.')
        render=self.preview['render'];path=Path(render['receipt'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=render['receipt_sha256']:
            raise ValueError('Recibo do mapa magnético alterado.')
        geometry=json.loads(path.read_text(encoding='utf-8'))['geometry']
        if geometry['reading']!=self.preview['reading']:raise ValueError('Mapa e leitura corporal divergiram.')
        representation=self.preview['representation'];data=geometry['field_maps'];rows=data[representation]['samples']
        if type(row) is not int or type(column) is not int or not 0<=row<len(rows) or not 0<=column<len(rows[row]):
            raise ValueError('Índice de célula fora da grade magnética.')
        sample=rows[row][column]
        if sample is None:raise ValueError('Célula fora do domínio adotado; B indisponível, não zero.')
        position=product(data['body_to_render'],sample['position_model_m'])
        node='LabBodyMapProbe_'+render['id'];quote=lambda v:json.dumps(v,ensure_ascii=False)
        vec=lambda v:'{'+','.join(format(x,'.17g') for x in v)+'}'
        # A native label marks this cell; it does not move the original point B
        # arrow or turn the original field query into a different observation.
        code='if not openspace.hasSceneGraphNode('+quote(node)+') then openspace.addSceneGraphNode({Identifier='+quote(node)+',Parent='+quote(render['frame_node'])+',Transform={Translation={Type="StaticTranslation",Position='+vec(position)+'}},Renderable={Type="RenderableLabel",Text="+ Sonda do mapa",FontSize=50,Size='+format(math.log10(render['view']['distance_m']*.0015),'.17g')+',MinMaxSize={14,19},OrientationOption="Camera View Direction",EnableFading=false,Enabled='+str(self.preview['visible']).lower()+'},GUI={Name="Sonda do mapa magnetico",Focusable=false}}) else openspace.setPropertyValueSingle("Scene.'+node+'.Translation.Position",'+vec(position)+') end;'
        code+='local p=openspace.propertyValue("Scene.'+node+'.Translation.Position");local e='+vec(position)+';for k=1,3 do if math.abs(p[k]-e[k])>0.001 then error("Map probe native position not confirmed") end end;return {ready=true}'
        operation=code.removesuffix('return {ready=true}')
        code='local existed=openspace.hasSceneGraphNode('+quote(node)+');local old=nil;if existed then old=openspace.propertyValue("Scene.'+node+'.Translation.Position") end;local ok,err=pcall(function() '+operation+' end);if not ok then if existed then openspace.setPropertyValueSingle("Scene.'+node+'.Translation.Position",old) elseif openspace.hasSceneGraphNode('+quote(node)+') then openspace.removeSceneGraphNode('+quote(node)+') end;error(err) end;return {ready=true}'
        if self.lab._lua(code,True).get('ready') is not True:raise RuntimeError('Sonda do mapa não confirmada no motor.')
        result={'schema':1,'row':row,'column':column,'sample':copy.deepcopy(sample),
                'frame':data['frame'],'epoch':copy.deepcopy(data['epoch']),'model':data['model'],'degree':data['degree'],
                'layer_id':render['id'],'native_node':node,'position_render_relative_m':position,
                'policy':'The exact stored SI sample that colored this glyph; masked cells unavailable, no new epoch query.'}
        with self.lab.lock:
            self.preview['map_probe']=result
            if node not in self.preview['render']['nodes']:self.preview['render']['nodes'].append(node)
        return copy.deepcopy(result)
