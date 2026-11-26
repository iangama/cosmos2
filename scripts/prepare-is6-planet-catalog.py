"""Assemble the pinned data model for the eight-planet reference catalogue."""
import argparse
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-spatial-import-product0.22.1/app'
sys.path.insert(0, str(APP))
import solar_contract

ROWS = [
    ('10', 'Sun', 'Sol', 'star', '0', None),
    ('199', 'Mercury', 'Mercúrio', 'planet', '1', 'IAU_MERCURY'),
    ('299', 'Venus', 'Vênus', 'planet', '2', 'IAU_VENUS'),
    ('399', 'Earth', 'Terra', 'planet', '3', 'IAU_EARTH'),
    ('301', 'Moon', 'Lua', 'moon', '3', 'IAU_MOON'),
    ('499', 'Mars', 'Marte', 'planet', '4', 'IAU_MARS'),
    ('599', 'Jupiter', 'Júpiter', 'planet', '5', 'IAU_JUPITER'),
    ('699', 'Saturn', 'Saturno', 'planet', '6', 'IAU_SATURN'),
    ('799', 'Uranus', 'Urano', 'planet', '7', 'IAU_URANUS'),
    ('899', 'Neptune', 'Netuno', 'planet', '8', 'IAU_NEPTUNE'),
]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def printed_parameter(path, expression, url):
    rows = [(i, line, match.group(1)) for i, line in enumerate(path.read_text().splitlines(), 1)
            if (match := re.match(expression, line))]
    numbers = {Decimal(raw) for _, _, raw in rows}
    if len(numbers) != 1:
        raise ValueError('One consistent printed GM required: ' + str(path))
    raw = rows[0][2]
    return dict(value=float(Decimal(raw) * Decimal(10)**9), unit='m^3/s^2',
                raw_value_km3_s2=raw, uncertainty=None,
                uncertainty_reason='Source standard uncertainty was not adopted.',
                source=url, source_file=path.relative_to(ROOT).as_posix(), source_sha256=sha(path),
                source_rows=[dict(line=i, text=line) for i, line, _ in rows],
                source_resolution_m3_s2=float(Decimal(10)**Decimal(raw).as_tuple().exponent * Decimal(10)**9),
                origin='Printed physical-body model parameter')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    label = parser.parse_args().label
    if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        parser.error('Invalid label')
    data_path = ROOT / 'evidence' / f'is6-planet-catalog-data-{label}.json'
    data = json.loads(data_path.read_text(encoding='utf-8-sig'))
    acquisition = json.loads((ROOT / 'evidence' / f'is6-planet-catalog-acquisition-{label}.json').read_text())
    assert data['accepted'] and data['completed'] and acquisition['completed']
    folder = ROOT / 'output' / f'is6-planet-catalog-model-{label}'
    folder.mkdir(exist_ok=False)
    runtime = dict(data['base_sha256'])
    pinned = solar_contract.providers()
    runtime.update({p: s for provider in pinned.values() for p, s in provider['kernels_sha256'].items()})
    sat = ROOT / 'data/spice/saturn-center-sat441.bsp'
    sat_receipt = json.loads((ROOT / 'evidence/saturn-subset.json').read_text())
    assert sha(sat) == sat_receipt['sha256']
    runtime[sat.relative_to(ROOT).as_posix()] = sha(sat)
    center_files = {'599': solar_contract.SUBSET, '699': sat.relative_to(ROOT).as_posix()}
    for entry in data['centers']:
        runtime[entry['file']] = entry['sha256']
        center_files[str(entry['target'])] = entry['file']
    gm = copy.deepcopy(solar_contract.parameters())
    de = ROOT / 'data/spice/de442_tech-comments.txt'
    url = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de442_tech-comments.txt'
    for target, code in [('199', 'GM1'), ('299', 'GM2')]:
        gm[target] = printed_parameter(de, r'^\s*' + code + r'\s+\S+\s+\S+\s+(\S+)\s*$', url)
    for target, name, path, url in [
        ('499', 'Mars', ROOT / data['centers'][0]['comments']['path'], acquisition['files']['mar099s.bsp']['url']),
        ('799', 'Uranus', ROOT / data['centers'][1]['comments']['path'], acquisition['files']['ura182.bsp']['url']),
        ('899', 'Neptune', ROOT / data['centers'][2]['comments']['path'], acquisition['files']['nep097.bsp']['url']),
        ('699', 'Saturn', ROOT / 'output/saturn-acquisition/sat459.cmt', sat_receipt['source']['url'])
    ]:
        gm[target] = printed_parameter(path, r'^\s*' + name + r'\s+' + target + r'\s+(\S+)\s+\d+\s+\d+\s+', url)
    bodies = []
    for target, node, name, kind, parent, frame in ROWS:
        parameter = gm[target]
        if 'source_file' in parameter:
            runtime[parameter['source_file']] = parameter['source_sha256']
        bodies.append(dict(id='sol:naif:' + target, naif_id=target, name=name, node=node,
                           entity_kind='physical_body', body_kind=kind,
                           chain_naif_ids=[target, '0'] if parent == '0' else [target, parent, '0'],
                           relative_kernel=center_files.get(target, 'data/spice/de442s.bsp'),
                           rotation_frame=frame, GM=parameter))
    assert all(sha(ROOT / p) == seal for p, seal in runtime.items())
    result = dict(schema=1, kind='eight_planet_reference_data', version='0.1.0', bodies=bodies,
                  application_utc=data['application_utc'], runtime_sha256=runtime,
                  extra_spk=list(center_files.values()), source_data_receipt=data_path.relative_to(ROOT).as_posix(),
                  source_data_sha256=sha(data_path), recipe_sha256=sha(Path(__file__)),
                  scope='Geometric physical centers and model parameters for an isolated catalogue candidate')
    path = folder / 'catalog-data.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bodies=len(bodies),
                          planets=sum(b['body_kind'] == 'planet' for b in bodies))), flush=True)


if __name__ == '__main__':
    main()
