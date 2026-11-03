"""Installed gravity maps: exact shared readings, atomic persistence and cost."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from session import Session
from body_registry import digest
from atlas import states
from atlas_import import prepare, experiment_subset
import field_layers
import gravity_field
import field_scene


def guard(s):
    return {'system_id': s.system_id, 'edit_token': s.edit_token, 'revision': s.revision,
            'expected_time': s.sim.t, 'frame': s.contract()['frame'], 'fields_revision': s.field_layers['revision']}


def physical(s):
    value = copy.deepcopy(s.state())
    value.pop('field_layers')
    return value


results, rejected, corrupt = [], 0, 0
with tempfile.TemporaryDirectory() as temp:
    for kind in ('fixture', 'atlas', 'single_mass', 'p128'):
        s = Session(Path(temp) / kind, 128 if kind == 'p128' else 32)
        if kind == 'atlas':
            s.import_atlas(prepare(experiment_subset(states(utc='2026-10-11T12:00:00'))))
        elif kind == 'single_mass':
            s.new_system({**guard(s), 'name': 'Massa isolada', 'mass_kg': 1e25,
                          'position_m': [3e9, -2e9, 7e9], 'velocity_m_s': [0, 0, 0]})
        s.sim.integrate(.01)
        before = physical(s)
        s.save()
        pointer = (s.directory / 'latest.json').read_bytes()
        s.sim.save_to_file(str(s.directory / 'before.bin'))
        cfg = field_layers.defaults()
        cfg.update(center_mode='follow', body_id=s.registry[0]['id'],
                   cut_orientation_deg=[30., -20., 15.], cut_offset_m=3e9,
                   shell_count=128 if kind == 'p128' else 96, cut_resolution=21 if kind == 'p128' else 17)
        s.configure_fields({**guard(s), 'settings': cfg})
        result = s.sample_fields(guard(s))
        assert physical(s) == before and result['source_ids'] == [b['id'] for b in s.registry]
        assert result['fields_revision'] == 1 and result['settings'] == cfg
        s.sim.save_to_file(str(s.directory / 'after.bin'))
        assert (s.directory / 'before.bin').read_bytes() == (s.directory / 'after.bin').read_bytes()
        assert (s.directory / 'latest.json').read_bytes() == pointer
        bodies = s._bodies(s.sim, s.registry)
        checked = 0
        for layer in ('shell', 'cut'):
            for reading in result[layer]['samples']:
                expected = gravity_field.evaluate(bodies, reading['position_m'])
                assert reading['valid'] and 'sources' not in reading
                for key in ('acceleration_m_s2', 'acceleration_norm_m_s2', 'potential_J_kg', 'tidal_tensor_s_2'):
                    assert reading[key] == expected[key]
                checked += 1
        u, v, normal = field_layers.axes(cfg['cut_orientation_deg'])
        for a, b in ((u, v), (v, normal), (normal, u)):
            assert abs(math.hypot(*a) - 1) < 1e-14 and abs(math.fsum(x * y for x, y in zip(a, b))) < 1e-14
        code, render = field_scene.prepare(result, s.atlas_initial)
        assert len(render['nodes']) <= 7 and len(render['meshes']) >= 3
        assert 'openspace.addSceneGraphNode' in code and render['meshes'][0]['segment_count'] == cfg['shell_count']
        # Export must carry an independently reproducible global SI source snapshot.
        encoded_bytes = len(json.dumps(result, separators=(',', ':'), allow_nan=False).encode())
        assert encoded_bytes < 650000
        baseline = copy.deepcopy(s.state())
        invalid_requests = []
        for key, value in [('system_id', 'old'), ('edit_token', 'old'), ('revision', -1),
                           ('expected_time', s.sim.t + 1), ('frame', 'wrong'),
                           ('fields_revision', True), ('fields_revision', 0)]:
            invalid_requests.append({**guard(s), key: value})
        for request in invalid_requests:
            try:
                s.sample_fields(request)
            except ValueError:
                rejected += 1
            else:
                raise AssertionError('Old field guard accepted')
            assert s.state() == baseline
        for key, value in [('center_m', [True, 0, 0]), ('shell_radius_m', float('nan')),
                           ('shell_count', 512), ('cut_resolution', 11), ('cut_offset_m', 1e18),
                           ('cut_orientation_deg', [0, 0, float('inf')]), ('magnitude_scale', 'signed_log'),
                           ('potential_levels_J_kg', [1, 1]), ('body_id', 'not-issued')]:
            bad = copy.deepcopy(cfg)
            bad[key] = value
            try:
                s.configure_fields({**guard(s), 'settings': bad})
            except ValueError:
                rejected += 1
            else:
                raise AssertionError('Invalid map configuration accepted')
            assert s.state() == baseline
        overflow = copy.deepcopy(cfg)
        overflow.update(center_mode='fixed', body_id=None, center_m=[1e17, 0, 0])
        try:
            s.configure_fields({**guard(s), 'settings': overflow})
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('Out-of-domain geometry accepted')
        assert s.state() == baseline
        s.save()
        path = s.directory / 'latest.json'
        manifest = json.loads(path.read_text())
        expected_definitions = copy.deepcopy(s.field_layers)
        old_token = s.edit_token
        s.sim.integrate(s.sim.t + .01)
        s.load()
        assert s.field_layers == expected_definitions and s.edit_token != old_token
        assert s.state()['bodies'] == before['bodies'] and s.conservation_reference == before['conservation']['reference']
        for mutation in (lambda m: m['field_layers']['settings'].update(cut_offset_m=9e9),
                         lambda m: m['field_layers'].update(revision=True),
                         lambda m: m['field_layers']['events'].pop(),
                         lambda m: m['field_layers']['events'][0].update(time=m['field_layers']['events'][0]['time'] + 1),
                         lambda m: m.pop('field_layers'), lambda m: m.pop('instruments')):
            bad = copy.deepcopy(manifest)
            mutation(bad)
            bad['manifest_sha256'] = digest({k: v for k, v in bad.items() if k != 'manifest_sha256'})
            path.write_text(json.dumps(bad))
            current = copy.deepcopy(s.state())
            try:
                s.load()
            except ValueError:
                corrupt += 1
            else:
                raise AssertionError('Resealed corrupt field checkpoint installed')
            assert s.state() == current
        legacy = copy.deepcopy(manifest)
        legacy.pop('field_layers')
        legacy['saved_generation']['model_version'] = '3.5.0'
        legacy['manifest_sha256'] = digest({k: v for k, v in legacy.items() if k != 'manifest_sha256'})
        path.write_text(json.dumps(legacy))
        s.load()
        assert s.field_layers == field_layers.empty() and s.state()['bodies'] == before['bodies']
        path.write_text(json.dumps(manifest))
        s.load()
        if len(s.registry) > 1:
            s.remove_body({**guard(s), 'body': cfg['body_id']})
            current = copy.deepcopy(s.state())
            try:
                s.sample_fields(guard(s))
            except ValueError as error:
                assert 'removido' in str(error)
            else:
                raise AssertionError('Removed center silently reassigned')
            assert s.state() == current
            s.save()
            s.load()
            assert s.field_layers['settings']['body_id'] == cfg['body_id']
        s.restart_seed()
        assert s.field_layers == field_layers.empty()
        results.append({'kind': kind, 'source_count': len(bodies), 'sample_count': checked,
                        'evaluation_ms': result['evaluation_ms'], 'compact_full_reading_bytes': encoded_bytes,
                        'same_evaluator_values_exact': True, 'physics_binary_pointer_unchanged': True,
                        'checkpoint_and_legacy3_5_exact': True, 'removed_center_identity_preserved': True})

# A singular center has a real gap. Uniform potential has no invented unique curve.
s = Session(Path(tempfile.gettempdir()) / 'cosmos2-unused-field-tests', 2)
s.new_system({**guard(s), 'name': 'Isolada', 'mass_kg': 1e25, 'position_m': [0, 0, 0], 'velocity_m_s': [0, 0, 0]})
cfg = field_layers.defaults()
cfg.update(shell_enabled=False, potential_levels_J_kg=[-1e8])
s.configure_fields({**guard(s), 'settings': cfg})
result = s.sample_fields(guard(s))
assert result['cut']['samples'][144]['valid'] is False and len(result['cut']['equipotentials']['invalid_cells']) == 4
assert field_scene.color_bin(0., {'minimum': 0., 'maximum': 1., 'minimum_positive': 1., 'scale': 'log'}) == 0
report = {'generation': '3.6.0', 'models': results, 'invalid_or_old_commands_rejected_atomically': rejected,
          'resealed_corrupt_checkpoints_rejected_atomically': corrupt, 'singular_center_creates_four_gap_cells': True,
          'scope': 'Gravity maps/probes; no J2/material tides/full C2-11 acceptance',
          'module_sha256': hashlib.sha256((ROOT / 'app/field_layers.py').read_bytes()).hexdigest()}
(ROOT / 'evidence/field-layers-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
