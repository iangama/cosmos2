"""C2-11 adapter: confirmed SI readings to frozen native labels."""
import hashlib
import json
import math
import uuid


def prepare(result, initial=None):
    matrix = initial['j2000_to_render_frame'] if initial else None
    nonce = uuid.uuid4().hex[:12]
    code, rendered = [], []
    for reading in result['readings']:
        if not reading['available']:
            continue
        identifier = 'LabInstrument_' + nonce + '_' + hashlib.sha256(reading['id'].encode()).hexdigest()[:12]
        point = reading['position_m']
        position = [math.fsum(row[k] * point[k] for k in range(3)) for row in matrix] if matrix else list(point)
        if not all(math.isfinite(v) for v in position):
            raise ValueError('Posição gráfica da sonda não finita.')
        name = reading['definition']['name']
        text = json.dumps('+ ' + (name if len(name) <= 24 else name[:23] + '…'), ensure_ascii=False)
        xyz = ','.join(format(v, '.17g') for v in position)
        nearest = reading['nearest_included_source_distance_m'] or 1e9
        view_distance = max(3e6, .3 * nearest)
        # Ghoul culls labels below MinMaxSize.x; it only clamps oversized text.
        # A fixed1e6 scale vanished when an Atlas probe was focused from billions
        # of meters away. Match scale to the advertised view, without changing SI.
        label_scale = .002 * view_distance
        label_size = format(math.log10(label_scale), '.17g')
        code.append('openspace.addSceneGraphNode({Identifier="' + identifier + '",Parent="LabRoot",'
                    'Transform={Translation={Type="StaticTranslation",Position={' + xyz + '}}},'
                    'Renderable={Type="RenderableLabel",Text=' + text + ',FontSize=50,Size=' + label_size + ','
                    'MinMaxSize={14,20},OrientationOption="Camera View Direction",EnableFading=false},'
                    'GUI={Name=' + text + ',Focusable=false}});')
        rendered.append({'id': reading['id'], 'scene_node': identifier,
                         'position_render_m': position, 'view_distance_m': view_distance,
                         'label_scale_m': label_scale, 'label_size_exponent': float(label_size)})
    return ''.join(code), {'nodes': [r['scene_node'] for r in rendered], 'readings': rendered,
                          'policy': 'frozen confirmed points; marker/font size has no physical extent'}
