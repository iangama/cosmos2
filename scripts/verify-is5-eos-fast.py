"""Compare thermal-row representation with frozen full-Hessian EOS data."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-compression-fast-staging'))
import is5_eos_fast as model
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);args=ap.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):ap.error('Invalid label')
    folder=ROOT/f'output/is5-eos-fast-{args.label}';path=ROOT/f'evidence/is5-eos-fast-{args.label}.json'
    if folder.exists() or path.exists():raise FileExistsError('Preserve fast EOS evidence')
    anchor=ROOT/'evidence/is5-eos-cross-20261029a.json';cross=json.loads(anchor.read_text());assert cross['accepted']
    sciencepath=ROOT/'evidence/is5-compression-20261029b.json';science=json.loads(sciencepath.read_text());assert science['accepted']
    assert cross['generation']==model.reference.generation()
    hashes={**cross['source_sha256'],**science['source_sha256']}
    for p in [Path(__file__),anchor,sciencepath,*model.FILES]:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    for case in science['cases']:
        hashes.update(case['artifact_sha256'])
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    folder.mkdir();archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    generation=model.generation()
    r=dict(accepted=False,completed=False,generation=generation,source_sha256=hashes,archive_sha256=sha(archive),
           limits_before_execution=dict(relative=5e-12,energy_pressure_floor_nbKT=1e-12,thermal_floor_nbK=1e-12,chemical_floor_KT=1e-12),
           fixtures=[],trajectory_states=[],refusals=[],scalar_checks=0,maximum_relative_error=0.)
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
    def compare(fixture,reference):
        t,rho,y,a,z=[fixture[k] for k in ['T','rho','Y','A','Z']]
        actual=model.evaluate(t,rho,y,a,z);nb=rho/model.parent.MU;k=model.parent.K
        errors=[]
        def field(label,x,v,floor):
            x=np.asarray(x);v=np.asarray(v);assert np.isfinite(x).all() and x.shape==v.shape,label
            error=float(np.max(abs(x-v)/np.maximum(np.maximum(abs(x),abs(v)),floor)))
            assert error<=5e-12,(label,error)
            errors.append(dict(field=label,relative=error,scalars=int(x.size)))
        for component in ['ii','ie','ee','mix','sum']:
            for key in ['free_energy_J_m3','internal_energy_J_m3','pressure_Pa','heat_capacity_J_m3_K',
                        'du_dnumber_per_baryon_J_m3','neutral_chemical_potential_J']:
                floor=1e-12*k*t if key=='neutral_chemical_potential_J' else 1e-12*nb*k*(1 if key=='heat_capacity_J_m3_K' else t)
                field(component+'.'+key,actual['state']['components'][component][key],reference['state']['components'][component][key],floor)
        for key in ['internal_energy_J_m3','pressure_Pa','heat_capacity_J_m3_K','du_dnumber_per_baryon_J_m3']:
            field('total.'+key,actual['state']['total'][key],reference['state']['total'][key],1e-12*nb*k*(1 if key=='heat_capacity_J_m3_K' else t))
        for component in ['ii','ie','ee','mix','Coulomb_sum','ideal','total']:
            for key in [model.PT,model.UR]:
                field(component+'.'+key,actual['derivatives'][component][key],reference['derivatives'][component][key],1e-12*nb*k*(1 if key==model.PT else t))
        r['scalar_checks']+=sum(e['scalars'] for e in errors)
        r['maximum_relative_error']=max(r['maximum_relative_error'],max(e['relative'] for e in errors))
        return dict(fixture=fixture,errors=errors)
    persist()
    try:
        for case in cross['cases']:r['fixtures'].append(compare(case['fixture'],case['result']))
        sys.path.insert(0,str(ROOT/'output/is5-coulomb-network-staging'))
        import is5_coulomb_network as network
        for index,case in enumerate(science['cases']):
            name=next(n for n in case['artifact_sha256'] if n.endswith('-Radau.json'))
            run=json.loads((ROOT/name).read_text())
            for sample in [1,20,60,120,180,220,239]:
                fixture=dict(T=run['temperature_K'][sample],rho=run['density_kg_m3'][sample],Y=run['number_per_baryon'][sample],A=network.AI,Z=network.ZI)
                reference=model.reference.evaluate(*[fixture[k] for k in ['T','rho','Y','A','Z']])
                r['trajectory_states'].append(dict(case=index,sample=sample,**compare(fixture,reference)))
            persist()
        original=cross['cases'][0]['fixture']
        bad=[('temperature',dict(T=9e6)),('density',dict(rho=3.1e5)),('boolean',dict(T=True)),
             ('negative',dict(Y=[-1e-6]+original['Y'][1:])),('normalization',dict(Y=[.4]+original['Y'][1:])),
             ('length',dict(Z=original['Z'][:-1]))]
        for label,changes in bad:
            f={**original,**changes};reasons=[]
            for fn in [model.reference.evaluate,model.evaluate]:
                try:fn(*[f[k] for k in ['T','rho','Y','A','Z']])
                except ValueError as error:reasons.append(str(error))
                else:raise AssertionError('Invalid state accepted: '+label)
            assert reasons[0]==reasons[1],reasons
            r['refusals'].append(dict(case=label,reason=reasons[0]))
        assert len(r['fixtures'])==12 and len(r['trajectory_states'])==21 and len(r['refusals'])==6
        assert generation==model.generation() and all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,scope='Exact thermal Hessian-row representation of accepted EOS; no optimized evolution, worker or product acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    persist();print(json.dumps({k:r.get(k) for k in ['accepted','scalar_checks','maximum_relative_error','failure']}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
