"""Prepare an isolated spatial product from preserved, accepted local sources."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='0.18.0')
    args = parser.parse_args()
    if args.version != '0.18.0':
        parser.error('This preparation describes the initial0.18.0 candidate only')
    base = ROOT / 'output/is5-compression-product0.17.2'
    target = ROOT / ('output/is6-spatial-product' + args.version)
    stage = ROOT / 'output/is6-product-staging'
    if target.exists():
        raise FileExistsError('Preserve the prepared candidate; create a revision')
    parent_path = base / 'build-manifest.json'
    parent = json.loads(parent_path.read_text())
    actual = {p.relative_to(base/'app').as_posix():sha(p) for p in (base/'app').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    assert actual == parent['files_sha256']
    anchors = [ROOT / ('evidence/' + name) for name in [
        'is5-native-compression-20261101c.json',
        'is5-compression-visual-review-20261101c.json',
        'is5-compression-profile-audit-20261101a.json',
        'is6-scene-transaction-20261101a.json']]
    sources = dict(parent['source_sha256'])
    for p in anchors:
        receipt = json.loads(p.read_text())
        assert receipt['accepted'], p
        for name, value in receipt.get('source_sha256', {}).items():
            assert sha(ROOT/name) == value, name
            sources[name] = value
    for p in [Path(__file__), parent_path, ROOT/'IS-6-PRODUTO-CONTRATO-PREVIO.md',
              ROOT/'IS-6-TRANSACAO-RESULTADO-20261102.md', ROOT/'scripts/launch-is6-spatial-candidate.py', *anchors]:
        sources[p.relative_to(ROOT).as_posix()] = sha(p)
    for p in stage.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            sources[p.relative_to(ROOT).as_posix()] = sha(p)
            if p.suffix == '.py':
                ast.parse(p.read_text(), filename=str(p))
    shutil.copytree(base/'app', target/'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    app = target/'app'
    for p in stage.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            destination = app/p.relative_to(stage)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, destination)
    server = app/'server.py'
    text = server.read_text()
    def replace(old, new):
        nonlocal text
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    replace('SOURCE_COMMANDS = threading.RLock()', 'from is6_laboratory import SpatialLaboratory\nSPATIAL = SpatialLaboratory(LAB)\nSOURCE_COMMANDS = threading.RLock()')
    replace("        if self.path=='/api/solar-zone/state':", "        if self.path=='/api/spatial/state':\n            return self.json_response(SPATIAL.status())\n        if self.path=='/api/solar-zone/state':")
    replace("if self.path in ('/api/shutdown','/api/solar-zone/cancel'):", "if self.path in ('/api/shutdown','/api/solar-zone/cancel','/api/spatial/cancel'):")
    replace("if self.path == '/api/solar-zone/command':\n            if not SOURCE_COMMANDS.acquire(blocking=False):", "if self.path in ('/api/solar-zone/command','/api/spatial/command'):\n            if not SOURCE_COMMANDS.acquire(blocking=False):")
    replace("        if SOLAR_ZONE.status().get('busy'):", "        if SPATIAL.status().get('busy'):\n            return self.json_response({'ok':False,'error':'Aguarde a confirmação da malha.'},400)\n        if SOLAR_ZONE.status().get('busy'):")
    old = "            if self.path == '/api/solar-zone/command':"
    replace(old, "            if SPATIAL.status()['active'] or SPATIAL.status().get('recovery_required'):\n                if self.path in ('/api/command','/api/particles/command','/api/solar-zone/command') or self.path.startswith(('/api/solar/','/api/atlas/','/api/navigation/')):\n                    raise ValueError('Feche a malha antes de alterar a cena orbital ou abrir outro instrumento.')\n            if self.path == '/api/spatial/command':\n                if PARTICLES.status()['active'] or SOLAR_ZONE.status()['active']:\n                    raise ValueError('Feche a partícula ou a zona solar antes de abrir a malha.')\n                self.json_response(SPATIAL.command(request))\n            elif self.path == '/api/spatial/cancel':\n                self.json_response(SPATIAL.cancel(request))\n            elif self.path == '/api/solar-zone/command':")
    replace("        if self.path not in ('/api/state','/api/particles/state','/api/solar-zone/state','/health'):", "        if self.path not in ('/api/state','/api/particles/state','/api/solar-zone/state','/api/spatial/state','/health'):")
    replace('        SOLAR_ZONE.close()', '        SPATIAL.close()\n        SOLAR_ZONE.close()')
    ast.parse(text)
    server.write_text(text, encoding='utf-8')
    index = app/'ui/index.html'
    html = index.read_text()
    old = '<link rel="stylesheet" href="stellar-reference.css">'
    assert html.count(old) == 1
    html = html.replace(old, old + '\n<link rel="stylesheet" href="is6-spatial.css">')
    old = '<button id="open-stellar-reference"'
    assert html.count(old) == 1
    html = html.replace(old, '<button id="open-spatial" aria-controls="spatial-panel" aria-expanded="false">Malha espacial</button>' + old)
    old = '  <script src="app.js">'
    assert html.count(old) == 1
    html = html.replace(old, (stage/'ui/is6-spatial-panel.html').read_text() + '\n' + old)
    old = '<script src="stellar-reference.js"></script>'
    assert html.count(old) == 1
    html = html.replace(old, old + '<script src="is6-spatial.js"></script>')
    index.write_text(html, encoding='utf-8')
    files = {p.relative_to(app).as_posix():sha(p) for p in app.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    assert all(sha(ROOT/n)==v for n,v in sources.items())
    manifest = dict(candidate=args.version, promoted=False, accepted=False,
        files_sha256=files, source_sha256=sources, base_files_sha256=actual,
        base_manifest=parent_path.relative_to(ROOT).as_posix(),
        scope='Prepared spatial candidate only; native/CEF/visual/profile acceptance pending.')
    (target/'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(prepared=True, accepted=False, candidate=str(target), files=len(files))))


if __name__ == '__main__':
    main()
