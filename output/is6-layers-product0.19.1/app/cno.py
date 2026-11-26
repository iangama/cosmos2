"""Fixed-zone CNO-I kinetics: six channels, eight nuclei, two beta+ sources.

Abundances are nuclei per conventional baryon, n_i/(rho/m_u); mass defects
are accounted for separately in Q. This is not a stellar structure model.
"""
from pathlib import Path
from collections import Counter
import json
import math
import numpy as np
from scipy.integrate import solve_ivp
from scipy.constants import atomic_mass, Avogadro, elementary_charge
from stellar import rate_value, YEAR_S

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT/'data/science/cno1.json').read_text(encoding='utf-8'))
SPECIES = ('p','he4','c12','n13','c13','n14','o15','n15')
CHANNELS = ('c12pg','n13beta','c13pg','n14pg','o15beta','n15pa')
A = np.array([DATA['nuclides'][n]['A'] for n in SPECIES])
Z = np.array([DATA['nuclides'][n]['Z'] for n in SPECIES])
STOICHIOMETRY = np.array([[Counter(DATA['rates'][channel]['products'])[n]-
                           Counter(DATA['rates'][channel]['reactants'])[n]
                          for channel in CHANNELS] for n in SPECIES],dtype=float)
PARENTS = np.array([2,3,4,5,6,7])
BINARY = np.array([True,False,True,True,False,True])
NAMES = {'p':'H','he4':'⁴He','c12':'¹²C','n13':'¹³N','c13':'¹³C','n14':'¹⁴N','o15':'¹⁵O','n15':'¹⁵N'}
REACTIONS = [
    ('c12pg','¹²C + p → ¹³N + γ','electromagnetic'),
    ('n13beta','¹³N → ¹³C + e⁺ + ν','weak'),
    ('c13pg','¹³C + p → ¹⁴N + γ','electromagnetic'),
    ('n14pg','¹⁴N + p → ¹⁵O + γ','electromagnetic'),
    ('o15beta','¹⁵O → ¹⁵N + e⁺ + ν','weak'),
    ('n15pa','¹⁵N + p → ¹²C + ⁴He','strong'),
]

def coefficients(temperature,density,active=None,decay_basis='nubase2020'):
    if decay_basis not in ('nubase2020','reaclib_wc12'): raise ValueError('Avaliação beta desconhecida.')
    active = {name:True for name in CHANNELS} if active is None else active
    if set(active)!=set(CHANNELS) or any(type(v) is not bool for v in active.values()):
        raise ValueError('Canais CNO-I inválidos.')
    baryons = density/atomic_mass
    k = []
    for name,binary in zip(CHANNELS,BINARY):
        rate = DATA['rates'][name]
        value = (rate['nubase2020_decay_constant_s'] if not binary and decay_basis=='nubase2020'
                 else rate_value(temperature,rate))
        if binary: value *= baryons*1e-6/Avogadro
        k.append(value*rate['prefactor']*int(active[name]))
    return np.array(k)

def event_flux(abundances,k):
    factors = np.where(BINARY,abundances[0],1.)
    return k*abundances[PARENTS]*factors

def integrate_zone(temperature,density,hydrogen,catalyst,duration_s,*,initial_species='n14',
                   channels=None,decay_basis='nubase2020',tolerance=1e-9,initial_mass_fractions=None):
    if not 1e7<=temperature<=3e7 or not 1e4<=density<=3e5 or duration_s<=0 or duration_s>5e9*YEAR_S:
        raise ValueError('Zona CNO-I fora do domínio de temperatura/densidade/duração.')
    if not .05<=hydrogen<=.75 or not 1e-8<=catalyst<=.05 or initial_species not in ('c12','n14'):
        raise ValueError('Composição CNO-I fora do domínio.')
    active = {name:True for name in CHANNELS} if channels is None else channels
    k = coefficients(temperature,density,active,decay_basis)
    baryons = density/atomic_mass
    initial = np.zeros(14)
    if initial_mass_fractions is None:
        initial[0],initial[1] = hydrogen,(1-hydrogen-catalyst)/4
        j = SPECIES.index(initial_species)
        initial[j] = catalyst/A[j]
    else:
        if set(initial_mass_fractions)!=set(SPECIES): raise ValueError('Espécies iniciais incompletas.')
        x = np.array([initial_mass_fractions[n] for n in SPECIES])
        if np.any(x<0) or not np.isfinite(x).all() or abs(x.sum()-1)>1e-12:
            raise ValueError('Frações mássicas iniciais inválidas.')
        initial[:8] = x/A
    def rhs(_,y):
        events = event_flux(y,k)
        return np.r_[STOICHIOMETRY@events,events]
    def jacobian(_,y):
        event_jac = np.zeros((6,14))
        for i,parent in enumerate(PARENTS):
            event_jac[i,parent] = k[i]*(y[0] if BINARY[i] else 1)
            if BINARY[i]: event_jac[i,0] = k[i]*y[parent]
        return np.vstack((STOICHIOMETRY@event_jac,event_jac))
    times = np.linspace(0,duration_s,241)
    solution = solve_ivp(rhs,(0,duration_s),initial,t_eval=times,method='Radau',jac=jacobian,
                         rtol=tolerance,atol=[1e-13,1e-13,1e-16,1e-28,1e-16,1e-16,1e-28,1e-16]+[1e-17]*6)
    if not solution.success: raise RuntimeError('A rede CNO-I não convergiu: '+solution.message)
    values = solution.y.T
    if np.min(values[:,:8]) < -1e-20: raise RuntimeError('Abundância CNO-I negativa fora da tolerância.')
    mass = values[:,:8]*A
    baryon_error = float(np.max(np.abs(mass.sum(axis=1)-1)))
    catalyst_error = float(np.max(np.abs(values[:,2:8].sum(axis=1)-initial[2:8].sum())) /
                           initial[2:8].sum())
    if baryon_error>1e-8 or catalyst_error>1e-8: raise RuntimeError('Conservação CNO-I fora da tolerância.')
    q = np.array([DATA['rates'][name]['Q_MeV'] for name in CHANNELS])
    neutrino = np.array([DATA['neutrino_mean_MeV'].get(name,0) for name in CHANNELS])
    extents = values[:,8:]*baryons
    available = extents@q*1e6*elementary_charge
    neutrino_energy = extents@neutrino*1e6*elementary_charge
    all_fluxes = np.array([event_flux(y,k) for y in values])*baryons
    return {'name':'CNO-I','species':list(SPECIES),'time_s':times.tolist(),'mass_fractions':mass.tolist(),
            'baryon_density_m3':baryons,
            'number_per_baryon':values[:,:8].tolist(),'reaction_extents_m3':extents.tolist(),
            'event_rates_m3_s':all_fluxes.tolist(),
            'final_event_rates_m3_s':dict(zip(CHANNELS,all_fluxes[-1].tolist())),
            'energy_available_J_m3':available.tolist(),'energy_neutrinos_J_m3':neutrino_energy.tolist(),
            'energy_deposited_J_m3':(available-neutrino_energy).tolist(),
            'neutrino_count_m3':(extents[:,1]+extents[:,4]).tolist(),
            'neutrinos_by_parent_m3':{'n13':extents[:,1].tolist(),'o15':extents[:,4].tolist()},
            'electron_fraction':(values[:,:8]@Z).tolist(),
            'final_deposition_power_W_m3':float(all_fluxes[-1]@(q-neutrino)*1e6*elementary_charge),
            'channels':active,'decay_basis':decay_basis,'baryon_error':baryon_error,
            'catalyst_number_relative_error':catalyst_error,'minimum_abundance':float(np.min(values[:,:8])),
            'solver':{'method':'Radau','rtol':tolerance,'nfev':solution.nfev,'nlu':solution.nlu}}

def experiment(params,controls):
    strong,weak,em = (controls[name] for name in ('strong','weak','electromagnetic'))
    radiative = strong['acting'] and em['acting'] and em['effects']['cno_radiative_capture']
    active = {'c12pg':radiative and strong['effects']['cno_c12_capture'],
              'c13pg':radiative and strong['effects']['cno_c13_capture'],
              'n14pg':radiative and strong['effects']['cno_n14_capture'],
              'n15pa':strong['acting'] and strong['effects']['cno_n15_alpha'],
              'n13beta':weak['acting'] and weak['effects']['cno_n13_beta'],
              'o15beta':weak['acting'] and weak['effects']['cno_o15_beta']}
    args=(params['temperature_K'],params['density_kg_m3'],params['hydrogen_fraction'],
          params['catalyst_fraction'],params['duration_years']*YEAR_S)
    kwargs={'initial_species':params['initial_catalyst'],'decay_basis':params['decay_evaluation']}
    baseline = integrate_zone(*args,**kwargs)
    actual = baseline if all(active.values()) else integrate_zone(*args,channels=active,**kwargs)
    reference = {'channels':{name:{'Q_MeV':entry['Q_MeV'],
                                   'rate_coefficient':entry['nubase2020_decay_constant_s'] if name.endswith('beta') and kwargs['decay_basis']=='nubase2020' else rate_value(args[0],entry),
                                   'rate_unit':entry['units'],
                                   'source':entry['decay_source'] if name.endswith('beta') and kwargs['decay_basis']=='nubase2020' else entry.get('verified_citation',entry['source'])}
                             for name,entry in DATA['rates'].items()},
                 'decay_basis':kwargs['decay_basis'],'mean_neutrino_MeV':DATA['neutrino_mean_MeV'],
                 'Q_cycle_MeV':sum(entry['Q_MeV'] for entry in DATA['rates'].values()),
                 'half_lives_s':{n:(DATA['nuclides'][n]['half_life_NUBASE_s'] if kwargs['decay_basis']=='nubase2020' else math.log(2)/rate_value(args[0],DATA['rates'][n+'beta'])) for n in ('n13','o15')},
                 'channel_dependencies':'Capturas radiativas: ligação forte + emissão EM; beta+: fraca; saída p,α: forte. Taxas incluem a barreira eletrostática fixa. T/densidade e estrutura gravitacional são prescritas; não há evolução térmica nem luminosidade superficial.'}
    return {'model':'Ciclo CNO-I de seis canais: taxas REACLIB, beta+ avaliado e evolução rígida Radau.',
            'domain':DATA['domain']+' Q usa massas atômicas/arredondamento REACLIB e inclui aniquilação local de pósitrons; médias de neutrinos são aproximações solares fixas. '+DATA['uncertainties'],
            'influences':['strong','weak','electromagnetic'],'time_s':actual['time_s'],
            'time_display':{'unit':'anos julianos','seconds_per_unit':YEAR_S},
            'curves':[{'name':NAMES[name],'values':[row[i] for row in actual['mass_fractions']]}
                      for i,name in enumerate(SPECIES)],'curve_axis':'fração mássica','probe_kind':'composition',
            'reference_curve':[row[0] for row in baseline['mass_fractions']],
            'network':actual,'reactions':[{'key':key,'reaction':text,'force':force,
                                          'from':SPECIES[int(PARENTS[i])],
                                          'to':SPECIES[int(PARENTS[(i+1)%6])],
                                          'products':('β⁺ · e⁺ + ν' if not BINARY[i] else '+ p · '+('⁴He' if key=='n15pa' else 'γ'))}
                                         for i,(key,text,force) in enumerate(REACTIONS)],
            'reference':reference,'measurements':[
                {'label':'Potência nuclear depositada na zona ao final','value':actual['final_deposition_power_W_m3'],'unit':'W/m³'},
                {'label':'Energia depositada acumulada','value':actual['energy_deposited_J_m3'][-1],'unit':'J/m³'},
                {'label':'Energia levada por neutrinos','value':actual['energy_neutrinos_J_m3'][-1],'unit':'J/m³'},
                {'label':'Neutrinos produzidos, valor esperado','value':actual['neutrino_count_m3'][-1],'unit':'m⁻³'},
                {'label':'Resíduo de conservação bariônica','value':actual['baryon_error'],'unit':'absoluto'},
                {'label':'Resíduo do número de catalisadores CNO','value':actual['catalyst_number_relative_error'],'unit':'relativo'}],
            'sources':['https://reaclib.jinaweb.org/index.php','https://www-nds.iaea.org/amdc/',
                       'https://pynucastro.github.io/pynucastro/examples/pp-cno.html',DATA['neutrino_source']['url']]}
