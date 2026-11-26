"""Shared-fuel pp-I/II/effective-III and cold CNO-I/II with an explicit catalytic pool."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import math
import sys
import numpy as np
from scipy.constants import Avogadro,atomic_mass,elementary_charge
from scipy.integrate import solve_ivp

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
sys.path.insert(0,str(ROOT/'output/is5-pp3-staging'))
import is5_pp3 as previous
legacy=previous.legacy
eos=previous.eos

HERE=Path(__file__).resolve().parent
DATA_PATH=HERE/'cno2-data.json'
DATA=json.loads(DATA_PATH.read_text(encoding='utf-8'))
SPECIES=tuple(DATA['species'])
CHANNELS=(*previous.CHANNELS,'n15pg','o16pg','f17beta','o17pa')
NSPEC=len(SPECIES);NCHAN=len(CHANNELS);NVAR=NSPEC+NCHAN
RATES=DATA['rates']
A=np.array([DATA['nuclides'][n]['A'] for n in SPECIES],dtype=float)
Z=np.array([DATA['nuclides'][n]['Z'] for n in SPECIES],dtype=float)
REACTANTS=[Counter(RATES[c]['reactants']) for c in CHANNELS]
S=np.array([[Counter(RATES[c]['products'])[n]-Counter(RATES[c]['reactants'])[n] for c in CHANNELS] for n in SPECIES],dtype=float)
BETA=np.array([c in ('pp','n13beta','o15beta','b8beta2a','f17beta') for c in CHANNELS],dtype=float)
EC=np.array([c=='be7ec' for c in CHANNELS],dtype=float)
NU=BETA+EC
MEV_J=1e6*elementary_charge
Q=np.array([RATES[c]['Q_MeV'] for c in CHANNELS])*MEV_J
QNU=np.array([DATA['neutrino_mean_MeV'].get(c,0.) for c in CHANNELS])*MEV_J
DEFAULT_PARAMETERS={**legacy.DEFAULT_PARAMETERS,'duration_s':1e4*31557600.}
ATOL=[1e-13,1e-25,1e-16,1e-13,1e-16,1e-28,1e-16,1e-16,1e-28,1e-16,1e-28,1e-29,1e-32,1e-22,1e-32,1e-25]+[1e-17]*NCHAN
FILES=[Path(__file__),DATA_PATH,ROOT/'data/science/decays-nubase-original.txt',ROOT/'output/is5-pp2-staging/is5_pp2.py',ROOT/'output/is5-pp2-staging/pp2-data.json',ROOT/'data/science/ame2020-mass-original.txt',ROOT/'app/nuclei.py']+[ROOT/e['raw_file'] for e in RATES.values() if 'raw_file' in e]
FILES += [ROOT/e['comparison_only']['raw_file'] for e in RATES.values() if 'comparison_only' in e]
FILES += [ROOT/p['path'] for p in DATA['primary_papers']]
FILES += previous.FILES
CATALYST_INDICES=[*range(4,10),*range(13,16)]
IMPORTED={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}


def generation():
    if any(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=value for n,value in IMPORTED.items()):
        raise ValueError('Restart after CNO-II scientific source changes')
    return dict(schema=1,id='is5:shared-ppI-ppII-ppIII-effective-CNOI-CNOII-SFII-EC-AME2020',version='0.1.0',
                source_sha256=dict(IMPORTED),previous_science=previous.generation(),EOS=eos.generation(),
                Q_basis=DATA['Q_basis'],Be7EC_scope=RATES['be7ec']['scope'])


def parameters(value):
    if not isinstance(value,dict) or value.get('catalyst_seed') not in ('c12','n14','o16'):
        raise ValueError('Explicit C12/N14/O16 catalytic seed required')
    p=legacy.parameters({**value,'catalyst_seed':'n14'});p['catalyst_seed']=value['catalyst_seed']
    if not 1e7<p['temperature_K']<1.6e7:
        raise ValueError('Solar Be7 EC requires strictly10<T_MK<16; no extrapolation')
    return p


def active_channels(acting=None,channel_switches=None):
    a=legacy.switches(acting,('strong','weak','electromagnetic'))
    c=legacy.switches(channel_switches,CHANNELS)
    old=previous.active_channels(a,{n:c[n] for n in previous.CHANNELS})[2]
    return a,c,{**old,'n15pg':a['strong'] and a['electromagnetic'] and c['n15pg'],
                'o16pg':a['strong'] and a['electromagnetic'] and c['o16pg'],
                'f17beta':a['weak'] and c['f17beta'],'o17pa':a['strong'] and c['o17pa']}


def rate_constants(temperature_K,density_kg_m3,active=None,decay_basis='nubase2020'):
    t,rho=legacy.number(temperature_K),legacy.number(density_kg_m3)
    enabled=legacy.switches(active,CHANNELS)
    k=list(previous.rate_constants(t,rho,{c:enabled[c] for c in previous.CHANNELS},decay_basis))
    nb=rho/atomic_mass
    for c in ('n15pg','o16pg','f17beta','o17pa'):
        if c=='f17beta':
            value=RATES[c]['nubase2020_decay_constant_s'] if decay_basis=='nubase2020' else legacy.rate_value(t,RATES[c])
        else:value=legacy.rate_value(t,RATES[c])*nb*1e-6/Avogadro
        prefactor=1/math.prod(math.factorial(m) for m in REACTANTS[CHANNELS.index(c)].values())
        if prefactor!=RATES[c]['prefactor']:raise ValueError('Identical-reactant prefactor differs')
        k.append(float(value)*prefactor*int(enabled[c]))
    return np.array(k)


def flux(y,k):
    f=np.array([k[j]*math.prod(y[SPECIES.index(n)]**m for n,m in reactants.items()) for j,reactants in enumerate(REACTANTS)])
    f[CHANNELS.index('be7ec')]*=float(Z@y[:NSPEC])
    return f


def flux_jacobian(y,k):
    df=np.zeros((NCHAN,NVAR));ec=CHANNELS.index('be7ec');be=SPECIES.index('be7')
    for j,reactants in enumerate(REACTANTS):
        if j==ec:
            df[j,:NSPEC]=k[j]*y[be]*Z
            df[j,be]+=k[j]*float(Z@y[:NSPEC])
        else:
            for n,m in reactants.items():
                df[j,SPECIES.index(n)]=k[j]*m*math.prod(y[SPECIES.index(other)]**(count-(other==n)) for other,count in reactants.items())
    return df


def initial_state(p):
    y=np.zeros(NVAR);y[0]=p['hydrogen_fraction'];y[3]=(1-p['hydrogen_fraction']-p['catalyst_fraction'])/4
    i=SPECIES.index(p['catalyst_seed']);y[i]=p['catalyst_fraction']/A[i]
    return y


def _integrate(p,acting,channel_switches,mode,decay_basis,tolerance,initial=None):
    p=parameters(p);a,c,enabled=active_channels(acting,channel_switches)
    tol=legacy.number(tolerance)
    if mode not in ('prescribed','isochoric_ideal') or not 1e-12<=tol<=1e-6:
        raise ValueError('Explicit CNO-II mode and integration tolerance required')
    y0=initial_state(p) if initial is None else np.asarray(initial,dtype=float).copy()
    if y0.shape!=(NVAR,) or not np.isfinite(y0).all() or np.min(y0)<0 or abs(float(A@y0[:NSPEC])-1)>1e-12 or np.any(y0[NSPEC:]):
        raise ValueError('Normalized16-species initial state and zero extents required')
    if mode=='isochoric_ideal':y0=np.r_[y0,p['temperature_K']/1e7]
    gen=generation();nb=p['density_kg_m3']/atomic_mass;calls=0
    def rhs(t,y):
        nonlocal calls
        calls+=1
        if calls>legacy.MAX_RHS_EVALUATIONS:raise RuntimeError('CNO-II RHS budget exceeded')
        T=float(y[-1]*1e7) if mode=='isochoric_ideal' else p['temperature_K']
        k=rate_constants(T,p['density_kg_m3'],enabled,decay_basis)
        f=flux(y,k);dy=S@f
        if mode=='prescribed':return np.r_[dy,f]
        state=eos.mixture(T,p['density_kg_m3'],float(np.sum(y[:NSPEC])),float(Z@y[:NSPEC]))
        gradient=state['du_dions_per_baryon_J_m3']+Z*state['du_delectrons_per_baryon_J_m3']
        dT=(nb*float((Q-QNU)@f)-float(gradient@dy))/state['heat_capacity_J_m3_K']
        return np.r_[dy,f,dT/1e7]
    kfixed=rate_constants(p['temperature_K'],p['density_kg_m3'],enabled,decay_basis)
    def jacobian(t,y):
        df=flux_jacobian(y,kfixed)
        return np.vstack((S@df,df))
    times=np.linspace(0,p['duration_s'],241)
    sol=solve_ivp(rhs,[0,p['duration_s']],y0,method='Radau',t_eval=times,rtol=tol,
                  atol=ATOL+([1e-12] if mode=='isochoric_ideal' else []),
                  jac=jacobian if mode=='prescribed' else None)
    if not sol.success:raise RuntimeError('CNO-II coupled integration did not converge: '+sol.message)
    values=sol.y.T;pop=values[:,:NSPEC];xi=values[:,NSPEC:NVAR]
    if not np.isfinite(values).all() or np.min(pop)<-1e-20 or np.min(xi)<-1e-20:
        raise RuntimeError('Invalid CNO-II populations/extents; no clamping')
    temperatures=values[:,-1]*1e7 if mode=='isochoric_ideal' else np.full(len(times),p['temperature_K'])
    baryon=float(np.max(abs(pop@A-1)))
    cat0=float(np.sum(y0[CATALYST_INDICES]));cat=float(np.max(abs(np.sum(pop[:,CATALYST_INDICES],axis=1)-cat0)))
    cat=cat/cat0 if cat0 else cat
    charge=float(np.max(abs(pop@Z-y0[:NSPEC]@Z+xi@NU)))
    extents=xi*nb;available=extents@Q;neutrinos=extents@QNU;retained=available-neutrinos
    events=np.array([flux(y,rate_constants(float(t),p['density_kg_m3'],enabled,decay_basis)) for t,y in zip(temperatures,pop)])*nb
    states=None;energy_error=None
    if mode=='isochoric_ideal':
        states=[eos.mixture(float(t),p['density_kg_m3'],float(np.sum(y)),float(Z@y)) for t,y in zip(temperatures,pop)]
        u=np.array([s['internal_energy_J_m3'] for s in states]);energy_error=float(np.max(abs(u-u[0]-retained)/np.maximum(u[0],available)))
        if energy_error>1e-8:raise RuntimeError('CNO-II thermal energy budget exceeded')
    if baryon>1e-8 or cat>1e-8 or charge>1e-10:raise RuntimeError('CNO-II conservation budget exceeded')
    if generation()!=gen:raise ValueError('Scientific generation changed during CNO-II integration')
    return dict(schema=1,kind='is5_shared_ppI_ppII_ppIII_effective_CNOI_CNOII_solar_zone',mode=mode,scientific_generation=gen,
        parameters=p,acting=a,channel_switches=c,active_channels=enabled,decay_basis=decay_basis,
        initial_number_per_baryon=y0[:NSPEC].tolist(),species=list(SPECIES),channels=list(CHANNELS),time_s=times.tolist(),
        temperature_K=temperatures.tolist(),number_per_baryon=pop.tolist(),mass_fractions=(pop*A).tolist(),
        reaction_extents_m3=extents.tolist(),event_rates_m3_s=events.tolist(),energy_available_J_m3=available.tolist(),
        energy_neutrinos_J_m3=neutrinos.tolist(),non_neutrino_energy_available_J_m3=retained.tolist(),
        nuclear_power_W_m3=(events@Q).tolist(),neutrino_power_W_m3=(events@QNU).tolist(),
        neutrino_count_m3=(extents@NU).tolist(),produced_positrons_m3=(extents@BETA).tolist(),
        annihilated_electrons_m3=(extents@BETA).tolist(),captured_electrons_m3=(extents@EC).tolist(),
        neutrinos_by_channel_m3={c:extents[:,j].tolist() for j,c in enumerate(CHANNELS) if NU[j]},
        internal_energy_J_m3=None if states is None else [s['internal_energy_J_m3'] for s in states],
        pressure_Pa=None if states is None else [s['pressure_Pa'] for s in states],
        heat_capacity_J_m3_K=None if states is None else [s['heat_capacity_J_m3_K'] for s in states],
        conservation=dict(baryon_absolute_error=baryon,catalyst_number_relative_error=cat,
            nuclear_charge_plus_leptons_per_baryon_error=charge,energy_normalized_error=energy_error,minimum_abundance=float(np.min(pop))),
        catalytic_pool_species=[SPECIES[i] for i in CATALYST_INDICES],
        beta_scope=RATES['f17beta']['decay_source'],
        solver=dict(method='Radau',rtol=tol,RHS_calls=calls,nfev=sol.nfev,njev=sol.njev,nlu=sol.nlu),
        scope='Shared pp-I/II/effective-III+cold-CNO-I/II, solar Be7 EC law only10<T_MK<16, AME2020 atomic Q. Fixed solar neutrino means. Adopted Be7 EC retains its published plasma approximation; no added fusion screening or Coulomb EOS. B8 beta-delayed two-alpha is effective with strong+weak gate; no resolved Be8 population/spectrum, pep/hep, CNOIII/hot-CNO, minor CNO electron-capture branches, spatial transport, full stellar structure or surface luminosity.')


def integrate_zone(value,acting=None,channel_switches=None,*,mode='prescribed',decay_basis='nubase2020',tolerance=1e-9):
    return _integrate(value,acting,channel_switches,mode,decay_basis,tolerance)
