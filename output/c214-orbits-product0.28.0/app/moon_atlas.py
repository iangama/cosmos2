"""Native Atlas adapter for the pinned scene of eight planets and seven moons."""
import copy
import hashlib
import json
import math
from pathlib import Path
import time

import atlas as base
from physics import PHYSICAL_SCALE
import is6_principal_moons_catalog as catalogue

ROOT = base.ROOT
SCENE_PATH = Path(__file__).with_name('planet_scene.json')
SCENE = json.loads(SCENE_PATH.read_text(encoding='utf8'))
BODIES = SCENE['bodies']
BODY_NODES = [name for name, item in BODIES.items() if item['kind'] in ('planet', 'moon')]
NODES = list(BODIES)
START_UTC, END_UTC = SCENE['coverage_utc']


def property_row(identifier, label, value, unit, status, origin, sources, frame=None, epoch=None, note=None):
    return dict(id=identifier, label=label, value=copy.deepcopy(value), unit=unit,
                status=status, origin=origin, sources=sources, frame=frame, epoch=epoch,
                uncertainty=dict(value=None, status='unknown'), note=note)


def gm_properties(body):
    gm = body['GM']
    source = dict(title='GM do centro físico ' + body['naif_id'], url=gm['source'],
                  sha256=gm['source_sha256'])
    mass = gm['value'] / PHYSICAL_SCALE['G_m3_kg_s2']
    parameter = property_row('GM', 'Parâmetro gravitacional GM', gm['value'], 'm³/s²',
                             'model_parameter', 'Parâmetro físico publicado', [source],
                             note='Valor impresso ' + gm['raw_value_km3_s2'] + ' km³/s².')
    inferred = property_row('mass', 'Massa derivada GM/G', mass, 'kg', 'inferred_from_model',
                            'GM/G com G CODATA2022', [source, dict(title='NIST CODATA2022',
                            url='https://physics.nist.gov/cuu/pdf/wall_2022.pdf',
                            file='data/science/canonical-units.json')])
    inferred['known_uncertainty_contribution_from_G_only_kg'] = (
        mass * PHYSICAL_SCALE['G_standard_uncertainty'] / PHYSICAL_SCALE['G_m3_kg_s2'])
    return parameter, inferred


def properties(body, state):
    epoch = state['epoch']
    provider = body['state_provider']
    paths = list(dict.fromkeys(['data/spice/de442s.bsp', provider['relative_kernel']]))
    kernels = [dict(title='JPL · ' + Path(path).name, file=path,
                    sha256=state['provenance']['kernels_sha256'][path]) for path in paths]
    pck = dict(title='PCK00011', file='data/spice/pck00011.tpc',
               url='https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc',
               sha256=state['provenance']['kernels_sha256']['data/spice/pck00011.tpc'])
    visual = BODIES[body['scene_node']].get('texture')
    textures = [dict(path=visual['path'], credit='Mapa visual OpenSpace',
                     sha256=visual['sha256'], source_url=visual['download_url'])] if visual else None
    rows = [
        property_row('position', 'Posição', body['position_m'], 'm', 'model_calculated',
                     'Estado geométrico ' + provider['model'], kernels, 'SSB / J2000-ICRF', epoch),
        property_row('velocity', 'Velocidade', body['velocity_m_s'], 'm/s', 'model_calculated',
                     'Derivada do estado geométrico', kernels, 'SSB / J2000-ICRF', epoch),
        *gm_properties(body),
        property_row('shape', 'Semieixos de referência', body['shape']['radii_m'], 'm',
                     'adopted_reference_shape', 'PCK00011', [pck], body['body_frame']),
        property_row('orientation', 'Orientação do corpo → J2000', body['body_to_j2000'], '1',
                     'model_calculated' if body['body_to_j2000'] else 'unknown',
                     'Rotação IAU geral do PCK00011', [pck], body['body_frame'], epoch),
        property_row('texture', 'Mapa visual', textures, 'image',
                     'illustrative_map' if textures else 'unknown',
                     'Mapa fixo OpenSpace', [dict(title='OpenSpace · mapa visual', url=visual['download_url'],
                     file=visual['path'], sha256=visual['sha256'])] if visual else [],
                     body['body_frame'], note='Época e origem observacional sem confirmação neste recurso.')
    ]
    return rows


def states(utc=None, et=None):
    result = catalogue.states(utc=utc, et=et)
    legacy = base.states(et=result['epoch']['et_tdb_s'])
    previous = {body['scene_node']: body for body in legacy['bodies']}
    result['epoch'] = {**legacy['epoch'], **result['epoch']}
    for body in result['bodies']:
        node = body['scene_node']
        body['body_frame'] = body['rotation']['frame']
        body['body_to_j2000'] = body['rotation']['body_to_j2000']
        if node in previous and previous[node]['shape']:
            body['shape'] = copy.deepcopy(previous[node]['shape'])
        if node in previous:
            body['properties'] = copy.deepcopy(previous[node]['properties'])
            replacements = {p['id']: p for p in gm_properties(body)}
            body['properties'] = [replacements.get(p['id'], p) for p in body['properties']]
        else:
            body['properties'] = properties(body, result)
    by_target = {body['naif_id']: body for body in result['bodies']}
    result.update(model='DE442s + MAR099/JUP365/SAT441/URA182/NEP097',
                  earth_moon_separation_m=math.dist(by_target['399']['position_m'], by_target['301']['position_m']),
                  matrix_layout='row-major, acts on column vectors',
                  packages_manifest_sha256=legacy['packages_manifest_sha256'],
                  observer=copy.deepcopy(legacy['observer']))
    result['provenance'].update(adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                scene_sha256=hashlib.sha256(SCENE_PATH.read_bytes()).hexdigest())
    return result


def normalize_epoch(utc):
    value = base.normalize_epoch(utc)
    states(utc=value)
    return value


def position_budget(position):
    return max(.001, 8 * math.ulp(max(abs(component) for component in position)))


class Atlas(base.Atlas):
    def _read(self):
        positions = ','.join(name + '=openspace.worldPosition(' + json.dumps(name) + ')' for name in NODES)
        return self._lua('return {et=openspace.time.currentTime(),utc=openspace.time.UTC(),'
                         'paused=openspace.time.isPaused(),positions={' + positions + '}}')

    def status(self):
        with self.lock:
            native = self._read()
            result = states(et=native['et'])
            result['renderer'] = native
            return result

    def apply_epoch(self, utc):
        result = states(utc=utc)
        et = result['epoch']['et_tdb_s']
        with self.lock:
            self._lua(f'openspace.time.setPause(true);openspace.time.setTime({et:.17g});return {{queued=true}}')
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                native = self._read()
                expected = {body['scene_node']: body['position_render_m'] for body in result['bodies']}
                if native['paused'] and native['et'] == et and all(
                    max(abs(a-b) for a, b in zip(native['positions'][node], position)) <= position_budget(position)
                    for node, position in expected.items()
                ):
                    result['renderer'] = native
                    return result
                time.sleep(.02)
            raise TimeoutError('O motor ainda não confirmou as dezesseis posições na época solicitada.')
