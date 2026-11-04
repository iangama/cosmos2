"""Pure four-physical-center contract; no SPICE dependency in the worker."""
from functools import lru_cache
from pathlib import Path
from decimal import Decimal
import copy
import datetime as dt
import hashlib
import json
import math
import re

from atlas_import import gm_data, vector, render_transform, digest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
TARGETS = [('10', 'Sol', None), ('399', 'Terra', 'IAU_EARTH'),
           ('301', 'Lua', 'IAU_MOON'), ('599', 'Júpiter', 'IAU_JUPITER')]
SUBSET = 'output/solar-integration-staging/jupiter-center-jup365-from-jup348.bsp'
SUBSET_SHA = '15603bf73505af983a1a76bc45ed522d0962aa237ac48e8f96f98379637a5ea5'
JUPITER_GM = 126686531900370400.0
FRAME = 'initial_subset_barycenter_inertial_axes_J2000'
EXCLUDED = ['demais planetas e luas, incluindo luas jovianas',
            'asteroides e outros corpos menores', 'relatividade',
            'multipolos e deformações de maré', 'campos EM e processos estelares',
            'colisões']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


@lru_cache(maxsize=1)
def parameters():
    receipt = json.loads((ROOT / 'evidence/jupiter-candidate-gm-20261023.json').read_text(encoding='utf-8'))
    source = receipt['source']
    path = ROOT / source['file']
    if sha(path) != source['sha256'] or source['sha256'] != '3c851a4b5d1223e155320e7f63558ebcc81908c8f68fb1c7b43985a69663e08a':
        raise ValueError('Fonte GM599 difere dos comentários JUP365 fixados.')
    values = [Decimal(m.group(1)) for line in path.read_text(encoding='ascii').splitlines()
              if (m := re.match(r'^\s+Jupiter\s+599\s+(\S+)\s+', line))]
    if len(values) != 2 or any(float(v * Decimal(10)**9) != JUPITER_GM for v in values):
        raise ValueError('Parâmetro físico599 incompatível com a fonte.')
    old = gm_data()
    return {**{t: copy.deepcopy(old[key]) for t, key in [('10', 'GMS'), ('399', 'GM3'), ('301', 'GMM')]},
            '599': {'value': JUPITER_GM, 'unit': 'm^3/s^2', 'uncertainty': None,
                    'uncertainty_reason': receipt['candidate_parameter']['uncertainty_reason'],
                    'origin': 'JUP365 physical planet599 printed GM; jovian moons omitted',
                    'raw_value_km3_s2': str(values[0]),
                    'source': source['url'], 'source_sha256': source['sha256'],
                    'source_rows': copy.deepcopy(receipt['matching_source_rows']),
                    'source_resolution_m3_s2': float(Decimal(10)**values[0].as_tuple().exponent * Decimal(10)**9)}}


@lru_cache(maxsize=1)
def providers():
    acquired = json.loads((ROOT / 'evidence/atlas-kernels-acquisition.json').read_text(encoding='utf-8'))
    files = {('data/spice/' + name): acquired['files'][name]['sha256']
             for name in ['naif0012.tls', 'pck00011.tpc', 'de442s.bsp']}
    files[SUBSET] = SUBSET_SHA
    for path, expected in files.items():
        if sha(ROOT / path) != expected:
            raise ValueError('Kernel da candidata difere da fonte fixada: ' + path)
    result = {}
    for target, _, _ in TARGETS:
        chain = [target, '5', '0'] if target == '599' else [target, '3', '0'] if target in ('399', '301') else [target, '0']
        result[target] = {
            'kind': 'geometric_spice_chain', 'target_naif_id': target, 'center_naif_id': '0',
            'frame': 'J2000/ICRF', 'aberration': 'NONE', 'chain_naif_ids': chain,
            'kernels_sha256': {p: value for p, value in files.items() if p != SUBSET or target == '599'},
            'application_coverage_utc': ['1950-01-01T00:00:00Z', '2050-12-31T23:59:59Z'],
            'coverage_policy': 'intersection of every SPK link, restricted to the application interval',
            'source_uncertainty': None, 'uncertainty_reason': 'Observational uncertainty not propagated locally.',
        }
    return result


def capabilities(target, epoch):
    def item(status, model, reason, frame=None, domain=None, dependencies=None):
        return {'status': status, 'model': model, 'version': None, 'reason': reason,
                'epoch': copy.deepcopy(epoch) if frame else None, 'frame': frame, 'domain': domain,
                'provenance': 'registered project bench/reference; no automatic coupling',
                'dependencies': dependencies or []}
    magnetic = item('available_bench', 'IGRF14', 'Instrumento validado separado; associação à cena pendente.',
                    domain='Ver domínio e conversão de eixos da bancada IGRF14.') if target == '399' else item(
                    'unavailable', None, 'Modelo de campo não adotado nesta candidata. Lua: campo crostal/externo não adotado.' if target == '301'
                    else 'Modelo de campo não adotado nesta candidata; JRM33 é apenas proposta de estudo.' if target == '599'
                    else 'Campo solar e plasma não adotados nesta candidata.')
    return {
        'gravity': item('available_reference', 'Newtonian point centers', 'Estado e GM disponíveis para uma cópia dinâmica reduzida.',
                        'J2000/ICRF', 'Quatro centros pontuais, sem relatividade/multipolos.', ['state', 'GM']),
        'magnetism': magnetic,
        'strong_processes': item('available_bench', 'pp-I/CNO-I' if target == '10' else 'AME2020 effective nuclear benches',
                                'Bancada separada; sem inventário isotópico ou resposta estrutural do corpo.'),
        'weak_processes': item('available_bench', 'pp-I/CNO-I and beta decay benches' if target == '10' else 'beta decay benches',
                              'Bancada separada; sem inventário isotópico ou transporte de neutrinos.'),
    }


def validate_catalog(value):
    if not isinstance(value, dict) or type(value.get('schema')) is not int or value['schema'] != 1 or value.get('kind') != 'solar_four_center_reference' or value.get('version') != '1.0.0':
        raise ValueError('Catálogo solar/versionamento incompatível.')
    if any(value.get(k) != v for k, v in {'frame': 'J2000/ICRF', 'center_naif_id': '0', 'aberration': 'NONE',
                                         'position_unit': 'm', 'velocity_unit': 'm/s'}.items()):
        raise ValueError('Catálogo exige estados simultâneos SSB/J2000 em SI.')
    epoch = value.get('epoch')
    if not isinstance(epoch, dict) or not isinstance(epoch.get('utc'), str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z', epoch['utc']):
        raise ValueError('Época UTC explícita ausente.')
    try:
        date = dt.datetime.fromisoformat(epoch['utc'].removesuffix('Z'))
    except ValueError:
        raise ValueError('Data UTC do catálogo inválida.') from None
    if not 1950 <= date.year <= 2050:
        raise ValueError('Data fora da cobertura da aplicação.')
    if type(epoch.get('et_tdb_s')) not in (int, float) or not math.isfinite(epoch['et_tdb_s']) or not epoch.get('utc_conversion'):
        raise ValueError('Época TDB/política UTC ausente.')
    render_transform(value.get('j2000_to_render_frame'), value.get('render_frame'))
    rows = value.get('bodies')
    if not isinstance(rows, list) or len(rows) != 4 or any(not isinstance(b, dict) for b in rows):
        raise ValueError('Catálogo exige quatro centros físicos.')
    if [b.get('naif_id') for b in rows] != [t[0] for t in TARGETS]:
        raise ValueError('IDs/ordem inválidos; baricentro5 não substitui planeta599.')
    for body, (target, name, frame) in zip(rows, TARGETS):
        if body.get('id') != 'sol:naif:' + target or body.get('entity_kind') != 'physical_body' or body.get('name') != name:
            raise ValueError('Identidade/tipo físico inválido.')
        vector(body.get('position_m')); vector(body.get('velocity_m_s'))
        gm = body.get('GM')
        if not isinstance(gm, dict) or type(gm.get('value')) not in (int, float) or not math.isfinite(gm['value']) or gm['value'] <= 0 or gm != parameters()[target]:
            raise ValueError('GM físico/procedência incompatível.')
        if body.get('state_provider') != providers()[target]:
            raise ValueError('Provedor/cadeia de estados incompatível.')
        coverage = body.get('coverage_et_s')
        if not isinstance(coverage, list) or not coverage or any(not isinstance(pair, list) or len(pair) != 2 or
                any(type(x) not in (int, float) or not math.isfinite(x) for x in pair) or pair[0] > pair[1] for pair in coverage):
            raise ValueError('Cobertura efetiva inválida.')
        if not any(a <= epoch['et_tdb_s'] <= b for a, b in coverage):
            raise ValueError('Época fora da cadeia de cobertura efetiva.')
        if body.get('capabilities') != capabilities(target, epoch):
            raise ValueError('Capacidades/modelos não correspondem à integração disponível.')
        if body.get('shape') != {'value': None, 'reason': 'Geometria científica ainda não adotada para este cadastro; marcador gráfico separado.'}:
            raise ValueError('Forma não adotada deve permanecer desconhecida, com motivo.')
        rotation = body.get('rotation')
        if not isinstance(rotation, dict) or rotation.get('frame') != frame or rotation.get('model') != ('general PCK00011' if frame else None) or rotation.get('precise_orientation') is not False:
            raise ValueError('Modelo de rotação incompatível.')
        if frame:
            render_transform(rotation.get('body_to_j2000'), 'GALACTIC')  # proper orthogonal matrix, independent of its label
        elif rotation.get('body_to_j2000') is not None:
            raise ValueError('Orientação solar não adotada.')
    for i, body in enumerate(rows):
        if any(math.dist(body['position_m'], other['position_m']) <= 1 for other in rows[i + 1:]):
            raise ValueError('Centros coincidentes ou separados por menos de1m.')
    # Enforce finite JSON throughout metadata as well as numerical vectors.
    try:
        digest(value)
    except (TypeError, ValueError):
        raise ValueError('Metadados não serializáveis ou números não finitos.') from None
    return copy.deepcopy(value)
