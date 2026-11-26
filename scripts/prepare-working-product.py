"""Prepare a local working copy without changing sealed candidates or scientific modules."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'output/original-flow-hotfix-staging-v2'
TARGET = ROOT / 'output/original-flow-hotfix-product0.27.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists(), 'Preserve prepared products'
    review = json.loads((ROOT / 'evidence/original-flow-hotfix-review-20261120a.json').read_text(encoding='utf8'))
    assert review['accepted'] and review['completed'] and review['scientific_python_unchanged'] == 137
    source = json.loads((SOURCE / 'preparation.json').read_text(encoding='utf8'))
    for name in ['app', 'data']:
        assert all(sha(SOURCE / name / relative) == digest for relative, digest in source[name + '_sha256'].items())
        shutil.copytree(SOURCE / name, TARGET / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    preserved = []
    old = ROOT / 'output/is6-expanded-journey-product0.27.0'
    for name in ['gravity-sessions', 'navigation', 'spatial-checkpoints', 'layer-checkpoints',
                 'particle-checkpoints', 'solar-zone-checkpoints']:
        if (old / name).is_dir():
            shutil.copytree(old / name, TARGET / name)
            for file in (old / name).rglob('*'):
                if file.is_file():
                    destination = TARGET / file.relative_to(old)
                    assert sha(file) == sha(destination)
                    preserved.append(dict(source=file.relative_to(ROOT).as_posix(),
                                          destination=destination.relative_to(ROOT).as_posix(), sha256=sha(file)))
    if (ROOT / 'user/forces').is_dir():
        shutil.copytree(ROOT / 'user/forces', TARGET / 'user/forces')
        for file in (ROOT / 'user/forces').rglob('*'):
            if file.is_file():
                destination = TARGET / 'user/forces' / file.relative_to(ROOT / 'user/forces')
                assert sha(file) == sha(destination)
                preserved.append(dict(source=file.relative_to(ROOT).as_posix(), destination=destination.relative_to(ROOT).as_posix(), sha256=sha(file)))
    manifest = dict(schema=1, candidate='0.27.1', promoted=False, native_user_flow_accepted=False,
                    scientific_python_unchanged=137, source_preparation_sha256=sha(SOURCE / 'preparation.json'),
                    files_sha256={f'{name}/{relative}': digest for name in ['app', 'data']
                                  for relative, digest in source[name + '_sha256'].items()},
                    preserved_state=preserved, preparation_script_sha256=sha(Path(__file__)),
                    scope='Local functional correction under review. No scientific milestone or final visual integration acceptance.')
    (TARGET / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    selection = ROOT / 'config/local-working-product.json'
    assert not selection.exists(), 'Preserve an existing local selection'
    selection.write_text(json.dumps(dict(schema=1, product=TARGET.relative_to(ROOT).as_posix(),
                                         runtime='.runtime-is4-stream', candidate='0.27.1',
                                         scope='Local working product; native functional review in progress, no milestone promotion.'), indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(prepared=True, product=TARGET.relative_to(ROOT).as_posix(),
                          preserved_state_files=len(preserved), scientific_python_unchanged=137)))


if __name__ == '__main__':
    main()
