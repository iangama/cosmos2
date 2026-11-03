"""Check J's perspective fit with independent matrix camera reconstruction."""
from pathlib import Path
import hashlib
import json
import math
import random
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'output/c212-em-viewport-product/app'))
from em_viewport import fit, validate_viewport, projection_from_config

DEST = ROOT / 'evidence/em-viewport-geometry-release2-check.json'
assert not DEST.exists()
rng = random.Random(21210)
cases = []
max_error = 0
for index in range(640):
    window = [rng.uniform(900, 3840), rng.uniform(700, 2160)]
    rect = [rng.uniform(0, .35) * window[0], rng.uniform(.04, .3) * window[1], 0, 0]
    rect[2] = rng.uniform(.6, .95) * (window[0] - rect[0])
    rect[3] = rng.uniform(.4, .85) * (window[1] - rect[1])
    viewport = {'window_px': window, 'rect_px': rect}
    projection = projection_from_config(ROOT, window)
    center = np.array([rng.uniform(-30, 30) for _ in range(3)])
    scale = 10 ** rng.uniform(-3, 4)
    points = center + np.array([[rng.uniform(-scale, scale) for _ in range(3)] for _ in range(64)])
    az, el = rng.uniform(-math.pi, math.pi), rng.uniform(-1.4, 1.4)
    result = fit(points.tolist(), center.tolist(), az, el, viewport, projection)
    # Reconstruct exactly the documented OpenSpace camera: lookAt inverse,
    # local negative-Y yaw and then local-X pitch. This does not use the fit's
    # component transform, plane inequalities or projected output.
    eye = center + result['position_model_m']
    backward = eye - center
    backward /= np.linalg.norm(backward)
    right = np.cross([0., 0., 1.], backward)
    right /= np.linalg.norm(right)
    up = np.cross(backward, right)
    neutral = np.column_stack((right, up, backward))
    yaw, pitch = result['yaw_rad'], result['pitch_rad']
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    rotation = neutral @ np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    local = (points - eye) @ rotation
    assert np.all(local[:, 2] < 0)
    ndc = local[:, :2] / -local[:, 2, None] / [projection['tan_half_horizontal'], projection['tan_half_vertical']]
    pixels = (ndc * [1, -1] + 1) * np.array(window) / 2
    low, high = pixels.min(axis=0), pixels.max(axis=0)
    pad = result['padding_fraction']
    minimum = np.array(rect[:2]) + pad * np.array(rect[2:])
    maximum = np.array(rect[:2]) + (1 - pad) * np.array(rect[2:])
    assert np.all(low >= minimum - 1e-6) and np.all(high <= maximum + 1e-6), (index, low, high, minimum, maximum)
    error = float(np.max(np.abs(np.array([low, high]) - [result['projected_bounds']['minimum_px'], result['projected_bounds']['maximum_px']])))
    max_error = max(max_error, error)
    assert error < 1e-6, error
    # Unless the explicit minimum distance is active, at least one plane
    # must be tight. A deliberately oversized constant sphere would fail.
    if result['distance_model_m'] > 3.000001:
        assert min(*abs(low - minimum), *abs(high - maximum)) < .001
    cases.append({'index': index, 'distance_model_m': result['distance_model_m'], 'projection_error_px': error})
invalid = [None, {}, {'window_px': [1920, 1080], 'rect_px': [0, 0, 1920, 1080], 'extra': 1},
           {'window_px': [True, 1080], 'rect_px': [0, 0, 100, 100]},
           {'window_px': [1920, 1080], 'rect_px': [-1, 0, 100, 100]},
           {'window_px': [1920, 1080], 'rect_px': [0, 0, 1921, 100]},
           {'window_px': [1920, 1080], 'rect_px': [0, 0, 100, 79]},
           {'window_px': [1920, 1080], 'rect_px': [0, 0, math.nan, 100]}]
for value in invalid:
    try:
        validate_viewport(value)
    except ValueError:
        continue
    raise AssertionError(value)
report = {'passed': True, 'cases': len(cases), 'max_independent_projection_error_px': max_error,
          'invalid_viewports_refused': len(invalid), 'results': cases,
          'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (Path(__file__), ROOT / 'output/c212-em-viewport-product/app/em_viewport.py')},
          'scope': '640independent matrix projections, padded-rectangle containment and tight-plane fit. Real engine/CEF/config/visual execution remains required.'}
DEST.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: report[key] for key in ('passed', 'cases', 'max_independent_projection_error_px', 'invalid_viewports_refused')}), flush=True)
