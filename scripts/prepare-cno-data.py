"""Freeze the six forward CNO-I channels; evaluated sources remain per rate."""
from pathlib import Path
import hashlib
import json
import math
import pynucastro as pyna

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'data/science'
library = pyna.ReacLibLibrary()
queries = {'c12pg':'c12(p,g)n13', 'n13beta':'n13(,)c13',
           'c13pg':'c13(p,g)n14', 'n14pg':'n14(p,g)o15',
           'o15beta':'o15(,)n15', 'n15pa':'n15(p,a)c12'}
entries, rates = {}, []
for name, query in queries.items():
    rate = library.get_rate_by_name(query)
    if isinstance(rate, list):
        candidates = [r for r in rate if r.weak_type == 'beta_pos']
        if len(candidates) != 1: raise RuntimeError(f'Taxa ambígua: {query}')
        rate = candidates[0]
    if name.endswith('beta') and rate.weak_type != 'beta_pos':
        raise RuntimeError(f'Canal fraco incorreto: {query}')
    rates.append(rate)
    raw = rate.original_data.encode()
    filename = f'cno1-{name}-reaclib.txt'
    (DEST/filename).write_bytes(raw)
    entries[name] = {'fname':rate.fname, 'reactants':[n.raw for n in rate.reactants],
                     'products':[n.raw for n in rate.products], 'Q_MeV':rate.Q,
                     'source':rate.source, 'sets':[s.a for s in rate.sets],
                     'prefactor':rate.prefactor, 'weak_type':rate.weak_type,
                     'raw_file':filename, 'sha256':hashlib.sha256(raw).hexdigest(),
                     'units':'s^-1' if name.endswith('beta') else 'cm^3 mol^-1 s^-1',
                     'reference_rates':{str(t):float(rate.eval(t)) for t in (1e7,1.5e7,2e7,3e7)}}
nuclides = {name:{'A':(n:=pyna.Nucleus(name)).A,'Z':n.Z,
                  'atomic_mass_MeV':n.mass,'half_life_NUBASE_s':n.tau}
            for name in ('p','he4','c12','n13','c13','n14','o15','n15')}
for channel,parent in (('n13beta','n13'),('o15beta','o15')):
    entries[channel]['nubase2020_decay_constant_s'] = math.log(2)/nuclides[parent]['half_life_NUBASE_s']
    entries[channel]['decay_source'] = 'NUBASE2020 via pinned pynucastro; REACLIB wc12 retained as an explicit comparison basis.'
# The package's ls09 citation fields are malformed; keep them above, alongside
# the publisher-verified bibliographic record, rather than inventing an author.
entries['c12pg']['verified_citation'] = {'author':'ZhiHong Li et al.',
    'title':'Determination of the 12C(p, gamma)13N reaction rates from the 12C(7Li,6He)13N reaction',
    'journal':'Science China Physics, Mechanics & Astronomy53,658-663(2010)',
    'doi':'10.1007/s11433-010-0128-8',
    'url':'https://link.springer.com/article/10.1007/s11433-010-0128-8'}
collection = pyna.RateCollection(rates=rates)
test_x = {'p':.35,'he4':.64,**{n:.01/6 for n in ('c12','n13','c13','n14','o15','n15')}}
composition = pyna.Composition(collection.unique_nuclei)
for name,value in test_x.items(): composition[pyna.Nucleus(name)] = value
references = []
for temperature in (1e7,1.5e7,3e7):
    state = pyna.ThermoState(rho=150,T=temperature,comp=composition)
    ydots = collection.evaluate_ydots(state)
    references.append({'T_K':temperature,'rho_g_cm3':150,'mass_fractions':test_x,
                       'ydot_mol_g_s':{n.raw:float(v) for n,v in ydots.items()},
                       'basis':'Original REACLIB coefficients, including wc12 weak channels; conventional molar normalization.'})
data = {'schema':1,'pynucastro':pyna.__version__,'network':'CNO-I forward six-channel cycle',
        'rates':entries,'nuclides':nuclides,'upstream_derivative_references':references,
        'neutrino_mean_MeV':{'n13beta':.706,'o15beta':.996},
        'neutrino_source':{'url':'https://arxiv.org/abs/hep-ph/0108148',
                           'doi':'10.1103/PhysRevC.65.025801','table':'I',
                           'scope':'Fixed solar-profile means; not spectra recalculated from T.'},
        'domain':'10-30 MK; fixed T/rho; unscreened CNO-I forward network only. No CNO-II/III, hot-CNO, reverse reactions, transport or thermal/hydrostatic evolution.',
        'uncertainties':'Rate fit/mass/half-life uncertainties absent from extraction; numerical tolerances are separate.'}
path = DEST/'cno1.json'
path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
(ROOT/'evidence/cno-data.json').write_text(json.dumps({
    'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
    'rates':{name:entry['source'] for name,entry in entries.items()},
    'nuclides':'AME2020/NUBASE2020 via pinned pynucastro3.1.0',
    'neutrino_source':data['neutrino_source']},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'dataset':str(path),'rates':list(entries),
                  'Q_cycle_MeV':sum(e['Q_MeV'] for e in entries.values())}))
