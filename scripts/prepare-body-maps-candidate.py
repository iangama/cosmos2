"""Integrate scientifically checked frozen maps in a new candidate after0.6.1 passes."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is3-body-view-topology-product'
DEST=ROOT/'output/is3-body-maps-product'
APP=DEST/'app'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def replace(name,before,after):
    p=APP/name;text=p.read_text(encoding='utf-8')
    assert text.count(before)==1,(name,before,text.count(before))
    p.write_text(text.replace(before,after),encoding='utf-8')


def main():
    receipt=ROOT/'evidence/is3-body-maps-candidate-prepared-20261024.json'
    if DEST.exists() or receipt.exists():raise FileExistsError('Preserve earlier maps candidate.')
    for name in ['is3-body-maps-check-20261024a.json','is3-map-geometry-check-20261024a.json',
                 'is3-view-topology-profile-audit-20261024b.json']:
        assert json.loads((ROOT/'evidence'/name).read_text(encoding='utf-8'))['accepted']
    paths=[p for p in (BASE/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    owner=sha(ROOT/'user/sessions/latest.json')
    checkpoints={p.relative_to(BASE).as_posix():sha(p) for p in (BASE/'gravity-sessions').rglob('*') if p.is_file()}
    DEST.mkdir()
    with zipfile.ZipFile(DEST/'base-0.6.1-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    shutil.copytree(BASE/'app',APP,ignore=shutil.ignore_patterns('__pycache__'))
    (DEST/'gravity-sessions').mkdir()
    for name in ['body_field_maps.py','body_field_map_geometry.py','body_field_map_layer.py']:
        shutil.copy2(ROOT/'output/is3-body-maps-staging'/name,APP/name)
    replace('body_registry.py',"'version':'0.6.1'","'version':'0.7.0'")
    replace('body_registry.py',"'body_field_lines.py','body_field_view.py'",
            "'body_field_lines.py','body_field_view.py','body_field_maps.py','body_field_map_geometry.py','body_field_map_layer.py'")
    replace('body_registry.py','output/is3-body-view-topology-product/app/jrm33-coefficients.json',
            'output/is3-body-maps-product/app/jrm33-coefficients.json')
    replace('body_field_scene.py','from body_field_lines import bundle,Model',
            'from body_field_lines import bundle,Model\nfrom body_field_maps import build as build_maps\nfrom body_field_map_geometry import build as map_geometry,view as map_view')
    replace('body_field_scene.py',"representation not in ('vector','lines')","representation not in ('vector','lines','shell','cut')")
    replace('body_field_scene.py',"    geometry['representation']=representation",
        """    geometry['representation']=representation
    if representation in ('shell','cut'):
        geometry['field_maps']=build_maps(reading)
        geometry['map_display']=map_geometry(geometry['field_maps'],representation)
        geometry['view']=map_view(geometry['field_maps'],geometry['map_display'])
        geometry['policy']='Frozen discrete internal magnetic sample map; eight |B| color bins, graphic sample glyphs, unavailable domain masked, no interpolation into unsampled points or force on neutral centers.'""")
    replace('body_field_scene.py',"    if geometry['arrow']['drawn']:mesh('magnetic_vector'",
        """    if representation in ('shell','cut'):
        for index,item in enumerate(geometry['map_display']['bins']):
            mesh('field_map_bin_'+str(index),item['segments_m'],item['color_rgb'],2)
    if geometry['arrow']['drawn']:mesh('magnetic_vector'""")
    replace('body_field_layer.py','from body_field_scene import prepare','from body_field_scene import prepare\nfrom body_field_map_layer import MapSelection')
    replace('body_field_layer.py','class BodyFieldLayer:','class BodyFieldLayer(MapSelection):')
    replace('body_field_layer.py',"        with self.lab.lock:self.preview=public;self.label_restore=label_restore",
        """        public['map_probe']=None
        if representation in ('shell','cut'):
            display=g['map_display']
            public['map_summary']={k:display[k] for k in ['shape','minimum_sampled_T','maximum_sampled_T','palette_rgb','sample_count','drawn_symbols','glyph_half_length_m','legend']}
        with self.lab.lock:self.preview=public;self.label_restore=label_restore""")
    replace('body_field_layer.py',"        nodes=[m['node'] for m in r['meshes']]+[r['label_node']]",
        "        nodes=[m['node'] for m in r['meshes']]+[r['label_node']]\n        if self.preview.get('map_probe'):nodes.append(self.preview['map_probe']['native_node'])")
    replace('body_field_layer.py',"            if not layer['visible']:self.set_visible(False)",
        "            if layer.get('map_probe'):self.select_map_cell(layer['map_probe']['row'],layer['map_probe']['column'])\n            if not layer['visible']:self.set_visible(False)")
    replace('laboratory.py',"                if representation not in ('vector','lines'):","                if representation not in ('vector','lines','shell','cut'):")
    replace('laboratory.py',"        if name in ('set_body_field_visible','export_body_field'):",
        """        if name=='select_body_field_map_cell':
            if self.mode!='experiment':raise ValueError('Abra a cópia solar primeiro.')
            if set(action)!={'command','layer_id','row','column'}:raise ValueError('Pedido de célula magnética incompatível.')
            self.body_field_layer.expect({k:v for k,v in action.items() if k not in ('row','column')})
            return {'type':'ack','command':name,'result':self.body_field_layer.select_map_cell(action['row'],action['column'])}
        if name in ('set_body_field_visible','export_body_field'):""")
    p=APP/'body_field_view.py';text=p.read_text(encoding='utf-8')
    assert text.count("('vector', 'lines')")==2
    text=text.replace("('vector', 'lines')","('vector', 'lines', 'shell', 'cut')")
    p.write_text(text,encoding='utf-8')
    replace('body_field_view.py',"set(layer) != {'reading', 'representation', 'visible'}",
        "not {'reading', 'representation', 'visible'} <= set(layer) or bool(set(layer)-{'reading','representation','visible','map_probe'})")
    replace('body_field_view.py',"        compare({k: v for k, v in reading.items() if k != 'scientific_generation'}, expected)",
        """        compare({k: v for k, v in reading.items() if k != 'scientific_generation'}, expected)
        cell=layer.get('map_probe')
        if cell is not None:
            if layer['representation'] not in ('shell','cut') or not isinstance(cell,dict) or set(cell)!={'row','column'}:
                raise ValueError('Sonda de mapa arquivada incompatível.')
            from body_field_maps import build as build_maps
            samples=build_maps(reading)[layer['representation']]['samples'];row,column=cell['row'],cell['column']
            if type(row) is not int or type(column) is not int or not 0<=row<len(samples) or not 0<=column<len(samples[row]) or samples[row][column] is None:
                raise ValueError('Célula arquivada ausente ou fora do domínio.')""")
    replace('body_field_view.py',"                 'visible': preview.get('visible', True)}}",
        "                 'visible': preview.get('visible', True),\n                 'map_probe':None if not preview.get('map_probe') else {k:preview['map_probe'][k] for k in ['row','column']}}}")
    replace('ui/index.html','<option value="lines">Linhas 3D do campo interno</option>',
        '<option value="lines">Linhas 3D do campo interno</option><option value="shell">Mapa da casca · |B|</option><option value="cut">Corte meridional · |B|</option>')
    replace('ui/index.html','<p id="body-field-status" class="field-help" role="status">',
        '<div id="body-map-controls" hidden><p id="body-map-legend" class="field-help"></p><div id="body-map-palette" style="display:flex;height:12px;margin-bottom:10px"></div><form id="body-map-probe-form"><div class="vector-fields"><label>Linha da grade<input id="body-map-row" type="number" min="0" step="1" required value="9"></label><label>Coluna da grade<input id="body-map-column" type="number" min="0" step="1" required value="0"></label></div><button id="body-map-sample" class="wide" type="submit">Consultar célula do mapa</button></form><p id="body-map-reading" class="field-help" role="status"></p></div><p id="body-field-status" class="field-help" role="status">')
    replace('ui/index.html','<script src="body-field-vector.js"></script>',
        '<script src="body-field-vector.js"></script><script src="body-field-map.js"></script>')
    replace('ui/body-field-vector.js',"  const layer=appState?.body_field_preview;\n  $('body-field-visible')",
        "  const layer=appState?.body_field_preview;\n  if(window.updateBodyFieldMap)updateBodyFieldMap(layer);\n  $('body-field-visible')")
    (APP/'ui/body-field-map.js').write_text('''"use strict";
let mapProbeIdentity=null;
function updateBodyFieldMap(layer){
  const available=layer&&['shell','cut'].includes(layer.representation),summary=layer?.map_summary;
  $('body-map-controls').hidden=!available;if(!available){mapProbeIdentity=null;return;}
  $('body-map-sample').disabled=pending;$('body-map-row').disabled=pending;$('body-map-column').disabled=pending;
  $('body-map-row').max=summary.shape[0]-1;$('body-map-column').max=summary.shape[1]-1;
  $('body-map-legend').textContent=`Cores: |B interno| de ${(summary.minimum_sampled_T*1e6).toPrecision(5)} a ${(summary.maximum_sampled_T*1e6).toPrecision(5)} µT na grade amostrada. ${summary.drawn_symbols} símbolos, tamanho gráfico. ${summary.shape[0]} linhas × ${summary.shape[1]} colunas, índices começando em zero. Pontos fora do domínio não são desenhados e não significam B = 0.`;
  $('body-map-palette').replaceChildren(...summary.palette_rgb.map(rgb=>{const swatch=document.createElement('span');swatch.style.flex='1';swatch.style.background=`rgb(${rgb.map(v=>Math.round(v*255)).join(',')})`;return swatch;}));
  const probe=layer.map_probe,identity=layer.render.id+'|'+(probe?probe.row+','+probe.column:'none');
  if(identity!==mapProbeIdentity){
    mapProbeIdentity=identity;$('body-map-row').value=probe?probe.row:Math.floor(summary.shape[0]/2);
    $('body-map-column').value=probe?probe.column:0;
  }
  $('body-map-reading').textContent=probe?`Célula ${probe.row}/${probe.column} · ${probe.model}, grau ${probe.degree}\\nÉpoca da amostra: ${probe.epoch.utc}\\nPosição x/y/z em ${probe.frame}: ${probe.sample.position_model_m.map(v=>v.toExponential(6)).join(' / ')} m\\nB x/y/z: ${probe.sample.field_model_T.map(v=>v.toExponential(6)).join(' / ')} T\\n|B| = ${(probe.sample.field_norm_T*1e6).toPrecision(8)} µT. Mesmo dado que determinou a cor; incerteza local não propagada.`:'Escolha uma célula para consultar o mesmo valor SI usado pelo mapa. Células mascaradas ficam indisponíveis.';
}
window.updateBodyFieldMap=updateBodyFieldMap;
$('body-map-probe-form').onsubmit=async event=>{
  event.preventDefault();const layer=appState?.body_field_preview;
  if(pending||!layer||!$('body-map-probe-form').reportValidity())return;
  await command({command:'select_body_field_map_cell',layer_id:layer.render.id,row:Number($('body-map-row').value),column:Number($('body-map-column').value)},'Sonda na célula do mapa; leitura e evolução preservadas.');
};
''',encoding='utf-8')
    launcher=(ROOT/'scripts/start-is3-body-view-topology-candidate.ps1').read_text(encoding='utf-8')
    launcher=launcher.replace('is3-body-view-topology-product','is3-body-maps-product').replace('bodyViewTopologyCandidate = $true;','bodyViewTopologyCandidate = $true; bodyMapsCandidate = $true;')
    launcher=launcher.replace('explicit-unapproved-IS3-persistent-view-topology-candidate','explicit-unapproved-IS3-frozen-magnetic-maps-candidate')
    (ROOT/'scripts/start-is3-body-maps-candidate.ps1').write_text(launcher,encoding='utf-8')
    assert all(sha(ROOT/name)==value for name,value in hashes.items())
    assert all(sha(BASE/name)==value for name,value in checkpoints.items()) and sha(ROOT/'user/sessions/latest.json')==owner
    receipt.write_text(json.dumps({'schema':1,'prepared':True,'accepted':False,'base_source_sha256':hashes,
        'base_checkpoint_sha256':checkpoints,'owner_pointer_sha256':owner,
        'scope':'Isolated0.7 native sampled shell/cut and persisted cell probes; scientific grid/display staging passed, own lifecycle/UI/profile pending.'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'prepared':True,'base_preserved':True}))


if __name__=='__main__':main()
