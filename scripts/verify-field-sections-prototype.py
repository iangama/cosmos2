"""C2-11 cut geometry: analytic circles, rotated planes and singular holes."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
installed = '--installed' in sys.argv
sys.path.insert(0, str(ROOT / 'app'))
from physics import PHYSICAL_SCALE as U


def candidate(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ('app' if installed else 'output/c211-staging') / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


field = candidate('gravity_field')
sections = candidate('field_sections')
center = [3e9, -2e9, 7e9]
u = [1 / math.sqrt(2), 1 / math.sqrt(2), 0]
v = [-1 / math.sqrt(6), 1 / math.sqrt(6), 2 / math.sqrt(6)]
normal = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
source = [{'id': 'mass', 'mass': 1., 'position': [x / U['length_unit_m'] for x in center]}]
radius = 3.3e8
level = -U['nominal_GM_unit_m3_s2'] / radius
results = []
for count in (17, 21):
    grid = sections.plane(center, 6e8, u, v, count)
    samples = field.evaluate_points(source, grid['points_m'])
    before = copy.deepcopy((grid, samples))
    contours = sections.equipotentials(grid, samples, [level])
    segments = contours['contours'][0]['segments_m']
    assert segments and len(contours['invalid_cells']) == 4
    error = plane_error = 0.
    for line in segments:
        for point in line:
            delta = [point[k] - center[k] for k in range(3)]
            plane_error = max(plane_error, abs(math.fsum(normal[k] * delta[k] for k in range(3))))
            error = max(error, abs(math.hypot(*delta) - radius) / radius)
    assert plane_error < 2e-6 and error < .04
    assert (grid, samples) == before
    results.append({'resolution': count, 'samples': count * count, 'segments': len(segments),
                    'circle_radius_relative_difference_max': error, 'plane_distance_m_max': plane_error,
                    'singular_cells_with_gaps': len(contours['invalid_cells'])})
assert results[1]['circle_radius_relative_difference_max'] < .7 * results[0]['circle_radius_relative_difference_max']
# A linear potential must be reproduced exactly in a rotated plane, independent
# of the point-mass evaluator and without falsely inventing closed trajectories.
grid = sections.plane([0, 0, 0], 10, u, v, 21)
linear = [{'index': i, 'valid': True, 'position_m': point,
           'potential_J_kg': math.fsum(point[k] * u[k] for k in range(3))} for i, point in enumerate(grid['points_m'])]
curves = sections.equipotentials(grid, linear, [-1.7, 1.3])
maxlinear = max(abs(math.fsum(point[k] * u[k] for k in range(3)) - contour['potential_J_kg'])
                for contour in curves['contours'] for line in contour['segments_m'] for point in line)
assert maxlinear < 1e-14
flat = [{**s, 'potential_J_kg': 0.} for s in linear]
plateau = sections.equipotentials(grid, flat, [0.])
assert not plateau['contours'][0]['segments_m'] and len(plateau['plateau_cells']) == 400
invalid = 0
for callback in [lambda: sections.plane([0, 0, 0], 10, u, u),
                 lambda: sections.plane([0, 0, 0], 10, u, v, 22),
                 lambda: sections.plane([math.nan, 0, 0], 10, u, v),
                 lambda: sections.equipotentials(grid, linear, [math.nan]),
                 lambda: sections.equipotentials(grid, linear, [1, 1]),
                 lambda: sections.equipotentials(grid, linear[:-1], [0])]:
    try:
        callback()
    except ValueError:
        invalid += 1
    else:
        raise AssertionError('Invalid cut accepted')
report = {'status': 'verified_staging_only_not_product', 'isolated_mass_rotated_cuts': results,
          'linear_interpolant_max_error': maxlinear, 'constant_plateau_has_no_unique_invented_contour': True,
          'invalid_requests_rejected': invalid, 'read_only_inputs': True,
          'prototype_sha256': hashlib.sha256((ROOT / 'output/c211-staging/field_sections.py').read_bytes()).hexdigest()}
if installed:
    report.update(status='verified_installed_math_not_full_C211', module_sha256=hashlib.sha256((ROOT / 'app/field_sections.py').read_bytes()).hexdigest())
(ROOT / ('evidence/field-sections-installed-check.json' if installed else 'evidence/field-sections-prototype-check.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
