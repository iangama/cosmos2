"""Build a candidate with an eight-planet scientific data page."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'output/is6-spatial-import-product0.22.1'
TARGET = ROOT / 'output/is6-planet-catalog-product0.23.0'
STAGE = ROOT / 'output/is6-planet-catalog-staging'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def main():
    if TARGET.exists():
        raise FileExistsError('Preserve catalogue candidate')
    parent = json.loads((BASE / 'build-manifest.json').read_text())
    files = {p.relative_to(BASE / 'app').as_posix(): sha(p) for p in (BASE / 'app').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    assert files == parent['files_sha256']
    proof_path = ROOT / 'evidence/is6-planet-catalog-verification-20261110a.json'
    assert json.loads(proof_path.read_text())['accepted']
    sources = dict(parent['source_sha256'])
    inputs = [BASE / 'build-manifest.json', proof_path, Path(__file__),
              ROOT / 'scripts/launch-is6-planet-catalog-candidate.py',
              ROOT / 'output/is6-planet-catalog-model-20261110a/catalog-data.json',
              *[STAGE / p for p in ['is6_planet_catalog.py', 'planet-catalog.html', 'planet-catalog.js']]]
    data = json.loads((ROOT / 'output/is6-planet-catalog-model-20261110a/catalog-data.json').read_text())
    sources.update(data['runtime_sha256'])
    for path in inputs:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    shutil.copytree(BASE / 'app', TARGET / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    app = TARGET / 'app'
    shutil.copy2(STAGE / 'is6_planet_catalog.py', app / 'is6_planet_catalog.py')
    for name in ['planet-catalog.html', 'planet-catalog.js']:
        shutil.copy2(STAGE / name, app / 'ui' / name)
    server = (app / 'server.py').read_text()
    server = replace_once(server, 'from urllib.parse import urlsplit', 'from urllib.parse import urlsplit, parse_qs')
    anchor = "        if parsed.path.startswith('/api/stellar-reference/'):"
    route = """        if parsed.path == '/api/planet-reference':
            try:
                fields = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
                if set(fields) != {'utc'} or len(fields['utc']) != 1:
                    raise ValueError('Informe uma época UTC para o catálogo.')
                from is6_planet_catalog import states
                return self.json_response(states(fields['utc'][0]))
            except ValueError as error:
                return self.json_response({'ok':False,'error':str(error)},400)
            except Exception as error:
                return self.json_response({'ok':False,'error':str(error)},503)
"""
    server = replace_once(server, anchor, route + anchor)
    anchor = "            elif self.path == '/api/atlas/export':"
    route = """            elif self.path == '/api/planet-reference/export':
                if set(request) != {'utc'}:
                    raise ValueError('Informe somente a época UTC da referência.')
                from is6_planet_catalog import states
                from artifacts import export_json
                self.json_response(export_json('planet-reference', states(request['utc'])))
"""
    server = replace_once(server, anchor, route + anchor)
    (app / 'server.py').write_text(server)
    content = app / 'ui/content.html'
    content.write_text(replace_once(
        content.read_text(), '<section id="property-options">',
        '<a id="planet-catalog-link" class="back" href="/planet-catalog.html">Catálogo dos oito planetas ↗</a><section id="property-options">'
    ))
    new_files = {p.relative_to(app).as_posix(): sha(p) for p in app.rglob('*') if p.is_file()}
    changed = sorted(name for name, seal in new_files.items() if files.get(name) != seal)
    assert changed == ['is6_planet_catalog.py', 'server.py', 'ui/content.html',
                       'ui/planet-catalog.html', 'ui/planet-catalog.js']
    manifest = dict(candidate='0.23.0', accepted=False, promoted=False, source_sha256=sources,
                    files_sha256=new_files, changed=changed, base_manifest='output/is6-spatial-import-product0.22.1/build-manifest.json',
                    scope='Eight-planet data page and export; native visual review, navigation expansion and candidate profiles pending')
    (TARGET / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(prepared=True, candidate='0.23.0', changed=changed)), flush=True)


if __name__ == '__main__':
    main()
