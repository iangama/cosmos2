"""Coupled pp/CNO: evaluated rates, isolated legacy limits and independent BDF."""
from pathlib import Path
from collections import Counter
import argparse
import copy
import hashlib
import itertools
import json
import math
import sys
import traceback
import zipfile
import numpy as np
from scipy.integrate import solve_ivp
from scipy.constants import Avogadro,atomic_mass,elementary_charge

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is5-solar-core-staging'
sys.path.insert(0,str(STAGE))
import is5_core as core
import is5_reference_pp as pp
import is5_reference_cno as cno
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def rate(T,entry):
    t=T/1e9
    return math.fsum(math.exp(c[0]+c[1]/t+c[2]/t**(1/3)+c[3]*t**(1/3)+c[4]*t+c[5]*t**(5/3)+c[6]*math.log(t)) for c in entry['sets'])

def independent(p,active,basis):
    species=['p','d','he3','he4','c12','n13','c13','n14','o15','n15'];channels=list(core.CHANNELS)
    data={**pp.DATA['rates'],**cno.DATA['rates']};A=np.array([1,2,3,4,12,13,13,14,15,15])
    rows=[];coeff=[];parents=[]
    for name in channels:
        entry=data[name];lhs=Counter(entry['reactants']);rhs=Counter(entry['products']);rows.append([rhs[n]-lhs[n] for n in species]);parents.append(lhs)
        k=entry['nubase2020_decay_constant_s'] if name in ['n13beta','o15beta'] and basis=='nubase2020' else rate(p['temperature_K'],entry)
        if sum(lhs.values())==2:k*=p['density_kg_m3']/atomic_mass*1e-6/Avogadro
        coeff.append(k/math.prod(math.factorial(v) for v in lhs.values())*active[name])
    stoich=np.array(rows).T;y=np.zeros(19);y[0]=p['hydrogen_fraction'];y[3]=(1-y[0]-p['catalyst_fraction'])/4;j=species.index(p['catalyst_seed']);y[j]=p['catalyst_fraction']/A[j]
    def rhs(t,y):
        f=np.array([k*math.prod(y[species.index(n)]**m for n,m in parent.items()) for k,parent in zip(coeff,parents)])
        return np.r_[stoich@f,f]
    sol=solve_ivp(rhs,[0,p['duration_s']],y,t_eval=np.linspace(0,p['duration_s'],241),method='BDF',rtol=1e-11,
        atol=[1e-14,1e-28,1e-18,1e-14,1e-18,1e-30,1e-18,1e-18,1e-30,1e-18]+[1e-19]*9)
    assert sol.success,sol.message
    return sol.y.T

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is5-core-'+args.label);receipt=ROOT/('evidence/is5-core-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve core evidence')
    folder.mkdir();manifest=json.loads((STAGE/'reference-manifest.json').read_text());assert all(sha(ROOT/n)==v for n,v in manifest['source_sha256'].items())
    files=[*core.FILES,Path(__file__),ROOT/'IS-5-NUCLEO-SOLAR-CONTRATO-PREVIO.md'];hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(schema=1,accepted=False,completed=False,source_sha256=hashes,cases=[],rate_comparisons=0,gate_comparisons=0,refusals=0)
    def persist():receipt.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    persist()
    try:
        maximum_rate_error=0.
        for name in core.CHANNELS:
            entry=core.RATES[name]
            for T in [1e7,1.5e7,2e7,3e7]:
                value=rate(T,entry);gold=entry['reference_rates'][str(T)];error=abs(value-gold)/gold
                assert error<=1e-12,(name,T,error);maximum_rate_error=max(maximum_rate_error,error);r['rate_comparisons']+=1
                actual=core.coefficients(T,1.5e5,decay_basis='reaclib_wc12')[core.CHANNELS.index(name)]
                count=len(entry['reactants']);expected=value*entry['prefactor']*(1.5e5/atomic_mass*1e-6/Avogadro if count==2 else 1.)
                assert math.isclose(actual,expected,rel_tol=1e-12)
        required={'pp':{'strong','weak'},'dp':{'strong','electromagnetic'},'he3he3':{'strong'},'c12pg':{'strong','electromagnetic'},'n13beta':{'weak'},'c13pg':{'strong','electromagnetic'},'n14pg':{'strong','electromagnetic'},'o15beta':{'weak'},'n15pa':{'strong'}}
        for flags in itertools.product([False,True],repeat=3):
            acting=dict(zip(['strong','weak','electromagnetic'],flags));enabled={k for k,v in acting.items() if v}
            for mask in range(512):
                channels={k:bool(mask&(1<<i)) for i,k in enumerate(core.CHANNELS)};_,_,actual=core.active_channels(acting,channels)
                assert actual=={k:channels[k] and required[k]<=enabled for k in core.CHANNELS};r['gate_comparisons']+=1
        cases=[('default',{}),('hot-long',dict(temperature_K=3e7,duration_s=5e9*core.YEAR_S)),('cold-small',dict(temperature_K=1e7,duration_s=1.)),('C12',dict(catalyst_seed='c12',duration_s=1e5*core.YEAR_S)),('pp-only',dict(catalyst_fraction=0.)),('cno-only',{})]
        results={}
        for name,patch in cases:
            print(json.dumps(dict(case=name,stage='Radau')),flush=True);p={**core.DEFAULT_PARAMETERS,**patch};before=copy.deepcopy(p);channels={c:not(name=='cno-only' and c in ['pp','dp','he3he3']) for c in core.CHANNELS}
            actual=core.integrate_zone(p,channel_switches=channels);assert p==before
            results[name]=actual;pop=np.array(actual['number_per_baryon']);xi=np.array(actual['reaction_extents_m3'])/actual['baryon_density_m3'];row=dict(name=name,conservation=actual['conservation'])
            reference=independent(p,actual['active_channels'],'nubase2020');error=float(np.max(abs(np.c_[pop,xi]-reference)))
            assert error<=1e-8,(name,error);row['independent_BDF_max_per_baryon_error']=error
            if name=='pp-only':
                legacy=pp.integrate_zone(p['temperature_K'],p['density_kg_m3'],p['hydrogen_fraction'],p['duration_s'])
                assert np.max(abs(pop[:,:4]-legacy['number_per_baryon']))<=1e-8
                assert np.max(abs(xi[:,:3]-np.array(legacy['reaction_extents_m3'])/actual['baryon_density_m3']))<=1e-8
                row['legacy_pp_limit']=True
            if name=='cno-only':
                legacy=cno.integrate_zone(p['temperature_K'],p['density_kg_m3'],p['hydrogen_fraction'],p['catalyst_fraction'],p['duration_s'],initial_species=p['catalyst_seed'])
                columns=[core.SPECIES.index(s) for s in legacy['species']]
                assert np.max(abs(pop[:,columns]-legacy['number_per_baryon']))<=1e-8
                assert np.max(abs(xi[:,3:]-np.array(legacy['reaction_extents_m3'])/actual['baryon_density_m3']))<=1e-8
                row['legacy_CNO_limit']=True
            ext=np.array(actual['reaction_extents_m3']);Q=np.array([core.RATES[c]['Q_MeV'] for c in core.CHANNELS]);nu=np.array([.2668 if c=='pp' else .706 if c=='n13beta' else .996 if c=='o15beta' else 0. for c in core.CHANNELS])
            available=ext@Q*1.602176634e-13;neutrino=ext@nu*1.602176634e-13
            assert np.allclose(actual['energy_available_J_m3'],available,rtol=1e-12,atol=1e-30) and np.allclose(actual['energy_neutrinos_J_m3'],neutrino,rtol=1e-12,atol=1e-30)
            assert np.all(available>=-1e-30) and np.all(neutrino>=-1e-30) and np.all(neutrino<=available+1e-30)
            if name=='cold-small':assert available[-1]>0 and np.max(ext[-1])>0
            assert actual['thermal_energy_stored_J'] is None and actual['surface_luminosity_W'] is None and actual['spatial_neutrino_flux_m2_s'] is None
            raw=folder/(name+'.json');raw.write_text(json.dumps(actual,indent=2)+'\n',encoding='utf-8');row.update(raw=raw.relative_to(ROOT).as_posix(),sha256=sha(raw));r['cases'].append(row);persist()
        refined=core.integrate_zone(core.DEFAULT_PARAMETERS,tolerance=1e-11);delta=np.max(abs(np.array(refined['number_per_baryon'])-results['default']['number_per_baryon']));assert delta<=1e-8
        for force in ['strong','weak','electromagnetic','all']:
            acting={k:force not in [k,'all'] for k in ['strong','weak','electromagnetic']};actual=core.integrate_zone(core.DEFAULT_PARAMETERS,acting)
            assert actual['parameters']==core.DEFAULT_PARAMETERS
            if force=='all':assert np.max(abs(np.array(actual['number_per_baryon'])-core.initial_state(core.DEFAULT_PARAMETERS)[:10]))<1e-14 and np.max(np.abs(np.array(actual['energy_available_J_m3'])))==0.
        bads=[{'temperature_K':True},{'temperature_K':1e7-1},{'temperature_K':3e7+1},{'density_kg_m3':float('nan')},{'hydrogen_fraction':.76},{'catalyst_fraction':-.01},{'catalyst_seed':'n13'},{'duration_s':0.},{'duration_s':float('inf')},{'volume_m3':False},{'extra':0}]
        for patch in bads:
            p={**core.DEFAULT_PARAMETERS,**patch};before=copy.deepcopy(p)
            try:core.integrate_zone(p)
            except ValueError:r['refusals']+=1
            else:raise AssertionError(patch)
            assert all((isinstance(v,float) and math.isnan(v) and math.isnan(p[k])) or p[k]==v for k,v in before.items())
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,maximum_rate_relative_error=maximum_rate_error,tolerance_refinement_max_per_baryon_error=float(delta),scope='Coupled prescribed pp-I/CNO-I zone science only; shared fuel, rates/gates/legacy limits/BDF/conservation/energy. No solar binding, worker, native UI, EOS/transport or full IS5 acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps(dict(accepted=r['accepted'],cases=len(r['cases']),failure=r.get('failure'))),flush=True);return 0 if r['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
