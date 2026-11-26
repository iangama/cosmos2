"""Prepare 0.23.1 with an explicit UTC date and Portuguese source labels."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'output/is6-planet-catalog-product0.23.0'
TARGET = ROOT / 'output/is6-planet-catalog-product0.23.1'
STAGE = ROOT / 'output/is6-planet-catalog-staging'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if TARGET.exists():
        raise FileExistsError('Preserve catalogue revision')
    parent_path = BASE / 'build-manifest.json'
    parent = json.loads(parent_path.read_text())
    files = {p.relative_to(BASE / 'app').as_posix(): sha(p) for p in (BASE / 'app').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    assert files == parent['files_sha256']
    functional = ROOT / 'evidence/is6-planet-catalog-native-20261110a.json'
    visual = ROOT / 'evidence/is6-planet-catalog-visual-20261111a.json'
    assert json.loads(functional.read_text())['functional_accepted']
    assert json.loads(visual.read_text())['accepted'] is False
    sources = dict(parent['source_sha256'])
    for path in [parent_path, functional, visual, Path(__file__),
                 ROOT / 'scripts/launch-is6-planet-catalog-candidate-v2.py',
                 STAGE / 'planet-catalog-v2.html', STAGE / 'planet-catalog-v2.js']:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT / p) == seal for p, seal in sources.items())
    shutil.copytree(BASE / 'app', TARGET / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for suffix in ('html', 'js'):
        shutil.copy2(STAGE / ('planet-catalog-v2.' + suffix), TARGET / 'app/ui' / ('planet-catalog.' + suffix))
    updated = {p.relative_to(TARGET / 'app').as_posix(): sha(p) for p in (TARGET / 'app').rglob('*') if p.is_file()}
    changed = sorted(p for p, seal in updated.items() if files.get(p) != seal)
    assert changed == ['ui/planet-catalog.html', 'ui/planet-catalog.js']
    result = dict(candidate='0.23.1', accepted=False, promoted=False, source_sha256=sources,
                  files_sha256=updated, changed=changed, base_manifest=parent_path.relative_to(ROOT).as_posix(),
                  scope='Explicit ISO UTC input and localised labels; native review and own profile pending')
    (TARGET / 'build-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(prepared=True, candidate='0.23.1', changed=changed)), flush=True)


if __name__ == '__main__':
    main()
