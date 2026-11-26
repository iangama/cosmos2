"""Build isolated0.26.0 from sealed0.25.1; never open or promote the app."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'output/is6-principal-moons-navigation-product0.25.1'
TARGET = ROOT/'output/is6-dynamics16-product0.26.0'
REGISTRY = ROOT/'output/is6-dynamics16-ui-staging'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def replace(text, old, new, count=1):
    assert text.count(old) == count, (old[:100], text.count(old), count)
    return text.replace(old, new)


def main():
    if TARGET.exists():
        raise FileExistsError('Preserve the prepared candidate; use a new revision.')
    parent = json.loads((BASE/'build-manifest.json').read_text(encoding='utf8'))
    actual = {p.relative_to(BASE/'app').as_posix(): sha(p) for p in (BASE/'app').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    assert actual == parent['files_sha256']
    proof = ROOT/'evidence/is6-dynamics16-audit-20261112b.json'
    assert json.loads(proof.read_text())['accepted']
    prepared = json.loads((REGISTRY/'backend-preparation.json').read_text())
    assert all(sha(REGISTRY/n) == s for n, s in prepared['files_sha256'].items())
    texts = {n: (BASE/'app'/n).read_text(encoding='utf8') for n in
             ['session.py', 'server.py', 'worker.py', 'laboratory.py', 'ui/app.js', 'ui/index.html', 'ui/solar.js']}

    session = texts['session.py']
    session = replace(session, "class Session:\n", "class Session:\n    def scientific_generation(self):\n        import dynamics16_runtime\n        return dynamics16_runtime.generation(editable_generation(self.seed['kind']), self.atlas_initial)\n\n    def dynamics16_reading(self, request):\n        from dynamics16_runtime import reading\n        return reading(self, request)\n\n")
    session = session.replace("editable_generation(self.seed['kind'])", "self.scientific_generation()")
    # Keep the single base-generation call inside the new method nonrecursive.
    session = replace(session, "dynamics16_runtime.generation(self.scientific_generation(), self.atlas_initial)",
                      "dynamics16_runtime.generation(editable_generation(self.seed['kind']), self.atlas_initial)")
    session = replace(session, "        if self.atlas_initial is not None:\n            state['atlas_initial'] = self.atlas_initial",
                      "        import dynamics16_runtime\n        state['dynamics16'] = dynamics16_runtime.metadata(self.atlas_initial, self.sim, self.revision)\n        if self.atlas_initial is not None:\n            state['atlas_initial'] = self.atlas_initial")
    session = replace(session, "        manifest['manifest_sha256'] = digest(manifest)",
                      "        import dynamics16_runtime\n        if dynamics16_runtime.active(self.atlas_initial):\n            manifest['split_inertial_frame'] = dynamics16_runtime.split_frame(self.atlas_initial, self.sim)\n        manifest['manifest_sha256'] = digest(manifest)")
    session = replace(session, "        current=editable_generation(kind)",
                      "        import dynamics16_runtime\n        expected_frame = dynamics16_runtime.split_frame(imported, replacement)\n        if expected_frame is not None:\n            if not __import__('system16_import').typed_equal(manifest.get('split_inertial_frame'), expected_frame):\n                raise ValueError('Origem inercial separada do checkpoint incompatível.')\n        elif 'split_inertial_frame' in manifest:\n            raise ValueError('Origem16 em um formato legado incompatível.')\n        current=dynamics16_runtime.generation(editable_generation(kind), imported)")
    for method in ['set_j2', 'set_tides', 'set_cloud', 'earth_field', 'jupiter_field']:
        import re
        pattern = rf'(    def {method}\(self, ?request\):\n)'
        session, count = re.subn(pattern, r"\1        if self.atlas_initial and self.atlas_initial.get('kind') == 'solar_sixteen_physical_centers':\n            raise ValueError('A cópia16 implementa somente gravidade pontual; use a bancada específica para este modelo.')\n", session)
        assert count == 1, method
    texts['session.py'] = session

    texts['server.py'] = replace(texts['server.py'], "            elif self.path in ('/api/solar/reference', '/api/solar/experiment'):",
        "            elif self.path == '/api/dynamics16/experiment':\n                from dynamics16_runtime import create\n                self.json_response(create(request, LAB, ATLAS))\n            elif self.path in ('/api/solar/reference', '/api/solar/experiment'):")
    # Existing worker ownership, pause and persistence semantics are retained.
    texts['worker.py'] = replace(texts['worker.py'], "('jupiter_field','earth_field','solar_tide','solar_reading'",
                                 "('dynamics16_reading','jupiter_field','earth_field','solar_tide','solar_reading'", 2)
    lab = texts['laboratory.py']
    lab = replace(lab, "        elif initial and len(positions)>1:",
        "        elif initial and initial.get('kind') == 'solar_sixteen_physical_centers':\n            distance = max(3e9, 2.2*max(math.dist(p, center) for p in positions))\n            camera = [0, -distance, distance*.6]\n            for body in state['bodies']:\n                enabled = body.get('reference_id') not in ('sol:naif:301', 'sol:naif:501', 'sol:naif:502', 'sol:naif:503', 'sol:naif:504', 'sol:naif:602', 'sol:naif:606')\n                code += 'openspace.setPropertyValueSingle(\"Scene.'+body['label_node']+'.Renderable.Enabled\",'+str(enabled).lower()+');'\n        elif initial and len(positions)>1:")
    lab = replace(lab, "if state.get('atlas_initial', {}).get('kind') == 'solar_four_physical_centers':",
                  "if state.get('atlas_initial', {}).get('kind') in ('solar_four_physical_centers', 'solar_sixteen_physical_centers'):")
    texts['laboratory.py'] = lab

    html = texts['ui/index.html']
    html = replace(html, '    <section class="atlas-copy"><button id="copy-solar"',
        '    <section class="atlas-copy"><button id="copy-sixteen" class="wide primary" disabled>Criar dinâmica dos16corpos</button><p class="field-help">Sol, oito planetas, Lua e seis luas principais na época confirmada. Modelo newtoniano de16centros físicos com gravidade recíproca, sem colisões, multipolos ou dissipação de marés. Campos magnéticos e processos nucleares permanecem nas bancadas próprias.</p></section>\n    <section class="atlas-copy"><button id="copy-solar"')
    html = replace(html, '<p id="solar-capabilities"', '<p id="dynamics16-model" class="field-help" hidden></p><p id="solar-capabilities"')
    texts['ui/index.html'] = html
    js = texts['ui/app.js']
    js = js.replace("$('copy-solar').disabled=", "$('copy-sixteen').disabled=$('copy-solar').disabled=")
    js = replace(js, "['/api/atlas/experiment','/api/solar/experiment']", "['/api/atlas/experiment','/api/solar/experiment','/api/dynamics16/experiment']")
    js = replace(js, "  const solar=initial?.kind==='solar_four_physical_centers',sourceCount=initial?.bodies.length;",
        "  const sixteen=initial?.kind==='solar_sixteen_physical_centers',solar=initial?.kind==='solar_four_physical_centers',sourceCount=initial?.bodies.length;\n  for (const id of ['gravity-harmonics','tides-panel','test-cloud']) $(id).hidden=sixteen;")
    js = replace(js, "textContent=solar?'Sol/Terra/Lua/Júpiter · cópia de referência'", "textContent=sixteen?'16centros físicos · cópia dinâmica':solar?'Sol/Terra/Lua/Júpiter · cópia de referência'")
    js = replace(js, ":solar?'Origem: cópia Sol/Terra/Lua/Júpiter", ":sixteen?'Origem: cópia dinâmica dos16centros físicos. ':solar?'Origem: cópia Sol/Terra/Lua/Júpiter")
    js = replace(js, "${solar?' + JUP365/599':''}", "${sixteen?' + JUP365 + SAT441':solar?' + JUP365/599':''}")
    js = replace(js, "const solar=p.atlas_initial?.kind==='solar_four_physical_centers';", "const solar=['solar_four_physical_centers','solar_sixteen_physical_centers'].includes(p.atlas_initial?.kind);")
    js = replace(js, "$('copy-solar').onclick=", "$('copy-sixteen').onclick=()=>{if(!atlasState||atlasPending||pending)return;command({utc:atlasState.epoch.utc},'Dinâmica dos16centros pronta e pausada.','/api/dynamics16/experiment');};\n$('copy-solar').onclick=")
    texts['ui/app.js'] = js
    solar = texts['ui/solar.js']
    solar = replace(solar, "  const available = initial?.kind === 'solar_four_physical_centers';",
        "  const sixteen = initial?.kind === 'solar_sixteen_physical_centers';\n  const available = sixteen || initial?.kind === 'solar_four_physical_centers';\n  $('dynamics16-model').hidden = !sixteen;\n  for (const panel of $('solar-panel').querySelectorAll(':scope > details')) panel.hidden=sixteen;\n  if(sixteen) {\n    const model=p.dynamics16;\n    $('dynamics16-model').textContent=`${model.model_id} · ${model.initial_format}\\n16fontes iniciais; ${p.bodies.length} corpos ativos. Época UTC: ${model.epoch.utc}\\nTempo decorrido: ${(model.elapsed_s/3600).toPrecision(8)} h · revisão ${p.revision}.\\nOrigem inercial separada; eixos J2000. O solver evolui a fase local, sem atualizar por efemérides a cada quadro.\\nMassas derivadas de GM/G; incertezas de origem desconhecidas. Edições são intervenções externas.\\nSem colisões, multipolos, dissipação de marés ou relatividade. EM e processos nucleares sem acoplamento nesta cópia.`;\n  }")
    for method in ['updateSolarTide', 'updateEarthField', 'updateJupiterField', 'updateBodyFieldVector']:
        solar = replace(solar, f'if (window.{method})', f'if (!sixteen && window.{method})')
    solar = replace(solar, "$('solar-capabilities').textContent = reference ?", "$('solar-capabilities').textContent = sixteen ? `${body.name} · ${body.reference_id || 'modelo criado nesta sessão'}\\nGravitação newtoniana pelas outras ${p.bodies.length-1} fontes ativas; campo próprio singular omitido. Sem acoplamento EM ou nuclear.` : reference ?")
    solar = replace(solar, "command: 'solar_reading', body_id:", "command: p.dynamics16 ? 'dynamics16_reading' : 'solar_reading', body_id:")
    texts['ui/solar.js'] = solar

    for name, text in texts.items():
        if name.endswith('.py'): compile(text, name, 'exec')
    shutil.copytree(BASE/'app', TARGET/'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name, text in texts.items(): (TARGET/'app'/name).write_text(text, encoding='utf8')
    for name in prepared['files_sha256']: shutil.copy2(REGISTRY/name, TARGET/'app'/name)
    shutil.copy2(ROOT/'scripts/dynamics16_runtime.py', TARGET/'app/dynamics16_runtime.py')
    inputs = [Path(__file__), ROOT/'scripts/dynamics16_runtime.py', BASE/'build-manifest.json',
              REGISTRY/'backend-preparation.json', proof, ROOT/'IS-6-DINAMICA16-INTERFACE-CONTRATO.md']
    inputs += [REGISTRY/n for n in prepared['files_sha256']]
    sources = {**parent['source_sha256'], **{p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}}
    assert all(sha(ROOT/n) == s for n, s in sources.items())
    files = {p.relative_to(TARGET/'app').as_posix(): sha(p) for p in (TARGET/'app').rglob('*') if p.is_file()}
    manifest = dict(candidate='0.26.0', accepted=False, promoted=False, source_sha256=sources,
                    files_sha256=files, changed=sorted(n for n, s in files.items() if actual.get(n) != s),
                    base_manifest=(BASE/'build-manifest.json').relative_to(ROOT).as_posix(),
                    scene_profile=parent['scene_profile'],
                    scope='Prepared sixteen-center dynamics; service, persistence, native, visual and performance acceptance pending.')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(prepared=True, candidate='0.26.0', changed=manifest['changed'])), flush=True)


if __name__ == '__main__': main()
