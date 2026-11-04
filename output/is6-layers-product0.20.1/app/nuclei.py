"""AME2020 reference states, with original precision, flags and missing values.

This is an evaluated data instrument. It does not integrate reactions, infer
half-lives or decompose the total binding energy into fundamental forces.
"""
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
import copy
import datetime
import hashlib
import json
import os
import platform
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/science/ame2020-mass-original.txt'
EXPECTED_SHA256 = 'e8599c6d7f724fac91934e59f1b9de8fb8f63e820f4b39456b790665ed2a3307'
FORMAT = 'a1,i3,i5,i5,i5,1x,a3,a4,1x,f14.6,f12.6,f13.5,1x,f10.5,1x,a2,f13.5,f11.5,1x,i3,1x,f13.6,f12.6'
SOURCES = [
    {'title': 'Huang et al., AME2020 (I), Chinese Physics C 45, 030002 (2021)',
     'url': 'https://doi.org/10.1088/1674-1137/abddb0'},
    {'title': 'Wang et al., AME2020 (II), Chinese Physics C 45, 030003 (2021)',
     'url': 'https://doi.org/10.1088/1674-1137/abddaf'},
    {'title': 'AMDC / IAEA · tabela original e convenções',
     'url': 'https://www-nds.iaea.org/amdc/ame2020/mass_1.mas20.txt'},
]
GENERATION = {
    'schema': 1, 'model_id': 'cosmos2:ame2020-reference-states', 'model_version': '1.0.0',
    'code_sha256': {'app/nuclei.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
    'data_sha256': {'data/science/ame2020-mass-original.txt': EXPECTED_SHA256},
    'runtime': {'python': platform.python_version()},
}


def number(raw):
    token = raw.strip()
    if token in ('', '*'):
        return None, None
    try:
        value = Decimal(token.replace('#', '.'))
    except InvalidOperation as error:
        raise ValueError('Campo AME2020 inválido: ' + repr(token)) from error
    if not value.is_finite():
        raise ValueError('Valor AME2020 não finito.')
    return value, Decimal(10) ** value.as_tuple().exponent


def quantity(raw, uncertainty, unit, offset=Decimal(0), scale=Decimal(1)):
    value, resolution = number(raw)
    sigma, _ = number(uncertainty)
    if sigma is not None and sigma < 0:
        raise ValueError('Incerteza AME2020 negativa.')
    return {
        'value': None if value is None else float(offset + value * scale),
        'uncertainty': None if sigma is None else float(sigma * scale),
        'unit': unit, 'status': 'not_calculable' if '*' in raw else 'missing' if value is None else 'estimated' if '#' in raw else 'evaluated',
        'estimated': '#' in raw, 'uncertainty_estimated': '#' in uncertainty,
        'raw_value': raw.strip(), 'raw_uncertainty': uncertainty.strip(),
        'source_resolution': None if resolution is None else float(resolution * scale),
        'uncertainty_kind': 'tabulated AME2020 standard uncertainty; evaluated correlations not included',
    }


def parse_table(raw):
    lines = raw.decode('ascii').splitlines()
    if not any('format    :  ' + FORMAT in line for line in lines[:36]):
        raise ValueError('Formato AME2020 diferente do contrato fixado.')
    header = next((i for i, line in enumerate(lines) if line.startswith('1N-Z')), None)
    if header is None or 'micro-u' not in lines[header + 1]:
        raise ValueError('Cabeçalho AME2020 ausente.')
    records, ids = [], set()
    for i, original in enumerate(lines[header + 2:], header + 3):
        try:
            if not 123 <= len(original) <= 135:
                raise ValueError('Comprimento de registro inválido.')
            line = original.ljust(135)
            if line[0] not in ('0', ' ') or any(line[j] != ' ' for j in (19, 27, 67, 78, 105, 109)):
                raise ValueError('Separadores/controle Fortran inválidos.')
            nz, n, z, a = (int(line[lo:hi]) for lo, hi in ((1, 4), (4, 9), (9, 14), (14, 19)))
            if min(n, z) < 0 or a <= 0 or n + z != a or n - z != nz:
                raise ValueError('N/Z/A inconsistentes.')
            ident = f'nucleus:ame2020:{z}:{a}'
            if ident in ids:
                raise ValueError('ID repetido.')
            ids.add(ident)
            integer_mass = int(line[106:109])
            symbol = line[20:23].strip()
            if not symbol or line[79:81] != 'B-':
                raise ValueError('Elemento/canal da tabela inválido.')
            q = {
                'mass_excess': quantity(line[28:42], line[42:54], 'keV'),
                'binding_per_nucleon': quantity(line[54:67], line[68:78], 'keV'),
                'beta_minus_energy': quantity(line[81:94], line[94:105], 'keV'),
                'atomic_mass': quantity(line[110:123], line[123:135], 'u', Decimal(integer_mass), Decimal('0.000001')),
            }
            records.append({'id': ident, 'N': n, 'Z': z, 'A': a, 'symbol': symbol,
                            'label': 'n' if z == 0 else f'{symbol}-{a}',
                            'origin_flag': line[23:27].strip(), 'source_line': i,
                            'atomic_mass_integer_u': integer_mass, 'quantities': q})
        except (ValueError, InvalidOperation) as error:
            raise ValueError(f'AME2020 linha {i}: {error}') from error
    if not records:
        raise ValueError('Tabela AME2020 vazia.')
    return records


@lru_cache(maxsize=1)
def catalog():
    raw = DATA.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise ValueError('A tabela AME2020 difere da aquisição fixada.')
    records = parse_table(raw)
    if len(records) != 3558 or max(r['A'] for r in records) != 295:
        raise ValueError('Cobertura AME2020 inesperada.')
    return {'schema': 1, 'generation': GENERATION, 'scientific_contract': {
        'model_id': GENERATION['model_id'], 'kind': 'evaluated_reference_data',
        'state': 'AME2020 reference state per N/Z/A; no isomer catalog',
        'coordinates': 'N and Z are counts, not spatial coordinates',
        'time': None, 'half_life': 'not inferred from binding energy',
        'binding': 'tabulated total binding per nucleon, not strong interaction alone',
        'atomic_mass': 'neutral atom mass in u; neutron is a free particle',
        'estimates': '# marks non-experimental estimates per property',
        'missing': '* means not calculable; blank means missing; both export null',
        'source_uncertainty': 'preserved per property, separate from numeric rounding; no covariance propagation',
        'provenance': GENERATION, 'sources': SOURCES,
    }, 'coverage': {'states': len(records), 'N': [min(r['N'] for r in records), max(r['N'] for r in records)],
                    'Z': [0, max(r['Z'] for r in records)], 'A': [1, 295],
                    'estimated_binding_states': sum(r['quantities']['binding_per_nucleon']['estimated'] for r in records)},
        'records': records}


def configuration(request):
    selection = request.get('selected_ids', ['nucleus:ame2020:26:56'])
    known = {r['id'] for r in catalog()['records']}
    if not isinstance(selection, list) or not 1 <= len(selection) <= 2 or any(not isinstance(i, str) or i not in known for i in selection) or len(set(selection)) != len(selection):
        raise ValueError('Selecione um ou dois estados distintos do catálogo AME2020.')
    view = request.get('view', 'chart')
    include = request.get('include_estimates', True)
    if view not in ('chart', 'binding') or not isinstance(include, bool):
        raise ValueError('Vista/filtro nuclear inválido.')
    return {'schema': 1, 'selected_ids': list(selection), 'view': view, 'include_estimates': include}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def export(request):
    cfg = configuration(request)
    data = catalog()
    return {'schema': 1, 'configuration': cfg, 'generation': GENERATION,
            'scientific_contract': data['scientific_contract'],
            'records': [r for r in data['records'] if r['id'] in cfg['selected_ids']],
            'catalog_sha256': EXPECTED_SHA256,
            'selection_sha256': digest({'ids': cfg['selected_ids'], 'generation': GENERATION})}


def write_atomic(path, envelope):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=path.stem + '-', suffix='.tmp', dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as f:
            json.dump(envelope, f, ensure_ascii=True, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return envelope


def export_file(request, folder=None):
    """The in-app CEF does not provide a browser download handler.

    Keep an actual local export even when its optional blob download is ignored.
    """
    result = {'ok': True, **export(request)}
    folder = Path(folder) if folder is not None else ROOT / 'user/exports'
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
    path = folder / f'cosmos2-ame2020-{stamp}-{uuid.uuid4().hex[:12]}.json'
    result['export_file'] = str(path)
    write_atomic(path, result)
    return result


def save(request, path=None):
    cfg = configuration(request)
    body = {'schema': 1, 'configuration': cfg, 'generation': GENERATION}
    envelope = {**body, 'sha256': digest(body)}
    path = Path(path) if path is not None else ROOT / 'user/nuclei/selection.json'
    return write_atomic(path, envelope)


def load(path=None):
    path = Path(path) if path is not None else ROOT / 'user/nuclei/selection.json'
    if path.stat().st_size > 8192:
        raise ValueError('Arquivo de seleção nuclear excede o limite.')
    envelope = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(envelope, dict) or envelope.get('schema') != 1:
        raise ValueError('Formato de seleção nuclear inválido.')
    body = {key: envelope.get(key) for key in ('schema', 'configuration', 'generation')}
    if envelope.get('sha256') != digest(body):
        raise ValueError('Integridade da seleção nuclear inválida.')
    saved = body['generation']
    if not isinstance(saved, dict):
        raise ValueError('Geração nuclear ausente.')
    return {'configuration': configuration(body['configuration']), 'saved_generation': copy.deepcopy(saved),
            'current_generation': GENERATION,
            'compatibility': 'same_generation' if saved == GENERATION else 'changed_generation'}
