"""Independent ODE and analytic checks for bounded frozen planetary field lines."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/is3-body-lines-staging'
APP = ROOT/'output/is3-body-vector-product/app'
sys.path[:0] = [str(STAGE), str(APP)]
import numpy as np
import scipy
from scipy.integrate import solve_ivp
import body_field_lines as lines
import geomagnetism as igrf

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid evidence label.')
    folder = ROOT/('output/is3-lines-check-'+args.label)
    receipt = ROOT/('evidence/is3-lines-check-'+args.label+'.json')
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve earlier evidence.')
    fixture = ROOT/'evidence/is3-vector-profile-20261024b.json'
    paths = [STAGE/'body_field_lines.py', Path(__file__).resolve(), ROOT/'IS-3-LINHAS-CONTRATO.md', fixture,
             APP/'geomagnetism.py', APP/'jrm33.py', APP/'jrm33-coefficients.json', ROOT/'data/science/igrf14coeffs.txt']
    folder.mkdir()
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in paths:
            archive.write(p, p.relative_to(ROOT).as_posix())
    owner = sha(ROOT/'user/sessions/latest.json')
    report = {'schema': 1, 'accepted': False, 'completed': False, 'source_sha256': hashes,
              'scipy_version': scipy.__version__, 'limits_before_execution': {
                  'ODE_max_component_error_R': 2e-6, 'refinement_max_component_error_R': 2e-6,
                  'dipole_relative_invariant_error': 2e-6, 'uniform_error_R': 1e-12,
                  'geodetic_altitude_error_m': 1e-6, 'geodetic_latitude_error_deg': 1e-10},
              'checks': {}, 'model_cases': []}
    def persist():
        receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    persist()
    try:
        alt_error = lat_error = 0.
        for lat in [-90., -89.999, -60., -23.55, 0., 30., 89.999, 90.]:
            for lon in [-180., -46.63, 0., 90., 180.]:
                for height in [0., 1., 1000., 500000., 1000000.]:
                    p = igrf.geodetic_position(lat, lon, height)
                    found = lines.geodetic(p)
                    alt_error = max(alt_error, abs(found[2]-height))
                    lat_error = max(lat_error, abs(found[0]-lat))
        assert alt_error <= 1e-6 and lat_error <= 1e-10
        report['checks']['geodetic_200_points'] = {'height_error_m': alt_error, 'latitude_error_deg': lat_error}

        def compare(field, clearance, seed, radius, direction, **options):
            original = lines.trace(field, clearance, seed, radius, direction, **options)
            arc = np.array(original['arc_m'])/radius
            # Keep the independent solver away from the boundary and compare
            # every product vertex in the first95% of its available arc.
            indices = np.where(arc <= arc[-1]*.95)[0]
            assert len(indices) >= 2, original['termination']
            target = arc[indices]
            oracle_calls = 0
            def rhs(s, y):
                nonlocal oracle_calls
                point = (y*radius).tolist()
                assert clearance(point) >= 0, 'Oracle attempted external sample.'
                b = np.asarray(field(point))
                oracle_calls += 1
                return direction*b/np.linalg.norm(b)
            oracle = solve_ivp(rhs, [0., float(target[-1])], np.array(seed)/radius,
                               method='DOP853', t_eval=target, rtol=1e-11, atol=1e-12,
                               max_step=min(.01, float(target[-1])/10))
            assert oracle.success and len(oracle.t) == len(target)
            raw = np.asarray(original['points_m'])[indices]/radius
            error = float(np.max(np.abs(raw-oracle.y.T)))
            assert error <= 2e-6, error
            refined = lines.trace(field, clearance, seed, radius, direction,
                                  **{**options, 'tolerance': 1e-11})
            refined_arc = np.asarray(refined['arc_m'])/radius
            upto = float(min(target[-1], refined_arc[-1]*.95))
            # Independent dense output measures the refined trace at its own
            # vertices; interpolation of coarse polylines would add display error.
            valid = np.where(refined_arc <= upto)[0]
            check = solve_ivp(rhs, [0., float(refined_arc[valid][-1])], np.array(seed)/radius,
                              method='DOP853', t_eval=refined_arc[valid], rtol=1e-11, atol=1e-12,
                              max_step=min(.01, float(refined_arc[valid][-1])/10))
            refined_error = float(np.max(np.abs(np.asarray(refined['points_m'])[valid]/radius-check.y.T)))
            assert check.success and refined_error <= 2e-6
            # Triangle inequality gives a conservative common-curve refinement
            # bound against the same independently integrated solution.
            assert error+refined_error <= 2e-6
            assert all(clearance(p) >= 0 for p in original['points_m'])
            return original, {'ODE_error_R': error, 'refined_ODE_error_R': refined_error,
                              'refinement_bound_R': error+refined_error, 'oracle_evaluations': oracle_calls}

        uniform = lambda p: [2., -3., 6.]
        seed = [1., 2., 3.]
        uniform_line = lines.trace(uniform, lambda p: 10., seed, 1., max_arc=.6)
        target = np.asarray(seed)+np.asarray(uniform_line['arc_m'])[:, None]*np.array([2., -3., 6.])/7
        uniform_error = float(np.max(np.abs(np.asarray(uniform_line['points_m'])-target)))
        assert uniform_error <= 1e-12 and uniform_line['termination'] == 'arc_limit'
        report['checks']['uniform'] = {'error_R': uniform_error}
        def dipole(p):
            x, y, z = p
            r = math.hypot(*p)
            return [3*x*z/r**5, 3*y*z/r**5, (3*z*z-r*r)/r**5]
        shell = lambda p: min(math.hypot(*p)-1., 3.-math.hypot(*p))
        dipoles = []
        for direction in [-1, 1]:
            curve, checked = compare(dipole, shell, [1.5, 0., .3], 1., direction)
            invariant = [math.hypot(*p)**3/(p[0]**2+p[1]**2) for p in curve['points_m']]
            error = max(abs(v/invariant[0]-1) for v in invariant)
            assert error <= 2e-6
            dipoles.append({**checked, 'dipole_invariant_relative_error': error})
        report['checks']['analytic_dipole_both_directions'] = dipoles
        q = np.array([[0., -1., 0.], [0., 0., -1.], [1., 0., 0.]])
        assert abs(np.linalg.det(q)-1) < 1e-15
        base = lines.trace(dipole, shell, [1.5, 0., .3], 1.)
        rotated = lines.trace(lambda p: (q@dipole((q.T@p).tolist())).tolist(), shell,
                              (q@np.array([1.5, 0., .3])).tolist(), 1.)
        covariance = float(np.max(np.abs(np.asarray(rotated['points_m'])-np.asarray(base['points_m'])@q.T)))
        assert covariance <= 1e-12
        reversed_field = lines.trace(lambda p: [-b for b in dipole(p)], shell, [1.5, 0., .3], 1.)
        negative = lines.trace(dipole, shell, [1.5, 0., .3], 1., -1)
        assert reversed_field['points_m'] == negative['points_m']
        null = lines.trace(lambda p: [0., 0., 0.], shell, [1.5, 0., .3], 1.)
        assert null['termination'] == 'null_field' and len(null['points_m']) == 1
        boundary = lines.trace(lambda p: [1., 0., 0.], shell, [3., 0., 0.], 1.)
        assert boundary['termination'] == 'domain_boundary' and len(boundary['points_m']) == 1
        report['checks']['rotation_sign_null_boundary'] = {'covariance_error_R': covariance, 'passed': True}

        profile = json.loads(fixture.read_text(encoding='utf-8'))
        readings = [row['frozen_layer']['reading'] for row in profile['runs']]
        adapter_error = 0.
        earth_model = lines.Model(readings[0])
        for lat in [-90., -45., 0., 45., 90.]:
            for lon in [-180., 0., 90.]:
                for height in [0., 500000., 1000000.]:
                    expected = igrf.field_at(earth_model.year, lat, lon, height)
                    found = earth_model.field(expected['position_ecef_m'])
                    adapter_error = max(adapter_error, max(abs(x-y) for x, y in zip(found, expected['field_ecef_T'])))
        assert adapter_error < 2e-18
        report['checks']['new_cartesian_IGRF_adapter_45_points'] = {'maximum_component_error_T': adapter_error}
        configurations = []
        for year in [2020., readings[0]['epoch']['decimal_UTC_year']]:
            r = copy.deepcopy(readings[0]); r['epoch']['decimal_UTC_year'] = year
            for lat, lon in [(0., 0.), (-45., 90.), (90., 0.)]:
                configurations.append((r, list(igrf.geodetic_position(lat, lon, 500000.))))
        for degree in [1, 13, 18]:
            r = copy.deepcopy(readings[1]); r['degree'] = degree
            for seed in [[1.5*71492000., 0., 0.], [0., -1.5*71492000., .3*71492000.], [0., 0., 1.5*71492000.]]:
                configurations.append((r, seed))
        for reading, seed in configurations:
            model = lines.Model(reading)
            for direction in [-1, 1]:
                start = time.perf_counter()
                curve, checked = compare(model.field, model.clearance, seed, model.radius, direction)
                report['model_cases'].append({'model': model.name, 'degree': model.degree,
                    'epoch': reading['epoch'], 'seed_m': seed, 'direction': direction, **checked,
                    'termination': curve['termination'], 'vertices': len(curve['points_m']),
                    'endpoint_clearance_m': curve['endpoint_clearance_m'],
                    'seconds': time.perf_counter()-start})
            persist()
        bundles = []
        for reading in readings:
            start = time.perf_counter(); bundle = lines.bundle(reading)
            path = folder/(bundle['model']+'-bundle.json')
            path.write_text(json.dumps(bundle, indent=2, allow_nan=False)+'\n', encoding='utf-8')
            bundles.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path),
                            'seconds': time.perf_counter()-start, 'curves': len(bundle['lines'])})
        report['bundles'] = bundles
        refusals = 0
        invalid = [{'seed_m': [True, 0., 0.]}, {'seed_m': [math.nan, 0., 0.]},
                   {'radius_m': True}, {'direction': True}, {'direction': 0}, {'max_arc': 17.},
                   {'max_step': .05}, {'tolerance': 0.}, {'min_step': .1},
                   {'max_steps': 0}, {'max_steps': 2049}, {'max_evaluations': 0},
                   {'field': lambda p: [math.inf, 0., 0.]}, {'field': lambda p: [0., 0.]},
                   {'clearance': lambda p: math.nan}, {'seed_m': [4., 0., 0.]},
                   {'max_evaluations': 1}]
        for changes in invalid:
            options = {'field': dipole, 'clearance': shell, 'seed_m': [1.5, 0., .3], 'radius_m': 1.}
            try:
                lines.trace(**{**options, **changes})
            except ValueError:
                refusals += 1
            else:
                raise AssertionError(('Invalid configuration accepted', str(changes)))
        assert refusals == len(invalid)
        report['checks']['invalid_inputs_and_effort_guards'] = refusals
        assert sha(ROOT/'user/sessions/latest.json') == owner
        assert all(sha(ROOT/name) == digest for name, digest in hashes.items())
        report.update(accepted=True, completed=True, owner_and_executed_sources_preserved=True,
            scope='Bounded frozen internal-model integral curves in staging only. ODE/geometry accuracy is not observational uncertainty, native integration or performance acceptance.')
    except Exception:
        report['failure'] = traceback.format_exc()
    persist()
    print(json.dumps({k: report[k] for k in ['accepted', 'completed', 'checks']}
                     | {'cases': len(report['model_cases']), 'failure': report.get('failure')}, ensure_ascii=False))
    return 0 if report['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
