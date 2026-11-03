"""C2-11 staging math only: independent derivatives and geometric covariance."""
from pathlib import Path
import importlib.util,json,math,sys,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from physics import PHYSICAL_SCALE as U
installed='--installed' in sys.argv
source=ROOT/('app/gravity_field.py' if installed else 'output/c211-staging/gravity_field.py')
spec=importlib.util.spec_from_file_location('candidate_field',source);field=importlib.util.module_from_spec(spec);spec.loader.exec_module(field)
rng=np.random.default_rng(611);cases=[];maxgradient=maxrotation=maxtrace=0.
for n in [1,2,32,128]:
 bodies=[{'id':'b'+str(i),'mass':float(rng.uniform(.001,1)),'position':rng.uniform(-2,2,3).tolist()} for i in range(n)];point=rng.uniform(5,10,3)*1e9;sample=field.evaluate(bodies,point.tolist());tensor=np.array(sample['tidal_tensor_s_2']);numeric=np.zeros((3,3));step=10000.
 for k in range(3):
  plus=point.copy();minus=point.copy();plus[k]+=step;minus[k]-=step;numeric[:,k]=(np.array(field.evaluate(bodies,plus.tolist())['acceleration_m_s2'])-field.evaluate(bodies,minus.tolist())['acceleration_m_s2'])/(2*step)
 err=float(np.linalg.norm(tensor-numeric)/np.linalg.norm(tensor));maxgradient=max(maxgradient,err);assert err<2e-8,err
 assert np.max(abs(tensor-tensor.T))==0;trace=abs(float(np.trace(tensor)))/float(np.linalg.norm(tensor));maxtrace=max(maxtrace,trace);assert trace<1e-14
 q,_=np.linalg.qr(rng.normal(size=(3,3)));q[:,0]*=np.linalg.det(q);rotated=[{**b,'position':(q@b['position']).tolist()} for b in bodies];other=field.evaluate(rotated,(q@point).tolist());terr=float(np.linalg.norm(np.array(other['tidal_tensor_s_2'])-q@tensor@q.T)/np.linalg.norm(tensor));gerr=float(np.linalg.norm(np.array(other['acceleration_m_s2'])-q@sample['acceleration_m_s2'])/sample['acceleration_norm_m_s2']);maxrotation=max(maxrotation,terr,gerr);assert terr<1e-13 and gerr<1e-13
 cases.append({'sources':n,'finite_difference_g_gradient_relative_difference':err,'tensor_rotation_covariance_relative_difference':terr})
one=field.evaluate([{'id':'one','mass':1,'position':[0,0,0]}],[2e9,0,0]);expected=np.diag([2.,-1.,-1.])*U['nominal_GM_unit_m3_s2']/(2e9)**3;assert np.allclose(one['tidal_tensor_s_2'],expected,rtol=1e-15,atol=0)
batch=field.evaluate_points([{'id':'one','mass':1,'position':[0,0,0]}],[[0,0,0],[2e9,0,0]]);assert batch[0]['valid'] is False and batch[1]['valid'] and [r['index'] for r in batch]==[0,1] and 'tidal_tensor_s_2' not in batch[0]
report={'status':'verified_staging_only_not_product','cases':cases,'max_finite_difference_gradient_relative_difference':maxgradient,'max_rotation_covariance_relative_difference':maxrotation,'max_trace_over_tensor_norm':maxtrace,'isolated_mass_radial_eigenvalues_2_minus1_minus1':True,'singular_batch_point_explicit_reason_no_invented_zero':True}
if installed:report.update(status='verified_installed_math_not_full_C211',module_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(ROOT/('evidence/field-tensor-installed-check.json' if installed else 'evidence/field-tensor-prototype-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
