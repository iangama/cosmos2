"""I mode-aware framing and observed-trajectory contrast, with core bytes intact."""
from pathlib import Path
import ast
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'output/c212-em-framing-product';H=ROOT/'output/c212-em-cloud-editor-product'
dest=ROOT/'evidence/em-framing-workspace-prepared.json';assert not dest.exists()
outputs={}
def change(s,old,new):
    assert s.count(old)==1,old
    return s.replace(old,new)
source=(I/'app/em_native.py').read_text()
source=change(source,'from copy import deepcopy','from copy import deepcopy\nfrom itertools import product')
source=change(source,'    def frame(self,state,selected=False):','    def frame(self,state,selected=False,include_layers=False):')
source=change(source,"            radius=max([state['editor']['visual']['map_radius_m'],*[math.dist(center,r['position_m']) for r in rows],1.])", """            points=[r['position_m'] for r in rows]
            if type(include_layers) is not bool:raise ValueError('Explicit framing scope required')
            if include_layers:
                for layer in (self.map,self.lines):
                    for mesh in (layer or {}).get('meshes',[]):
                        if not state['editor']['visual'][mesh['quantity']+'_visible']:continue
                        box=mesh['bounds_model_m']
                        points.extend(product(*zip(box['minimum_m'],box['maximum_m'])))
                p=self.potential.status()
                if p['settings']['visible'] and p['render'] and p['render']['meshes']:
                    g=p['render']['grid'];points.extend(product((g['x_m'][0],g['x_m'][-1]),(g['y_m'][0],g['y_m'][-1]),(g['z_m'],)))
                if points and not selected:center=[min(p[k] for p in points)/2+max(p[k] for p in points)/2 for k in range(3)]
            radius=max([state['editor']['visual']['map_radius_m'],*[math.dist(center,p) for p in points],1.])""")
source=change(source,"distance=4.*radius*DISPLAY_SCALE","distance=(6. if include_layers else 4.)*radius*DISPLAY_SCALE")
source=change(source,"return {'center_model_m':center,'navigation':nav,'graphic_render_m_per_model_m':DISPLAY_SCALE}","return {'center_model_m':center,'radius_model_m':radius,'framing_scope':'visible_layers' if include_layers else 'matter','navigation':nav,'graphic_render_m_per_model_m':DISPLAY_SCALE}")
source=change(source,"'float32_vertex_component_error_model_m':error,'graphic_length_model_m':length,'local_unit_model_m':radius}","'float32_vertex_component_error_model_m':error,'graphic_length_model_m':length,'local_unit_model_m':radius,\n                               'bounds_model_m':{'minimum_m':[min(p[k] for path in paths for p in path) for k in range(3)],'maximum_m':[max(p[k] for path in paths for p in path) for k in range(3)]}}")
source=change(source,"'float32_vertex_component_error_model_m':error,'local_unit_model_m':radius}","'float32_vertex_component_error_model_m':error,'local_unit_model_m':radius,\n                               'bounds_model_m':{'minimum_m':[min(p[k] for _,c in curves for p in c['points_m']) for k in range(3)],'maximum_m':[max(p[k] for _,c in curves for p in c['points_m']) for k in range(3)]}}")
source=change(source,"for quantity,color in (('electric',[1.,.65,.25]),('magnetic',[.35,.55,1.])):","for quantity,color in (('electric',[.72,.49,.22]),('magnetic',[.29,.43,.72])):")
source=change(source,"'LineWidth':1.5,'Enabled':state['editor']['visual'][quantity+'_visible']","'LineWidth':1.,'Enabled':state['editor']['visual'][quantity+'_visible']")
ast.parse(source);outputs[I/'app/em_native.py']=source
source=(I/'app/em_laboratory.py').read_text();source=change(source,'    def frame(self,selected=False):','    def frame(self,selected=False,include_layers=False):')
source=change(source,'return self.native.frame(self.latest,selected)','return self.native.frame(self.latest,selected,include_layers)');ast.parse(source);outputs[I/'app/em_laboratory.py']=source
source=(I/'app/server.py').read_text();source=change(source,"EM.frame(request.get('selected',False))","EM.frame(request.get('selected',False),request.get('include_layers',False))");ast.parse(source);outputs[I/'app/server.py']=source
source=(I/'app/ui/em/app.js').read_text()
old="  const project=p=>{const x=Math.cos(azimuth)*p[0]-Math.sin(azimuth)*p[1],y=Math.sin(azimuth)*p[0]+Math.cos(azimuth)*p[1];return [w/2+scale*x,h/2-scale*(Math.cos(elevation)*p[2]-Math.sin(elevation)*y)];};"
source=change(source,old,"  const project=window.makeCanvasProjection?window.makeCanvasProjection(w,h):p=>[w/2+scale*p[0],h/2-scale*p[1]];")
source=change(source,"  for(let i=1;i<trail.length;i++)line(trail[i-1].p,trail[i].p,'#78ddd2',2);",'')
source=change(source,"curve.quantity==='electric'?'#ffb75a':'#7196ff',1.3","curve.quantity==='electric'?'#b89054':'#4768ae',1")
old="  sources.forEach((p,index)=>{const q=project(p),sid=ex.mode==='test_particle'?ex.model.sources[index].id:ex.system.ids[index];ctx.fillStyle='#ffd184';ctx.beginPath();ctx.arc(...q,7,0,2*Math.PI);ctx.fill();if(sid===state.editor.visual.selected_id){ctx.strokeStyle='#ffffff';ctx.beginPath();ctx.arc(...q,11,0,2*Math.PI);ctx.stroke();}});\n  for(const p of positions()){const q=project(p);ctx.fillStyle='#78ddd2';ctx.beginPath();ctx.arc(...q,5,0,2*Math.PI);ctx.fill();}"
assert old in source;source=source.replace(old,'')
key="arrows.push({x:a[0],y:a[1],sample});}}"
source=change(source,key,key+"\n  for(const [color,width] of [['#07121e',6],['#a5fff0',3]])for(let i=1;i<trail.length;i++)line(trail[i-1].p,trail[i].p,color,width);\n"+old)
outputs[I/'app/ui/em/app.js']=source
source=(I/'app/ui/em.html').read_text()
source=change(source,'<button id="native-frame">Restaurar enquadramento</button>','<button id="native-frame">Enquadrar matéria</button><button id="frame-layers">Enquadrar camadas</button><button id="orient-cut">Inclinar para o corte</button><label class="canvas-only canvas-zoom-label">Escala visual<select id="canvas-zoom" aria-label="Ampliação do mapa"><option value="1">Ajustada</option><option value="1.5">150%</option><option value="2">200%</option><option value="4">400%</option></select></label>')
source=change(source,'<p id="potential-legend"></p>','<p id="potential-legend"></p><p id="trajectory-state"></p>')
source=change(source,'<script src="em/particle.js"></script>','<script src="em/particle.js"></script><script src="em/frame.js"></script>')
outputs[I/'app/ui/em.html']=source
source=(I/'app/ui/em/style.css').read_text();source+='\n.canvas-zoom-label{display:flex;align-items:center;gap:6px;margin:0;font-size:13px}.canvas-zoom-label select{width:auto;margin:0;padding:6px;font-size:13px}.native-view .canvas-only{display:none}#trajectory-state{font-size:12px;color:#a5fff0;margin:5px 0 0}\n';outputs[I/'app/ui/em/style.css']=source
outputs[I/'app/ui/em/frame.js']=(ROOT/'scripts/em-framing-ui/frame.js').read_text()
source=(I/'app/ui/index.html').read_text();outputs[I/'app/ui/index.html']=change(source,'CANDIDATA · FONTES DA NUVEM','CANDIDATA · ENQUADRAMENTO EM')
for p,s in outputs.items():p.write_text(s)
for folder in ('em','em-cloud'):
    for p in (H/folder).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:assert p.read_bytes()==(I/folder/p.relative_to(H/folder)).read_bytes()
(I/'LEIA-CANDIDATA.md').write_text('# C2-12 — candidata I\n\nBase H incompleta, sem aceite herdado. Núcleos e workers byteiguais H/G/F.\nGeometria de exclusões0.1.1 mantém distâncias/triângulos/SI; limite2s preservado.\nEnquadramento explícito matéria/camadas na vista atual, ampliação e inclinação do mapa, trajetória observada destacada.\nPreparação exige CEF/reinício/legado/provas de geometria e perfis próprios. Não é aceiteC2-12 ou promoção.\n')
report={'status':'I_mode_aware_framing_and_observed_trajectory_prepared_awaiting_execution','scientific_and_worker_sources_byte_identical_to_H':True,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs},
        'scope':'Graphics/UI and parent framing only. Source positions, physics, sampled values, contour segments and original sampling/frame/resource limits preserved; own execution and profiles required.'}
dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'files':len(outputs)}),flush=True)
