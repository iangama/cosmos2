"""Fixed numerical controls: same initial doubles, units and incremental reference states."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import solve_ivp

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'evidence/is6-dynamics16-verification-20261112a.json'
r=json.loads(source.read_text());assert not r['accepted'] and r.get('failure')
initial_path=ROOT/r['fixture']['path'];initial=json.loads(initial_path.read_text())
series_path=ROOT/r['propagation']['series_file'];data=json.loads(series_path.read_text())
out=ROOT/'evidence/is6-dynamics16-numerics-20261112a.json'
folder=ROOT/'output/is6-dynamics16-numerics-20261112a'
assert not out.exists() and not folder.exists();folder.mkdir()
baseline=np.array(data['canonical_IAS15']);times=np.array(data['seconds'])
U=initial['physical_scale'];L,V,T=[U[k] for k in ['length_unit_m','velocity_unit_m_s','time_unit_s']]
masses=np.array([b['mass'] for b in initial['bodies']]);gm=np.array([b['source_GM']['value'] for b in initial['bodies']])
first=baseline[0];n=16;c=3*n
p0=first[:,:3]*L;v0=first[:,3:]*V
raw0=np.array(data['canonical_DOP853'])[0]
transformed=np.array(data['canonical_transformed'])[0]
recipe=r['recipe_before_execution'];transformed[:,:3]-=np.array(recipe['translation_m'])/L;transformed[:,3:]-=np.array(recipe['boost_m_s'])/V
result=dict(completed=False,accepted_as_product=False,source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),source,initial_path,series_path]},
    hypothesis='Short-period satellite velocity differences may include roundoff from initial conversion, absolute state accumulation and translated coordinates, beyond IAS15 epsilon.',
    recipes_before_execution=['aligned_SI: same canonical initial doubles converted to SI; DOP853 rtol2e-13,atol1mm/1e-9m/s,max_step3600s',
                              'canonical: same initial canonical doubles and masses; tolerances scaled to canonical units,max_step3600s',
                              'incremental_SI: integrate offsets from the same initial phase; pair differences use initial separation plus offset differences; same SI limits'],
    initial_DOP853_position_difference_m=(np.abs(first[:,:3]-raw0[:,:3])*L).tolist(),
    initial_transformation_position_difference_m=(np.abs(first[:,:3]-transformed[:,:3])*L).tolist(),runs=[],
    scope='Diagnostic controls only; original formal refusal preserved and no product or tolerance acceptance.')


def acceleration(position,parameters):
    delta=position[None,:,:]-position[:,None,:]
    distance=np.linalg.norm(delta,axis=2);np.fill_diagonal(distance,np.inf)
    return np.sum(delta*(parameters[None,:]/distance**3)[:,:,None],axis=1)


for name in ['aligned_SI','canonical','incremental_SI']:
    if name=='canonical':
        def equation(t,x):return np.concatenate((x[c:],acceleration(x[:c].reshape(n,3),masses).ravel()))
        start=np.concatenate((first[:,:3].ravel(),first[:,3:].ravel()));end=times[-1]/T
        atols=np.array([.001/L]*c+[1e-9/V]*c);step=3600/T;sample_times=times/T
    elif name=='aligned_SI':
        def equation(t,x):return np.concatenate((x[c:],acceleration(x[:c].reshape(n,3),gm).ravel()))
        start=np.concatenate((p0.ravel(),v0.ravel()));end=times[-1];sample_times=times
        atols=np.array([.001]*c+[1e-9]*c);step=3600
    else:
        separation=p0[None,:,:]-p0[:,None,:]
        def equation(t,x):
            offset=x[:c].reshape(n,3)
            delta=separation+(offset[None,:,:]-offset[:,None,:])
            distance=np.linalg.norm(delta,axis=2);np.fill_diagonal(distance,np.inf)
            a=np.sum(delta*(gm[None,:]/distance**3)[:,:,None],axis=1)
            return np.concatenate(((v0+x[c:].reshape(n,3)).ravel(),a.ravel()))
        start=np.zeros(2*c);end=times[-1];sample_times=times
        atols=np.array([.001]*c+[1e-9]*c);step=3600
    began=time.perf_counter()
    solution=solve_ivp(equation,(0,end),start,method='DOP853',rtol=2e-13,atol=atols,max_step=step,dense_output=True)
    assert solution.success and solution.t[-1]==end
    values=solution.sol(sample_times)
    states=np.concatenate((values[:c].T.reshape(-1,n,3),values[c:].T.reshape(-1,n,3)),axis=2)
    if name=='incremental_SI':states[:,:,:3]+=p0[None,:,:];states[:,:,3:]+=v0[None,:,:]
    if name!='canonical':states[:,:,:3]/=L;states[:,:,3:]/=V
    error=np.abs(states-baseline);error[:,:,:3]*=L;error[:,:,3:]*=V
    path=folder/(name+'.json');path.write_text(json.dumps(dict(canonical_states=states.tolist()),allow_nan=False)+'\n')
    row=dict(name=name,position_component_max_m=float(error[:,:,:3].max()),velocity_component_max_m_s=float(error[:,:,3:].max()),
             per_body_velocity_max_m_s={b['naif_id']:float(error[:,i,3:].max()) for i,b in enumerate(initial['bodies'])},
             steps=len(solution.t)-1,nfev=solution.nfev,wall_s=time.perf_counter()-began,path=path.relative_to(ROOT).as_posix(),sha256=sha(path))
    result['runs'].append(row);print(json.dumps(row),flush=True)
result['completed']=True
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
