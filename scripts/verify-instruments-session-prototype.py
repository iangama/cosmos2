"""Uninstalled C2-11 Session candidate: sealed probes without physical mutation.

The current product generation remains3.4. This exercises candidate Session,
attributes, instruments and field files; it does not certify an installed3.5.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
sys.path.insert(0, str(ROOT / 'output/c211-staging'))
from session import Session
from body_registry import digest
from atlas import states
from atlas_import import prepare, experiment_subset
import instrument_scene


def guard(s):
    return {'system_id': s.system_id, 'edit_token': s.edit_token, 'revision': s.revision,
            'expected_time': s.sim.t, 'frame': s.contract()['frame'],
            'instruments_revision': s.instruments['revision']}


def physical(s):
    value = copy.deepcopy(s.state())
    value.pop('instruments')
    return value


invalid = corrupt = 0
results = []
with tempfile.TemporaryDirectory() as tmp:
    for kind in ('fixture', 'atlas', 'user'):
        s = Session(Path(tmp) / kind, 32)
        if kind == 'atlas':
            s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
        elif kind == 'user':
            s.new_system({**guard(s), 'name': 'Corpo único', 'mass_kg': 1e25,
                          'position_m': [0, 0, 0], 'velocity_m_s': [0, 0, 0]})
        s.sim.integrate(.01)
        s.save()
        before = physical(s)
        s.sim.save_to_file(str(s.directory / 'before.bin'))
        pointer = (s.directory / 'latest.json').read_bytes()
        original = copy.deepcopy(s.atlas_initial)
        followed = s.registry[-1]['id']
        fixed = {'mode': 'fixed', 'name': 'Ponto fixo "órbita" \\', 'position_m': [1.7e10, -9e9, 3e9]}
        follow = {'mode': 'follow', 'name': 'Seguindo', 'body_id': followed,
                  'offset_m': [1e5, -2e5, 3e5], 'exclude_followed_source': True}
        for definition in (fixed, follow):
            s.configure_instruments({**guard(s), 'operation': 'create', 'definition': definition})
        result = s.sample_instruments(guard(s))
        assert len(result['readings']) == 2 and all(r['available'] for r in result['readings'])
        assert result['instruments_revision'] == 2 and physical(s) == before
        s.sim.save_to_file(str(s.directory / 'after.bin'))
        assert (s.directory / 'before.bin').read_bytes() == (s.directory / 'after.bin').read_bytes()
        assert (s.directory / 'latest.json').read_bytes() == pointer
        saved_definitions = copy.deepcopy(s.instruments)
        state = copy.deepcopy(s.state())
        state['instruments']['probes'][0]['name'] = 'must not alias'
        assert s.instruments == saved_definitions
        for key, value in [('system_id', 'bad'), ('edit_token', 'bad'), ('revision', -1),
                           ('expected_time', s.sim.t + 1), ('frame', 'wrong'),
                           ('instruments_revision', True), ('instruments_revision', 0)]:
            baseline = copy.deepcopy(s.state())
            try:
                s.sample_instruments({**guard(s), key: value})
            except ValueError:
                invalid += 1
            else:
                raise AssertionError('Stale probe sample accepted')
            assert s.state() == baseline
        create, render = instrument_scene.prepare(result, s.atlas_initial)
        create_again, render_again = instrument_scene.prepare(result, s.atlas_initial)
        assert len(render['nodes']) == 2 and not (set(render['nodes']) & set(render_again['nodes']))
        assert 'Ponto fixo' in create and '\\"' in create
        for reading, display in zip(result['readings'], render['readings']):
            expected = reading['position_m']
            if s.atlas_initial:
                matrix = s.atlas_initial['j2000_to_render_frame']
                expected = [sum(row[k] * expected[k] for k in range(3)) for row in matrix]
            assert max(abs(a - b) for a, b in zip(expected, display['position_render_m'])) < 1e-5
        old_guard = guard(s)
        s.save()
        manifest_path = s.directory / 'latest.json'
        manifest = json.loads(manifest_path.read_text())
        s.sim.integrate(s.sim.t + .01)
        s.load()
        assert s.instruments == saved_definitions and physical(s)['bodies'] == before['bodies']
        assert s.edit_token != old_guard['edit_token'] and s.atlas_initial == original
        restored = Session(s.directory, 2)
        restored.load()
        assert restored.instruments == saved_definitions
        assert restored.state()['bodies'] == s.state()['bodies']
        mutations = [lambda m: m['instruments']['probes'][0].update(name='without event'),
                     lambda m: m['instruments'].update(revision=True),
                     lambda m: m['instruments']['issued_ids'].append(m['instruments']['issued_ids'][0]),
                     lambda m: m['instruments']['probes'][1].update(body_id='not-issued'),
                     lambda m: m['instruments']['probes'][0].update(position_m=[True, 0, 0]),
                     lambda m: m['instruments']['events'].pop()]
        for mutation in mutations:
            bad = copy.deepcopy(manifest)
            mutation(bad)
            bad['manifest_sha256'] = digest({k: v for k, v in bad.items() if k != 'manifest_sha256'})
            manifest_path.write_text(json.dumps(bad))
            baseline = copy.deepcopy(s.state())
            try:
                s.load()
            except ValueError:
                corrupt += 1
            else:
                raise AssertionError('Corrupt instruments installed')
            assert s.state() == baseline
        missing = copy.deepcopy(manifest)
        missing.pop('instruments')
        missing['saved_generation']['model_version'] = '3.5.0'
        missing['manifest_sha256'] = digest({k: v for k, v in missing.items() if k != 'manifest_sha256'})
        manifest_path.write_text(json.dumps(missing))
        baseline = copy.deepcopy(s.state())
        try:
            s.load()
        except ValueError:
            corrupt += 1
        else:
            raise AssertionError('Missing new-format instruments accepted')
        assert s.state() == baseline
        # A real3.4-shaped checkpoint has no instrument block and migrates empty.
        missing['saved_generation']['model_version'] = '3.4.0'
        missing['manifest_sha256'] = digest({k: v for k, v in missing.items() if k != 'manifest_sha256'})
        manifest_path.write_text(json.dumps(missing))
        s.load()
        assert s.instruments['probes'] == [] and s.instruments['revision'] == 0
        manifest_path.write_text(json.dumps(manifest))
        s.load()
        if len(s.registry) > 1:
            s.remove_body({**guard(s), 'body': followed})
            assert s.sample_instruments(guard(s))['readings'][1]['available'] is False
            s.save()
            s.load()
            assert s.instruments['probes'][1]['body_id'] == followed
        s.restart_seed()
        assert s.instruments == {'schema': 1, 'revision': 0, 'probes': [], 'issued_ids': [], 'events': []}
        results.append({'kind': kind, 'definitions_checkpoint_exact': True,
                        'configure_and_sample_physics_binary_and_pointer_exact': True,
                        'renderer_positions_match_SI_transform': True,
                        'removed_follow_target_not_reassigned': True, 'legacy3_4_migrates_empty': True})
report = {'status': 'verified_uninstalled_session_candidate_not_product', 'models': results,
          'stale_guards_rejected_without_mutation': invalid,
          'resealed_corruption_or_missing_new_block_rejected_atomically': corrupt,
          'candidate_session_sha256': hashlib.sha256((ROOT / 'output/c211-staging/session.py').read_bytes()).hexdigest()}
(ROOT / 'evidence/instruments-session-prototype-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
