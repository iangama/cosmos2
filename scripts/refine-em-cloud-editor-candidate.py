"""Prepare H UI/source selection and honest two-file cloud saves; no core edits."""
from pathlib import Path
import ast
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1];H=ROOT/'output/c212-em-cloud-editor-product'
STAGE=ROOT/'scripts/em-cloud-editor-ui'
receipt=ROOT/'evidence/em-cloud-editor-workspace-prepared.json'
assert H.exists() and not receipt.exists()
before=json.loads((ROOT/'evidence/em-cloud-editor-candidate-prepared.json').read_bytes())
for name,digest in before['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
owner=(ROOT/'user/sessions/latest.json').read_bytes()
outputs={}
def change(text,old,new,count=1):
    assert text.count(old)==count,old
    return text.replace(old,new)

source=(H/'app/em_cloud_laboratory.py').read_text()
source=change(source,"'map_radius_m': 3., 'map_cut_z_m': 0.}","'map_radius_m': 3., 'map_cut_z_m': 0., 'selected_source_id': None}")
source=change(source,"        return deepcopy(value)\n\n    def _apply_visual", """        selected=value['selected_source_id']
        if selected is not None and (type(selected) is not str or not 1<=len(selected)<=128):
            raise ValueError('Seleção de fonte inválida.')
        return deepcopy(value)

    def _apply_visual""")
source=change(source,"                self.visual = self._visual({**self.visual, **changes})", """                proposed=self._visual({**self.visual, **changes})
                selected=proposed['selected_source_id']
                if selected is not None and selected not in {s['id'] for s in self._current()['model']['sources']}:
                    raise ValueError('A fonte selecionada não pertence ao modelo confirmado.')
                self.visual=proposed""")
source=change(source,"            response = self._worker(value)\n            with self.sync_lock:", """            response = self._worker(value)
            if name=='save':
                response['persistence']={'state':'partial','scientific_checkpoint_saved':True,'view_preferences_saved':False}
            with self.sync_lock:""")
source=change(source,"                        self.field_map = None\n                    if name == 'load':", """                        self.field_map = None
                    if name=='load_preset':self.visual['selected_source_id']=None
                    if name=='set_model' and self.visual['selected_source_id'] not in {s['id'] for s in self._current()['model']['sources']}:
                        self.visual['selected_source_id']=None
                    if name == 'load':""")
source=change(source,"                        self._restore_preferences(adjunct)\n                    self._sync()", """                        self._restore_preferences(adjunct)
                        response['view_preferences_source_schema']=adjunct.get('_source_schema',adjunct['schema']) if adjunct else None
                    self._sync()""")
source=change(source,"                    if name == 'save':\n                        self._save_aux(value['file'])\n",'')
source=change(source,"            return response\n\n    def _artifact", """                if name=='save':
                    if response.get('display'):
                        response['persistence']['message']=response['display']['message']
                    else:
                        try:
                            response['preferences_artifact']=self._save_aux(value['file'])
                            response['persistence'].update(state='complete',view_preferences_saved=True)
                        except Exception as error:
                            response['persistence']['message']=type(error).__name__+': '+str(error)
            return response

    def _artifact""")
source=change(source,"        body = {'schema': 1, 'checkpoint_sha256':", "        body = {'schema': 2, 'checkpoint_sha256':")
source=change(source,"            temp.unlink(missing_ok=True)\n\n    def _load_aux", """            temp.unlink(missing_ok=True)
        return {'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def _load_aux""")
source=change(source,"type(body['schema']) is not int or body['schema'] != 1):", "type(body['schema']) is not int or body['schema'] not in (1,2)):")
source=change(source,"        self._visual(body['visual'])\n        NativeEM.validate_view", """        body=deepcopy(body)
        original_schema=body['schema']
        if original_schema==1:
            if not isinstance(body['visual'],dict) or set(body['visual'])!=set(DEFAULT_VISUAL)-{'selected_source_id'}:
                raise ValueError('Preferências anteriores têm campos inesperados.')
            body['visual']['selected_source_id']=None
        self._visual(body['visual'])
        NativeEM.validate_view""")
source=change(source,"        count = json.loads((STORAGE/(name+'.json')).read_bytes())['count']", """        checkpoint=json.loads((STORAGE/(name+'.json')).read_bytes())
        count=checkpoint['count']
        selected_source=body['visual']['selected_source_id']
        if selected_source is not None and selected_source not in {s['id'] for s in checkpoint['model']['sources']}:
            raise ValueError('Seleção de fonte salva fora do modelo do checkpoint.')""")
source=change(source,"        return body\n\n    def _restore_preferences", "        body['_source_schema']=original_schema\n        return body\n\n    def _restore_preferences")
ast.parse(source);outputs[H/'app/em_cloud_laboratory.py']=source

source=(H/'app/ui/em/cloud.js').read_text()
source=change(source,"$('status').textContent=v.display?'Estado científico confirmado. Exibição: '+v.display.message:'Estado confirmado.';return v;", """$('status').textContent=v.persistence?.state==='partial'?'Fase salva; vista e preferências incompletas: '+v.persistence.message:v.display?'Estado científico confirmado. Exibição: '+v.display.message:v.view_preferences_source_schema===1?'Fase anterior retomada; nenhuma fonte estava selecionada nesse registro.':v.view_preferences_source_schema===null?'Fase retomada com preferências de vista no padrão.':'Condição confirmada.';return v;""")
source=change(source,"}\n$('load-preset').onclick", "  if(window.renderCloudSources)window.renderCloudSources();if(window.renderCloudWorkspace)window.renderCloudWorkspace();\n}\n$('load-preset').onclick")
source=change(source,"await command('save',{file:'ui-phase'});$('status').textContent='Fase científica, vista, seleção, ritmo e preferências salvos.';", "const saved=await command('save',{file:'ui-phase'});if(saved.persistence?.state==='complete')$('status').textContent='Fase, vista, seleções e preferências salvas.';")
outputs[H/'app/ui/em/cloud.js']=source

source=(H/'app/ui/em/native.js').read_text()
source=change(source,"  document.documentElement.classList.toggle('native-view',nativeMode);", """  document.documentElement.classList.toggle('native-view',nativeMode);
  document.querySelector('.native-scale').textContent=nativeMode?'Cena nativa · 10⁹ m gráficos por metro do modelo · marcadores com raio gráfico. Medições em SI.':'Mapa interativo · projeção 3D de posições em metros · setas com comprimento gráfico uniforme. Arraste para mudar a orientação.';""")
outputs[H/'app/ui/em/native.js']=source
source=(H/'app/ui/em/workspace.js').read_text()
outputs[H/'app/ui/em/workspace.js']=change(source,'cosmos2.em.integration.uiScale','cosmos2.em.cloudEditor.uiScale',2)
source=(H/'app/ui/index.html').read_text()
outputs[H/'app/ui/index.html']=change(source,'CANDIDATA DE INTEGRAÇÃO EM','CANDIDATA · FONTES DA NUVEM')
for name,target in [('em-cloud.html','app/ui/em-cloud.html'),('cloud.css','app/ui/em/cloud.css'),
                    ('cloud-workspace.js','app/ui/em/cloud-workspace.js'),('cloud-sources.js','app/ui/em/cloud-sources.js')]:
    outputs[H/target]=(STAGE/name).read_text()

# Preflight every transformation before writing any candidate source.
for path,contents in outputs.items():path.write_text(contents)
(H/'LEIA-CANDIDATA.md').write_text(
    '# C2-12 — candidata H, editor de fontes da nuvem\n\n'
    'Núcleos e workers byteiguais a G/F; storage próprio e parent/interface novos.\n'
    'Editor de até128fontes usa set_model existente; seleção de fonte emviewaux2,\n'
    'legacy1 explícito sem seleção; fase e preferências com confirmação separada.\n'
    'Layoutnuvem100–150% e legenda de canvas do pequeno preparados.\n'
    'Preparação não é prova de execução, perfil ou aceite de experiência.\n',encoding='utf-8')
for folder in ('em','em-cloud'):
    for base in (ROOT/'output/c212-em-integration-product'/folder).rglob('*'):
        if base.is_file() and '__pycache__' not in base.parts:
            assert base.read_bytes()==(H/base.relative_to(ROOT/'output/c212-em-integration-product')).read_bytes()
assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
report={'status':'H_cloud_source_editor_and_partial_save_prepared_awaiting_tests',
        'scientific_and_worker_sources_byte_identical_to_G':True,'owner_pointer_preserved':True,
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs},
        'scope':'Own UI, guarded visual selection, view schema2/legacy1, truthful phase/preferences save result. No inherited native performance or experience acceptance.'}
receipt.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'changed_files':len(outputs)}),flush=True)
