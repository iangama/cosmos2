"""Curate ten ground-state parents without mixing evaluated generations."""
from collections import Counter
from decimal import Decimal
from pathlib import Path
import csv
import hashlib
import io
import json

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'output/research-decays'
DEST = ROOT / 'data/science'
SPECS = {'n': ('1n', 'bm'), 't': ('3h', 'bm'), 'c14': ('14c', 'bm'),
         'be7': ('7be', 'bp'), 'n13': ('13n', 'bp'), 'o15': ('15o', 'bp'),
         'f18': ('18f', 'bp'), 'na22': ('22na', 'bp'),
         'sr90': ('90sr', 'bm'), 'y90': ('90y', 'bm')}
receipts = {r['key']: r for r in json.loads((RESEARCH / 'acquisition.json').read_text())['files']}
used = {}


def raw(key):
    r = receipts[key]
    path = ROOT / r['file']
    content = path.read_bytes()
    assert len(content) == r['bytes'] and hashlib.sha256(content).hexdigest() == r['sha256']
    filename = 'decays-' + key + ('.txt' if key == 'nubase-original' else '.csv')
    (DEST / filename).write_bytes(content)
    used[key] = {**r, 'path': 'data/science/' + filename}
    return content


def rows(key):
    result = list(csv.DictReader(io.StringIO(raw(key).decode('utf-8'))))
    if not result:
        raise ValueError('Empty source: ' + key)
    return result


def number(token):
    return None if token.strip() == '' else float(Decimal(token))


def quantity(row, value, uncertainty):
    return {'value': number(row.get(value, '')), 'uncertainty_raw': row.get(uncertainty, ''),
            'raw_value': row.get(value, ''), 'unit': 'keV',
            'uncertainty_propagated': False}


nubase = {}
for line_number, line in enumerate(raw('nubase-original').decode('ascii').splitlines(), 1):
    if line.startswith('#') or len(line) < 119 or line[7] != '0':
        continue
    a, z = int(line[:3]), int(line[4:7])
    nubase[(z, a)] = {'source_line': line_number, 'raw_line': line,
                      'half_life_raw': line[69:78].strip(), 'unit_raw': line[78:80].strip(),
                      'uncertainty_raw': line[81:88].strip(), 'modes_raw': line[119:].strip()}

parents, channels, nodes = {}, {}, {}
for key, (nuclide, kind) in SPECS.items():
    ground = [r for r in rows(nuclide + '-gs') if Decimal(r['energy']) == 0 and not r['energy_shift']]
    assert len(ground) == 1
    gs = ground[0]
    z, a = int(gs['z']), int(gs['z']) + int(gs['n'])
    source_key = 'decay:' + str(z) + ':' + str(a)
    label = 'n' if z == 0 else gs['symbol'] + '-' + str(a)
    nodes[source_key] = {'A': a, 'Z': z, 'label': label}
    nb = nubase[(z, a)]
    factors = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'y': 31556926, 'ky': 31556926000}
    nb['half_life_s'] = float(Decimal(nb['half_life_raw']) * factors[nb['unit_raw']])
    nb['uncertainty_s'] = float(Decimal(nb['uncertainty_raw']) * factors[nb['unit_raw']])
    nb['year_definition'] = 'NUBASE2020 tropical year =365.2422d, rounded to31556926s as published'
    parent = {'id': key, 'node_id': source_key, 'label': label,
              'half_life_s': number(gs['half_life_sec']), 'half_life_uncertainty_s': number(gs['unc_hls']),
              'half_life_raw': {k: gs[k] for k in ('half_life', 'unit_hl', 'unc_hl', 'operator_hl')},
              'ENSDF_ground_state': gs, 'NUBASE2020_comparison': nb, 'channels': []}
    assert parent['half_life_s'] > 0 and not gs['operator_hl']
    rad = rows(nuclide + '-' + kind)
    for row_index, row in enumerate(rad):
        if row['p_energy_shift'] or Decimal(row['p_energy']) != 0:
            continue
        assert int(row['p_z']) == z and int(row['p_n']) + z == a
        daughter_z, daughter_a = int(row['d_z']), int(row['d_z']) + int(row['d_n'])
        assert daughter_a == a
        daughter_id = 'decay:' + str(daughter_z) + ':' + str(a)
        nodes[daughter_id] = {'A': a, 'Z': daughter_z, 'label': row['d_symbol'] + '-' + str(a)}
        modes = [('beta_minus', 'intensity_beta', 'unc_ib', 'anti_nu_mean_energy')] if kind == 'bm' else [
            ('beta_plus', 'intensity_beta', 'unc_ib', 'nu_mean_energy'),
            ('electron_capture', 'intensity_ec', 'unc_ie', 'energy_ec')]
        for mode, intensity_field, sigma_field, nu_field in modes:
            intensity = number(row.get(intensity_field, ''))
            if intensity is None:
                # Pure EC rows have no positron branch, explicitly labelled EC.
                assert kind == 'bp' and mode == 'beta_plus' and row['decay'] == 'EC'
                continue
            if intensity == 0:
                continue
            assert 0 < intensity <= 100
            assert daughter_z - z == (1 if mode == 'beta_minus' else -1)
            branch_key = key + '_' + mode + '_' + str(row_index)
            neutrino = quantity(row, nu_field, 'unc_eec' if mode == 'electron_capture' else 'unc_ame')
            q = quantity(row, 'q', 'unc_q')
            beta = quantity(row, 'mean_energy', 'unc_me') if mode != 'electron_capture' else None
            excitation = number(row['daughter_level_energy'])
            assert q['value'] is not None and 0 <= neutrino['value'] < q['value']
            branch = {'id': branch_key, 'parent': key, 'parent_node': source_key,
                      'daughter_node': daughter_id, 'daughter_label': nodes[daughter_id]['label'],
                      'mode': mode, 'printed_intensity_percent': intensity,
                      'intensity_uncertainty_raw': row.get(sigma_field, ''),
                      'daughter_excitation_keV': excitation,
                      'Q': q, 'mean_beta_energy': beta, 'neutrino_energy': neutrino,
                      'neutrino_energy_kind': 'nominal_EC_energy_approximation_no_shell_distribution' if mode == 'electron_capture' else 'source_mean_beta_neutrino_energy',
                      'source_file': used[nuclide + '-' + kind]['path'], 'source_line': row_index + 2,
                      'source_row': row}
            if beta:
                pair_rest = 1021.99790138 if mode == 'beta_plus' else 0
                branch['independent_source_energy_residual_keV'] = q['value'] - excitation - beta['value'] - neutrino['value'] - pair_rest
            channels[branch_key] = branch
            parent['channels'].append(branch_key)
    total = sum(Decimal(str(channels[k]['printed_intensity_percent'])) for k in parent['channels'])
    assert Decimal('99.5') <= total <= Decimal('100.5')
    parent['printed_total_intensity_percent'] = float(total)
    parent['branch_normalization_factor'] = float(Decimal(100) / total)
    for c in parent['channels']:
        channels[c]['probability'] = float(Decimal(str(channels[c]['printed_intensity_percent'])) / total)
    assert abs(sum(channels[k]['probability'] for k in parent['channels']) - 1) < 1e-14
    parents[key] = parent

data = {'schema': 1, 'parents': parents, 'channels': channels, 'nodes': nodes,
        'source': 'IAEA LiveChart ENSDF snapshot; do not mix with NUBASE comparison',
        'source_scope': 'CSV returned by API; evaluation dates/authors per row, extraction date is not measurement date',
        'normalization': 'Within each parent, complete printed intensities divided by printed total; raw probabilities and normalization retained',
        'energy_convention': 'ENSDF atomic Q includes daughter excitation and possible positron annihilation; no deposition model',
        'neutrino_EC': 'Nominal per-branch energy_ec approximation; no atomic shell distribution',
        'source_energy_residual': 'Independent electron/neutrino/Q entries can differ; preserved, not forced to close',
        'pair_rest_reference_keV': 1021.99790138,
        'sources': ['https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html',
                    'https://iaea-nds.github.io/ndlab/code.html',
                    'https://www-nds.iaea.org/amdc/ame2020/NUBASE2020.pdf'],
        'raw_files': used}
path = DEST / 'decays.json'
path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
receipt = {'schema': 1, 'dataset': 'data/science/decays.json', 'bytes': path.stat().st_size,
           'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
           'files': list(used.values()), 'source': data['source']}
(ROOT / 'evidence/decay-data.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'parents': len(parents), 'channels': len(channels), 'nodes': len(nodes),
                  'raw_files': len(used), 'dataset_sha256': receipt['sha256'],
                  'printed_intensity_totals': {k: p['printed_total_intensity_percent'] for k, p in parents.items()}}))
