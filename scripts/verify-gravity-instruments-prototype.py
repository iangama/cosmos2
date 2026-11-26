"""C2-11 staging: stable probe identity, inertial following and read-only physics."""
from pathlib import Path
import copy
import ctypes
import hashlib
import importlib.util
import json
import math
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from session import Session
from physics import PHYSICAL_SCALE as U
import rebound


def candidate(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'output/c211-staging' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


instruments = candidate('gravity_instruments')
field = candidate('gravity_field')
invalid = corrupt = 0
checks = []
with tempfile.TemporaryDirectory() as tmp:
    session = Session(tmp, 32)
    session.sim.integrate(.01)
    session.save()
    frozen = copy.deepcopy(session.state())
    session.sim.save_to_file(str(Path(tmp) / 'before.bin'))
    pointer = (Path(tmp) / 'latest.json').read_bytes()
    ids = [b['id'] for b in frozen['bodies']]
    def configure(current, operation, **parameters):
        return instruments.configure(current, {'instruments_revision': current['revision'],
                                             'operation': operation, **parameters}, ids, ids)
    config = instruments.empty()
    fixed = {'name': 'Órbita "Lua" \\ teste', 'mode': 'fixed', 'position_m': [1.7e10, -9e9, 3e9]}
    config = configure(config, 'create', definition=fixed)
    fixed_id = config['probes'][0]['id']
    follow = {'name': 'Externa no corpo', 'mode': 'follow', 'body_id': ids[1],
              'offset_m': [0, 0, 0], 'exclude_followed_source': True}
    config = configure(config, 'create', definition=follow)
    followed_id = config['probes'][1]['id']
    readings = instruments.sample(config, frozen, field.evaluate)
    fixed_reading, follow_reading = readings['readings']
    expected = field.evaluate(frozen['bodies'], fixed['position_m'])
    for key in ('acceleration_m_s2', 'potential_J_kg', 'tidal_tensor_s_2'):
        assert fixed_reading[key] == expected[key]
    position = [v * U['length_unit_m'] for v in frozen['bodies'][1]['position']]
    assert follow_reading['position_m'] == position
    external = field.evaluate([b for b in frozen['bodies'] if b['id'] != ids[1]], position)
    assert follow_reading['acceleration_m_s2'] == external['acceleration_m_s2']
    assert follow_reading['excluded_source_ids'] == [ids[1]]
    # IAS15's cached ax can belong to its last internal stage. Evaluate the
    # current positions on a copy through REBOUND's force routine explicitly.
    reference = session.sim.copy()
    rebound.clibrebound.reb_simulation_update_acceleration(ctypes.byref(reference))
    solver = reference.particles[1]
    solver_g = [solver.ax, solver.ay, solver.az]
    factor = U['nominal_GM_unit_m3_s2'] / U['length_unit_m'] ** 2
    difference = math.dist([v * factor for v in solver_g], external['acceleration_m_s2'])
    relative = difference / external['acceleration_norm_m_s2']
    assert relative < 1e-12, relative
    moved = copy.deepcopy(frozen)
    moved['bodies'][1]['position'] = [v + .125 for v in moved['bodies'][1]['position']]
    moved['time'] += 1
    moved_readings = instruments.sample(config, moved, field.evaluate)
    assert moved_readings['readings'][0]['position_m'] == fixed['position_m']
    assert moved_readings['readings'][1]['position_m'] == [v * U['length_unit_m'] for v in moved['bodies'][1]['position']]
    removed = copy.deepcopy(frozen)
    removed['bodies'] = [b for b in removed['bodies'] if b['id'] != ids[1]]
    missing = instruments.sample(config, removed, field.evaluate)['readings'][1]
    assert not missing['available'] and missing['definition']['body_id'] == ids[1]
    assert 'acceleration_m_s2' not in missing and 'potential_J_kg' not in missing
    singular = configure(config, 'create', definition={**follow, 'exclude_followed_source': False})
    bad_sample = instruments.sample(singular, frozen, field.evaluate)['readings'][-1]
    assert not bad_sample['available'] and '1 mm' in bad_sample['reason']
    # Names, definitions, identities, tombstones and history survive JSON exactly.
    serialized = json.dumps(config, allow_nan=False, ensure_ascii=False)
    assert instruments.validate(json.loads(serialized), ids) == config
    restored = instruments.validate(json.loads(serialized), ids)
    assert instruments.sample(restored, frozen, field.evaluate) == readings
    before_delete = copy.deepcopy(config)
    config = configure(config, 'remove', id=fixed_id)
    config = configure(config, 'create', definition=fixed)
    assert fixed_id in config['issued_ids'] and config['probes'][-1]['id'] != fixed_id
    assert config['probes'][0]['id'] == followed_id
    bad_requests = [
        {'instruments_revision': config['revision'] - 1, 'operation': 'remove', 'id': followed_id},
        {'instruments_revision': True, 'operation': 'remove', 'id': followed_id},
        {'instruments_revision': config['revision'], 'operation': 'remove', 'id': fixed_id},
    ]
    for name, value in [('name', ''), ('name', 'x' * 81), ('name', 'bad\nname'),
                        ('position_m', [math.nan, 0, 0]), ('position_m', [True, 0, 0]),
                        ('position_m', [0, 0]), ('position_m', [2e17, 0, 0]), ('mode', 'corotating')]:
        bad_requests.append({'instruments_revision': config['revision'], 'operation': 'create',
                             'definition': {**fixed, name: value}})
    bad_requests.append({'instruments_revision': config['revision'], 'operation': 'create',
                         'definition': {**follow, 'body_id': 'p999'}})
    for request in bad_requests:
        before = copy.deepcopy(config)
        try:
            instruments.configure(config, request, ids, ids)
        except ValueError:
            invalid += 1
        else:
            raise AssertionError(('Accepted invalid request', request))
        assert config == before
    corruptions = [
        lambda c: c.update(revision=True),
        lambda c: c['issued_ids'].append(c['issued_ids'][0]),
        lambda c: c['probes'][0].update(id=fixed_id),
        lambda c: c['probes'][0].update(body_id='p999'),
        lambda c: c['probes'][0].update(exclude_followed_source='yes'),
        lambda c: c['probes'][0].update(name='changed without event'),
        lambda c: c['events'].pop(),
        lambda c: c['events'][-1]['definition'].update(id=fixed_id),
        lambda c: c['events'][0].update(revision=2),
    ]
    for change in corruptions:
        bad = copy.deepcopy(config)
        change(bad)
        try:
            instruments.validate(bad, ids)
        except ValueError:
            corrupt += 1
        else:
            raise AssertionError('Accepted incoherent instrument history')
    full = copy.deepcopy(config)
    while len(full['probes']) < 16:
        full = configure(full, 'create', definition=fixed)
    try:
        configure(full, 'create', definition=fixed)
    except ValueError:
        invalid += 1
    else:
        raise AssertionError('Probe bound not enforced')
    session.sim.save_to_file(str(Path(tmp) / 'after.bin'))
    assert (Path(tmp) / 'before.bin').read_bytes() == (Path(tmp) / 'after.bin').read_bytes()
    assert session.state() == frozen and (Path(tmp) / 'latest.json').read_bytes() == pointer
    assert readings['revision'] == frozen['revision'] and readings['instruments_revision'] == 2
    large = Session(Path(tmp) / 'population128', 128).state()
    all_probes = instruments.sample(full, large, field.evaluate)
    payload_bytes = len(json.dumps(all_probes, allow_nan=False).encode())
    assert len(all_probes['source_snapshot_si']) == 128 and len(all_probes['readings']) == 16
    assert all('sources' not in reading for reading in all_probes['readings'])
    assert payload_bytes < 128 * 1024, payload_bytes
    checks = ['fixed_point_shared_evaluator_exact', 'follow_inertial_offset_without_corotation',
              'explicit_self_exclusion_matches_solver', 'missing_target_keeps_original_identity',
              'singularity_has_reason_without_invented_value', 'configuration_roundtrip_exact',
              'own_revision_and_tombstones', 'binary_checkpoint_phase_and_conservation_unchanged',
              'bounded_16_probes']

report = {'status': 'verified_staging_only_not_product', 'checks': checks,
          'invalid_without_mutation': invalid, 'incoherent_persisted_definitions_rejected': corrupt,
          'external_acceleration_vs_solver_relative_difference': relative,
          'P128_16_probe_payload_bytes': payload_bytes,
          'global_SI_source_snapshot_avoids_repeating_all_contributions_per_probe': True,
          'prototype_sha256': hashlib.sha256((ROOT / 'output/c211-staging/gravity_instruments.py').read_bytes()).hexdigest()}
(ROOT / 'evidence/gravity-instruments-prototype-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
