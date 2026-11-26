"""Verify catalogue states, isolation, input refusals and interpreter reopening."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-spatial-import-product0.22.1/app'
STAGE = ROOT / 'output/is6-planet-catalog-staging'
sys.path[:0] = [str(STAGE), str(APP)]
import atlas
import is6_planet_catalog as catalog

EPOCHS = ['1995-01-01T00:00:00Z', '2000-01-01T12:00:00Z', '2026-10-11T12:00:00Z',
          '2030-06-15T18:30:00Z', '2049-12-30T23:59:59Z']
TARGETS = ['10', '199', '299', '399', '301', '499', '599', '699', '799', '899']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def loaded():
    return sorted(str(Path(atlas.SPICE.kdata(i, 'SPK')[0]).resolve())
                  for i in range(atlas.SPICE.ktotal('SPK')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    label = parser.parse_args().label
    if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        parser.error('Invalid label')
    folder = ROOT / 'output' / f'is6-planet-catalog-verification-{label}'
    receipt = ROOT / 'evidence' / f'is6-planet-catalog-verification-{label}.json'
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve catalogue verification')
    folder.mkdir()
    protected = [ROOT / 'user/sessions/latest.json', ROOT / 'Iniciar-Cosmos2.cmd',
                 ROOT / 'evidence/is6-layers-import-profile-20261105k5a.json',
                 ROOT / 'evidence/is6-spatial-import-profile-audit-20261105p4.json']
    seals = {p: sha(p) for p in protected}
    result = dict(accepted=False, completed=False, cases=[], refusals=[],
                  script_sha256=sha(Path(__file__)), module_sha256=sha(Path(catalog.__file__)),
                  data_sha256=sha(catalog.DATA), scope='CPU reference catalogue verification')
    try:
        atlas.initialize()
        kernel_pool = loaded()
        baseline = {utc: atlas.states(utc=utc) for utc in EPOCHS}
        for index, utc in enumerate(EPOCHS):
            state = catalog.states(utc)
            assert loaded() == kernel_pool
            assert [b['naif_id'] for b in state['bodies']] == TARGETS
            assert sum(b['body_kind'] == 'planet' for b in state['bodies']) == 8
            assert all(b['entity_kind'] == 'physical_body' for b in state['bodies'])
            assert state['center_naif_id'] == '0' and state['frame'] == 'J2000/ICRF' and state['aberration'] == 'NONE'
            assert state['position_unit'] == 'm' and state['velocity_unit'] == 'm/s'
            render = np.array(state['j2000_to_render_frame'])
            assert np.max(np.abs(render @ render.T - np.eye(3))) <= 1e-12
            by_id = {b['naif_id']: b for b in state['bodies']}
            for body in state['bodies']:
                assert math.isfinite(body['GM']['value']) and body['GM']['value'] > 0
                assert all(math.isfinite(x) for x in body['position_m'] + body['velocity_m_s'])
                assert all(math.isfinite(x) and x > 0 for x in body['shape']['radii_m'])
                assert np.max(np.abs(render @ body['position_m'] - body['position_render_m'])) <= .005
                matrix = body['rotation']['body_to_j2000']
                if matrix is not None:
                    rotation = np.array(matrix)
                    assert np.max(np.abs(rotation @ rotation.T - np.eye(3))) <= 1e-12
                    assert abs(np.linalg.det(rotation) - 1) <= 1e-12
            for old in baseline[utc]['bodies']:
                assert by_id[old['naif_id']]['position_m'] == old['position_m']
                assert by_id[old['naif_id']]['velocity_m_s'] == old['velocity_m_s']
            assert atlas.states(utc=utc) == baseline[utc]
            saved = folder / f'epoch-{index+1}.json'
            saved.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
            result['cases'].append(dict(utc=utc, bodies=10, planets=8,
                                        path=saved.relative_to(ROOT).as_posix(), sha256=sha(saved)))
        for value in [None, True, False, 0, 1., float('nan'), float('inf'), [], {}, '',
                      '1994-12-31T23:59:59Z', '2049-12-31T00:00:00Z', '2026-02-30T12:00:00Z',
                      '2026-10-11T12:00:00+03:00', '2026-10-11']:
            try:
                catalog.states(value)
            except ValueError as error:
                result['refusals'].append(dict(input=repr(value), error=str(error)))
            else:
                raise AssertionError('Invalid epoch admitted: ' + repr(value))
            assert loaded() == kernel_pool
        original_data = catalog.DATA
        changed = folder / 'changed-catalog-data.json'
        changed.write_bytes(original_data.read_bytes() + b' ')
        catalog.DATA = changed
        try:
            catalog.states(EPOCHS[2])
        except ValueError as error:
            result['refusals'].append(dict(input='changed data after warm cache', error=str(error)))
        else:
            raise AssertionError('Changed model metadata admitted')
        finally:
            catalog.DATA = original_data
        assert loaded() == kernel_pool
        assert catalog.states(EPOCHS[2]) == json.loads((folder / 'epoch-3.json').read_text(encoding='utf8'))
        code = (
            'import sys,json;sys.path[:0]=' + repr([str(STAGE), str(APP)]) +
            ';import is6_planet_catalog as c;print(json.dumps(c.states(' + repr(EPOCHS[2]) + ')))'
        )
        reopened = subprocess.run([sys.executable, '-Xutf8', '-c', code], capture_output=True,
                                  encoding='utf8', check=True, timeout=60)
        assert json.loads(reopened.stdout) == json.loads((folder / 'epoch-3.json').read_text(encoding='utf8'))
        result.update(accepted=True, completed=True, fresh_interpreter_equal=True,
                      kernel_pool_restored=True, protected_unchanged=all(sha(p) == s for p, s in seals.items()))
        assert result['protected_unchanged']
    except Exception:
        result['failure'] = traceback.format_exc()
        result['accepted'] = False
    finally:
        if atlas.SPICE is not None:
            atlas.SPICE.kclear()
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], cases=len(result['cases']),
                          refusals=len(result['refusals']), failure=result.get('failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
