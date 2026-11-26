"""Five-epoch independent service comparison of the new physical centers."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys
import traceback
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'output/is6-planet-catalog-staging'),
               str(ROOT / 'output/is6-spatial-import-product0.22.1/app')]
import atlas
import is6_planet_catalog as catalog

EPOCHS = ['1995-01-01T00:00:00', '2000-01-01T12:00:00', '2026-10-11T12:00:00',
          '2030-06-15T18:30:00', '2049-12-30T23:59:59']
QUERIES = [('199', '0'), ('299', '0'), ('499', '4'), ('799', '7'), ('899', '8')]
POSITION_LIMIT_M = 1.
VELOCITY_LIMIT_M_S = .00001
EXPECTED_MODELS = {'199': 'DE442', '299': 'DE442', '499': 'MAR099',
                   '799': 'URA182', '899': 'NEP097'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    label = parser.parse_args().label
    if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        parser.error('Invalid label')
    folder = ROOT / 'output' / f'is6-planet-catalog-horizons-{label}'
    receipt = ROOT / 'evidence' / f'is6-planet-catalog-horizons-{label}.json'
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve Horizons comparisons')
    folder.mkdir()
    result = dict(same_model_comparisons_accepted=False, completed=False, queries=[],
                  script_sha256=sha(Path(__file__)), catalogue_sha256=sha(Path(catalog.__file__)),
                  data_sha256=catalog.DATA_SHA256, position_limit_m=POSITION_LIMIT_M,
                  velocity_limit_m_s=VELOCITY_LIMIT_M_S,
                  scope='Same-model service agreement and separately recorded cross-model differences',
                  timestamp_basis='Printed Horizons JD converted to ET, evaluated in full original source coverage')
    try:
        catalog.states(EPOCHS[2])
        spice = atlas.SPICE
        data = catalog._data()
        for path in data['extra_spk']:
            spice.furnsh(str(ROOT / path))
        prepared = json.loads((ROOT / data['source_data_receipt']).read_text(encoding='utf-8-sig'))
        source_by_target = {str(row['target']): row['source'] for row in prepared['centers']}
        source_sha = prepared['sources']
        dates = [spice.unitim(spice.str2et(t), 'ET', 'JDTDB') for t in EPOCHS]
        for target, center in QUERIES:
            params = dict(
                format='json', COMMAND=f"'{target}'", OBJ_DATA="'YES'", MAKE_EPHEM="'YES'",
                EPHEM_TYPE="'VECTORS'", CENTER=f"'500@{center}'", REF_PLANE="'FRAME'",
                REF_SYSTEM="'ICRF'", VEC_CORR="'NONE'", OUT_UNITS="'KM-S'", VEC_TABLE="'2'",
                CSV_FORMAT="'YES'", TIME_TYPE="'TDB'", TIME_DIGITS="'FRACSEC'", TLIST_TYPE="'JD'",
                TLIST="'" + ','.join(f'{date:.16f}' for date in dates) + "'"
            )
            url = 'https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(params)
            cached = ROOT / 'output/is6-planet-catalog-horizons-20261110a' / f'{target}-relative-{center}.json'
            if not cached.exists():
                cached = ROOT / 'output/is6-planet-catalog-horizons-20261110b' / f'{target}-relative-{center}.json'
            if cached.exists():
                print('Using preserved response ' + target + '/' + center, flush=True)
                raw = cached.read_bytes()
            else:
                print('Querying ' + target + '/' + center, flush=True)
                with urllib.request.urlopen(url, timeout=60) as response:
                    raw = response.read()
            raw_path = folder / f'{target}-relative-{center}.json'
            raw_path.write_bytes(raw)
            response = json.loads(raw)
            if response.get('error'):
                raise ValueError(response['error'])
            text = response['result']
            header = text.split('$$SOE')[0]
            source_match = re.search(r'Target body name:.*\{source:\s*([^}]+)\}', header)
            assert source_match, 'Horizons target source model required'
            horizon_model = source_match.group(1).strip()
            same_model = horizon_model.upper() == EXPECTED_MODELS[target]
            rows = list(csv.reader(io.StringIO(text.split('$$SOE')[1].split('$$EOE')[0].strip())))
            assert len(rows) == len(EPOCHS)
            entry = dict(target=target, center=center, query=params, url=url,
                         header=header, local_model=EXPECTED_MODELS[target], horizons_model=horizon_model,
                         comparison_kind='same_model_agreement' if same_model else 'cross_model_difference',
                         response=raw_path.relative_to(ROOT).as_posix(),
                         response_sha256=sha(raw_path), cases=[])
            if target in source_by_target:
                relative = source_by_target[target]
                path = ROOT / relative
                with path.open('rb') as stream:
                    source_seal = hashlib.file_digest(stream, 'sha256').hexdigest()
                assert source_seal == source_sha[relative]
                spice.furnsh(str(path))
                entry['comparison_kernel'] = dict(path=relative, sha256=source_seal)
            for utc, row in zip(EPOCHS, rows, strict=True):
                et = spice.unitim(float(row[0]), 'JDTDB', 'ET')
                state, _ = spice.spkezr(target, et, 'J2000', 'NONE', center)
                pe = math.dist(state[:3], [float(x) for x in row[2:5]]) * 1000
                ve = math.dist(state[3:], [float(x) for x in row[5:8]]) * 1000
                entry['cases'].append(dict(utc=utc, jd_tdb=float(row[0]), position_difference_m=pe,
                                          velocity_difference_m_s=ve,
                                          passed=pe <= POSITION_LIMIT_M and ve <= VELOCITY_LIMIT_M_S))
            result['queries'].append(entry)
            receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        result['completed'] = True
        compatible = [q for q in result['queries'] if q['comparison_kind'] == 'same_model_agreement']
        assert {q['target'] for q in compatible} == {'499'}
        result['same_model_targets'] = [q['target'] for q in compatible]
        result['same_model_comparisons_accepted'] = all(c['passed'] for q in compatible for c in q['cases'])
        result['cross_model_differences_recorded'] = [
            q['target'] for q in result['queries'] if q['comparison_kind'] == 'cross_model_difference'
        ]
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        if atlas.SPICE is not None:
            atlas.SPICE.kclear()
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(same_model_comparisons_accepted=result['same_model_comparisons_accepted'], completed=result['completed'],
                          queries=len(result['queries']), failure=result.get('failure'))), flush=True)
    return 0 if result['same_model_comparisons_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
