"""Freeze Sun axes, prescribed Parker field and four monopoles in one paused phase."""
from pathlib import Path
from dataclasses import dataclass
import copy
import hashlib
import json
import math
import atlas
from physics import PHYSICAL_SCALE
from is4_values import scalar,vector
from is4_domains import outside_ellipsoid
from is4_wind_field import Parker

FRAME='initial_subset_barycenter_inertial_axes_J2000'
RADII={'sol:naif:10':695700000.,'sol:naif:399':100*6378137.,'sol:naif:301':10*1737400.,'sol:naif:599':100*71492000.}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()
def product(matrix,value):return tuple(math.fsum(row[k]*value[k] for k in range(3)) for row in matrix)

@dataclass(frozen=True)
class Source:
    id:str
    reference_id:str
    GM_m3_s2:float
    position_model_m:tuple
    exclusion_radius_m:float

class Snapshot:
    def __init__(self,phase,configuration=None):
        if not isinstance(phase,dict):raise ValueError('Explicit paused solar phase required')
        phase=copy.deepcopy(phase);self.field=Parker(configuration)
        if phase.get('paused') is not True:raise ValueError('Pause the solar copy before freezing wind sources')
        if phase.get('contract',{}).get('frame')!=FRAME or phase['contract'].get('model')!='newtonian_point_masses':raise ValueError('Adopted inertial monopoles required')
        if digest(phase.get('physical_scale'))!=digest(PHYSICAL_SCALE):raise ValueError('Adopted SI scale required')
        if phase.get('gravity_effects') or phase.get('material_tides'):raise ValueError('Additional gravity terms are not adopted')
        initial=phase.get('atlas_initial',{})
        if initial.get('kind')!='solar_four_physical_centers':raise ValueError('Four-center solar source required')
        for key in ['system_id','edit_token']:
            v=phase.get(key)
            if not isinstance(v,str) or len(v)!=32 or any(c not in '0123456789abcdef' for c in v):raise ValueError('Invalid source identity')
        if type(phase.get('revision')) is not int or phase['revision']<0:raise ValueError('Invalid source revision')
        if scalar(phase.get('time'))<0:raise ValueError('Nonnegative source time required')
        if phase.get('scientific_generation',{}).get('candidate_extension',{}).get('id')!='is3-body-fields':raise ValueError('Adopted body-field scientific generation required')
        fixture=phase.get('fixture_sha256')
        if not isinstance(fixture,str) or len(fixture)!=64 or any(c not in '0123456789abcdef' for c in fixture):raise ValueError('Fixture identity required')
        bodies=phase.get('bodies')
        if not isinstance(bodies,list) or len(bodies)!=4 or any(not isinstance(b,dict) for b in bodies) or {b.get('reference_id') for b in bodies}!=set(RADII):raise ValueError('Exactly four physical centers required')
        if any(not isinstance(b.get('id'),str) or not b['id'] for b in bodies) or len({b['id'] for b in bodies})!=4:raise ValueError('Unique source identities required')
        sun=next(b for b in bodies if b['reference_id']=='sol:naif:10');origin=vector(sun.get('position'))
        et=scalar(initial['source']['epoch']['et_tdb_s'])+phase['time']*PHYSICAL_SCALE['time_unit_s']
        if not math.isfinite(et):raise ValueError('Unrepresentable source epoch')
        with atlas.LOCK:
            atlas.initialize();spice=atlas.SPICE
            rotation=spice.pxform('IAU_SUN','J2000',et).tolist();render=spice.pxform('J2000','GALACTIC',et).tolist()
            utc=spice.et2utc(et,'ISOC',6)+'Z';atlas.normalize_epoch(utc[:19]);provenance=copy.deepcopy(atlas.PROVENANCE)
        self._rotation=tuple(vector(row) for row in rotation)
        transpose=tuple(tuple(self._rotation[j][i] for j in range(3)) for i in range(3))
        sources=[]
        for b in bodies:
            position=vector(b.get('position'));mass=scalar(b.get('mass'))
            if not 0<mass<=100 or math.hypot(*position)*PHYSICAL_SCALE['length_unit_m']>1e17:raise ValueError('Source mass/position outside adopted range')
            delta=tuple((position[k]-origin[k])*PHYSICAL_SCALE['length_unit_m'] for k in range(3))
            sources.append(Source(b['id'],b['reference_id'],scalar(mass*PHYSICAL_SCALE['nominal_GM_unit_m3_s2']),product(transpose,delta),RADII[b['reference_id']]))
        self.sources=tuple(sources);self._phase=phase;self.magnetic_evaluations=0
        self._descriptor=dict(schema=1,kind='static_solar_wind_snapshot_test_particle',frame='IAU_SUN_orientation_frozen_as_inertial_axes',
            epoch=dict(et_tdb_s=et,utc=utc,UTC_rounding_s=1e-6),scene_phase={k:phase[k] for k in ['system_id','edit_token','revision','time','fixture_sha256']},
            scene_phase_sha256=digest(phase),source_body_id=sun['id'],source_body_reference_id=sun['reference_id'],
            origin_inertial_m=[v*PHYSICAL_SCALE['length_unit_m'] for v in origin],model_to_J2000=rotation,J2000_to_render=render,
            sources=[dict(id=s.id,reference_id=s.reference_id,GM_m3_s2=s.GM_m3_s2,position_model_m=list(s.position_model_m),exclusion_radius_m=s.exclusion_radius_m) for s in sources],
            field=self.field.descriptor,orientation_provenance=provenance,implementation_sha256={n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ['is4_wind_snapshot.py','is4_wind_field.py','is4_values.py','is4_domains.py','is4_particles.py']},provider_code_sha256=hashlib.sha256(Path(atlas.__file__).read_bytes()).hexdigest(),clock='Independent particle seconds; all source centers, orientation and epoch frozen.',
            source_feedback=False,potential_policy='Static monopoles and conservative prescribed E; no origin-acceleration subtraction.')
        self.configuration_sha256=digest(self._descriptor)

    @property
    def descriptor(self):return copy.deepcopy(self._descriptor)

    def segment_in_domain(self,start,end):
        a,b=vector(start),vector(end)
        if not self.field.segment_in_domain(a,b):return False
        for s in self.sources:
            left=[a[k]-s.position_model_m[k] for k in range(3)];right=[b[k]-s.position_model_m[k] for k in range(3)]
            if not outside_ellipsoid(left,right,[s.exclusion_radius_m]*3):return False
        return True

    def evaluate(self,position):
        p=vector(position)
        if not self.segment_in_domain(p,p):raise ValueError('Point outside wind/gravity domain; field not queried')
        field=self.field.evaluate(p);self.magnetic_evaluations+=1;accelerations=[];potentials=[]
        for s in self.sources:
            d=[p[k]-s.position_model_m[k] for k in range(3)];r=math.hypot(*d)
            accelerations.append([-s.GM_m3_s2*v/r**3 for v in d]);potentials.append(-s.GM_m3_s2/r)
        g=[math.fsum(a[k] for a in accelerations) for k in range(3)];potential=math.fsum(potentials)
        if not all(math.isfinite(v) for v in [*g,potential]):raise ValueError('Unrepresentable gravity')
        return {**field,'gravity_m_s2':g,'gravity_potential_J_kg':potential,'configuration_sha256':self.configuration_sha256}

    def potential_difference(self,start,end):
        a,b=vector(start),vector(end)
        if not self.segment_in_domain(a,a) or not self.segment_in_domain(b,b):raise ValueError('Potential endpoint outside wind/gravity domain')
        d=[b[k]-a[k] for k in range(3)];d2=math.fsum(v*v for v in d);terms=[]
        for s in self.sources:
            left=[a[k]-s.position_model_m[k] for k in range(3)];right=[b[k]-s.position_model_m[k] for k in range(3)]
            r0,r1=math.hypot(*left),math.hypot(*right)
            difference=math.fsum([2*math.fsum(left[k]*d[k] for k in range(3)),d2])
            terms.append(s.GM_m3_s2*difference/(r0*r1*(r0+r1)))
        value=math.fsum(terms)
        if not math.isfinite(value):raise ValueError('Unrepresentable gravity potential difference')
        return value

    def electric_potential_difference(self,start,end):
        if not self.segment_in_domain(start,start) or not self.segment_in_domain(end,end):raise ValueError('Potential endpoint outside wind/gravity domain')
        return self.field.electric_potential_difference(start,end)
