"""pp-II rates, mass-Q cycles, plasma EC/Jacobian, analytic fixtures and independent ODEs."""
from pathlib import Path
from collections import Counter
from decimal import Decimal,localcontext
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
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is5-pp2-staging'
sys.path.insert(0,str(STAGE))
import is5_pp2 as m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def independent(p,acting,switches,mode,times):
    a,c,enabled=m.active_channels(acting,switches)
    initial=m.initial_state(p);nb=p['density_kg_m3']/m.atomic_mass
    own=np.array([[Counter(m.RATES[c]['products'])[n]-Counter(m.RATES[c]['reactants'])[n] for c in m.CHANNELS] for n in m.SPECIES],dtype=float)
    reactants=[Counter(m.RATES[c]['reactants']) for c in m.CHANNELS]
    u0=m.eos.mixture(p['temperature_K'],p['density_kg_m3'],float(np.sum(initial[:12])),float(m.Z@initial[:12]))['internal_energy_J_m3']
    def temperature(y):
        if mode=='prescribed':return p['temperature_K']
        target=float(y[-1]*u0);yi=float(np.sum(y[:12]));ye=float(m.Z@y[:12])
        return brentq(lambda t:m.eos.mixture(float(t),p['density_kg_m3'],yi,ye)['internal_energy_J_m3']-target,1e7,1.6e7,xtol=2e-6,rtol=2e-14)
    def rhs(t,y):
        T=temperature(y);k=m.rate_constants(float(T),p['density_kg_m3'],enabled)
        f=np.array([k[j]*math.prod(y[m.SPECIES.index(n)]**count for n,count in r.items()) for j,r in enumerate(reactants)])
        f[m.CHANNELS.index('be7ec')]*=float(m.Z@y[:12])
        out=np.r_[own@f,f]
        return out if mode=='prescribed' else np.r_[out,nb*float((m.Q-m.QNU)@f)/u0]
    sol=solve_ivp(rhs,[0,p['duration_s']],initial if mode=='prescribed' else np.r_[initial,1.],method='BDF',t_eval=times,rtol=2e-10,atol=m.ATOL+([] if mode=='prescribed' else [1e-12]))
    assert sol.success,sol.message
    states=sol.y.T
    return dict(number_per_baryon=states[:,:12],extents_per_baryon=states[:,12:24],temperature_K=np.array([temperature(y) for y in states]))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    path=ROOT/('evidence/is5-pp2-'+args.label+'.json');folder=ROOT/('output/is5-pp2-'+args.label)
    if path.exists() or folder.exists():raise FileExistsError('Preserve pp-II evidence')
    folder.mkdir();files=[ROOT/n for n in m.IMPORTED]+[Path(__file__),ROOT/'IS-5-PP-II-CONTRATO-PREVIO.md']
    files += list((ROOT/'output/is5-thermal-staging').glob('*.py'))
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,cases=[],refusals=0,rate_checks=[],gate_checks=0)
    def persist():path.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    persist()
    try:
        assert np.array_equal(m.A@m.S,np.zeros(12)) and np.array_equal(m.Z@m.S+m.NU,np.zeros(12))
        with localcontext() as ctx:
            ctx.prec=50;Q={c:Decimal(m.RATES[c]['Q_AME2020_decimal_MeV']) for c in m.CHANNELS}
            cycles=dict(ppI=2*Q['pp']+2*Q['dp']+Q['he3he3'],ppII=Q['pp']+Q['dp']+Q['he3alpha']+Q['be7ec']+Q['li7pa'],CNOI=sum((Q[c] for c in m.legacy.CHANNELS[3:]),Decimal(0)))
            target=(4*Decimal(m.DATA['nuclides']['p']['AME2020']['quantities']['mass_excess']['raw_value'])-Decimal(m.DATA['nuclides']['he4']['AME2020']['quantities']['mass_excess']['raw_value']))/1000
            assert all(q==target for q in cycles.values()),cycles
            r['Q_cycle_MeV']={k:str(v) for k,v in cycles.items()}
        for c in ('he3alpha','li7pa'):
            for T,expected in m.RATES[c]['reference_rates'].items():
                actual=m.legacy.rate_value(float(T),m.RATES[c]);error=abs(actual-expected)/expected
                assert error<=1e-12;r['rate_checks'].append(dict(channel=c,T_K=float(T),relative_error=error))
        for row in m.DATA['ec_decimal_references']:
            actual=m.rate_constants(row['T_K'],row['rho_kg_m3'])[m.CHANNELS.index('be7ec')]*row['Ye'];expected=float(row['rate_s_inverse_decimal'])
            error=abs(actual-expected)/expected;assert error<=1e-12
            r['rate_checks'].append(dict(channel='be7ec',**row,relative_error=error))
        for force_bits in itertools.product((False,True),repeat=3):
            acting=dict(zip(('strong','weak','electromagnetic'),force_bits))
            for bits in itertools.product((False,True),repeat=12):
                switches=dict(zip(m.CHANNELS,bits));enabled=m.active_channels(acting,switches)[2]
                assert enabled['he3alpha']==(acting['strong'] and acting['electromagnetic'] and switches['he3alpha'])
                assert enabled['be7ec']==(acting['weak'] and switches['be7ec'])
                assert enabled['li7pa']==(acting['strong'] and switches['li7pa'])
                assert all(not value or switches[c] for c,value in enabled.items());r['gate_checks']+=1
        x=np.array([.4,.02,.02,.4]+[.02]*8);x/=np.sum(x);y=np.r_[x/m.A,np.zeros(12)]
        k=m.rate_constants(15e6,1.5e5);jac=m.flux_jacobian(y,k);ec=m.CHANNELS.index('be7ec');errors=[]
        for i in range(12):
            delta=y[i]*1e-5;plus=y.copy();minus=y.copy();plus[i]+=delta;minus[i]-=delta
            numeric=(m.flux(plus,k)-m.flux(minus,k))/(2*delta)
            nonzero=abs(jac[:,i])>1e-50
            errors.append(float(np.max(abs(numeric[nonzero]-jac[nonzero,i])/abs(jac[nonzero,i]))))
            assert abs(numeric[ec]-jac[ec,i])/jac[ec,i]<2e-7
        assert max(errors)<2e-7;r['flux_jacobian_relative_max']=max(errors)
        p={**m.DEFAULT_PARAMETERS,'hydrogen_fraction':.5,'catalyst_fraction':0.}
        for channel,seed in [('be7ec','be7'),('li7pa','li7')]:
            initial=np.zeros(24);initial[0]=.5;initial[3]=.48/4;initial[m.SPECIES.index(seed)]=.02/7
            switches={c:c==channel for c in m.CHANNELS};constants=m.rate_constants(p['temperature_K'],p['density_kg_m3'],switches)
            b0=initial[m.SPECIES.index(seed)];other=float(m.Z@initial[:12]) if channel=='be7ec' else initial[0]
            coefficient=constants[m.CHANNELS.index(channel)];a=other-b0;duration=max(1.,12/(coefficient*other))
            result=m._integrate({**p,'duration_s':float(duration)},None,switches,'prescribed','nubase2020',1e-10,initial)
            t=np.array(result['time_s']);ex=np.exp(-a*coefficient*t);b=a*b0*ex/(a+b0*(-np.expm1(-a*coefficient*t)))
            pop=np.array(result['number_per_baryon']);error=float(np.max(abs(pop[:,m.SPECIES.index(seed)]-b)))
            assert error<1e-10
            nb=p['density_kg_m3']/m.atomic_mass;events=(b0-b)*nb
            if channel=='be7ec':
                assert np.max(abs(pop[:,m.SPECIES.index('li7')]-(b0-b)))<1e-10
                assert not np.any(result['produced_positrons_m3'])
                assert np.max(abs(np.array(result['captured_electrons_m3'])-events))/max(events)<1e-8
                assert result['neutrino_count_m3']==result['captured_electrons_m3']
            else:
                assert np.max(abs(pop[:,3]-(initial[3]+2*(b0-b))))<1e-10
                assert np.max(abs(pop[:,0]-(a+b)))<1e-10 and not np.any(result['neutrino_count_m3'])
            out=folder/(channel+'-analytic.json');out.write_text(json.dumps(result,indent=2)+'\n');r['cases'].append(dict(name=channel+'-analytic',absolute_error_per_baryon=error,result=out.relative_to(ROOT).as_posix(),sha256=sha(out)))
        cases=[('mixed-prescribed',{},None,None,'prescribed'),('mixed-thermal',{},None,None,'isochoric_ideal'),
            ('legacy-limit',{},None,{c:c in m.legacy.CHANNELS for c in m.CHANNELS},'prescribed'),
            ('ppII-route',dict(catalyst_fraction=0.,duration_s=1e6*31557600.),None,{c:c not in ('he3he3',*m.legacy.CHANNELS[3:]) for c in m.CHANNELS},'prescribed'),
            ('weak-off',{},dict(strong=True,weak=False,electromagnetic=True),None,'isochoric_ideal'),
            ('EM-off',{},dict(strong=True,weak=True,electromagnetic=False),None,'prescribed'),
            ('all-off',{},dict(strong=False,weak=False,electromagnetic=False),None,'isochoric_ideal'),
            ('cold1s',dict(temperature_K=10.1e6,duration_s=1.),None,None,'prescribed')]
        for name,changes,acting,switches,mode in cases:
            p={**m.DEFAULT_PARAMETERS,**changes};before=copy.deepcopy(p);result=m.integrate_zone(p,acting,switches,mode=mode);assert p==before
            out=folder/(name+'.json');out.write_text(json.dumps(result,indent=2)+'\n');row=dict(name=name,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),conservation=result['conservation'])
            pop=np.array(result['number_per_baryon']);xi=np.array(result['reaction_extents_m3'])
            assert np.max(abs(np.array(result['neutrino_count_m3'])-xi@m.NU))/max(1.,max(result['neutrino_count_m3']))<=1e-12
            assert np.max(abs(np.array(result['energy_neutrinos_J_m3'])-xi@m.QNU))/max(1e-99,max(result['energy_neutrinos_J_m3']))<=1e-12
            if name.startswith('mixed-'):
                print(json.dumps(dict(stage='independent',case=name)),flush=True)
                ref=independent(p,acting,switches,mode,result['time_s'])
                err=float(np.max(abs(ref['number_per_baryon']-pop)));ext=float(np.max(abs(ref['extents_per_baryon']-xi/(p['density_kg_m3']/m.atomic_mass))))
                terr=float(np.max(abs(ref['temperature_K']-result['temperature_K'])/np.array(result['temperature_K'])))
                assert err<=1e-8 and ext<=1e-8 and terr<=1e-7,(name,err,ext,terr)
                refined=m.integrate_zone(p,acting,switches,mode=mode,tolerance=1e-10)
                delta=float(np.max(abs(np.array(refined['number_per_baryon'])-pop)));assert delta<=1e-8
                row.update(BDF_composition_absolute=err,BDF_extents_absolute=ext,BDF_temperature_relative=terr,refinement_composition_absolute=delta)
            if name=='legacy-limit':
                old=m.legacy.integrate_zone(p)
                assert np.max(abs(pop[:,:10]-old['number_per_baryon']))<=1e-8 and not np.any(pop[:,10:])
            if name=='ppII-route':assert pop[-1,10]>0 and pop[-1,11]>0 and result['captured_electrons_m3'][-1]>0
            if name=='all-off':assert all(t==p['temperature_K'] for t in result['temperature_K']) and not np.any(result['energy_available_J_m3'])
            if name=='weak-off':assert result['captured_electrons_m3'][-1]==result['produced_positrons_m3'][-1]==0
            r['cases'].append(row);persist();print(json.dumps(dict(stage='case',name=name)),flush=True)
        for change in [dict(temperature_K=1e7),dict(temperature_K=16e6),dict(temperature_K=True),dict(duration_s=0),dict(density_kg_m3=float('nan'))]:
            try:m.integrate_zone({**m.DEFAULT_PARAMETERS,**change})
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Invalid pp-II request accepted')
        try:m.integrate_zone({**m.DEFAULT_PARAMETERS,'duration_s':1e6*31557600.},mode='isochoric_ideal')
        except ValueError:r['refusals']+=1
        else:raise AssertionError('Thermal Be7 EC domain exceeded without refusal')
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,scope='Shared pp-I/II+CNO-I scientific slice only; no ppIII, worker/UI or complete stellar model acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    persist();print(json.dumps(dict(accepted=r['accepted'],rate_checks=len(r['rate_checks']),gates=r['gate_checks'],cases=len(r['cases']),refusals=r['refusals'],failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
