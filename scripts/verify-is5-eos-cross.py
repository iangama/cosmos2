"""Independent50dps and finite-difference audit of density/temperature EOS derivatives."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import time
import traceback
import zipfile
import mpmath as mp

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is5-eos-cross-{args.label}'
    path=ROOT/f'evidence/is5-eos-cross-{args.label}.json'
    if folder.exists() or path.exists():raise FileExistsError('Preserve EOS cross evidence')
    anchor=ROOT/'evidence/is5-coulomb-science-20261028a.json'
    accepted=json.loads(anchor.read_text());assert accepted['accepted']
    hashes=dict(accepted['source_sha256'])
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    sys.path.insert(0,str(ROOT/'output/is5-compression-staging'))
    import is5_eos_cross as cross
    model=cross.model
    sys.path.insert(0,str(ROOT/'output/is5-coulomb-network-staging'))
    import is5_coulomb_network as network
    assert network.generation()==accepted['generation']
    base=network.base
    gen=cross.generation()
    files=[Path(__file__),anchor,*cross.FILES]
    hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    fixtures=[]
    for temp in [12e6,14e6,15e6]:
        for rho in [1e5,1.5e5]:
            for seed in ['n14','o16']:
                parameters=base.parameters(dict(temperature_K=temp,density_kg_m3=rho,hydrogen_fraction=.34,
                    catalyst_fraction=.01,catalyst_seed=seed,duration_s=315576000000.,volume_m3=1.))
                y=base.initial_state(parameters)[:base.NSPEC].tolist()
                fixtures.append(dict(T=temp,rho=rho,seed=seed,Y=y,A=[int(v) for v in base.A],Z=[int(v) for v in base.Z]))
    folder.mkdir()
    fixture_path=folder/'fixtures-before-execution.json';fixture_path.write_text(json.dumps(fixtures,indent=2)+'\n')
    hashes[fixture_path.relative_to(ROOT).as_posix()]=sha(fixture_path)
    archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),generation=gen,
           cases=[],refusals=[],mp_derivative_checks=0,FD_derivative_checks=0,
           limits_before_execution=dict(mp_dps=50,mp_relative=1e-8,FD_relative=2e-6,
               FD_steps=[1e-4,5e-5,2.5e-5],maxwell_total_relative=1e-10,pressure_floor_nb_k=1e-14,energy_floor_nb_kT=1e-14))
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    persist()
    try:
        mp.mp.dps=50
        for p in fixtures:
            began=time.perf_counter();t,rho,y,aa,zz=p['T'],p['rho'],p['Y'],p['A'],p['Z']
            actual=cross.evaluate(t,rho,y,aa,zz)
            assert actual['scientific_generation']==gen
            mt,mrho=mp.mpf(t),mp.mpf(rho);my=[mp.mpf(v) for v in y]
            yi,ye=mp.fsum(my),mp.fsum(q*v for q,v in zip(zz,my))
            mk,mmu=mp.mpf(model.K),mp.mpf(model.MU)
            def ideal(temp,density):
                nb=density/mmu;ne=nb*ye;ni=nb*yi
                wavelength=mp.mpf(model.ideal.H)/mp.sqrt(2*mp.pi*mp.mpf(model.ideal.ME)*mk*temp)
                target=ne*wavelength**3/2
                f=lambda order,eta:mp.re(-mp.polylog(order+1,-mp.exp(eta)))
                eta=mp.findroot(lambda value:f(mp.mpf('.5'),value)-target,mp.mpf(actual['state']['ideal']['electron_eta']))
                pe=ne*mk*temp*f(mp.mpf('1.5'),eta)/f(mp.mpf('.5'),eta)
                ur=mp.mpf(model.ideal.ARAD)*temp**4
                return dict(ideal_ions=(ni*mk*temp,mp.mpf('1.5')*ni*mk*temp),
                            ideal_electrons=(pe,mp.mpf('1.5')*pe),photons=(ur/3,ur))
            reference={}
            for name in ['ideal_ions','ideal_electrons','photons']:
                reference[name]={cross.PT:mp.diff(lambda temp:ideal(temp,mrho)[name][0],mt),
                                 cross.UR:mp.diff(lambda ell:ideal(mt,mp.exp(ell))[name][1],mp.log(mrho))}
            reference['ideal']={field:mp.fsum(reference[name][field] for name in ['ideal_ions','ideal_electrons','photons']) for field in [cross.PT,cross.UR]}
            tau,ell=mp.log(mt),mp.log(mrho/mmu)
            for name in ['ii','ie','ee','mix']:
                free=lambda a,b:model.free_energy_components(mp.exp(a),mp.exp(b),my,zz,mp)[name]
                ft=mp.diff(lambda a:free(a,ell),tau)
                fr=mp.diff(lambda b:free(tau,b),ell)
                mixed=mp.diff(free,(tau,ell),(1,1))
                reference[name]={cross.PT:(mixed-ft)/mt,cross.UR:fr-mixed}
            reference['Coulomb_sum']={field:mp.fsum(reference[name][field] for name in ['ii','ie','ee','mix']) for field in [cross.PT,cross.UR]}
            reference['total']={field:reference['ideal'][field]+reference['Coulomb_sum'][field] for field in [cross.PT,cross.UR]}
            nb=actual['state']['ideal']['baryon_density_m3']
            floors={cross.PT:1e-14*nb*model.K,cross.UR:1e-14*nb*model.K*t}
            errors=[]
            for name,fields in reference.items():
                for field,value in fields.items():
                    error=float(abs(mp.mpf(actual['derivatives'][name][field])-value)/max(abs(value),mp.mpf(floors[field])))
                    assert error<=1e-8,(p,name,field,error)
                    errors.append(dict(component=name,field=field,reference_decimal=mp.nstr(value,55),relative=error));r['mp_derivative_checks']+=1
            def values(temp,density):
                state=model.evaluate(temp,density,y,aa,zz);b=state['ideal']
                result={'ideal_ions':(b['ion_pressure_Pa'],b['ion_internal_energy_J_m3']),
                        'ideal_electrons':(b['electron_pressure_Pa'],b['electron_internal_energy_J_m3']),
                        'photons':(b['radiation_pressure_Pa'],b['radiation_internal_energy_J_m3']),
                        'ideal':(b['pressure_Pa'],b['internal_energy_J_m3'])}
                result.update({name:(v['pressure_Pa'],v['internal_energy_J_m3']) for name,v in state['components'].items() if name!='sum'})
                result['Coulomb_sum']=(state['components']['sum']['pressure_Pa'],state['components']['sum']['internal_energy_J_m3'])
                result['total']=(state['total']['pressure_Pa'],state['total']['internal_energy_J_m3'])
                return result
            finite=[]
            for step in [1e-4,5e-5,2.5e-5]:
                tp,tm=values(t*(1+step),rho),values(t*(1-step),rho)
                rp,rm=values(t,rho*math.exp(step)),values(t,rho*math.exp(-step))
                for name in reference:
                    measured={cross.PT:(tp[name][0]-tm[name][0])/(2*step*t),cross.UR:(rp[name][1]-rm[name][1])/(2*step)}
                    for field,value in measured.items():
                        target=actual['derivatives'][name][field]
                        error=abs(value-target)/max(abs(target),floors[field])
                        assert error<=2e-6,(p,name,field,step,error)
                        finite.append(dict(component=name,field=field,step=step,relative=error));r['FD_derivative_checks']+=1
            assert actual['maxwell']['total']['relative']<=1e-10
            r['cases'].append(dict(fixture=p,result=actual,mp_errors=errors,FD_errors=finite,elapsed_s=time.perf_counter()-began))
            persist();print(json.dumps(dict(case=len(r['cases']),T=t,rho=rho,seed=p['seed'],mp_max=max(e['relative'] for e in errors),FD_max=max(e['relative'] for e in finite))),flush=True)
        first=fixtures[0]
        for name,args in [
            ('boolT',(True,first['rho'],first['Y'],first['A'],first['Z'])),
            ('boolrho',(first['T'],False,first['Y'],first['A'],first['Z'])),
            ('lowT',(9e6,first['rho'],first['Y'],first['A'],first['Z'])),
            ('lowrho',(first['T'],1e3,first['Y'],first['A'],first['Z'])),
            ('length',(first['T'],first['rho'],first['Y'][:-1],first['A'],first['Z'])),
            ('zeroY',(first['T'],first['rho'],[0.]*len(first['Y']),first['A'],first['Z'])),
            ('boolZ',(first['T'],first['rho'],first['Y'],first['A'],[True,*first['Z'][1:]])),
            ('positive_Fe_trace',(1e7,3e5,[.7-56e-30,.075,1e-30],[1,4,56],[1,2,26]))]:
            try:cross.evaluate(*args)
            except ValueError as error:r['refusals'].append(dict(case=name,reason=str(error)))
            else:raise AssertionError('Invalid cross EOS accepted: '+name)
        assert r['mp_derivative_checks']==240 and r['FD_derivative_checks']==720 and len(r['refusals'])==8
        assert all(sha(ROOT/n)==value for n,value in hashes.items())
        r.update(accepted=True,completed=True,scope='Cross derivatives only, frozen parent EOS and12interior states; no compression evolution or product acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    persist();print(json.dumps({k:r.get(k) for k in ['accepted','completed','mp_derivative_checks','FD_derivative_checks','failure']}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
