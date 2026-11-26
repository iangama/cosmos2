"""Portable-view metadata replay checks; no scientific checkpoint integration claim."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/is3-body-view-staging'
APP = ROOT/'output/is3-body-lines-product/app'
sys.path[:0] = [str(STAGE), str(APP)]
import body_field_view as view

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder = ROOT/'output/is3-view-check-20261024a'
    receipt = ROOT/'evidence/is3-view-check-20261024a.json'
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve previous view evidence.')
    fixture = ROOT/'evidence/is3-vector-profile-20261024b.json'
    files = [STAGE/'body_field_view.py', Path(__file__).resolve(), ROOT/'IS-3-VISUAL-PERSISTENCIA-CONTRATO.md', fixture]
    files += [APP/name for name in ['body_field_geometry.py', 'earth_magnetism.py', 'jupiter_magnetism.py',
                                   'geomagnetism.py', 'jrm33.py', 'jrm33-coefficients.json', 'atlas.py', 'physics.py']]
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    owner = sha(ROOT/'user/sessions/latest.json')
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
    report = {'schema': 1, 'accepted': False, 'completed': False, 'source_sha256': hashes, 'roundtrips': []}
    try:
        fixture_data = json.loads(fixture.read_text(encoding='utf-8'))
        examples = []
        for row in fixture_data['runs']:
            state, reading = row['initial'], row['frozen_layer']['reading']
            # The profile initial snapshot is dynamic; the preserved reading is
            # its earlier, confirmed sample. Both share one physical origin.
            config = {'selected_body_id': reading['body_id'], 'representation': 'lines',
                      'earth': [-23.55, -46.63, 1000.], 'jupiter': [1.5*71492000., 0., 0., 13]}
            options = {'system_id': state['system_id'], 'fixture_sha256': state['fixture_sha256'],
                       'bodies': state['bodies'], 'time': state['time'], 'revision': state['revision'],
                       'initial': state['atlas_initial']}
            for representation in ['vector', 'lines']:
                for visible in [True, False]:
                    current = {**config, 'representation': representation}
                    preview = {'reading': reading, 'representation': representation, 'visible': visible}
                    captured = view.capture(state, current, preview)
                    encoded = json.dumps(captured, allow_nan=False)
                    for stale in [False, True]:
                        context = {**options, 'time': options['time']+(1. if stale else 0.),
                                   'revision': options['revision']+(1 if stale else 0)}
                        loaded = view.validate(json.loads(encoded), **context)
                        assert loaded == captured
                        report['roundtrips'].append({'model': row['model'], 'representation': representation,
                                                    'visible': visible, 'additional_phase_change': stale})
            assert view.validate(view.capture(state, config, None), **options)['layer'] is None
            assert view.validate(None, **options) is None
            examples.append((view.capture(state, config, preview), options))
        example, options = examples[0]
        def changed(keys, value):
            item = copy.deepcopy(example)
            target = item
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
            return item
        mutations = [(['schema'], True), (['schema'], 2), (['system_id'], '0'*32), (['fixture_sha256'], '0'*64),
            (['configuration', 'selected_body_id'], 'unknown'), (['configuration', 'representation'], 'plasma'),
            (['configuration', 'earth'], [False, 0., 0.]), (['configuration', 'earth'], [0., 0., -1.]),
            (['configuration', 'earth'], [0., 0., 1000001.]), (['configuration', 'earth'], [float('nan'), 0., 0.]),
            (['configuration', 'jupiter'], [1.5*71492000., 0., 0., True]),
            (['configuration', 'jupiter'], [1.5*71492000., 0., 0., 30]),
            (['configuration', 'jupiter'], [71491999., 0., 0., 13]),
            (['layer', 'visible'], 1), (['layer', 'representation'], 'external'),
            (['layer', 'reading', 'body_id'], 'unknown'), (['layer', 'reading', 'system_id'], '0'*32),
            (['layer', 'reading', 'body_reference_id'], 'sol:naif:301'),
            (['layer', 'reading', 'time'], options['time']+1), (['layer', 'reading', 'time'], -1),
            (['layer', 'reading', 'revision'], True), (['layer', 'reading', 'revision'], options['revision']+1),
            (['layer', 'reading', 'edit_token'], 'stale'), (['layer', 'reading', 'field_norm_T'], 0.),
            (['layer', 'reading', 'field_ITRF93_T'], [0., 0., 0.]),
            (['layer', 'reading', 'ITRF93_to_J2000'], [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]),
            (['layer', 'reading', 'epoch', 'utc'], '2000-01-01T00:00:00Z'),
            (['layer', 'reading', 'provenance', 'coefficient_sha256'], '0'*64),
            (['layer', 'reading', 'scientific_generation', 'candidate_extension', 'id'], 'unknown')]
        refused = 0
        for keys, value in mutations:
            try:
                view.validate(changed(keys, value), **options)
            except (ValueError, KeyError, TypeError):
                refused += 1
            else:
                raise AssertionError(('Invalid view accepted', keys))
        for item in [{**example, 'unknown': 1}, {k: v for k, v in example.items() if k != 'layer'}]:
            try:
                view.validate(item, **options)
            except ValueError:
                refused += 1
            else:
                raise AssertionError('Invalid structure accepted.')
        report['refusals'] = refused
        assert refused >= 22
        assert sha(ROOT/'user/sessions/latest.json') == owner
        assert all(sha(ROOT/name) == digest for name, digest in hashes.items())
        report.update(accepted=True, completed=True, sources_and_owner_preserved=True,
            scope='Portable metadata validation/replay in staging only; no Session/worker save/load integration, branch persistence or native restart acceptance.')
    except Exception:
        report['failure'] = traceback.format_exc()
    receipt.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'accepted': report['accepted'], 'roundtrips': len(report['roundtrips']),
                      'refusals': report.get('refusals'), 'failure': report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
