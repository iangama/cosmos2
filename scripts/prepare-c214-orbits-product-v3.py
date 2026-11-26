"""Seal an isolated UI candidate on the accepted timelike HTTP backend."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def files(folder):
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    candidate = ROOT / 'output/c214-orbits-product0.28.2'
    assert not candidate.exists()
    sources = {}
    for suffix in ['numerics-20261114a', 'service-20261114a', 'http-20261114b']:
        path = ROOT / f'evidence/c214-orbits-{suffix}.json'
        receipt = json.loads(path.read_text(encoding='utf8'))
        assert receipt['accepted'] and receipt['completed']
        for name, seal in (receipt.get('source_sha256', {}) | receipt.get('protected_sha256', {})).items():
            if name == 'output/session.json':
                transition_path = ROOT / 'evidence/c214-orbits-native-20261114b.json'
                transition = json.loads(transition_path.read_text())
                assert transition.get('owner_restored') is True and len(transition['closures']) == 2
                assert all(row['code'] == 0 for closure in transition['closures'] for row in closure['exits'].values())
                current = json.loads((ROOT / name).read_text(encoding='utf-8-sig'))
                assert Path(current['serverScript']).resolve() == ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
                sources[transition_path.relative_to(ROOT).as_posix()] = sha(transition_path)
                continue
            assert sha(ROOT / name) == seal, name
            sources[name] = seal
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    stage = ROOT / 'output/c214-orbits-ui-staging-v3'
    backend = ROOT / 'output/c214-orbits-staging-v2'
    for name, seal in files(backend / 'app').items():
        if not name.startswith('ui/'):
            assert sha(stage / 'app' / name) == seal, name
    assert files(stage / 'data/science') == files(backend / 'data/science')
    parent = ROOT / 'output/is6-expanded-journey-product0.27.0'
    inherited = json.loads((parent / 'build-manifest.json').read_text(encoding='utf8'))
    assert files(parent / 'app') == inherited['files_sha256']
    for name, seal in inherited['source_sha256'].items():
        assert sha(ROOT / name) == seal, name
    sources.update(inherited['source_sha256'])
    sources[(parent / 'build-manifest.json').relative_to(ROOT).as_posix()] = sha(parent / 'build-manifest.json')
    for tree in ['app', 'data']:
        for name, seal in files(stage / tree).items():
            sources[(stage / tree / name).relative_to(ROOT).as_posix()] = seal
    for name in ['scripts/prepare-c214-orbits-product-v3.py', 'scripts/launch-c214-orbits-candidate-v3.py', 'C2-14-ORBITAS-NATIVO-CONTRATO-20261114.md', 'C2-14-ORBITAS-NATIVO-REVISAO-B-20261114.md', 'C2-14-ORBITAS-NATIVO-REVISAO-C-20261114.md']:
        sources[name] = sha(ROOT / name)
    candidate.mkdir()
    for tree in ['app', 'data']:
        shutil.copytree(stage / tree, candidate / tree, ignore=shutil.ignore_patterns('__pycache__'))
    current = files(candidate / 'app')
    manifest = dict(candidate='0.28.2', accepted=False, promoted=False,
                    parent='0.27.0', scope='C2-14 native CEF timelike bench; no native/visual/performance acceptance yet',
                    source_sha256=sources, files_sha256=current, data_sha256=files(candidate / 'data'),
                    changed=[name for name, seal in current.items() if inherited['files_sha256'].get(name) != seal])
    (candidate / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(candidate=str(candidate), sources=len(sources), app_files=len(current), changed=manifest['changed'])))


if __name__ == '__main__':
    main()
