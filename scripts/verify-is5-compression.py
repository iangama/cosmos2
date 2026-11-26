"""Prescribed-density RadauT evolution vs BDF total energy with EOS inversion."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import sys
import time
import traceback
import zipfile
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-compression-staging'))
import is5_compression as model
base=model.base
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
YEAR=31557600.


def independent(p,history,acting,channels,times,tolerance=2e-10):
    """Total E and pressure work; no production thermal/pressure derivatives."""
    _,_,enabled=base.active_channels(acting,channels)
    initial=base.initial_state(p)
    count=p['density_kg_m3']/model.network.eos.MU*p['volume_m3']
    def density(seconds):
        phase=seconds/p['duration_s'];ratio=history.get('ratio',1.)
        if history['kind']=='cycle':
            rho=p['density_kg_m3']*ratio**(math.sin(math.pi*phase)**2)
            rate=math.log(ratio)*math.pi*math.sin(2*math.pi*phase)/p['duration_s']
        else:
            rho=p['density_kg_m3']*ratio**phase
            rate=math.log(ratio)/p['duration_s']
        # SciPy supplies NumPy scalar times; the accepted SI API deliberately
        # accepts only Python numeric scalars. Preserve that API and convert
        # this reference adapter's coordinates explicitly.
        return float(rho),float(rate),float(count*model.network.eos.MU/rho)
    def thermo(temp,rho,pop):
        return model.network.eos.evaluate(float(temp),float(rho),[float(v) for v in pop],model.network.AI,model.network.ZI)
    energy0=thermo(p['temperature_K'],p['density_kg_m3'],initial[:16])['total']['internal_energy_J_m3']*p['volume_m3']
    calls=inversions=0
    def inverse(pop,rho,volume,energy):
        nonlocal inversions
        inversions+=1;cache={}
        def residual(temp):
            state=thermo(temp,rho,pop);cache[temp]=state
            return state['total']['internal_energy_J_m3']*volume/energy0-energy
        temp=brentq(residual,1e7*(1+1e-12),1.6e7*(1-1e-12),xtol=1e-6,rtol=2e-13)
        return float(temp),cache.get(temp) or thermo(temp,rho,pop)
    def rhs(seconds,values):
        nonlocal calls
        calls+=1
        if calls>base.legacy.MAX_RHS_EVALUATIONS:raise RuntimeError('Reference compression RHS budget exceeded')
        rho,rate,volume=density(seconds);pop=values[:16]
        temp,state=inverse(pop,rho,volume,float(values[34]))
        constants=base.rate_constants(temp,rho,enabled)
        factors=model.network._screening_from_state(temp,rho,pop,dict(components=state['components']))[0]
        flux=[]
        for j,reactants in enumerate(base.REACTANTS):
            value=constants[j]*factors[j]
            for species,multiplicity in reactants.items():value*=pop[base.SPECIES.index(species)]**multiplicity
            if base.CHANNELS[j]=='be7ec':value*=float(base.Z@pop)
            flux.append(value)
        flux=np.array(flux)
        power_work=state['total']['pressure_Pa']*volume*rate
        return np.r_[base.S@flux,flux,(count*float((base.Q-base.QNU)@flux)+power_work)/energy0,power_work/energy0]
    sol=solve_ivp(rhs,[0,p['duration_s']],np.r_[initial,1.,0.],method='BDF',t_eval=times,
                  rtol=tolerance,atol=np.r_[base.ATOL,1e-12,1e-13])
    if not sol.success:raise RuntimeError(sol.message)
    temperatures=[]
    for seconds,values in zip(times,sol.y.T):
        rho,_,volume=density(float(seconds));temperatures.append(inverse(values[:16],rho,volume,float(values[34]))[0])
    return dict(number_per_baryon=sol.y[:16,:].T.tolist(),temperature_K=temperatures,
                reaction_extents_per_baryon=sol.y[16:34,:].T.tolist(),
                internal_energy_J=(sol.y[34]*energy0).tolist(),external_pressure_work_J=(sol.y[35]*energy0).tolist(),
                solver=dict(method='BDF',coordinate='total_E/E0',RHS_calls=calls,EOS_inversions=inversions))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is5-compression-{args.label}'
    path=ROOT/f'evidence/is5-compression-{args.label}.json'
    if folder.exists() or path.exists():raise FileExistsError('Preserve compression evidence')
    anchor=ROOT/'evidence/is5-eos-cross-20261029a.json';accepted=json.loads(anchor.read_text());assert accepted['accepted']
    assert accepted['generation']==model.cross.generation()
    science=ROOT/'evidence/is5-coulomb-science-20261028a.json';old=json.loads(science.read_text());assert old['accepted']
    control_case=next(c for c in old['evolution_cases'] if c['seed']=='n14' and c['mode']=='isochoric' and c['years']==1000)
    control_name=next(n for n in control_case['artifact_sha256'] if n.endswith('case1-Radau.json'))
    assert sha(ROOT/control_name)==control_case['artifact_sha256'][control_name]
    hashes={**accepted['source_sha256'],**old['source_sha256']}
    for p in [Path(__file__),anchor,science,ROOT/control_name,*model.FILES]:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    folder.mkdir();archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    gen=model.generation()
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),generation=gen,cases=[],controls=[],refusals=[],
           limits_before_execution=dict(T_relative=1e-7,Y_absolute=1e-8,W_over_E0_absolute=1e-8,energy_normalized=1e-8,
                                        frozen_cycle_T_relative=1e-8,frozen_cycle_work_normalized=1e-8))
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def store(name,run):
        p=folder/(name+'.json');p.write_text(json.dumps(run,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8');return p.relative_to(ROOT).as_posix(),sha(p)
    def ledger(run):
        energy=np.array(run['internal_energy_J']);work=np.array(run['external_pressure_work_J']);q=np.array(run['non_neutrino_energy_available_J'])
        scale=np.maximum.reduce([np.full(241,energy[0]),abs(energy),abs(np.array(run['energy_available_J'])),abs(work)])
        err=float(np.max(abs(energy-energy[0]-q-work)/scale));assert err<=1e-8
        assert np.max(abs(np.array(run['density_kg_m3'])*np.array(run['volume_m3'])/model.network.eos.MU/run['baryon_count']-1))<=1e-14
        assert np.max(abs(np.array(run['annihilated_electrons'])-np.array(run['produced_positrons'])))==0
        assert np.allclose(np.array(run['neutrino_count']),np.array(run['produced_positrons'])+np.array(run['captured_electrons']),rtol=1e-12,atol=1e-99)
        return err
    persist()
    try:
        alloff=dict(strong=False,weak=False,electromagnetic=False)
        specs=[('n14',15e6,1.5e5,1000,dict(kind='exponential',ratio=1.05),None),
               ('o16',15e6,1.5e5,1000,dict(kind='exponential',ratio=.95),None),
               ('n14',14e6,1e5,1,dict(kind='cycle',ratio=1.05),alloff)]
        for index,(seed,temp,rho,years,history,acting) in enumerate(specs):
            p={**base.DEFAULT_PARAMETERS, 'catalyst_seed':seed,'temperature_K':temp,'density_kg_m3':rho,'duration_s':years*YEAR}
            began=time.perf_counter();actual=model.integrate_zone(p,history,acting);artifacts=dict([store(f'case{index}-Radau',actual)])
            print(json.dumps(dict(case=index,stage='Radau',T_final=actual['temperature_K'][-1],solver=actual['solver'],seconds=time.perf_counter()-began)),flush=True)
            ref=independent(actual['parameters'],history,actual['acting'],actual['channel_switches'],actual['time_s'])
            artifacts.update([store(f'case{index}-BDF-E',ref)])
            print(json.dumps(dict(case=index,stage='BDF-E',solver=ref['solver'],seconds=time.perf_counter()-began)),flush=True)
            refined=model.integrate_zone(p,history,acting,tolerance=2e-10);artifacts.update([store(f'case{index}-Radau-refined',refined)])
            temps=np.array(actual['temperature_K']);pop=np.array(actual['number_per_baryon']);e0=actual['initial_internal_energy_J']
            errors={}
            for label,other in [('BDF',ref),('refined',refined)]:
                ey=float(np.max(abs(pop-np.array(other['number_per_baryon']))))
                et=float(np.max(abs(temps-np.array(other['temperature_K']))/temps))
                ew=float(np.max(abs(np.array(actual['external_pressure_work_J'])-np.array(other['external_pressure_work_J']))/e0))
                assert ey<=1e-8 and et<=1e-7 and ew<=1e-8,(index,label,ey,et,ew)
                errors[label]=dict(Y_absolute=ey,T_relative=et,W_over_E0_absolute=ew)
            for run in [actual,refined]:ledger(run)
            if index==0:
                assert actual['external_pressure_work_J'][-1]>0 and temps[-1]>temps[0]
            elif index==1:
                assert actual['external_pressure_work_J'][-1]<0 and temps[-1]<temps[0]
            else:
                assert max(actual['neutrino_count'])==0 and np.max(abs(pop-pop[0]))<=1e-14
                assert abs(temps[-1]/temps[0]-1)<=1e-8 and abs(actual['external_pressure_work_J'][-1]/e0)<=1e-8
                assert temps[120]>temps[0] and actual['density_kg_m3'][-1]==rho
            r['cases'].append(dict(seed=seed,history=history,years=years,acting=actual['acting'],errors=errors,
                conservation=actual['conservation'],temperature_range=[float(min(temps)),float(max(temps))],
                W_final_J=actual['external_pressure_work_J'][-1],artifact_sha256=artifacts,elapsed_s=time.perf_counter()-began))
            persist();print(json.dumps(dict(case=index,completed=True,errors=errors,seconds=time.perf_counter()-began)),flush=True)
        previous=json.loads((ROOT/control_name).read_text())
        p=previous['parameters'];constant=model.integrate_zone(p,dict(kind='constant'))
        assert constant['parameters']==previous['parameters'] and constant['acting']==previous['acting']
        ey=float(np.max(abs(np.array(constant['number_per_baryon'])-np.array(previous['number_per_baryon']))))
        et=float(np.max(abs(np.array(constant['temperature_K'])-np.array(previous['temperature_K']))/np.array(previous['temperature_K'])))
        assert ey<=1e-8 and et<=1e-7 and set(constant['external_pressure_work_J'])=={0.}
        r['controls'].append(dict(name='constant_accepted_Coulomb_limit',Y_error=ey,T_error=et,
                                 reused_accepted_artifact=control_name,artifact_sha256=dict([store('control-constant-Coulomb',constant)]),energy=ledger(constant)));persist()
        p={**base.DEFAULT_PARAMETERS,'duration_s':100*YEAR}
        ideal=model.integrate_zone(p,dict(kind='constant'),include_coulomb=False,include_screening=False)
        legacy=base.integrate_zone(p,mode='isochoric_ideal')
        ey=float(np.max(abs(np.array(ideal['number_per_baryon'])-np.array(legacy['number_per_baryon']))))
        et=float(np.max(abs(np.array(ideal['temperature_K'])-np.array(legacy['temperature_K']))/np.array(legacy['temperature_K'])))
        assert ey<=1e-8 and et<=1e-7 and set(ideal['external_pressure_work_J'])=={0.}
        r['controls'].append(dict(name='constant_ideal_limit',Y_error=ey,T_error=et,energy=ledger(ideal),
                                 artifact_sha256=dict([store('control-ideal-new',ideal),store('control-ideal-parent',legacy)])));persist()
        p={**base.DEFAULT_PARAMETERS,'duration_s':10*YEAR}
        for name,acting in [('weakoff',dict(strong=True,weak=False,electromagnetic=True)),
                            ('EMoff',dict(strong=True,weak=True,electromagnetic=False))]:
            run=model.integrate_zone(p,dict(kind='exponential',ratio=1.03),acting)
            assert run['external_pressure_work_J'][-1]>0 and run['temperature_K'][-1]>p['temperature_K']
            if name=='weakoff':assert max(run['neutrino_count'])==0
            else:assert run['reaction_extents_count'][-1][0]>0 and run['neutrino_count'][-1]>0
            r['controls'].append(dict(name=name,energy=ledger(run),conservation=run['conservation'],artifact_sha256=dict([store('control-'+name,run)])));persist()
        for label,history,opts in [('unknown',dict(kind='unknown'),{}),('extra',dict(kind='constant',ratio=1),{}),
                ('bool_ratio',dict(kind='exponential',ratio=True),{}),('small_ratio',dict(kind='cycle',ratio=.79),{}),
                ('large_ratio',dict(kind='exponential',ratio=1.21),{}),('unknown_field',dict(kind='cycle',ratio=1.05,x=1),{}),
                ('screen_without_EOS',dict(kind='constant'),dict(include_coulomb=False)),
                ('EOS_type',dict(kind='constant'),dict(include_coulomb=1)),('screen_type',dict(kind='constant'),dict(include_screening=1)),
                ('tolerance_type',dict(kind='constant'),dict(tolerance=True)),('tolerance_small',dict(kind='constant'),dict(tolerance=1e-14))]:
            try:model.integrate_zone(p,history,**opts)
            except ValueError as error:r['refusals'].append(dict(case=label,reason=str(error)))
            else:raise AssertionError('Invalid density setup accepted: '+label)
        try:model.integrate_zone({**p,'density_kg_m3':2.9e5},dict(kind='exponential',ratio=1.1))
        except ValueError as error:r['refusals'].append(dict(case='density_extrema',reason=str(error)))
        else:raise AssertionError('Invalid density extrema accepted')
        try:base.rate_constants(1.6001e7,p['density_kg_m3'])
        except ValueError as error:domain_reason=str(error)
        else:raise AssertionError('Missing accepted upper temperature guard')
        hot={**base.DEFAULT_PARAMETERS,'temperature_K':1.5999e7,'duration_s':1000*YEAR}
        try:model.integrate_zone(hot,dict(kind='exponential',ratio=1.05))
        except ValueError as error:
            assert str(error)==domain_reason,str(error)
            r['refusals'].append(dict(case='whole_hot_trajectory',reason=str(error)))
        else:raise AssertionError('Hot trajectory should have been refused without a result')
        assert len(r['cases'])==3 and len(r['controls'])==4 and len(r['refusals'])==13
        assert all(sha(ROOT/n)==value for n,value in hashes.items())
        r.update(accepted=True,completed=True,scope='Local prescribed-density nuclear/thermal evolution and external pressure work only; no worker, product, hydrostatic or gravitational evolution acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    persist();print(json.dumps({k:r.get(k) for k in ['accepted','completed','failure']}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
