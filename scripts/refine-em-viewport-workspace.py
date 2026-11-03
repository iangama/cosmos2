"""J graphic-only viewport fit and compact, accessible potential legend."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
J = ROOT / 'output/c212-em-viewport-product'
DEST = ROOT / 'evidence/em-viewport-workspace-prepared.json'
assert not DEST.exists()
outputs = {}


def change(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


source = (J / 'app/em_native.py').read_text()
source = change(source, 'from itertools import product', 'from itertools import product\nfrom em_viewport import fit as fit_viewport, validate_viewport, projection_from_config')
source = change(source, 'def frame(self,state,selected=False,include_layers=False):', 'def frame(self,state,selected=False,include_layers=False,viewport=None):')
source = change(source, "            rows=objects(state);sid=state['editor']['visual']['selected_id'];center=[0.,0.,0.]", "            if type(selected) is not bool or type(include_layers) is not bool:raise ValueError('Explicit framing flags required')\n            if viewport is not None:viewport=validate_viewport(viewport)\n            rows=objects(state);sid=state['editor']['visual']['selected_id'];center=[0.,0.,0.]")
source = change(source, "            radius=max([state['editor']['visual']['map_radius_m'],*[math.dist(center,p) for p in points],1.])", "            if viewport is not None and points and not selected:center=[min(p[k] for p in points)/2+max(p[k] for p in points)/2 for k in range(3)]\n            radius=max([state['editor']['visual']['map_radius_m'],*[math.dist(center,p) for p in points],1.])")
source = change(source, "            self._call('openspace.setPropertyValueSingle(\"Scene.C2EMCamera.Translation.Position\",'+lua([v*DISPLAY_SCALE for v in center])+');openspace.navigation.setNavigationState('+lua(nav)+');return {queued=true}')", """            fit=None
            if viewport is not None:
                # Graphical marker extents keep matter framing nondegenerate.
                marker_points=[tuple(v+offset[k] for k,v in enumerate(row['position_m'])) for row in rows for offset in product((-.065,.065),repeat=3)]
                fit=fit_viewport(points+marker_points,center,az,el,viewport,projection_from_config(PROJECT,viewport['window_px']))
                nav.update(Position=[v*DISPLAY_SCALE for v in fit['position_model_m']],Yaw=fit['yaw_rad'],Pitch=fit['pitch_rad'])
            self._call('openspace.setPropertyValueSingle("Scene.C2EMCamera.Translation.Position",'+lua([v*DISPLAY_SCALE for v in center])+');openspace.navigation.setNavigationState('+lua(nav)+');return {queued=true}')""")
source = change(source, "'graphic_render_m_per_model_m':DISPLAY_SCALE}\n\n    def _confirm_camera", "'graphic_render_m_per_model_m':DISPLAY_SCALE,'viewport_fit':fit}\n\n    def _confirm_camera")
ast.parse(source)
outputs[J / 'app/em_native.py'] = source
source = (J / 'app/em_laboratory.py').read_text()
source = change(source, 'def frame(self,selected=False,include_layers=False):', 'def frame(self,selected=False,include_layers=False,viewport=None):')
source = change(source, 'return self.native.frame(self.latest,selected,include_layers)', 'return self.native.frame(self.latest,selected,include_layers,viewport)')
ast.parse(source)
outputs[J / 'app/em_laboratory.py'] = source
source = (J / 'app/server.py').read_text()
source = change(source, "EM.frame(request.get('selected',False),request.get('include_layers',False))", "EM.frame(request.get('selected',False),request.get('include_layers',False),request.get('viewport'))")
ast.parse(source)
outputs[J / 'app/server.py'] = source
source = (J / 'app/ui/em/frame.js').read_text()
source = change(source, 'async function frameCurrentEMView(layers=false){', """function availableNativeViewport(){
  const z=Number(getComputedStyle(document.body).zoom)||1,r=canvas.getBoundingClientRect();
  return {window_px:[innerWidth,innerHeight],rect_px:[r.left*z,r.top*z,r.width*z,r.height*z]};
}
async function frameCurrentEMView(layers=false){""")
source = change(source, "if(nativeMode){await nativeRequest('frame',{include_layers:layers});return;}", "if(nativeMode){await new Promise(requestAnimationFrame);await nativeRequest('frame',{include_layers:layers,viewport:availableNativeViewport()});return;}")
source += "\n$('native-focus').onclick=()=>run(()=>nativeRequest('frame',{selected:true,viewport:availableNativeViewport()}));\n"
outputs[J / 'app/ui/em/frame.js'] = source
source = (J / 'app/ui/em.html').read_text()
source = change(source, '    <p>Mesmo raio e altura z do mapa.', '    <details id="potential-details"><summary>Legenda completa do corte</summary><p id="potential-details-text"></p></details>\n    <p>Mesmo raio e altura z do mapa.')
outputs[J / 'app/ui/em.html'] = source
source = (J / 'app/ui/em/potential.js').read_text()
source = change(source, "  $('potential-legend').textContent=r?", "  $('potential-details-text').textContent=r?")
source = change(source, "};\n$('potential-auto')", """  const stale=r&&['system_id','edit_token','revision','time_s'].some(k=>r.metadata[k]!==state[k]);
  $('potential-legend').textContent=r?(settings.visible?'φ visível':'φ oculto')+' · z '+number(r.grid.z_m)+' m · t '+number(r.metadata.time_s)+' s'+(stale?' · CONGELADO':'')+' · '+(r.sample_range_V[0]===r.sample_range_V[1]?'constante '+number(r.sample_range_V[0])+' V':r.levels_V.length+' níveis em V · azul − / claro 0 / dourado +')+' · Detalhes em Potencial elétrico.':'';
};
$('potential-auto')""")
outputs[J / 'app/ui/em/potential.js'] = source
source = (J / 'app/ui/em/style.css').read_text()
source += "\n/* Keep zoomed controls in the document; the scene receives all remaining height. */\nhtml{height:100%;overflow:hidden}body{min-height:0}article{overflow:hidden}.heading{padding:7px 12px}.heading .eyebrow{margin-bottom:1px}.scene-footer{padding:7px 12px;flex-shrink:0}#view{min-height:0}#potential-details-text{overflow-wrap:anywhere;white-space:pre-line}#trajectory-state{line-height:1.35}.native-scale,#potential-legend{line-height:1.35}\n"
outputs[J / 'app/ui/em/style.css'] = source
source = (J / 'app/ui/index.html').read_text()
outputs[J / 'app/ui/index.html'] = change(source, 'CANDIDATA · ENQUADRAMENTO EM', 'CANDIDATA · ÁREA ÚTIL EM')
for path, source in outputs.items():
    path.write_text(source)
for folder in ('em', 'em-cloud'):
    base = ROOT / 'output/c212-em-framing-product' / folder
    for path in base.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            assert path.read_bytes() == (J / folder / path.relative_to(base)).read_bytes()
report = {'status': 'J_actual_viewport_fit_and_compact_scene_legend_prepared_awaiting_execution',
          'scientific_workers_and_helpers_byte_equal_I': True,
          'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [*outputs, J / 'app/em_viewport.py']},
          'scope': 'Camera/UI only; same SI positions, fields, trajectory observations,limits and storage schemas. Own geometry/CEF/visual/restart/native profiles required.'}
DEST.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'files': len(report['source_sha256'])}), flush=True)
