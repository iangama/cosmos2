"""Confirmed SI maps to a few frozen native line meshes with display receipts."""
from pathlib import Path
import json
import math
import uuid

import numpy as np
from body_attributes import rotation_euler

ROOT = Path(__file__).resolve().parents[1]
PALETTE = [[.22, .55, 1.], [.15, .82, .83], [.53, .9, .46], [1., .76, .25], [1., .34, .24]]
CONTOUR_COLORS = [[.85, .56, 1.], [1., .72, .4], [.96, .92, .55], [.9, .5, .65]]


def join_segments(segments):
    """Join exactly equal endpoints; retain every original edge and branch gap.

    Signed one-based source indices describe the orientation of each edge.
    A branch is a path boundary, never an invented connection between curves.
    """
    adjacency = {}
    for index, segment in enumerate(segments):
        for endpoint in segment:
            adjacency.setdefault(tuple(endpoint), []).append(index)
    unused = set(range(len(segments)))
    paths, orders = [], []
    while unused:
        first = min(unused)
        # Start at a non-degree-two boundary where possible, otherwise a loop.
        seed = next((index for index in sorted(unused) if any(len(adjacency[tuple(p)]) != 2 for p in segments[index])), first)
        ends = segments[seed]
        start = next((tuple(p) for p in ends if len(adjacency[tuple(p)]) != 2), tuple(ends[0]))
        point, path, order = start, [list(start)], []
        while True:
            candidates = [i for i in adjacency[point] if i in unused]
            if not candidates:
                break
            index = min(candidates)
            a, b = map(tuple, segments[index])
            forward = a == point
            point = b if forward else a
            unused.remove(index)
            order.append(index + 1 if forward else -index - 1)
            path.append(list(point))
            if len(adjacency[point]) != 2:
                break
        paths.append(path)
        orders.append(order)
    return paths, orders


def color_bin(magnitude, legend):
    lo, hi = legend['minimum'], legend['maximum']
    if hi is None or hi == 0 or lo == hi:
        return 2
    if legend['scale'] == 'log':
        if magnitude <= 0:
            return 0
        lo = legend['minimum_positive']
        if lo == hi:
            return 2
        ratio = (math.log(magnitude) - math.log(lo)) / (math.log(hi) - math.log(lo))
    else:
        ratio = (magnitude - lo) / (hi - lo)
    return min(4, max(0, int(ratio * 5)))


def prepare(result, initial=None):
    token = uuid.uuid4().hex
    folder = ROOT / 'output/field-previews' / token
    folder.mkdir(parents=True)
    matrix = np.array(initial['j2000_to_render_frame'] if initial else np.eye(3))
    rotation = rotation_euler([1, 0, 0, 0], matrix.tolist())
    origin = np.array(result['center_m'])
    extent = max([result['settings']['shell_radius_m'] if result['shell'] else 0.,
                  result['settings']['cut_half_width_m'] if result['cut'] else 0.,
                  abs(result['settings']['cut_offset_m']) if result['cut'] else 0., 1.])
    literal = lambda value: json.dumps(value, ensure_ascii=False)
    vec = lambda value: '{' + ','.join(format(float(v), '.17g') for v in value) + '}'
    frame = 'LabFieldFrame_' + token
    frame_position = matrix @ origin
    code = 'openspace.addSceneGraphNode({Identifier=' + literal(frame) + ',Parent="LabRoot",Transform={Translation={Type="StaticTranslation",Position=' + vec(frame_position) + '}},GUI={Name="Mapa de campo confirmado"}});'
    nodes, meshes = [frame], []

    def mesh(label, segments, colors, indices=None, source_orders=None):
        nonlocal code
        if not segments:
            return
        node = 'LabField_' + label + '_' + token
        file, namefile = folder / (label + '.speck'), folder / (label + '.names')
        lines, names, maximum = ['# Frozen derived map; float32 vertices; scientific SI readings in receipt.'], [], 0.
        for index, segment in enumerate(segments):
            values = (np.array(segment) - origin) / extent
            maximum = max(maximum, float(np.max(abs(values.astype(np.float32).astype(float) - values))) * extent)
            group = indices[index] + 1 if indices is not None else 1
            lines.extend(['mesh -c ' + str(group) + ' {', 'id segment' + str(index), str(len(segment)),
                          *[' '.join(format(float(v), '.17g') for v in row) for row in values], '}'])
            names.append('segment' + str(index) + ' ' + label + str(index))
        file.write_text('\n'.join(lines) + '\n', encoding='utf8')
        namefile.write_text('\n'.join(names) + '\n', encoding='utf8')
        code += 'openspace.addSceneGraphNode({Identifier=' + literal(node) + ',Parent=' + literal(frame) + ',Transform={Rotation={Type="StaticRotation",Rotation=' + vec(rotation) + '},Scale={Type="StaticScale",Scale=' + format(extent, '.17g') + '}},Renderable={Type="RenderableConstellationLines",File=' + literal(file.as_posix()) + ',NamesFile=' + literal(namefile.as_posix()) + ',Unit="m",Colors={' + ','.join(vec(c) for c in colors) + '},LineWidth=2},GUI={Name=' + literal(label) + ',Focusable=false}});'
        nodes.append(node)
        meshes.append({'layer': label, 'node': node, 'file': file.as_posix(), 'names_file': namefile.as_posix(),
                       'segment_count': len(segments), 'float32_vertex_max_component_error_m': maximum,
                       'conservative_display_position_error_bound_m': 3 * maximum + 4e-6 * extent + .1,
                       'position_render_m': frame_position.tolist(), 'scale_m': extent,
                       'rotation_euler_rad': rotation, 'colors_rgb': colors})
        if source_orders is not None:
            meshes[-1]['source_segment_orders'] = source_orders

    for layer in ('shell', 'cut'):
        if not result[layer]:
            continue
        drawn = [a for a in result[layer]['geometry']['arrows'] if a['drawn']]
        mesh(layer + '_vectors', [a['segment_m'] for a in drawn], PALETTE,
             [color_bin(a['acceleration_norm_m_s2'], result['magnitude_legend']) for a in drawn])
    if result['cut']:
        mesh('cut_border', [result['cut']['outline_m']], [[.23, .4, .48]])
        for index, contour in enumerate(result['cut']['equipotentials']['contours']):
            paths, orders = join_segments(contour['segments_m'])
            mesh('potential_' + str(index), paths, [CONTOUR_COLORS[index]], source_orders=orders)
    render = {'id': token, 'nodes': nodes, 'frame_node': frame, 'meshes': meshes,
              'frame_position_render_m': frame_position.tolist(), 'view_distance_m': 3.2 * extent,
              'palette_rgb': PALETTE, 'contour_colors_rgb': CONTOUR_COLORS,
              'policy': 'float32 display local to confirmed float64 SI center; no elastic sheet or material deformation'}
    (folder / 'receipt.json').write_text(json.dumps({**result, 'render': render}, indent=2, allow_nan=False) + '\n', encoding='utf8')
    return code, render
