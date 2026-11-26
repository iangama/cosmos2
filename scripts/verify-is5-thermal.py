"""Thermal burning against an independent internal-energy BDF formulation."""
from pathlib import Path
from collections import Counter
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

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is5-thermal-staging'
sys.path.insert(0,str(STAGE))
import is5_core as core
import is5_eos as eos
import is5_thermal as model
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
YEAR=31557600.


def independent(configuration,acting,switches,times):
    p=configuration;nb=p['density_kg_m3']/eos.MU
    active=core.active_channels(acting,switches)[2]
    initial=core.initial_state(p)
    stoich=np.array([[Counter(core.RATES[c]['products'])[n]-Counter(core.RATES[c]['reactants'])[n] for c in core.CHANNELS] for n in core.SPECIES],dtype=float)
    reactants=[Counter(core.RATES[c]['reactants']) for c in core.CHANNELS]
    energy0=eos.mixture(p['temperature_K'],p['density_kg_m3'],float(np.sum(initial[:10])),float(core.Z@initial[:10]))['internal_energy_J_m3']
    q=np.array([core.RATES[c]['Q_MeV'] for c in core.CHANNELS])-core.NEUTRINO_MEV
    calls=0
    def temperature(y):
        yi=float(np.sum(y[:10]));ye=float(core.Z@y[:10]);target=float(y[-1]*energy0)
        return brentq(lambda t:eos.mixture(float(t),p['density_kg_m3'],yi,ye)['internal_energy_J_m3']-target,1e7,3e7,xtol=2e-6,rtol=2e-14)
    def rhs(t,y):
        nonlocal calls
        calls+=1
        if calls>200000:raise RuntimeError('Independent BDF budget exceeded')
        t=temperature(y);k=core.coefficients(float(t),p['density_kg_m3'],active)
        f=np.array([k[j]*math.prod(y[core.SPECIES.index(n)]**m for n,m in species.items()) for j,species in enumerate(reactants)])
        return np.r_[stoich@f,f,nb*float(q@f)*model.MEV_J/energy0]
    solution=solve_ivp(rhs,[0,p['duration_s']],np.r_[initial,1.],method='BDF',t_eval=times,rtol=2e-10,atol=model.ATOL)
    assert solution.success,solution.message
    states=solution.y.T
    return dict(number_per_baryon=states[:,:10],extents_per_baryon=states[:,10:19],temperature_K=np.array([temperature(y) for y in states]),calls=calls)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    path=ROOT/('evidence/is5-thermal-'+args.label+'.json');folder=ROOT/('output/is5-thermal-'+args.label)
    if path.exists() or folder.exists():raise FileExistsError('Preserve thermal evidence')
    folder.mkdir();files=[*STAGE.glob('*.py'),STAGE/'reference-manifest.json',STAGE/'base-manifest.json',Path(__file__),ROOT/'IS-5-TERMICA-CONTRATO-PREVIO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files};archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),cases=[],refusals=0,
           limits_before_execution=dict(temperature_relative=1e-7,composition_absolute_per_baryon=1e-8,energy_normalized=1e-8))
    def persist():path.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    persist()
    try:
        defaults=copy.deepcopy(core.DEFAULT_PARAMETERS)
        cases=[('mixed10kyr',dict(duration_s=1e4*YEAR),None,None),
            ('pp-only1kyr',dict(duration_s=1e3*YEAR,catalyst_fraction=0.),None,None),
            ('CNO-only30yr',dict(duration_s=30*YEAR,catalyst_seed='c12'),None,{k:k not in ('pp','dp','he3he3') for k in core.CHANNELS}),
            ('all-off1Myr',{},dict(strong=False,weak=False,electromagnetic=False),None),
            ('weak-off1Myr',{},dict(strong=True,weak=False,electromagnetic=True),None),
            ('EM-off10kyr',dict(duration_s=1e4*YEAR),dict(strong=True,weak=True,electromagnetic=False),None),
            ('cold1s',dict(temperature_K=11e6,duration_s=1.,hydrogen_fraction=.75,catalyst_fraction=0.),None,None),
            ('hot1yr',dict(temperature_K=29e6,duration_s=YEAR),None,None)]
        for name,overrides,acting,switches in cases:
            p={**defaults,**overrides};before=copy.deepcopy(p);began=time.perf_counter()
            result=model.integrate_zone(p,acting,switches)
            assert p==before
            data=folder/(name+'.json');data.write_text(json.dumps(result,indent=2)+'\n')
            row=dict(name=name,result=data.relative_to(ROOT).as_posix(),sha256=sha(data),wall_s=time.perf_counter()-began,
                initial_temperature_K=result['temperature_K'][0],final_temperature_K=result['temperature_K'][-1],conservation=result['conservation'],solver=result['solver'])
            assert result['surface_luminosity_W'] is None and result['closure']['external_work_W']==0 and result['closure']['photon_escape_W']==0
            if name=='all-off1Myr':
                assert all(t==p['temperature_K'] for t in result['temperature_K']) and not np.any(result['energy_available_J_m3'])
            else:
                assert result['energy_available_J_m3'][-1]>0 and result['temperature_K'][-1]>=p['temperature_K']
            if name=='weak-off1Myr':assert result['neutrino_count_m3'][-1]==0
            if name=='EM-off10kyr':assert result['mass_fractions'][-1][1]>0 and result['mass_fractions'][-1][3]==result['mass_fractions'][0][3]
            if name=='mixed10kyr':
                print(json.dumps(dict(stage='independent-energy-BDF',case=name)),flush=True)
                ref=independent(p,acting,switches,result['time_s'])
                temp_error=float(np.max(abs(ref['temperature_K']-np.array(result['temperature_K']))/np.array(result['temperature_K'])))
                composition_error=float(np.max(abs(ref['number_per_baryon']-np.array(result['number_per_baryon']))))
                extents_error=float(np.max(abs(ref['extents_per_baryon']-np.array(result['reaction_extents_m3'])/(p['density_kg_m3']/eos.MU))))
                assert temp_error<=1e-7 and composition_error<=1e-8 and extents_error<=1e-8,(temp_error,composition_error,extents_error)
                refined=model.integrate_zone(p,acting,switches,tolerance=1e-10)
                delta=float(np.max(abs(np.array(refined['temperature_K'])-np.array(result['temperature_K']))/np.array(result['temperature_K'])))
                assert delta<=1e-7
                refpath=folder/'independent-BDF.json';refpath.write_text(json.dumps({k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in ref.items()},indent=2)+'\n')
                row.update(temperature_relative_error=temp_error,composition_absolute_error=composition_error,extents_absolute_error=extents_error,
                    refinement_temperature_relative=delta,independent_reference=refpath.relative_to(ROOT).as_posix(),independent_sha256=sha(refpath))
            r['cases'].append(row);persist();print(json.dumps(dict(stage='case',name=name,final_temperature_K=row['final_temperature_K'],wall_s=row['wall_s'])),flush=True)
        for changes,acting in [({'temperature_K':True},None),({'density_kg_m3':0},None),({'duration_s':float('inf')},None),
                               ({},dict(strong=1,weak=True,electromagnetic=True)),({'temperature_K':29.999e6,'duration_s':5e9*YEAR},None)]:
            try:model.integrate_zone({**defaults,**changes},acting)
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Invalid/out-of-domain thermal scenario accepted')
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,scope='Ideal isochoric coupled thermal science only; no worker/UI/stellar-profile acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    persist();print(json.dumps(dict(accepted=r['accepted'],cases=len(r['cases']),refusals=r['refusals'],failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
