"""Create an isolated native-line candidate after its scientific staging passes."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'output/is3-body-vector-product'
DEST = ROOT/'output/is3-body-lines-product'
APP = DEST/'app'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def replace(name, before, after):
    path = APP/name
    text = path.read_text(encoding='utf-8')
    assert text.count(before) == 1, (name, before)
    path.write_text(text.replace(before, after), encoding='utf-8')


def main():
    receipt = ROOT/'evidence/is3-body-lines-candidate-prepared-20261024.json'
    if DEST.exists() or receipt.exists():
        raise FileExistsError('Preserve earlier candidate.')
    for name in ['is3-lines-check-20261024a.json', 'is3-vector-profile-audit-20261024b.json',
                 'is3-body-vector-controls-visual-review-20261024.json']:
        assert json.loads((ROOT/'evidence'/name).read_text(encoding='utf-8'))['accepted']
    sources = [p for p in (BASE/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}
    owner = sha(ROOT/'user/sessions/latest.json')
    checkpoint = {p.relative_to(BASE).as_posix(): sha(p) for p in (BASE/'gravity-sessions').rglob('*') if p.is_file()}
    DEST.mkdir()
    with zipfile.ZipFile(DEST/'base-vector-sources.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sources:
            archive.write(path, path.relative_to(ROOT).as_posix())
    shutil.copytree(BASE/'app', APP, ignore=shutil.ignore_patterns('__pycache__'))
    (DEST/'gravity-sessions').mkdir()
    shutil.copy2(ROOT/'output/is3-body-lines-staging/body_field_lines.py', APP/'body_field_lines.py')
    replace('body_registry.py', "'version':'0.4.0'", "'version':'0.5.0'")
    replace('body_registry.py', "'body_field_geometry.py','body_field_scene.py','body_field_layer.py'",
            "'body_field_geometry.py','body_field_scene.py','body_field_layer.py','body_field_lines.py'")
    replace('body_registry.py', 'output/is3-body-vector-product/app/jrm33-coefficients.json',
            'output/is3-body-lines-product/app/jrm33-coefficients.json')
    replace('body_field_scene.py', 'from body_field_geometry import build,product',
            'from body_field_geometry import build,product,arrow\nfrom body_field_lines import bundle,Model')
    replace('body_field_scene.py', 'def prepare(reading):\n    geometry=build(reading);token=uuid.uuid4().hex',
            '''def prepare(reading,representation='vector'):
    if representation not in ('vector','lines'):raise ValueError('Representação magnética não adotada.')
    geometry=build(reading);token=uuid.uuid4().hex
    geometry['representation']=representation
    if representation=='lines':
        geometry['field_lines']=bundle(reading)
        geometry['policy']='Frozen confirmed internal-model field lines; domain and arc stops recorded, no inferred closure, plasma trajectory or force on neutral centers.'
'''.rstrip())
    replace('body_field_scene.py', "    if geometry['arrow']['drawn']:mesh('magnetic_vector'",
            """    if representation=='lines':
        traced=geometry['field_lines'];model=Model(reading)
        mesh('field_lines',[line['points_m'] for line in traced['lines'] if len(line['points_m'])>1],[.3,.83,.95],2)
        directions=[]
        for line in traced['lines']:
            point=line['points_m'][len(line['points_m'])//2]
            direction=arrow(point,model.field(point),.07*scale)
            if direction['drawn']:directions.extend(direction['segments_m'])
        mesh('field_line_directions',directions,[.35,1.,.62],3)
    if geometry['arrow']['drawn']:mesh('magnetic_vector'""")
    replace('body_field_scene.py', "'policy':geometry['policy']}",
            "'policy':geometry['policy'],'representation':representation}")
    replace('body_field_layer.py', 'def show(self,reading):\n        code,result=prepare(reading)',
            "def show(self,reading,representation='vector'):\n        code,result=prepare(reading,representation)")
    replace('body_field_layer.py', "        with self.lab.lock:self.preview=public;self.label_restore=label_restore",
            """        public['representation']=representation
        if representation=='lines':
            traced=g['field_lines']
            public['line_summary']={'curves':len(traced['lines']),'degree':traced['degree'],'domain':traced['domain'],
                'vertices':sum(len(line['points_m']) for line in traced['lines']),
                'ends':[[line[side]['termination'] for side in ['negative','positive']] for line in traced['lines']],
                'SI_vertices_and_fields_receipt':r['receipt'],'observational_uncertainty':None}
        with self.lab.lock:self.preview=public;self.label_restore=label_restore""")
    replace('laboratory.py', "                request={k:v for k,v in action.items() if k!='model'}",
            """                representation=action.get('representation','vector')
                if representation not in ('vector','lines'):raise ValueError('Representação magnética não adotada.')
                request={k:v for k,v in action.items() if k not in ('model','representation')}""")
    replace('laboratory.py', "self.body_field_layer.show(ack['result'])", "self.body_field_layer.show(ack['result'],representation)")
    replace('ui/index.html', '<summary>Vetor magnético na cena</summary>', '<summary>Campo magnético na cena</summary>')
    replace('ui/index.html', '<button id="body-field-show" class="wide">Pausar e mostrar vetor selecionado</button>',
            '<p id="body-field-model-status" class="field-help" role="status"></p><label class="field">Representação<select id="body-field-representation"><option value="vector">Vetor da amostra</option><option value="lines">Linhas 3D do campo interno</option></select></label><button id="body-field-show" class="wide">Pausar e mostrar campo selecionado</button>')
    replace('ui/body-field-vector.js', "  $('body-field-show').disabled=pending||!available;",
            """  $('body-field-show').disabled=pending||!available;
  $('body-field-representation').disabled=pending||!available;
  const reference=body?.reference_id;
  $('body-field-model-status').textContent=reference==='sol:naif:399'?
    'Terra: IGRF14 interno, eixos ITRF93 e época da cena. Linhas restritas à altura WGS84 de 0 a 1000 km; sem campo externo.':
    reference==='sol:naif:599'?'Júpiter: JRM33 interno estático de 2019, Sistema III e época da cena; domínio numérico de 1 a 20 Rj, sem correntes externas.':
    reference==='sol:naif:301'?'Lua: modelo crostal, induzido e externo não adotados. Campo indisponível não significa B = 0.':
    reference==='sol:naif:10'?'Sol: campo solar e plasma não adotados nesta camada. Campo indisponível não significa B = 0.':
    'Nenhum modelo magnético adotado para este corpo.';""")
    replace('ui/body-field-vector.js', "  $('body-field-status').textContent=`${name}\\n`+",
            """  const lineNote=layer.representation==='lines'?
    `Linhas internas 3D: ${layer.line_summary.curves} curvas, ${layer.line_summary.vertices} vértices.\\n`+
    'Traçado interrompido nas bordas ou no limite de arco; não implica linha fechada. Setas verdes indicam +B; seu comprimento é gráfico. Não são trajetórias de partículas.\\n':'';
  $('body-field-status').textContent=`${name}\\n`+lineNote+""")
    replace('ui/body-field-vector.js', "command:'show_body_field',model:earth?'IGRF14':'JRM33',...editGuard(p)",
            "command:'show_body_field',model:earth?'IGRF14':'JRM33',representation:$('body-field-representation').value,...editGuard(p)")
    replace('ui/body-field-vector.js', "'Vetor da amostra confirmado no motor. O comprimento da seta é gráfico.'",
            "'Camada magnética confirmada no motor. Setas têm comprimento gráfico; linhas usam o campo interno.'")
    launcher = (ROOT/'scripts/start-is3-body-vector-candidate.ps1').read_text(encoding='utf-8')
    launcher = launcher.replace('is3-body-vector-product', 'is3-body-lines-product')
    launcher = launcher.replace('bodyVectorCandidate = $true;', 'bodyVectorCandidate = $true; bodyLinesCandidate = $true;')
    launcher = launcher.replace('explicit-unapproved-IS3-frozen-magnetic-vector-candidate', 'explicit-unapproved-IS3-frozen-magnetic-lines-candidate')
    (ROOT/'scripts/start-is3-body-lines-candidate.ps1').write_text(launcher, encoding='utf-8')
    assert all(sha(ROOT/name) == digest for name, digest in hashes.items())
    assert all(sha(BASE/name) == digest for name, digest in checkpoint.items())
    assert sha(ROOT/'user/sessions/latest.json') == owner
    receipt.write_text(json.dumps({'schema': 1, 'prepared': True, 'base_source_sha256': hashes,
        'base_checkpoint_sha256': checkpoint, 'owner_pointer_sha256': owner,
        'scope': 'Isolated line candidate0.5; science staging passed, native lifecycle and profile pending. Vector candidate and checkpoints preserved.'}, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'prepared': True, 'candidate': DEST.relative_to(ROOT).as_posix(), 'base_preserved': True}))


if __name__ == '__main__':
    main()
