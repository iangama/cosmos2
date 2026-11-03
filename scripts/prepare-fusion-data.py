"""Freeze seven original forward fits and independent upstream evaluations."""
from pathlib import Path
import hashlib
import json
import pynucastro as pyna

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data/science'
library = pyna.ReacLibLibrary()
queries = {'dt': 't(d,n)he4', 'ddn': 'd(d,n)he3', 'ddp': 'd(d,p)t',
           'dp': 'd(p,g)he3', 'he3he3': 'he3(he3,pp)he4',
           'li7p': 'li7(p,a)he4', 'c12alpha': 'c12(a,g)o16'}
rates, nuclides = {}, {}
for key, query in queries.items():
    rate = library.get_rate_by_name(query)
    if isinstance(rate, list):
        raise ValueError('Ambiguous rate: ' + query)
    raw = rate.original_data.encode('ascii')
    filename = f'fusion-{key}-reaclib.txt'
    (DEST / filename).write_bytes(raw)
    rates[key] = {'query': query, 'fname': rate.fname,
                  'reactants': [n.raw for n in rate.reactants],
                  'products': [n.raw for n in rate.products],
                  'Q_MeV': rate.Q, 'prefactor': rate.prefactor,
                  'label': rate.labelprops.strip(), 'source': rate.source,
                  'sets': [s.a for s in rate.sets], 'units': 'cm^3 mol^-1 s^-1',
                  'raw_file': filename, 'sha256': hashlib.sha256(raw).hexdigest(),
                  'reference_rates': {str(t): float(rate.eval(t))
                                      for t in (1e7, 3e7, 1e8, 3e8, 1e9)}}
    for n in [*rate.reactants, *rate.products]:
        nuclides[n.raw] = {'A': n.A, 'Z': n.Z,
                          'ame2020_id': f'nucleus:ame2020:{n.Z}:{n.A}'}
data = {'schema': 1, 'pynucastro': pyna.__version__, 'rates': rates,
        'nuclides': nuclides,
        'domain': '10-1000MK; forward isolated mixtures; fixed T/volume; no screening, reverse or secondary reactions, confinement, thermal feedback or deposition model',
        'uncertainties': 'Fit uncertainties not in this extraction; unknown, not zero.',
        'sources': ['https://reaclib.jinaweb.org/',
                    'https://pynucastro.github.io/pynucastro/_modules/pynucastro/rates/rate.html']}
path = DEST / 'fusion.json'
path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
receipt = {'schema': 1, 'dataset': 'data/science/fusion.json',
           'dataset_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
           'method': 'Local installed pynucastro3.1.0, original REACLIB text plus upstream eval(T); no network replacement of existing datasets',
           'rates': {key: {'source': rate['source'], 'raw_file': rate['raw_file'],
                           'sha256': rate['sha256']} for key, rate in rates.items()}}
(ROOT / 'evidence/fusion-data.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'dataset_sha256': receipt['dataset_sha256'], 'channels': list(rates)}))
