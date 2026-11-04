"""Prescribed SI split-polarity Parker field; no plasma dynamics or HCS solver."""
import copy
import math
from is4_values import scalar,vector
from is4_domains import shell_segment

AU_M=149597870700.
INNER_M=.1*AU_M
OUTER_M=10.*AU_M
MIN_LATITUDE_SIN=math.sin(math.radians(5.))
DEFAULT={'wind_speed_m_s':400000.,'radial_field_at_AU_T':3e-9,
         'rotation_rate_rad_s':2*math.pi/(25.38*86400.),'polarity':1}

def parameters(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULT):raise ValueError('Exact Parker parameter schema required')
    u,b,w=(scalar(value[k]) for k in ['wind_speed_m_s','radial_field_at_AU_T','rotation_rate_rad_s'])
    if not 1e4<=u<=2e6 or not 1e-12<=b<=1e-6 or not 0<=w<=1e-4:raise ValueError('Parker parameters outside declared SI limits')
    p=value['polarity']
    if type(p) is not int or p not in [-1,1]:raise ValueError('Explicit polarity +1 or -1 required')
    return dict(wind_speed_m_s=u,radial_field_at_AU_T=b,rotation_rate_rad_s=w,polarity=p)

class Parker:
    def __init__(self,configuration=None):
        self._parameters=parameters(DEFAULT if configuration is None else configuration)
        self.evaluations=0

    @property
    def configuration(self):return copy.deepcopy(self._parameters)

    @property
    def descriptor(self):
        return {'schema':1,'kind':'prescribed_stationary_split_polarity_Parker_SI',
            'parameters':self.configuration,'reference_radius_m':AU_M,
            'domain':{'inner_radius_m':INNER_M,'outer_radius_m':OUTER_M,'excluded_equatorial_latitude_deg':5.},
            'units':{'position':'m','B':'T','E':'V/m','potential':'V','u':'m/s'},
            'electric_policy':'SI E=-u cross B; conservative within each retained sector; no Gaussian1/c factor.',
            'parameter_origin':'Explicit didactic parameters; not fitted or current observations.',
            'reference':'Dalla et al.2013 doi:10.1002/jgra.50589, equations1-6 and split polarities section2.2.',
            'scope':'Prescribed kinematic wind and electromagnetic field; no MHD, plasma reaction, scattering, CME, HCS or planetary magnetosphere.'}

    def segment_in_domain(self,start,end):
        a,b=vector(start),vector(end)
        if not shell_segment(a,b,INNER_M,OUTER_M):return False
        # A retained hemisphere is a convex second-order cone. Endpoints in
        # the SAME cone guarantee the full segment avoids the excluded band.
        if a[2]*b[2]<=0:return False
        return all(abs(x[2])>=MIN_LATITUDE_SIN*math.hypot(*x) for x in [a,b])

    def evaluate(self,position):
        x,y,z=vector(position)
        if not self.segment_in_domain([x,y,z],[x,y,z]):raise ValueError('Point outside Parker domain; field not queried')
        cfg=self._parameters;r=math.hypot(x,y,z);r2=r*r;r3=r2*r
        a=cfg['radial_field_at_AU_T']*AU_M**2
        p=cfg['polarity']*(1 if z>0 else -1);w=cfg['rotation_rate_rad_s'];u=cfg['wind_speed_m_s']
        B=[p*a*(x/r3+w*y/(u*r2)),p*a*(y/r3-w*x/(u*r2)),p*a*z/r3]
        E=[-p*w*a*z*x/r3,-p*w*a*z*y/r3,p*w*a*(x*x+y*y)/r3]
        velocity=[u*x/r,u*y/r,u*z/r];potential=-cfg['polarity']*w*a*abs(z)/r
        if not all(math.isfinite(v) for v in [*B,*E,*velocity,potential]):raise ValueError('Unrepresentable Parker field')
        self.evaluations+=1
        return dict(valid=True,magnetic_field_T=B,electric_field_V_m=E,wind_velocity_m_s=velocity,electric_potential_V=potential)

    def electric_potential_difference(self,start,end):
        a,b=vector(start),vector(end)
        if not self.segment_in_domain(a,a) or not self.segment_in_domain(b,b):raise ValueError('Potential endpoint outside Parker domain')
        d=[b[k]-a[k] for k in range(3)];r0,r1=math.hypot(*a),math.hypot(*b)
        dr=math.fsum([2*math.fsum(a[k]*d[k] for k in range(3)),math.fsum(v*v for v in d)])/(r0+r1)
        dz=(1 if a[2]>0 else -1)*d[2] if a[2]*b[2]>0 else abs(b[2])-abs(a[2])
        difference=math.fsum([dz/r1,-abs(a[2])*dr/(r0*r1)])
        c=self._parameters
        value=-c['polarity']*c['rotation_rate_rad_s']*c['radial_field_at_AU_T']*AU_M**2*difference
        if not math.isfinite(value):raise ValueError('Unrepresentable electric potential difference')
        return value
