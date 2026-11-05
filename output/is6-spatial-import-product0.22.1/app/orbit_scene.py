"""Float64 conic receipts and isolated float32 polyline adapters for OpenSpace."""
from pathlib import Path
import json,math,uuid
import numpy as np
from body_attributes import rotation_euler
ROOT=Path(__file__).resolve().parents[1]

def prepare(result,initial):
    token=uuid.uuid4().hex;folder=ROOT/'output/orbit-previews'/token;folder.mkdir(parents=True)
    matrix=np.array(initial['j2000_to_render_frame'] if initial else np.eye(3));rotation=rotation_euler([1,0,0,0],matrix.tolist())
    script='';nodes=[];receipts=[];all_positions=[]
    for name,color in [('before',[.25,.75,1.]),('after',[1.,.65,.2])]:
        diagnostic=result.get(name)
        if diagnostic is None:continue
        segments=diagnostic['preview']['segments_model_units'];origin=np.array(diagnostic['preview']['primary_position_model_units'])
        if not segments:continue
        speck=['# Derived frozen conic; float32 display only, nominal units scaled by1e9m.'];names=[];maxerror=0.;radius=0.
        for i,segment in enumerate(segments):
            values=np.array(segment)-origin;quantized=values.astype(np.float32).astype(float);maxerror=max(maxerror,float(np.max(abs(quantized-values)))*1e9);radius=max(radius,float(np.max(np.linalg.norm(values,axis=1)))*1e9)
            speck+=['mesh -c 1 {','id segment'+str(i),str(len(segment)),*[' '.join(format(v,'.17g') for v in row) for row in values],'}']
            names.append('segment'+str(i)+' '+name+str(i));all_positions.extend((np.array(segment)@matrix.T*1e9).tolist())
        file=folder/(name+'.speck');file.write_text('\n'.join(speck)+'\n',encoding='utf-8');namefile=folder/(name+'.names');namefile.write_text('\n'.join(names)+'\n',encoding='utf-8')
        node='LabOrbit_'+name+'_'+token;nodes.append(node);position=matrix@origin*1e9
        literal=lambda value:json.dumps(value,ensure_ascii=False)
        vec=lambda value:'{'+','.join(format(v,'.17g') for v in value)+'}'
        script+='openspace.addSceneGraphNode({Identifier=%s,Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position=%s},Rotation={Type="StaticRotation",Rotation=%s},Scale={Type="StaticScale",Scale=1e9}},Renderable={Type="RenderableConstellationLines",File=%s,NamesFile=%s,Unit="m",Colors={%s},LineWidth=2},GUI={Name=%s,Focusable=false}});'%(literal(node),vec(position),vec(rotation),literal(file.as_posix()),literal(namefile.as_posix()),vec(color),literal('Conica '+name))
        receipts.append({'branch':name,'node':node,'file':file.as_posix(),'names_file':namefile.as_posix(),'float32_vertex_max_component_error_m':maxerror,'conservative_display_position_error_bound_m':3*maxerror+2e-6*radius+.1,'scientific_samples_are_float64':True})
    if all_positions:
        positions=np.array(all_positions);center=(positions.min(axis=0)+positions.max(axis=0))/2;distance=max(result.get('minimum_view_distance_m',1e9),2.5*float(np.max(np.linalg.norm(positions-center,axis=1))))
    else:center=np.zeros(3);distance=result.get('minimum_view_distance_m',1e9)
    rendered={'id':token,'nodes':nodes,'curves':receipts,'frame_position_render_m':center.tolist(),'view_distance_m':distance,
              'colors':{'before':'cyan','after':'orange'},'scope':'frozen pair conics; float32 graphics, scientific samples retained in float64'}
    receipt={**result,'render':rendered};(folder/'receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return script,rendered
