"""Freeze the three forward pp-I reaction rates, with their upstream checks."""
from pathlib import Path
import hashlib
import json
import pynucastro as pyna

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data' / 'science'
library = pyna.ReacLibLibrary()
pp = next(rate for rate in library.get_rate_by_name('p(p,e)d') if rate.weak_type == 'beta_pos')
rates = {
    'pp': pp,
    'dp': library.get_rate_by_name('d(p,g)he3'),
    'he3he3': library.get_rate_by_name('he3(he3,pp)he4'),
}
entries = {}
for name, rate in rates.items():
    raw = rate.original_data.encode()
    filename = f'pp1-{name}-reaclib.txt'
    (DEST / filename).write_bytes(raw)
    entries[name] = {
        'fname': rate.fname, 'reactants': [n.raw for n in rate.reactants],
        'products': [n.raw for n in rate.products], 'Q_MeV': rate.Q,
        'source': rate.source, 'sets': [s.a for s in rate.sets],
        'prefactor': rate.prefactor, 'weak_type': rate.weak_type,
        'raw_file': filename, 'sha256': hashlib.sha256(raw).hexdigest(),
        'units': 'cm^3 mol^-1 s^-1',
        'reference_rates': {str(t): float(rate.eval(t)) for t in (1e7, 1.5e7, 2e7, 3e7)},
    }
data = {'schema': 1, 'pynucastro': pyna.__version__, 'network': 'pp-I forward only',
        'rates': entries, 'nuclides': {n: {'A': (nuc := pyna.Nucleus(n)).A, 'Z': nuc.Z}
                                     for n in ('p', 'd', 'he3', 'he4')},
        'pp_neutrino_mean_MeV': .2668,
        'neutrino_source': {'url': 'https://arxiv.org/abs/hep-ph/0108148',
                            'doi': '10.1103/PhysRevC.65.025801', 'table': 'I',
                            'scope': 'Solar-profile mean, fixed approximation; not recalculated from T.'},
        'domain': 'Forward pp-I only; 10-30 MK; fixed density/T, unscreened evaluated rates. No pep, pp-II/III, CNO or reverse reactions.',
        'uncertainties': 'Rate fit uncertainties not carried by this extraction; numerical tolerances are separate.'}
path = DEST / 'pp1.json'
path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
(ROOT / 'evidence/stellar-data.json').write_text(json.dumps({
    'dataset_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'rates': {k: v['source'] for k, v in entries.items()}, 'neutrino_source': data['neutrino_source'],
}, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'dataset': str(path), 'rates': list(entries)}))
