"""Freeze the small evaluated nuclear dataset used by the first force bench."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import pynucastro as pyna

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data' / 'science'
DEST.mkdir(parents=True, exist_ok=True)
rate = pyna.ReacLibLibrary().get_rate_by_name('t(d,n)he4')
raw = rate.original_data.encode()
(DEST / 'dt-reaclib.txt').write_bytes(raw)
package = Path(pyna.__file__).parent
half_path = package / 'nucdata' / 'AtomicMassEvaluation' / 'halflife2020.txt'
mass_path = package / 'nucdata' / 'AtomicMassEvaluation' / 'mass_excess2020.txt'
data = {
    'schema': 1, 'pynucastro': pyna.__version__,
    'rate': {'reaction': 'D + T -> He4 + n', 'source': rate.source,
             'label': rate.labelprops, 'Q_MeV': rate.Q,
             'sets': [s.a for s in rate.sets],
             'raw_file': 'dt-reaclib.txt', 'sha256': hashlib.sha256(raw).hexdigest(),
             'units': 'cm^3 mol^-1 s^-1',
             'url': 'https://reaclib.jinaweb.org/index.php'},
    'nuclides': {name: {'A': (n := pyna.Nucleus(name)).A, 'Z': n.Z,
                       'half_life_s': n.tau, 'binding_MeV_per_nucleon': n.nucbind,
                       'atomic_mass_MeV': n.mass} for name in ('n', 'p', 'd', 't', 'he3', 'he4', 'c14', 'n14', 'be7', 'li7')},
    'evaluations': {'name': 'AME2020 / NUBASE2020 via pynucastro',
                    'url': 'https://www-nds.iaea.org/amdc/',
                    'half_life_table_sha256': hashlib.sha256(half_path.read_bytes()).hexdigest(),
                    'mass_table_sha256': hashlib.sha256(mass_path.read_bytes()).hexdigest(),
                    'uncertainties': 'This extracted table does not carry uncertainties; do not report them as zero.'},
    'reference_rates': {str(t): float(rate.eval(t)) for t in (1e7, 3e7, 1e8, 3e8, 1e9)},
}
(DEST / 'nuclear.json').write_text(json.dumps(data, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
pins = '\n'.join(f'{n}=={importlib.metadata.version(n)}' for n in ('numpy', 'scipy', 'pynucastro'))
(ROOT / 'requirements-science-windows.txt').write_text(pins + '\n')
(ROOT / 'evidence' / 'forces-data.json').write_text(json.dumps({
    'schema': 1, 'dataset_sha256': hashlib.sha256((DEST / 'nuclear.json').read_bytes()).hexdigest(),
    'packages': pins.splitlines(), 'rate_source': rate.source,
    'evaluations': data['evaluations'],
}, indent=2) + '\n')
print(json.dumps({'dataset': str(DEST / 'nuclear.json'), 'source': rate.source, 'pins': pins}))
