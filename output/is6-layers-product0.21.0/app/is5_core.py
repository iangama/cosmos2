"""One prescribed pp-I/CNO-I zone: shared fuel, explicit leptons and energy ledger."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import math
import platform
import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.constants import Avogadro,atomic_mass,elementary_charge
from is5_reference_pp import rate_value,YEAR_S

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
HERE=Path(__file__).resolve().parent
DATA=ROOT/'data/science'
PP=json.loads((DATA/'pp1.json').read_text(encoding='utf-8'))
CNO=json.loads((DATA/'cno1.json').read_text(encoding='utf-8'))
SPECIES=('p','d','he3','he4','c12','n13','c13','n14','o15','n15')
CHANNELS=('pp','dp','he3he3','c12pg','n13beta','c13pg','n14pg','o15beta','n15pa')
RATES={**PP['rates'],**CNO['rates']}
NUCLIDES={**CNO['nuclides'],**PP['nuclides']}
A=np.array([NUCLIDES[n]['A'] for n in SPECIES],dtype=float)
Z=np.array([NUCLIDES[n]['Z'] for n in SPECIES],dtype=float)
S=np.array([[Counter(RATES[c]['products'])[n]-Counter(RATES[c]['reactants'])[n] for c in CHANNELS] for n in SPECIES],dtype=float)
REACTANTS=[Counter(RATES[c]['reactants']) for c in CHANNELS]
WEAK=np.array([c in ['pp','n13beta','o15beta'] for c in CHANNELS],dtype=float)
Q_MEV=np.array([RATES[c]['Q_MeV'] for c in CHANNELS])
NEUTRINO_MEV=np.array([PP['pp_neutrino_mean_MeV'] if c=='pp' else CNO['neutrino_mean_MeV'].get(c,0.) for c in CHANNELS])
CODE=['is5_core.py','is5_reference_pp.py','is5_reference_cno.py']
FILES=[HERE/n for n in CODE]+[HERE/'reference-manifest.json',DATA/'pp1.json',DATA/'cno1.json']+[DATA/RATES[c]['raw_file'] for c in CHANNELS]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
IMPORTED={p.relative_to(ROOT).as_posix():sha(p) for p in FILES}
MAX_RHS_EVALUATIONS=200000
DEFAULT_PARAMETERS=dict(temperature_K=15e6,density_kg_m3=1.5e5,hydrogen_fraction=.34,catalyst_fraction=.01,catalyst_seed='n14',duration_s=1e6*YEAR_S,volume_m3=1.)

def number(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite numeric SI value required')
    return float(value)

def parameters(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULT_PARAMETERS):raise ValueError('Complete prescribed-zone parameter schema required')
    p={k:number(v) for k,v in value.items() if k!='catalyst_seed'};p['catalyst_seed']=value['catalyst_seed']
    if not 1e7<=p['temperature_K']<=3e7 or not 1e4<=p['density_kg_m3']<=3e5:raise ValueError('Prescribed zone T/density outside adopted domain')
    if not .05<=p['hydrogen_fraction']<=.75 or not 0<=p['catalyst_fraction']<=.05 or p['catalyst_seed'] not in ['c12','n14']:raise ValueError('Initial composition outside adopted domain')
    if not 1<=p['duration_s']<=5e9*YEAR_S or not 1e-6<=p['volume_m3']<=1e18:raise ValueError('Prescribed duration/volume outside adopted domain')
    return p

def switches(value,keys):
    value={k:True for k in keys} if value is None else value
    if not isinstance(value,dict) or set(value)!=set(keys) or any(type(v) is not bool for v in value.values()):raise ValueError('Exact explicit physical switches required')
    return dict(value)

def generation():
    if any(sha(ROOT/n)!=v for n,v in IMPORTED.items()):raise ValueError('Restart after scientific source/data changes')
    for c in CHANNELS:
        if sha(DATA/RATES[c]['raw_file'])!=RATES[c]['sha256']:raise ValueError('Pinned rate source differs')
    return dict(schema=1,id='cosmos2:is5-prescribed-coupled-zone',version='0.1.0',source_sha256=dict(IMPORTED),runtime=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),constants=dict(Avogadro_mol_inverse=Avogadro,atomic_mass_kg=atomic_mass,elementary_charge_C=elementary_charge))

def active_channels(acting=None,channel_switches=None):
    a=switches(acting,['strong','weak','electromagnetic']);c=switches(channel_switches,CHANNELS)
    dependencies={'pp':a['strong'] and a['weak'],'dp':a['strong'] and a['electromagnetic'],'he3he3':a['strong'],
        'c12pg':a['strong'] and a['electromagnetic'],'n13beta':a['weak'],'c13pg':a['strong'] and a['electromagnetic'],
        'n14pg':a['strong'] and a['electromagnetic'],'o15beta':a['weak'],'n15pa':a['strong']}
    return a,c,{k:c[k] and dependencies[k] for k in CHANNELS}

def coefficients(temperature_K,density_kg_m3,active=None,decay_basis='nubase2020'):
    t,rho=number(temperature_K),number(density_kg_m3)
    if not 1e7<=t<=3e7 or not 1e4<=rho<=3e5:raise ValueError('Coefficient conditions outside adopted domain')
    active=switches(active,CHANNELS)
    if decay_basis not in ['nubase2020','reaclib_wc12']:raise ValueError('Unknown beta evaluation')
    k=[];nb=rho/atomic_mass
    for c,reactants in zip(CHANNELS,REACTANTS):
        binary=sum(reactants.values())==2
        value=RATES[c]['nubase2020_decay_constant_s'] if c in ['n13beta','o15beta'] and decay_basis=='nubase2020' else rate_value(t,RATES[c])
        prefactor=1/math.prod(math.factorial(v) for v in reactants.values())
        if prefactor!=RATES[c]['prefactor']:raise ValueError('Rate identical-reactant convention differs')
        k.append(value*(nb*1e-6/Avogadro if binary else 1.)*prefactor*int(active[c]))
    return np.array(k)

def flux(y,k):
    return np.array([k[j]*math.prod(y[SPECIES.index(n)]**m for n,m in reactants.items()) for j,reactants in enumerate(REACTANTS)])

def initial_state(p):
    y=np.zeros(len(SPECIES)+len(CHANNELS));y[0]=p['hydrogen_fraction'];y[3]=(1-p['hydrogen_fraction']-p['catalyst_fraction'])/4
    index=SPECIES.index(p['catalyst_seed']);y[index]=p['catalyst_fraction']/A[index]
    return y

def integrate_zone(value,acting=None,channel_switches=None,*,decay_basis='nubase2020',tolerance=1e-9):
    p=parameters(value);a,c,active=active_channels(acting,channel_switches);tol=number(tolerance)
    if not 1e-12<=tol<=1e-6:raise ValueError('Integrator tolerance outside declared range')
    gen=generation();k=coefficients(p['temperature_K'],p['density_kg_m3'],active,decay_basis);initial=initial_state(p);calls=0
    if not np.array_equal(A@S,np.zeros(len(CHANNELS))) or not np.array_equal(Z@S+WEAK,np.zeros(len(CHANNELS))):raise ValueError('Baryon/charge stoichiometry differs')
    def rhs(t,y):
        nonlocal calls
        calls+=1
        if calls>MAX_RHS_EVALUATIONS:raise RuntimeError('Prescribed-zone RHS budget exceeded')
        f=flux(y,k);return np.r_[S@f,f]
    def jacobian(t,y):
        df=np.zeros((len(CHANNELS),len(initial)))
        for j,reactants in enumerate(REACTANTS):
            for n,m in reactants.items():
                df[j,SPECIES.index(n)]=k[j]*m*math.prod(y[SPECIES.index(other)]**(count-(other==n)) for other,count in reactants.items())
        return np.vstack((S@df,df))
    times=np.linspace(0,p['duration_s'],241)
    atol=[1e-13,1e-25,1e-16,1e-13,1e-16,1e-28,1e-16,1e-16,1e-28,1e-16]+[1e-17]*len(CHANNELS)
    solution=solve_ivp(rhs,[0,p['duration_s']],initial,t_eval=times,method='Radau',jac=jacobian,rtol=tol,atol=atol)
    if not solution.success:raise RuntimeError('Coupled pp-I/CNO-I did not converge: '+solution.message)
    values=solution.y.T;pop=values[:,:len(SPECIES)];xi=values[:,len(SPECIES):]
    if not np.isfinite(values).all() or np.min(pop)<-1e-20 or np.min(xi)<-1e-20:raise RuntimeError('Invalid coupled-zone populations/extents')
    baryon=float(np.max(abs(pop@A-1.)));catalyst0=float(np.sum(initial[4:len(SPECIES)]))
    catalyst=float(np.max(abs(np.sum(pop[:,4:],axis=1)-catalyst0)))/catalyst0 if catalyst0 else float(np.max(abs(pop[:,4:])))
    beta=xi@WEAK;charge=float(np.max(abs(pop@Z-initial[:len(SPECIES)]@Z+beta)))
    if baryon>1e-8 or catalyst>1e-8 or charge>1e-10:raise RuntimeError('Coupled-zone conservation limit exceeded')
    nb=p['density_kg_m3']/atomic_mass;events=np.array([flux(y,k) for y in values])*nb;extents=xi*nb
    available=extents@Q_MEV*1e6*elementary_charge;neutrino=extents@NEUTRINO_MEV*1e6*elementary_charge
    non_neutrino=available-neutrino;volume=p['volume_m3']
    if not all(np.isfinite(v).all() for v in [events,extents,available,neutrino,non_neutrino]):raise RuntimeError('Unrepresentable nuclear ledger')
    if generation()!=gen:raise ValueError('Scientific generation changed during integration')
    return dict(schema=1,kind='coupled_ppI_CNOI_prescribed_zone',scientific_generation=gen,parameters=p,acting=a,channel_switches=c,active_channels=active,decay_basis=decay_basis,
        species=list(SPECIES),channels=list(CHANNELS),time_s=times.tolist(),number_per_baryon=pop.tolist(),mass_fractions=(pop*A).tolist(),
        baryon_density_m3=nb,reaction_extents_m3=extents.tolist(),event_rates_m3_s=events.tolist(),electron_fraction=(pop@Z).tolist(),
        produced_positrons_m3=(beta*nb).tolist(),annihilated_electrons_m3=(beta*nb).tolist(),neutrino_count_m3=(beta*nb).tolist(),
        neutrinos_by_channel_m3={name:extents[:,CHANNELS.index(name)].tolist() for name in ['pp','n13beta','o15beta']},
        energy_available_J_m3=available.tolist(),energy_neutrinos_J_m3=neutrino.tolist(),non_neutrino_energy_available_J_m3=non_neutrino.tolist(),
        total_energy_available_J=(available*volume).tolist(),total_energy_neutrinos_J=(neutrino*volume).tolist(),
        nuclear_power_W_m3=(events@Q_MEV*1e6*elementary_charge).tolist(),neutrino_power_W_m3=(events@NEUTRINO_MEV*1e6*elementary_charge).tolist(),
        thermal_energy_stored_J=None,surface_luminosity_W=None,spatial_neutrino_flux_m2_s=None,
        conservation=dict(baryon_absolute_error=baryon,catalyst_number_relative_error=catalyst,nuclear_charge_plus_beta_per_baryon_error=charge,minimum_abundance=float(np.min(pop))),
        solver=dict(method='Radau',rtol=tol,atol=atol,nfev=solution.nfev,njev=solution.njev,nlu=solution.nlu,RHS_budget=MAX_RHS_EVALUATIONS),
        provenance=dict(rates=copy.deepcopy(RATES),pp_neutrino_mean_MeV=PP['pp_neutrino_mean_MeV'],CNO_neutrino_mean_MeV=copy.deepcopy(CNO['neutrino_mean_MeV']),beta_evaluation=decay_basis),
        scope='One homogeneous prescribed T/rho/volume zone. Shared p/He4; fixed unscreened forward rates. Atomic Q includes local positron annihilation; neutrino means fixed. No thermal/EOS feedback, screening, pp-II/III, spatial transport, surface luminosity or full stellar model.')
