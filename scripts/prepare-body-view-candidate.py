"""Integrate validated view persistence in a new, isolated candidate0.6."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is3-body-lines-product'
DEST=ROOT/'output/is3-body-view-product'
APP=DEST/'app'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def replace(name,before,after):
    path=APP/name;text=path.read_text(encoding='utf-8')
    assert text.count(before)==1,(name,before,text.count(before))
    path.write_text(text.replace(before,after),encoding='utf-8')


def main():
    receipt=ROOT/'evidence/is3-body-view-candidate-prepared-20261024.json'
    if DEST.exists() or receipt.exists():raise FileExistsError('Preserve earlier candidate.')
    for name in ['is3-view-check-20261024a.json','is3-lines-profile-audit-20261024b.json']:
        assert json.loads((ROOT/'evidence'/name).read_text())['accepted']
    sources=[p for p in (BASE/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    checkpoints={p.relative_to(BASE).as_posix():sha(p) for p in (BASE/'gravity-sessions').rglob('*') if p.is_file()}
    owner=sha(ROOT/'user/sessions/latest.json')
    DEST.mkdir()
    with zipfile.ZipFile(DEST/'base-lines-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in sources:archive.write(p,p.relative_to(ROOT).as_posix())
    shutil.copytree(BASE/'app',APP,ignore=shutil.ignore_patterns('__pycache__'))
    (DEST/'gravity-sessions').mkdir()
    shutil.copy2(ROOT/'output/is3-body-view-staging/body_field_view.py',APP/'body_field_view.py')
    replace('body_registry.py',"'version':'0.5.0'","'version':'0.6.0'")
    replace('body_registry.py',"'body_field_layer.py','body_field_lines.py'","'body_field_layer.py','body_field_lines.py','body_field_view.py'")
    replace('body_registry.py','output/is3-body-lines-product/app/jrm33-coefficients.json','output/is3-body-view-product/app/jrm33-coefficients.json')
    replace('session.py','        self._branch_catalog=None','        self.body_field_view=None\n        self._branch_catalog=None')
    replace('session.py',"                'branches':self._branch_summary(),","                'branches':self._branch_summary(),\n                'body_field_view':copy.deepcopy(self.body_field_view) if self.body_field_view and self.body_field_view['system_id']==self.system_id else None,")
    replace('session.py','    def save(self, directory=None):','    def save(self, directory=None, renderer_view=None):')
    replace('session.py','        destination.mkdir(parents=True, exist_ok=True)',
        """        import body_field_view
        validated_view=body_field_view.validate(renderer_view,system_id=self.system_id,fixture_sha256=self.fixture_sha256,
            bodies=self.registry,time=self.sim.t,revision=self.revision,initial=self.atlas_initial)
        destination.mkdir(parents=True, exist_ok=True)""")
    replace('session.py',"        manifest['physical_scale']=PHYSICAL_SCALE","        manifest['body_field_view']=validated_view\n        manifest['physical_scale']=PHYSICAL_SCALE")
    replace('session.py',"        temporary.replace(destination / 'latest.json')","        temporary.replace(destination / 'latest.json')\n        self.body_field_view=validated_view")
    replace('session.py','        self.sim,self.initial_energy=replacement,baseline;self.registry,self.issued_ids=registry,copy.deepcopy(issued)',
        """        import body_field_view
        restored_body_view=body_field_view.validate(manifest.get('body_field_view'),system_id=system,fixture_sha256=source_hash,
            bodies=registry,time=replacement.t,revision=revision,initial=imported)
        self.sim,self.initial_energy=replacement,baseline;self.registry,self.issued_ids=registry,copy.deepcopy(issued)
        self.body_field_view=restored_body_view""")
    replace('worker.py','                        session.save()','                        session.save(renderer_view=command.get("renderer_view"))')
    replace('branch_store.py','            session.save(temporary)','            session.save(temporary,renderer_view=request.get("renderer_view"))')
    replace('body_field_layer.py',"return self.preview['reading']['body_id'] if self.preview else None",
        "return self.preview['reading']['body_id'] if self.preview and self.preview.get('visible',True) else None")
    replace('body_field_layer.py',"def show(self,reading,representation='vector'):","def show(self,reading,representation='vector',restored=False):")
    replace('body_field_layer.py',"['system_id','edit_token','revision','time']):","(['system_id'] if restored else ['system_id','edit_token','revision','time'])):")
    replace('body_field_layer.py',"        public['representation']=representation","        public['visible']=True;public['restored_from_checkpoint']=restored\n        public['representation']=representation")
    replace('body_field_layer.py',"'persistence':'Current renderer session only; restored checkpoints clear it. CEF reload reattaches the active sample.'",
        "'persistence':'Configuration, visibility and frozen SI reading saved atomically with checkpoint/branch. Native node IDs are rebuilt on restore.'")
    with (APP/'body_field_layer.py').open('a',encoding='utf-8') as f:
        f.write('''

    def set_visible(self,visible):
        if type(visible) is not bool or self.preview is None:raise ValueError('Visibilidade da camada magnética inválida.')
        r=self.preview['render'];body=next(b for b in self.lab.latest['bodies'] if b['id']==self.preview['reading']['body_id'])
        nodes=[m['node'] for m in r['meshes']]+[r['label_node']]
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
''')
    replace('laboratory.py',"        self.body_field_layer=BodyFieldLayer(self)","        self.body_field_layer=BodyFieldLayer(self)\n        self.body_field_restore_status=None")
    replace('laboratory.py',"                    'body_field_preview':self.body_field_layer.public,","                    'body_field_preview':self.body_field_layer.public,\n                    'body_field_restore_status':self.body_field_restore_status,")
    replace('laboratory.py',"        if name in ('show_body_field','clear_body_field','view_body_field'):",
        """        if name in ('set_body_field_visible','export_body_field'):
            if self.mode!='experiment':raise ValueError('Abra a cópia solar primeiro.')
            key='visible' if name=='set_body_field_visible' else 'configuration'
            self.body_field_layer.expect({k:v for k,v in action.items() if k!=key})
            if set(action)!={'command','layer_id',key}:raise ValueError('Pedido visual magnético incompatível.')
            result=self.body_field_layer.set_visible(action['visible']) if name=='set_body_field_visible' else self.body_field_layer.export(action['configuration'])
            return {'type':'ack','command':name,'result':result}
        if name in ('save','create_branch'):
            if self.mode!='experiment':raise ValueError('Abra a cópia solar primeiro.')
            configuration=action.get('body_field_configuration')
            action={k:v for k,v in action.items() if k!='body_field_configuration'}
            action['renderer_view']=self.body_field_layer.checkpoint(configuration)
        if name in ('show_body_field','clear_body_field','view_body_field'):""")
    # Each successful restore creates a fresh scene, then restores visual data.
    replace('laboratory.py',"                self._render()\n            return ack\n        if name in ('configure_orbital_instruments'",
        "                self._render()\n                self._restore_body_field_view()\n            return ack\n        if name in ('configure_orbital_instruments'")
    replace('laboratory.py',"        self.rendered_sequence = None\n        return ack\n\n    def _render(self):",
        """        self.rendered_sequence = None
        if name=='load':self._restore_body_field_view()
        return ack

    def _restore_body_field_view(self):
        try:
            self.body_field_layer.restore(self.latest.get('body_field_view'))
            self.body_field_restore_status={'status':'restored' if self.latest.get('body_field_view') else 'no_saved_view'}
        except Exception as error:
            self.body_field_restore_status={'status':'unavailable','reason':str(error),'physics_checkpoint_loaded':True}

    def _render(self):""")
    replace('ui/index.html','<button id="body-field-clear">Ocultar camada</button>','<button id="body-field-clear">Limpar camada</button>')
    replace('ui/index.html','<p id="body-field-status" class="field-help" role="status">',
        '<label class="compact-check"><input id="body-field-visible" type="checkbox" checked> Exibir camada magnética</label><button id="body-field-export" class="wide">Exportar leitura e geometria</button><p id="body-field-status" class="field-help" role="status">')
    replace('ui/body-field-vector.js',"function updateBodyFieldVector(p,body) {",
        """let restoredBodyFieldToken=null;
window.bodyFieldConfiguration=()=>({selected_body_id:$('solar-body').value,representation:$('body-field-representation').value,
  earth:earthCoordinates(),jupiter:jupiterCoordinates()});
function restoreBodyFieldConfiguration(p){
  if(!p.body_field_view||restoredBodyFieldToken===p.edit_token)return;
  restoredBodyFieldToken=p.edit_token;
  const c=p.body_field_view.configuration;
  $('solar-body').value=c.selected_body_id;$('body-field-representation').value=c.representation;
  ['earth-field-latitude','earth-field-longitude','earth-field-altitude'].forEach((id,i)=>$(id).value=c.earth[i]/(i===2?1000:1));
  ['jupiter-field-radius','jupiter-field-latitude','jupiter-field-longitude','jupiter-field-degree'].forEach((id,i)=>$(id).value=c.jupiter[i]/(i===0?71492000:1));
}
function updateBodyFieldVector(p,body) {
  restoreBodyFieldConfiguration(p);
  body=p.bodies.find(b=>b.id===$('solar-body').value);""")
    replace('ui/body-field-vector.js',"  const layer=appState?.body_field_preview;\n  $('body-field-clear').disabled=pending||!layer;",
        """  const layer=appState?.body_field_preview;
  $('body-field-visible').disabled=pending||!layer;$('body-field-visible').checked=layer?.visible??true;
  $('body-field-export').disabled=pending||!layer;
  $('body-field-clear').disabled=pending||!layer;""")
    replace('ui/body-field-vector.js',"  $('body-field-status').textContent=`${name}\\n`+lineNote+",
        "  $('body-field-status').textContent=`${name}\\n`+(layer.visible?'Camada visível.\\n':'Camada oculta; leitura preservada.\\n')+(layer.restored_from_checkpoint?'Amostra original restaurada do checkpoint.\\n':'')+lineNote+")
    replace('ui/body-field-vector.js',"restaurar limpa a camada.","salvar/restaurar preserva a amostra e sua visibilidade.")
    with (APP/'ui/body-field-vector.js').open('a',encoding='utf-8') as f:
        f.write('''
$('body-field-visible').onchange=async()=>{
  const layer=appState?.body_field_preview;if(pending||!layer)return;
  await command({command:'set_body_field_visible',layer_id:layer.render.id,visible:$('body-field-visible').checked},'Visibilidade alterada; leitura e evolução preservadas.');
};
$('body-field-export').onclick=async()=>{
  const layer=appState?.body_field_preview;if(pending||!layer)return;
  const result=await command({command:'export_body_field',layer_id:layer.render.id,configuration:bodyFieldConfiguration()},'Leitura magnética exportada.');
  if(result?.ack?.result?.export_file)$('notice').textContent='Exportado: '+result.ack.result.export_file;
};
''')
    replace('ui/app.js',"  if (pending) return;\n  pending=true;", "  if (pending) return;\n  if(['save','create_branch'].includes(request.command)&&window.bodyFieldConfiguration)request={...request,body_field_configuration:bodyFieldConfiguration()};\n  pending=true;")
    launcher=(ROOT/'scripts/start-is3-body-lines-candidate.ps1').read_text()
    launcher=launcher.replace('is3-body-lines-product','is3-body-view-product').replace('bodyLinesCandidate = $true;','bodyLinesCandidate = $true; bodyViewCandidate = $true;')
    launcher=launcher.replace('explicit-unapproved-IS3-frozen-magnetic-lines-candidate','explicit-unapproved-IS3-persistent-magnetic-view-candidate')
    (ROOT/'scripts/start-is3-body-view-candidate.ps1').write_text(launcher)
    assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
    assert all(sha(BASE/name)==digest for name,digest in checkpoints.items())
    assert sha(ROOT/'user/sessions/latest.json')==owner
    receipt.write_text(json.dumps({'schema':1,'prepared':True,'base_source_sha256':hashes,
        'base_checkpoint_sha256':checkpoints,'owner_pointer_sha256':owner,
        'scope':'Isolated0.6 candidate; view metadata stage passed, worker/atomic checkpoints/native restart/performance pending.'},indent=2)+'\n')
    print(json.dumps({'prepared':True,'base_preserved':True,'candidate':DEST.relative_to(ROOT).as_posix()}))


if __name__=='__main__':main()
