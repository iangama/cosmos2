"""Static SI E=0/internal B/four-center gravity, bound to one paused solar phase.

The local axes retain the body's orientation at the snapshot epoch and are
inertial axes of this prescribed static experiment. No corotation E, fictitious
force, orbital clock advance, source feedback or external field is inferred.
"""
from dataclasses import dataclass
import copy
import hashlib
import json
import math

from physics import PHYSICAL_SCALE
from body_field_lines import Model,geodetic
from body_field_view import compare
from is4_values import scalar,vector
from is4_domains import outside_ellipsoid,shell_segment

FRAME='initial_subset_barycenter_inertial_axes_J2000'
REFERENCES={'sol:naif:10','sol:naif:399','sol:naif:301','sol:naif:599'}


def product(matrix,value):
    return tuple(math.fsum(row[k]*value[k] for k in range(3)) for row in matrix)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Source:
    id:str
    reference_id:str
    GM_m3_s2:float
    position_model_m:tuple
    exclusion_radius_m:float=.001


class Snapshot:
    def __init__(self,phase,reading):
        # Validate and reconstruct the provider before retaining caller-owned data.
        if not isinstance(phase,dict) or not isinstance(reading,dict):raise ValueError('Explicit phase and field reading required')
        phase,reading=copy.deepcopy(phase),copy.deepcopy(reading)
        if phase.get('paused') is not True:raise ValueError('Pause the solar copy before freezing particle sources')
        if phase.get('contract',{}).get('frame')!=FRAME or phase['contract'].get('model')!='newtonian_point_masses':
            raise ValueError('Adopted four-center inertial monopoles required')
        if digest(phase.get('physical_scale'))!=digest(PHYSICAL_SCALE):raise ValueError('SI scale differs from the adopted solar contract')
        if phase.get('gravity_effects') or phase.get('material_tides'):raise ValueError('Additional gravity terms are not adopted here')
        if phase.get('atlas_initial',{}).get('kind')!='solar_four_physical_centers':raise ValueError('Solar initial source required')
        bodies=phase.get('bodies')
        if not isinstance(bodies,list) or len(bodies)!=4 or any(not isinstance(b,dict) for b in bodies) or {b.get('reference_id') for b in bodies}!=REFERENCES:
            raise ValueError('Exactly the four physical centers are required')
        if any(not isinstance(b.get('id'),str) or not b['id'] for b in bodies) or len({b['id'] for b in bodies})!=4:
            raise ValueError('Unique source identities required')
        for name in ['system_id','edit_token']:
            value=phase.get(name)
            if not isinstance(value,str) or len(value)!=32 or any(c not in '0123456789abcdef' for c in value):raise ValueError('Invalid phase identity')
        if type(phase.get('revision')) is not int or phase['revision']<0:raise ValueError('Invalid phase revision')
        if scalar(phase.get('time'))<0:raise ValueError('Nonnegative scene time required')
        for key in ['system_id','edit_token','revision','time']:
            if type(reading.get(key)) is not type(phase[key]) or reading[key]!=phase[key]:raise ValueError('Field and phase identity/time differ')
        generation=phase.get('scientific_generation')
        if not isinstance(generation,dict) or generation.get('candidate_extension',{}).get('id')!='is3-body-fields':raise ValueError('Body-field scientific generation required')
        fixture=phase.get('fixture_sha256')
        if not isinstance(fixture,str) or len(fixture)!=64 or any(c not in '0123456789abcdef' for c in fixture):raise ValueError('Fixture identity required')
        if reading.get('frame')!=FRAME or digest(reading.get('scientific_generation'))!=digest(generation):
            raise ValueError('Field frame/generation differs from paused phase')
        body=next((b for b in bodies if b['id']==reading.get('body_id')),None)
        if body is None or body['reference_id']!=reading.get('body_reference_id'):raise ValueError('Field body is not an active matching source')
        c=reading.get('coordinates',{})
        if not isinstance(c,dict):raise ValueError('Explicit field coordinates required')
        if body['reference_id']=='sol:naif:399':
            from earth_magnetism import read
            expected=read(phase,body['id'],c.get('latitude_deg'),c.get('longitude_deg'),c.get('altitude_m'))
            matrix=reading.get('ITRF93_to_J2000');center_key='earth_center_inertial_m';point_key='point_ITRF93_m'
        elif body['reference_id']=='sol:naif:599':
            from jupiter_magnetism import read
            expected=read(phase,body['id'],c.get('radius_m'),c.get('latitude_planetocentric_deg'),c.get('longitude_east_deg'),reading.get('degree'))
            matrix=reading.get('SystemIII_to_J2000');center_key='jupiter_center_inertial_m';point_key='point_SystemIII_m'
        else:raise ValueError('No internal magnetic provider adopted for this body')
        compare({k:v for k,v in reading.items() if k!='scientific_generation'},expected)
        self._rotation=tuple(vector(row) for row in matrix)
        transpose=tuple(tuple(self._rotation[j][i] for j in range(3)) for i in range(3))
        length=PHYSICAL_SCALE['length_unit_m'];gm_unit=PHYSICAL_SCALE['nominal_GM_unit_m3_s2']
        origin=vector(body.get('position'));sources=[]
        for b in bodies:
            position=vector(b.get('position'));mass=scalar(b.get('mass'))
            if not 0<mass<=100 or math.hypot(*position)*length>1e17:raise ValueError('Source mass/position outside adopted editor range')
            delta=tuple((position[k]-origin[k])*length for k in range(3))
            sources.append(Source(b['id'],b['reference_id'],scalar(mass*gm_unit),product(transpose,delta)))
        self.sources=tuple(sources);self._reading=reading;self._magnetic=Model(reading);self.magnetic_evaluations=0
        self.seed_m=vector(reading[point_key])
        self._descriptor={'schema':1,'kind':'static_body_snapshot_test_particle','frame':'body_orientation_frozen_as_inertial_axes',
            'reading':reading,'scene_phase':{k:phase[k] for k in ['system_id','edit_token','revision','time','fixture_sha256']},
            'scene_phase_sha256':digest(phase),'sources':[{'id':s.id,'reference_id':s.reference_id,'GM_m3_s2':s.GM_m3_s2,
                'position_model_m':list(s.position_model_m),'exclusion_radius_m':s.exclusion_radius_m} for s in self.sources],
            'origin_inertial_m':list(vector(reading[center_key])),'model_to_J2000':[list(row) for row in self._rotation],
            'electric_field_V_m':[0.,0.,0.],'electric_policy':'Explicit E=0 prescribed scenario; no inferred corotation/induction/solar wind.',
            'clock':'Independent particle seconds; all source positions/orientations/model epoch fixed.',
            'source_feedback':False,'potential_policy':'Static monopoles, no origin-acceleration subtraction or extra gravity terms.'}
        self.configuration_sha256=digest(self._descriptor)
        if not self.segment_in_domain(self.seed_m,self.seed_m):raise ValueError('Seed outside strict adopted particle domain')

    @property
    def descriptor(self):return copy.deepcopy(self._descriptor)

    def _magnetic_segment(self,start,end):
        if self._magnetic.name=='JRM33':return shell_segment(start,end,self._magnetic.radius,20*self._magnetic.radius)
        import geomagnetism as igrf
        # Outside an ellipsoid, geodetic height is its normal distance. Distance
        # to a convex set is convex: endpoint upper heights bound the segment.
        if not outside_ellipsoid(start,end,[igrf.WGS_A,igrf.WGS_A,igrf.WGS_B]):return False
        return all(0<=geodetic(p)[2]<=1e6 for p in [start,end])

    def segment_in_domain(self,start,end):
        start,end=vector(start),vector(end)
        if not self._magnetic_segment(start,end):return False
        for source in self.sources:
            a=[start[k]-source.position_model_m[k] for k in range(3)]
            b=[end[k]-source.position_model_m[k] for k in range(3)]
            if not outside_ellipsoid(a,b,[source.exclusion_radius_m]*3):return False
        return True

    def evaluate(self,position):
        position=vector(position)
        if not self.segment_in_domain(position,position):raise ValueError('Point outside adopted domain; field not queried')
        field=self._magnetic.field(list(position));self.magnetic_evaluations+=1
        acceleration=[];potentials=[]
        for source in self.sources:
            delta=[position[k]-source.position_model_m[k] for k in range(3)];radius=math.hypot(*delta)
            acceleration.append([-source.GM_m3_s2*v/radius**3 for v in delta]);potentials.append(-source.GM_m3_s2/radius)
        g=[math.fsum(a[k] for a in acceleration) for k in range(3)];potential=math.fsum(potentials)
        if not all(math.isfinite(v) for v in [*field,*g,potential]):raise ValueError('Unrepresentable field/potential')
        return {'valid':True,'electric_field_V_m':[0.,0.,0.],'magnetic_field_T':list(field),
            'gravity_m_s2':g,'gravity_potential_J_kg':potential,'configuration_sha256':self.configuration_sha256}

    def potential_difference(self,start,end):
        """Phi(end)-Phi(start), avoiding subtraction of large common offsets."""
        start,end=vector(start),vector(end)
        if not self.segment_in_domain(start,start) or not self.segment_in_domain(end,end):
            raise ValueError('Potential endpoints outside adopted domain')
        displacement=[end[k]-start[k] for k in range(3)]
        length2=math.fsum(v*v for v in displacement);terms=[]
        for source in self.sources:
            initial=[start[k]-source.position_model_m[k] for k in range(3)]
            final=[end[k]-source.position_model_m[k] for k in range(3)]
            r0,r1=math.hypot(*initial),math.hypot(*final)
            difference_squared=math.fsum([2*math.fsum(initial[k]*displacement[k] for k in range(3)),length2])
            terms.append(source.GM_m3_s2*difference_squared/(r0*r1*(r0+r1)))
        result=math.fsum(terms)
        if not math.isfinite(result):raise ValueError('Unrepresentable potential difference')
        return result
