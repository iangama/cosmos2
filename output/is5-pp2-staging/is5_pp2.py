"""Shared-fuel pp-I/II+CNO-I with solar Be7 capture and a distinct AME2020 Q basis."""
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
sys.path.insert(0,str(ROOT/'output/is5-thermal-staging'))
import is5_core as legacy
import is5_eos as eos

HERE=Path(__file__).resolve().parent
DATA_PATH=HERE/'pp2-data.json'
DATA=json.loads(DATA_PATH.read_text(encoding='utf-8'))
SPECIES=tuple(DATA['species'])
CHANNELS=(*legacy.CHANNELS,'he3alpha','be7ec','li7pa')
RATES=DATA['rates']
A=np.array([DATA['nuclides'][n]['A'] for n in SPECIES],dtype=float)
Z=np.array([DATA['nuclides'][n]['Z'] for n in SPECIES],dtype=float)
REACTANTS=[Counter(RATES[c]['reactants']) for c in CHANNELS]
S=np.array([[Counter(RATES[c]['products'])[n]-Counter(RATES[c]['reactants'])[n] for c in CHANNELS] for n in SPECIES],dtype=float)
BETA=np.array([c in ('pp','n13beta','o15beta') for c in CHANNELS],dtype=float)
EC=np.array([c=='be7ec' for c in CHANNELS],dtype=float)
NU=BETA+EC
MEV_J=1e6*elementary_charge
Q=np.array([RATES[c]['Q_MeV'] for c in CHANNELS])*MEV_J
QNU=np.array([DATA['neutrino_mean_MeV'].get(c,0.) for c in CHANNELS])*MEV_J
DEFAULT_PARAMETERS={**legacy.DEFAULT_PARAMETERS,'duration_s':1e4*31557600.}
ATOL=[1e-13,1e-25,1e-16,1e-13,1e-16,1e-28,1e-16,1e-16,1e-28,1e-16,1e-28,1e-29]+[1e-17]*12
FILES=[Path(__file__),DATA_PATH,ROOT/'data/science/ame2020-mass-original.txt',ROOT/'app/nuclei.py']+[ROOT/e['raw_file'] for e in RATES.values() if 'raw_file' in e]
FILES += [ROOT/e['comparison_only']['raw_file'] for e in RATES.values() if 'comparison_only' in e]
FILES += [ROOT/p['path'] for p in DATA['primary_papers']]
IMPORTED={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}


def generation():
    if any(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=value for n,value in IMPORTED.items()):
        raise ValueError('Restart after pp-II scientific source changes')
    return dict(schema=1,id='is5:shared-ppI-ppII-CNOI-SFII-EC-AME2020',version='0.1.0',
                source_sha256=dict(IMPORTED),legacy_rates=legacy.generation(),EOS=eos.generation(),
                Q_basis=DATA['Q_basis'],Be7EC_scope=RATES['be7ec']['scope'])


def parameters(value):
    p=legacy.parameters(value)
    if not 1e7<p['temperature_K']<1.6e7:
        raise ValueError('Solar Be7 EC requires strictly10<T_MK<16; no extrapolation')
    return p


def active_channels(acting=None,channel_switches=None):
    a=legacy.switches(acting,('strong','weak','electromagnetic'))
    c=legacy.switches(channel_switches,CHANNELS)
    old=legacy.active_channels(a,{n:c[n] for n in legacy.CHANNELS})[2]
    return a,c,{**old,'he3alpha':a['strong'] and a['electromagnetic'] and c['he3alpha'],
                'be7ec':a['weak'] and c['be7ec'],'li7pa':a['strong'] and c['li7pa']}


def rate_constants(temperature_K,density_kg_m3,active=None,decay_basis='nubase2020'):
    t,rho=legacy.number(temperature_K),legacy.number(density_kg_m3)
    if not 1e7<t<1.6e7 or not 1e4<=rho<=3e5:
        raise ValueError('Solar pp-II rate domain requires10<T_MK<16 and adopted density')
    enabled=legacy.switches(active,CHANNELS)
    k=list(legacy.coefficients(t,rho,{c:enabled[c] for c in legacy.CHANNELS},decay_basis))
    nb=rho/atomic_mass
    for c in ('he3alpha','be7ec','li7pa'):
        if c=='be7ec':
            T6=t/1e6
            value=5.60e-9*(rho/1000)*T6**(-.5)*(1+.004*(T6-16))
        else:
            value=legacy.rate_value(t,RATES[c])*nb*1e-6/Avogadro
            value/=math.prod(math.factorial(m) for m in REACTANTS[CHANNELS.index(c)].values())
        k.append(float(value)*int(enabled[c]))
    return np.array(k)


def flux(y,k):
    f=np.array([k[j]*math.prod(y[SPECIES.index(n)]**m for n,m in reactants.items()) for j,reactants in enumerate(REACTANTS)])
    f[CHANNELS.index('be7ec')]*=float(Z@y[:12])
    return f


def flux_jacobian(y,k):
    df=np.zeros((12,24));ec=CHANNELS.index('be7ec');be=SPECIES.index('be7')
    for j,reactants in enumerate(REACTANTS):
        if j==ec:
            df[j,:12]=k[j]*y[be]*Z
            df[j,be]+=k[j]*float(Z@y[:12])
        else:
            for n,m in reactants.items():
                df[j,SPECIES.index(n)]=k[j]*m*math.prod(y[SPECIES.index(other)]**(count-(other==n)) for other,count in reactants.items())
    return df


def initial_state(p):
    return np.r_[legacy.initial_state(p)[:10],np.zeros(2),np.zeros(12)]


def _integrate(p,acting,channel_switches,mode,decay_basis,tolerance,initial=None):
    p=parameters(p);a,c,enabled=active_channels(acting,channel_switches)
    tol=legacy.number(tolerance)
    if mode not in ('prescribed','isochoric_ideal') or not 1e-12<=tol<=1e-6:
        raise ValueError('Explicit pp-II mode and integration tolerance required')
    y0=initial_state(p) if initial is None else np.asarray(initial,dtype=float).copy()
    if y0.shape!=(24,) or not np.isfinite(y0).all() or np.min(y0)<0 or abs(float(A@y0[:12])-1)>1e-12 or np.any(y0[12:]):
        raise ValueError('Normalized12-species initial state and zero extents required')
    if mode=='isochoric_ideal':y0=np.r_[y0,p['temperature_K']/1e7]
    gen=generation();nb=p['density_kg_m3']/atomic_mass;calls=0
    def rhs(t,y):
        nonlocal calls
        calls+=1
        if calls>legacy.MAX_RHS_EVALUATIONS:raise RuntimeError('pp-II RHS budget exceeded')
        T=float(y[-1]*1e7) if mode=='isochoric_ideal' else p['temperature_K']
        k=rate_constants(T,p['density_kg_m3'],enabled,decay_basis)
        f=flux(y,k);dy=S@f
        if mode=='prescribed':return np.r_[dy,f]
        state=eos.mixture(T,p['density_kg_m3'],float(np.sum(y[:12])),float(Z@y[:12]))
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
    if not sol.success:raise RuntimeError('pp-II coupled integration did not converge: '+sol.message)
    values=sol.y.T;pop=values[:,:12];xi=values[:,12:24]
    if not np.isfinite(values).all() or np.min(pop)<-1e-20 or np.min(xi)<-1e-20:
        raise RuntimeError('Invalid pp-II populations/extents; no clamping')
    temperatures=values[:,-1]*1e7 if mode=='isochoric_ideal' else np.full(len(times),p['temperature_K'])
    baryon=float(np.max(abs(pop@A-1)))
    cat0=float(np.sum(y0[4:10]));cat=float(np.max(abs(np.sum(pop[:,4:10],axis=1)-cat0)))
    cat=cat/cat0 if cat0 else cat
    charge=float(np.max(abs(pop@Z-y0[:12]@Z+xi@NU)))
    extents=xi*nb;available=extents@Q;neutrinos=extents@QNU;retained=available-neutrinos
    events=np.array([flux(y,rate_constants(float(t),p['density_kg_m3'],enabled,decay_basis)) for t,y in zip(temperatures,pop)])*nb
    states=None;energy_error=None
    if mode=='isochoric_ideal':
        states=[eos.mixture(float(t),p['density_kg_m3'],float(np.sum(y)),float(Z@y)) for t,y in zip(temperatures,pop)]
        u=np.array([s['internal_energy_J_m3'] for s in states]);energy_error=float(np.max(abs(u-u[0]-retained)/np.maximum(u[0],available)))
        if energy_error>1e-8:raise RuntimeError('pp-II thermal energy budget exceeded')
    if baryon>1e-8 or cat>1e-8 or charge>1e-10:raise RuntimeError('pp-II conservation budget exceeded')
    if generation()!=gen:raise ValueError('Scientific generation changed during pp-II integration')
    return dict(schema=1,kind='is5_shared_ppI_ppII_CNOI_solar_zone',mode=mode,scientific_generation=gen,
        parameters=p,acting=a,channel_switches=c,active_channels=enabled,decay_basis=decay_basis,
        initial_number_per_baryon=y0[:12].tolist(),species=list(SPECIES),channels=list(CHANNELS),time_s=times.tolist(),
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
        solver=dict(method='Radau',rtol=tol,RHS_calls=calls,nfev=sol.nfev,njev=sol.njev,nlu=sol.nlu),
        scope='Shared pp-I/II+CNO-I, solar Be7 EC law only10<T_MK<16, AME2020 atomic Q. Fixed solar neutrino means. No ppIII/pep/hep, CNOII, spatial transport, full stellar structure or surface luminosity.')


def integrate_zone(value,acting=None,channel_switches=None,*,mode='prescribed',decay_basis='nubase2020',tolerance=1e-9):
    return _integrate(value,acting,channel_switches,mode,decay_basis,tolerance)
