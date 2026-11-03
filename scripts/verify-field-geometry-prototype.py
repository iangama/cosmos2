"""C2-11 staging 3D sampling and geometry, with actual field directions."""
from pathlib import Path
import copy,importlib.util,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
def module(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'output/c211-staging'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
field=module('gravity_field');geometry=module('field_geometry');center=[3e9,-2e9,7e9];radius=1e8;points=geometry.shell(center,radius);bodies=[{'id':'source','mass':1,'position':[v/1e9 for v in center]}];samples=field.evaluate_points(bodies,points);frozen=copy.deepcopy(samples);arrows=geometry.arrows(samples,1e7);maxangle=maxlength=maxradius=0.;octants=set()
for point,arrow in zip(points,arrows['arrows']):
 d=[point[k]-center[k] for k in range(3)];octants.add(tuple(v>0 for v in d));maxradius=max(maxradius,abs(math.hypot(*d)-radius));tail,tip,*_=arrow['segment_m'];v=[tip[k]-tail[k] for k in range(3)];maxlength=max(maxlength,abs(math.hypot(*v)-1e7));cos=math.fsum(-d[k]*v[k] for k in range(3))/(math.hypot(*d)*math.hypot(*v));maxangle=max(maxangle,abs(1-cos));assert cos>1-1e-14
assert len(octants)==8 and maxradius<2e-6 and maxlength<2e-6 and samples==frozen
zero={'index':7,'valid':True,'position_m':[0,0,0],'acceleration_m_s2':[0,0,0]};bad={'index':8,'valid':False,'reason':'singular'};r=geometry.arrows([zero,bad],1);assert all(not a['drawn'] and 'segment_m' not in a for a in r['arrows'])
report={'status':'verified_staging_only_not_native_product','spherical_samples':len(points),'octants_covered':len(octants),'radial_shell_radius_difference_m_max':maxradius,'arrow_length_difference_m_max':maxlength,'one_minus_radial_inward_cosine_max':maxangle,'sampling_does_not_mutate_physical_samples':True,'zero_and_singular_fields_do_not_invent_arrows':True,'legend_explicit_direction_only_not_magnitude':arrows['scale']}
(ROOT/'evidence/field-geometry-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
