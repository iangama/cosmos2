"""Uninstalled C2-11 rotated cuts and piecewise-linear equipotential contours."""
import math


def _vector(value):
    if (not isinstance(value, list) or len(value) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in value)):
        raise ValueError('Vetor do corte inválido.')
    return list(value)


def plane(center_m, half_width_m, axis_u, axis_v, resolution=17):
    center = _vector(center_m)
    u, v = _vector(axis_u), _vector(axis_v)
    if (abs(math.hypot(*u) - 1) > 1e-12 or abs(math.hypot(*v) - 1) > 1e-12
            or abs(math.fsum(a * b for a, b in zip(u, v))) > 1e-12):
        raise ValueError('Os dois eixos do corte devem ser ortonormais.')
    if (type(half_width_m) not in (int, float) or not math.isfinite(half_width_m)
            or not .001 <= half_width_m <= 1e17
            or type(resolution) is not int or resolution not in (17, 21)):
        raise ValueError('Corte fora dos limites: resolução17ou21 e domínio SI do editor.')
    points = []
    for j in range(resolution):
        y = half_width_m * (2 * j / (resolution - 1) - 1)
        for i in range(resolution):
            x = half_width_m * (2 * i / (resolution - 1) - 1)
            point = [center[k] + x * u[k] + y * v[k] for k in range(3)]
            if math.hypot(*point) > 1e17:
                raise ValueError('Uma amostra do corte ultrapassa o domínio do editor.')
            points.append(point)
    return {'center_m': center, 'half_width_m': half_width_m, 'axis_u': u,
            'axis_v': v, 'resolution': resolution, 'points_m': points,
            'coordinate_policy': 'fixed plane in simulation inertial axes; no physical deformation'}


def equipotentials(grid, samples, levels_J_kg):
    n = grid['resolution']
    points = grid['points_m']
    if not isinstance(samples, list) or len(samples) != n * n:
        raise ValueError('Amostras incompletas para o corte.')
    if (not isinstance(levels_J_kg, list) or not 1 <= len(levels_J_kg) <= 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in levels_J_kg)
            or len(levels_J_kg) != len(set(levels_J_kg))):
        raise ValueError('Escolha1–4potenciais SI finitos distintos.')
    for index, (point, sample) in enumerate(zip(points, samples)):
        if sample['index'] != index or sample['position_m'] != point or type(sample['valid']) is not bool:
            raise ValueError('Amostra não corresponde ao ponto do corte.')
        if sample['valid']:
            value = sample.get('potential_J_kg')
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError('Potencial amostrado inválido.')
    contours = []
    invalid_cells = set()
    plateau_cells = set()
    for level in levels_J_kg:
        segments = []
        seen = set()
        for j in range(n - 1):
            for i in range(n - 1):
                cell = (j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i)
                if not all(samples[k]['valid'] for k in cell):
                    invalid_cells.add(j * (n - 1) + i)
                    continue
                # Fixed diagonal: an explicitly triangulated scalar interpolant,
                # not a claim about sub-cell topology of the analytic potential.
                for triangle in ((cell[0], cell[1], cell[2]), (cell[0], cell[2], cell[3])):
                    if all(samples[k]['potential_J_kg'] == level for k in triangle):
                        plateau_cells.add(j * (n - 1) + i)
                        continue
                    intersections = []
                    for a, b in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
                        a, b = sorted((a, b))
                        fa, fb = samples[a]['potential_J_kg'], samples[b]['potential_J_kg']
                        if (fa < level) == (fb < level):
                            continue
                        fraction = (level - fa) / (fb - fa)
                        point = tuple(points[a][k] + fraction * (points[b][k] - points[a][k]) for k in range(3))
                        if point not in intersections:
                            intersections.append(point)
                    if len(intersections) == 2 and intersections[0] != intersections[1]:
                        key = tuple(sorted(intersections))
                        if key not in seen:
                            segments.append([list(v) for v in intersections])
                            seen.add(key)
        contours.append({'potential_J_kg': level, 'segments_m': segments})
    return {'contours': contours, 'invalid_cells': sorted(invalid_cells),
            'plateau_cells': sorted(plateau_cells),
            'interpolation': 'piecewise linear on two fixed triangles per grid cell',
            'policy': 'sampled equipotentials, not trajectories; singular cells have gaps; plateau contour not unique'}
