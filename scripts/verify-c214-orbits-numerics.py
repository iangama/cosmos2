"""Sealed native CPU cohort: proper-time IVP versus independent anomaly quadrature and Kepler/Cartesian reference."""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback
import zipfile

import numpy as np
import scipy
from scipy.integrate import quad, solve_ivp

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'output/c214-orbits-staging/timelike_orbits.py'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('c214_timelike_under_test', MODULE)
product = importlib.util.module_from_spec(spec)
spec.loader.exec_module(product)


def reference(eccentricity, kappa):
    """Original p in units GM/c², not the production IVP's scaled constants or RHS."""
    p = 2/kappa

    def parts(chi):
        cosine = math.cos(chi)
        radial = 1+eccentricity*cosine
        root = math.sqrt((p-3-eccentricity**2)/(p-6-2*eccentricity*cosine))
        tau = root/radial**2
        tt = math.sqrt(((p-2)**2-4*eccentricity**2)/(p-6-2*eccentricity*cosine))*math.sqrt(p)
        tt /= (p-2-2*eccentricity*cosine)*radial**2
        return tau, tt

    proper, proper_error = quad(lambda chi: parts(chi)[0], 0, 2*math.pi, epsabs=2e-12, epsrel=2e-13)
    coordinate, coordinate_error = quad(lambda chi: parts(chi)[1], 0, 2*math.pi, epsabs=2e-12, epsrel=2e-13)
    advance, advance_error = quad(lambda chi: math.expm1(-.5*math.log1p(-(6+2*eccentricity*math.cos(chi))/p)),
                                  0, 2*math.pi, epsabs=1e-18, epsrel=2e-13)
    return dict(proper=proper, coordinate=coordinate, advance=advance,
                quadrature_error=dict(proper=proper_error, coordinate=coordinate_error, advance=advance_error))


def check_result(result, expected):
    cfg, m = result['configuration'], result['measurements']
    cycles, e = cfg['radial_cycles'], cfg['eccentricity']
    assert result['completed'] and m['apsidal_defined'] and len(result['pericenters']) == cycles+1 and len(result['apocenters']) == cycles
    error = abs(m['apsidal_advance_rad_per_cycle']-expected['advance'])
    assert error <= 5e-10+5e-7*abs(expected['advance']), ('precession', error, expected['advance'])
    for key, target in [('radial_period_coordinate_scaled', expected['coordinate']), ('radial_period_proper_scaled', expected['proper'])]:
        assert abs(m[key]/target-1) <= 2e-9, (key, m[key], target)
    assert m['maximum_radial_invariant_residual'] <= 2e-10 and m['maximum_metric_residual'] <= 2e-12
    rp, ra = 1/(1+e), 1/(1-e)
    assert all(abs(row['radius_scaled']/rp-1) <= 2e-9 for row in result['pericenters'])
    assert all(abs(row['radius_scaled']/ra-1) <= 2e-9 for row in result['apocenters'])
    gr, newton = result['gr'], result['newton']
    assert np.max(np.abs(np.array(gr['positions_scaled'][0])-newton['positions_scaled'][0])) <= 2e-13
    assert np.max(np.abs(np.array(gr['velocities_coordinate_scaled'][0])-newton['velocities_coordinate_scaled'][0])) <= 2e-13
    assert newton['maximum_energy_residual'] <= 2e-12 and newton['maximum_angular_residual'] <= 2e-12
    assert np.all(np.diff(result['coordinate_time_scaled']) > 0) and np.all(np.diff(result['proper_time_scaled']) > 0)
    assert 0 < m['average_proper_over_coordinate'] < 1 and all(value > 0 for value in result['clock_lag_scaled'][1:])
    assert np.max(np.array(gr['local_radial_speed_over_c'])**2+np.array(gr['local_transverse_speed_over_c'])**2) < 1
    return dict(precession_absolute_error_rad=error,
                coordinate_period_relative_error=abs(m['radial_period_coordinate_scaled']/expected['coordinate']-1),
                proper_period_relative_error=abs(m['radial_period_proper_scaled']/expected['proper']-1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / f'output/c214-orbits-numerics-{args.label}'
    out = ROOT / f'evidence/c214-orbits-numerics-{args.label}.json'
    assert not folder.exists() and not out.exists(), 'Preserve original cohort'
    names = ['scripts/verify-c214-orbits-numerics.py', 'output/c214-orbits-staging/timelike_orbits.py',
             'C2-14-ORBITAS-CONTRATO-20261114.md', 'C2-14-ORBITAS-PREPARACAO-20261114.md']
    sources = {name: sha(ROOT / name) for name in names}
    recipes = [dict(mu_m3_s2=1.3271244e21, semi_latus_rectum_rs=1/k, eccentricity=e, radial_cycles=1,
                    output_samples=257, source_radius_rs=1., orientation=1)
               for e in [.05, .2, .6, .8] for k in [1e-3, 1e-4, 1e-6, 1e-8]]
    recipes.extend([dict(recipes[5], radial_cycles=8, output_samples=1025),
                    dict(recipes[13], radial_cycles=16, output_samples=4097),
                    dict(recipes[3], radial_cycles=16, output_samples=257),
                    dict(recipes[8], radial_cycles=2, orientation=-1)])
    folder.mkdir()
    (folder / 'recipe-before-execution.json').write_text(json.dumps(dict(recipes=recipes, sources=sources), indent=2)+'\n', encoding='utf8')
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    answer = dict(accepted=False, completed=False, source_sha256=sources, cases=[], refusals=[], checks=[],
                  python=sys.version, numpy=np.__version__, scipy=scipy.__version__, platform=sys.platform,
                  scope='Native CPU science only. No service, UI, persistence or scene/performance acceptance.')
    began = time.perf_counter()

    def refusal(name, call, exception=ValueError):
        try:
            call()
        except exception as error:
            answer['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid configuration/run accepted: '+name)

    try:
        for index, recipe in enumerate(recipes):
            expected = reference(recipe['eccentricity'], 1/recipe['semi_latus_rectum_rs'])
            first = product.experiment(recipe)
            (folder / f'case-{index:02d}-base.json').write_text(json.dumps(first, allow_nan=False)+'\n', encoding='utf8')
            metric = check_result(first, expected)
            refined = product.experiment(recipe, refined=True)
            (folder / f'case-{index:02d}-refined.json').write_text(json.dumps(refined, allow_nan=False)+'\n', encoding='utf8')
            check_result(refined, expected)
            for key in ['radial_period_coordinate_scaled', 'radial_period_proper_scaled']:
                assert abs(first['measurements'][key]/refined['measurements'][key]-1) <= 2e-9
            answer['cases'].append(dict(recipe=recipe, expected=expected, errors=metric, measurements=first['measurements'],
                                        solver=first['solver'], refined_solver=refined['solver'],
                                        base_sha256=sha(folder / f'case-{index:02d}-base.json'),
                                        refined_sha256=sha(folder / f'case-{index:02d}-refined.json')))
            print(json.dumps(dict(case=index, e=recipe['eccentricity'], p_rs=recipe['semi_latus_rectum_rs'], cycles=recipe['radial_cycles'],
                                  precession=first['measurements']['apsidal_advance_rad_per_cycle'], errors=metric)), flush=True)
        # A separate Cartesian ODE checks the closed Newton reference at common coordinate times.
        fixture = product.experiment(recipes[8])
        tt = np.asarray(fixture['coordinate_time_scaled'])
        initial = fixture['newton']['positions_scaled'][0][:2]+fixture['newton']['velocities_coordinate_scaled'][0][:2]

        def cartesian(_, y):
            r = math.hypot(y[0], y[1])
            return [y[2], y[3], -y[0]/r**3, -y[1]/r**3]

        independent = solve_ivp(cartesian, (0, tt[-1]), initial, method='DOP853', rtol=1e-12, atol=1e-14,
                                t_eval=tt, max_step=tt[-1]/256)
        assert independent.success and np.max(np.abs(independent.y[:2].T-np.asarray(fixture['newton']['positions_scaled'])[:, :2])) <= 2e-9
        answer['checks'].append('Closed Kepler reference versus independent Cartesian Newton IVP on the same coordinate grid')
        circle = product.experiment(dict(eccentricity=0., radial_cycles=2))
        cm = circle['measurements']; k = circle['constants']['kappa']
        assert cm['apsidal_advance_rad_per_cycle'] is None and not cm['apsidal_defined'] and not circle['pericenters']
        assert cm['radial_period_coordinate_scaled'] is None and cm['radial_period_proper_scaled'] is None
        assert abs(cm['average_proper_over_coordinate']/math.sqrt(1-1.5*k)-1) <= 2e-14
        assert np.max(np.abs(np.asarray(circle['gr']['radius_scaled'])-1)) <= 2e-14
        answer['checks'].append('Circular clock and phase; no fabricated radial period or apsidal measurement')
        small = product.experiment(recipes[5]); big = product.experiment(dict(recipes[5], mu_m3_s2=recipes[5]['mu_m3_s2']*10))
        assert small['gr'] == big['gr'] and small['measurements'] == big['measurements']
        for key in ['length_m', 'time_s', 'schwarzschild_radius_m', 'source_radius_m']:
            assert abs(big['units'][key]/small['units'][key]/10-1) <= 2e-12
        answer['checks'].append('Mass scaling preserves dimensionless trajectories/clocks; physical lengths and times scale by10')
        mirror = product.experiment(dict(recipes[5], orientation=-1))
        x, y = np.asarray(small['gr']['positions_scaled']), np.asarray(mirror['gr']['positions_scaled'])
        assert np.max(np.abs(x*np.array([1,-1,1])-y)) <= 2e-13
        answer['checks'].append('Reversed angular direction mirrors the orbit and preserves the physical advance')
        for key, invalid in [('mu_m3_s2', True), ('mu_m3_s2', 0), ('mu_m3_s2', float('nan')),
                             ('mu_m3_s2', float('inf')), ('semi_latus_rectum_rs', 999), ('semi_latus_rectum_rs', 1e9),
                             ('eccentricity', .001), ('eccentricity', -.1), ('eccentricity', .9),
                             ('source_radius_rs', .99), ('source_radius_rs', 1e8), ('radial_cycles', True),
                             ('radial_cycles', 0), ('radial_cycles', 17), ('output_samples', 256),
                             ('output_samples', 4098), ('orientation', True), ('orientation', 0)]:
            refusal(key+'='+str(invalid), lambda key=key, invalid=invalid: product.experiment({key: invalid}))
        refusal('unknown-field', lambda: product.experiment(dict(unknown=1)))
        refusal('non-object', lambda: product.experiment([]))
        refusal('RHS-budget', lambda: product.experiment(recipes[0], max_rhs=1), product.BudgetExceeded)
        refusal('wall-budget', lambda: product.experiment(recipes[0], max_seconds=1e-12), product.BudgetExceeded)
        refusal('cancelled', lambda: product.experiment(recipes[0], cancelled=lambda: True), product.Cancelled)
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        answer.update(accepted=True, completed=True)
    except Exception:
        answer['failure'] = traceback.format_exc()
    answer['wall_seconds'] = time.perf_counter()-began
    out.write_text(json.dumps(answer, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps({key:value for key,value in answer.items() if key not in ['source_sha256','cases']}, ensure_ascii=False), flush=True)
    return 0 if answer['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
