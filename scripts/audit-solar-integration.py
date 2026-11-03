"""Audit preserved IS-1/2 series and recheck persistence after an interrupted runner."""
from pathlib import Path
import argparse
import json
import math
import sys
import traceback
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is12-solar-product/app'
sys.path.insert(0, str(APP))
from solar_contract import sha
from physics import PHYSICAL_SCALE as U
from session import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label.')
    receipt = ROOT / ('evidence/is12-solar-audit-' + args.label + '.json')
    if receipt.exists():
        raise FileExistsError(receipt)
    source_path = ROOT / ('evidence/is12-solar-check-' + args.label + '.json')
    source = json.loads(source_path.read_text(encoding='utf-8'))
    folder = ROOT / ('output/is12-solar-check-' + args.label)
    report = {'schema': 1, 'input_receipt': source_path.relative_to(ROOT).as_posix(),
              'input_receipt_sha256': sha(source_path), 'runner_completed_flag': source['completed'],
              'scope': 'Independent audit of saved 30-day arrays plus executed checkpoint/branch/restart checks. Does not rewrite or complete the interrupted runner receipt; no UI/performance acceptance.',
              'checks': {}, 'accepted': False}
    try:
        assert all(sha(ROOT / p) == value for p, value in source['source_sha256'].items())
        assert sha(ROOT / source['source_archive']) == source['source_archive_sha256']
        data_path = ROOT / source['propagation']['series_file']
        assert sha(data_path) == source['propagation']['series_sha256']
        data = json.loads(data_path.read_text(encoding='utf-8'))
        seconds = np.array(data['seconds'])
        series, refined, independent = [np.array(data[name], dtype=float) for name in
            ['canonical_IAS15', 'canonical_IAS15_refined', 'canonical_DOP853']]
        assert np.array_equal(seconds, np.arange(0, 30*86400+1, 21600))
        assert all(x.shape == (121, 4, 6) and np.all(np.isfinite(x)) for x in [series, refined, independent])
        initial = json.loads((folder / 'initial.json').read_text(encoding='utf-8'))
        expected_phase = np.array([b['position'] + b['velocity'] for b in initial['bodies']])
        assert np.array_equal(series[0], expected_phase)
        assert np.array_equal(series[0], refined[0])
        limits = source['limits_before_execution']
        values = {'position_component_m': float(np.max(np.abs(series[:, :, :3] - independent[:, :, :3])) * U['length_unit_m']),
                  'velocity_component_m_s': float(np.max(np.abs(series[:, :, 3:] - independent[:, :, 3:])) * U['velocity_unit_m_s']),
                  'refinement_position_component_m': float(np.max(np.abs(series[:, :, :3] - refined[:, :, :3])) * U['length_unit_m'])}
        for k, value in values.items():
            assert value <= limits[k], (k, value)
        report['checks']['whole_series_errors'] = values
        masses = np.array([b['mass'] for b in initial['bodies']])
        checks = {}
        for name, phase in [('production', series), ('refined', refined), ('independent', independent)]:
            r, v = phase[:, :, :3], phase[:, :, 3:]
            energies, momenta, angular = [], [], []
            for positions, velocities in zip(r, v):
                kinetic = math.fsum(.5 * masses[i] * float(np.dot(velocities[i], velocities[i])) for i in range(4))
                potential = math.fsum(-masses[i]*masses[j] / float(np.linalg.norm(positions[j]-positions[i]))
                                      for i in range(4) for j in range(i+1, 4))
                energies.append(kinetic + potential)
                momenta.append([math.fsum(masses[i]*velocities[i, k] for i in range(4)) for k in range(3)])
                angular.append([math.fsum(masses[i]*np.cross(positions[i], velocities[i])[k] for i in range(4)) for k in range(3)])
            energies, momenta, angular = map(np.array, [energies, momenta, angular])
            pscale = math.fsum(masses[i]*np.linalg.norm(v[0, i]) for i in range(4))
            lscale = math.fsum(masses[i]*np.linalg.norm(np.cross(r[0, i], v[0, i])) for i in range(4))
            checks[name] = {'relative_energy_drift': float(np.max(np.abs(energies - energies[0])) / abs(energies[0])),
                            'normalized_linear_momentum_drift': float(np.max(np.linalg.norm(momenta - momenta[0], axis=1)) / pscale),
                            'normalized_angular_momentum_drift': float(np.max(np.linalg.norm(angular - angular[0], axis=1)) / lscale)}
            for k, value in checks[name].items():
                assert value <= limits[k], (name, k, value)
        report['checks']['recomputed_balances'] = checks
        assert len(source['checks']['transactional_refusals']) == 17
        assert len(source['checks']['all_reciprocal_source_accelerations']) == 12
        report['checks']['prior_refusals_and_pair_accelerations_preserved'] = True

        session = Session(folder / 'sessions')
        session.load()
        def phase(sim):
            return [[p.x, p.y, p.z, p.vx, p.vy, p.vz] for p in sim.particles]
        assert np.array_equal(phase(session.sim), series[-1])
        assert session.atlas_initial == initial
        assert session.restoration['status'] == 'same_generation'
        branch = next((folder / 'sessions/branches').glob('*/branch.json'))
        record = json.loads(branch.read_text(encoding='utf-8'))
        session.integrate(31*86400/U['time_unit_s'])
        session.load_branch({'system_id': session.system_id, 'edit_token': session.edit_token,
                             'revision': session.revision, 'expected_time': session.sim.t,
                             'frame': session.contract()['frame'], 'branch_id': record['id']})
        assert np.array_equal(phase(session.sim), series[-1]) and session.atlas_initial == initial
        session.restart_seed()
        assert np.array_equal(phase(session.sim), series[0]) and session.atlas_initial == initial
        report['checks']['reexecuted_exact_checkpoint_branch_restart'] = True
        legacy_path = folder / 'legacy-atlas-import-check.json'
        legacy = json.loads(legacy_path.read_text(encoding='utf-8'))
        assert len(legacy['epoch_clones']) == 5 and legacy['invalid_states_rejected_without_mutation'] == 9
        assert legacy['independent_DOP853_24h_max_position_difference_m'] <= 10
        assert all(legacy[k] is True for k in ['checkpoint_exact_bodies_and_source', 'checkpoint_corruption_refused',
                                             'source_not_changed_by_intervention', 'changed_generation_reported'])
        report['checks']['preserved_legacy_suite'] = {'receipt': legacy_path.relative_to(ROOT).as_posix(), 'sha256': sha(legacy_path)}
        baseline = json.loads((ROOT / 'evidence/is12-solar-candidate-prepared-20261023.json').read_text())
        assert all(sha(ROOT/p) == value for p, value in baseline['base_files_sha256'].items())
        assert sha(ROOT / 'user/sessions/latest.json') == baseline['owner_pointer_sha256']
        assert sha(ROOT / 'output/session.json') == baseline['session_pointer_sha256']
        report['checks']['installed_owner_and_session_pointer_preserved'] = True
        report['accepted'] = True
    except Exception:
        report['failure'] = traceback.format_exc()
    report['script_sha256'] = sha(Path(__file__))
    receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
