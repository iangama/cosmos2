"""EOS against independent50-digit polylogs, numerical derivatives and Maxwell identity."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile
import mpmath as mp
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is5-thermal-staging'
sys.path.insert(0,str(STAGE))
import is5_eos as eos
import is5_core as core
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    path=ROOT/('evidence/is5-thermal-eos-'+args.label+'.json')
    archive=ROOT/('output/is5-thermal-eos-'+args.label+'.zip')
    if path.exists() or archive.exists():raise FileExistsError('Preserve EOS evidence')
    files=[STAGE/n for n in ['is5_eos.py','is5_core.py','is5_reference_pp.py','is5_reference_cno.py','reference-manifest.json','base-manifest.json']]
    files += [Path(__file__),ROOT/'IS-5-TERMICA-CONTRATO-PREVIO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),generation=eos.generation(),
           fermi=[],cases=[],refusals=0,limits_before_execution=dict(fermi_relative=2e-10,EOS_relative=2e-10,derivatives_relative=2e-6,Maxwell_relative=2e-6))
    mp.mp.dps=50
    fd=lambda s,eta:mp.re(-mp.polylog(mp.mpf(str(s))+1,-mp.exp(eta)))
    try:
        for eta in [-20.,-10.,-5.,-1.,0.,1.,3.,10.,20.]:
            for order in [-.5,.5,1.5]:
                actual=eos.fermi(order,eta);expected=float(fd(order,mp.mpf(str(eta))))
                error=abs(actual-expected)/expected
                assert error<=2e-10,(order,eta,error)
                r['fermi'].append(dict(order=order,eta=eta,value=actual,reference=expected,relative_error=error))
        for order in [-.5,.5,1.5]:
            assert abs(eos.fermi(order,-20)/math.exp(-20)-1)<3e-9
        for t in [1.1e7,1.5e7,2.9e7]:
            for rho in [1.1e4,1.5e5,2.9e5]:
                for hydrogen,catalyst,seed in [(.05,0.,'n14'),(.34,.01,'n14'),(.75,.05,'c12')]:
                    p={**core.DEFAULT_PARAMETERS,'hydrogen_fraction':hydrogen,'catalyst_fraction':catalyst,'catalyst_seed':seed}
                    y=core.initial_state(p)[:10];yi=float(np.sum(y));ye=float(core.Z@y)
                    actual=eos.evaluate(t,rho,[float(v) for v in y])
                    mt,mrho,mk,mh,mme,mmu,ma=map(lambda v:mp.mpf(str(v)),(t,rho,eos.K,eos.H,eos.ME,eos.MU,eos.ARAD))
                    nb=mrho/mmu;ne=nb*mp.mpf(str(ye));ni=nb*mp.mpf(str(yi))
                    wavelength=mh/mp.sqrt(2*mp.pi*mme*mk*mt);phi=ne*wavelength**3/2
                    eta=mp.findroot(lambda q:fd(.5,q)-phi,(mp.log(phi),mp.log(phi)+1),tol=mp.mpf('1e-40'))
                    pe=2/wavelength**3*mk*mt*fd(1.5,eta)
                    pressure=ni*mk*mt+pe+ma*mt**4/3
                    energy=mp.mpf('1.5')*(ni*mk*mt+pe)+ma*mt**4
                    errors={k:abs(actual[k]-float(v))/abs(float(v)) for k,v in [('pressure_Pa',pressure),('internal_energy_J_m3',energy),('electron_pressure_Pa',pe)]}
                    assert abs(actual['electron_eta']-float(eta))<1e-9
                    assert max(errors.values())<=2e-10 and actual['electron_number_relative_residual']<=1e-10
                    dt=t*5e-5;dr=rho*5e-5
                    tp=eos.mixture(t+dt,rho,yi,ye);tm=eos.mixture(t-dt,rho,yi,ye)
                    rp=eos.mixture(t,rho+dr,yi,ye);rm=eos.mixture(t,rho-dr,yi,ye)
                    cv=(tp['internal_energy_J_m3']-tm['internal_energy_J_m3'])/(2*dt)
                    cv_error=abs(cv-actual['heat_capacity_J_m3_K'])/actual['heat_capacity_J_m3_K']
                    derivatives={}
                    for key,n,coordinate in [('ions',yi,0),('electrons',ye,1)]:
                        delta=n*5e-5;plus=[yi,ye];minus=[yi,ye];plus[coordinate]+=delta;minus[coordinate]-=delta
                        derivative=(eos.mixture(t,rho,*plus)['internal_energy_J_m3']-eos.mixture(t,rho,*minus)['internal_energy_J_m3'])/(2*delta)
                        expected=actual['du_d'+key+'_per_baryon_J_m3']
                        derivatives[key]=abs(derivative-expected)/expected
                    assert max(cv_error,*derivatives.values())<=2e-6,(cv_error,derivatives)
                    de_drho=(rp['internal_energy_J_m3']/(rho+dr)-rm['internal_energy_J_m3']/(rho-dr))/(2*dr)
                    dp_dt=(tp['pressure_Pa']-tm['pressure_Pa'])/(2*dt)
                    maxwell=abs(actual['pressure_Pa']-rho*rho*de_drho-t*dp_dt)/actual['pressure_Pa']
                    assert maxwell<=2e-6 and actual['heat_capacity_J_m3_K']>0
                    r['cases'].append(dict(temperature_K=t,density_kg_m3=rho,hydrogen=hydrogen,catalyst=catalyst,seed=seed,
                        EOS=actual,reference_relative_errors=errors,heat_capacity_derivative_relative_error=cv_error,
                        composition_derivative_relative_errors=derivatives,Maxwell_relative_error=maxwell))
        good=[float(v) for v in core.initial_state(core.DEFAULT_PARAMETERS)[:10]]
        for request in [(True,1.5e5,good),(9e6,1.5e5,good),(31e6,1.5e5,good),(15e6,1e3,good),
                        (15e6,1.5e5,good[:9]),(15e6,1.5e5,[True,*good[1:]]),(15e6,1.5e5,[-1.,*good[1:]]),
                        (15e6,1.5e5,[2.,*good[1:]])]:
            try:eos.evaluate(*request)
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Invalid EOS accepted')
        for request in [(.5,True),(.5,41),(.5,float('nan')),(0,0)]:
            try:eos.fermi(*request)
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Invalid Fermi request accepted')
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,scope='Numerical ideal-mixture EOS only; not physical precision against MESA/HELM or coupled thermal evolution.')
    except Exception:r['failure']=traceback.format_exc()
    path.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(accepted=r['accepted'],fermi=len(r['fermi']),cases=len(r['cases']),refusals=r['refusals'],failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
