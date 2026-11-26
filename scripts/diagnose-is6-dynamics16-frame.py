"""One predefined control: retain an explicit inertial origin and integrate near the COM."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'output/is6-dynamics16-staging'),str(ROOT/'output/is6-principal-moons-navigation-product0.25.1/app')]
import system16_import as product
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'evidence/is6-dynamics16-verification-20261112a.json';r=json.loads(source.read_text())
fixture=ROOT/r['fixture']['path'];initial=json.loads(fixture.read_text())
series_path=ROOT/r['propagation']['series_file'];data=json.loads(series_path.read_text())
out=ROOT/'evidence/is6-dynamics16-frame-20261112a.json';assert not out.exists()
U=initial['physical_scale'];L,V,T=[U[k] for k in ['length_unit_m','velocity_unit_m_s','time_unit_s']]
baseline=np.array(data['canonical_IAS15']);seconds=np.array(data['seconds'])
shift=np.array([3e12,-4e12,5e12])/L;boost=np.array([1000.,-2000.,3000.])/V
sim=product.simulation(initial)
for p in sim.particles:
 p.x+=shift[0];p.y+=shift[1];p.z+=shift[2];p.vx+=boost[0];p.vy+=boost[1];p.vz+=boost[2]
center=sim.com();origin=np.array([center.x,center.y,center.z]);origin_velocity=np.array([center.vx,center.vy,center.vz])
before=np.array([[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in sim.particles])
sim.move_to_com()
states=[]
for t in seconds:
 sim.integrate(t/T);states.append([[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in sim.particles])
states=np.array(states)
world=states.copy();world[:,:,:3]+=origin[None,None,:]+seconds[:,None,None]/T*origin_velocity[None,None,:];world[:,:,3:]+=origin_velocity[None,None,:]
roundtrip=world[0]-before
world[:,:,:3]-=shift[None,None,:]+seconds[:,None,None]/T*boost[None,None,:];world[:,:,3:]-=boost[None,None,:]
error=np.abs(world-baseline);error[:,:,:3]*=L;error[:,:,3:]*=V
result=dict(completed=True,accepted_as_product=False,hypothesis_before_execution='Absolute translation/boost is a representation choice; preserve its inertial COM origin explicitly and integrate the internal phase near zero.',
 recipe_before_execution=dict(shift_m=[3e12,-4e12,5e12],boost_m_s=[1000.,-2000.,3000.],normalization='rebound.move_to_com once before integration; origin and uniform velocity retained',epsilon=1e-9),
 source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),source,fixture,series_path,Path(product.__file__)]},
 inertial_origin_canonical=origin.tolist(),inertial_origin_velocity_canonical=origin_velocity.tolist(),
 initial_frame_roundtrip_position_m=float(np.abs(roundtrip[:,:3]).max()*L),initial_frame_roundtrip_velocity_m_s=float(np.abs(roundtrip[:,3:]).max()*V),
 position_component_max_m=float(error[:,:,:3].max()),velocity_component_max_m_s=float(error[:,:,3:].max()),
 per_body_velocity_max_m_s={b['naif_id']:float(error[:,i,3:].max()) for i,b in enumerate(initial['bodies'])},
 canonical_internal_series=states.tolist(),scope='One diagnostic frame representation control; no formal acceptance or change to original refusal.')
out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='canonical_internal_series'}),flush=True)
