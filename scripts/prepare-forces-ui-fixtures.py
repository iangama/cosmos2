"""Freeze real default model responses for isolated UI transition checks; no renderer or save writes."""
from pathlib import Path
import hashlib
import json
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/original-flow-hotfix-product0.27.1/app'
FOLDER = ROOT / 'output/forces-confirmed-ui-fixtures-20261120a'
OUT = ROOT / 'evidence/forces-confirmed-ui-fixtures-20261120a.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not FOLDER.exists() and not OUT.exists()
    FOLDER.mkdir()
    manifest = json.loads((APP.parent / 'build-manifest.json').read_text(encoding='utf8'))
    proof = dict(accepted=False, completed=False, cases=[],
                 source_sha256={str((APP.parent / name).relative_to(ROOT)).replace('\\','/'):digest for name,digest in manifest['files_sha256'].items()},
                 script_sha256=sha(Path(__file__)),
                 scope='Real default scientific outputs frozen as fixtures for subsequent isolated UI state checks. No UI, renderer, persistence or performance acceptance.')
    try:
        sys.path.insert(0, str(APP))
        import forces
        catalog = dict(schema=2, scenarios=forces.SCENARIOS, effects=forces.EFFECTS)
        (FOLDER / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
        for scenario in forces.SCENARIOS:
            value = forces.evaluate(dict(scenario=scenario, controls={}, parameters={}))
            assert value['ok'] and value['configuration']['scenario'] == scenario
            path = FOLDER / (scenario+'.json')
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
            proof['cases'].append(dict(scenario=scenario, sha256=sha(path), physics_sha256=value['physics_sha256']))
        assert len(proof['cases']) == 12
        assert all(sha(ROOT / name) == digest for name,digest in proof['source_sha256'].items())
        proof.update(accepted=True, completed=True, catalog_sha256=sha(FOLDER / 'catalog.json'))
    except Exception:
        proof['failure'] = traceback.format_exc()
    finally:
        OUT.write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(accepted=proof['accepted'], completed=proof['completed'], cases=len(proof['cases']), failure=proof.get('failure')), ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
