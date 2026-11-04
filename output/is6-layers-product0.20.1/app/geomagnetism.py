"""Own IGRF14 harmonic synthesis; fixed IAGA coefficients, SI/NED/ECEF outputs.

Mathematical implementation is separate from the upstream BGS Fortran used for
local reference checks. Main internal field only, never a storm/magnetosphere.
"""
from pathlib import Path
from functools import lru_cache
import hashlib
import math

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
COEFFICIENT_PATH=ROOT/'data/science/igrf14coeffs.txt'
EXPECTED_SHA='8f8d88403028fc4ee92c4f38d97b46e0a87e2cfc496045b43c9e26c1d6b0903c'
raw=COEFFICIENT_PATH.read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA:
    raise ValueError('Os coeficientes IGRF14 diferem da aquisição fixada.')
rows=raw.decode('ascii').splitlines()
EPOCHS=tuple(float(x) for x in rows[3].split()[3:-1])
if EPOCHS!=tuple(range(1900,2030,5)):
    raise ValueError('Épocas IGRF14 inesperadas.')
COEFFICIENTS={}
for row in rows[4:]:
    items=row.split()
    if not items:continue
    kind,n,m=items[0],int(items[1]),int(items[2])
    values=tuple(float(x) for x in items[3:])
    if kind not in ('g','h') or not 1<=n<=13 or not 0<=m<=n or len(values)!=27:
        raise ValueError('Linha de coeficientes IGRF14 inválida.')
    if (kind,n,m) in COEFFICIENTS:raise ValueError('Coeficiente IGRF14 duplicado.')
    COEFFICIENTS[kind,n,m]=values
if len(COEFFICIENTS)!=195:raise ValueError('Contagem IGRF14 inválida.')
REFERENCE_RADIUS_M=6371200.
WGS_A=6378137.
WGS_F=1/298.257223563
WGS_B=WGS_A*(1-WGS_F)
SCHMIDT={(n,m):math.sqrt((2 if m else 1)*math.factorial(n-m)/math.factorial(n+m)) for n in range(14) for m in range(n+1)}
SOURCES=['https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field',
         'https://www.ngdc.noaa.gov/IAGA/vmod/coeffs/igrf14coeffs.txt',
         'https://geomag.bgs.ac.uk/research/modelling/IGRF.html',
         'https://earth-info.nga.mil/?action=wgs84&dir=wgs84']


@lru_cache(maxsize=64)
def coefficients(year,secular=False):
    if not math.isfinite(year) or not 1900<=year<=2030:
        raise ValueError('IGRF14: informe ano decimal entre1900 e2030.')
    if year>=2025:
        return {key:values[-1] if secular else values[-2]+(year-2025)*values[-1] for key,values in COEFFICIENTS.items()}
    index=min(24,int((year-1900)//5));fraction=(year-EPOCHS[index])/5
    return {key:(values[index+1]-values[index])/5 if secular else values[index]*(1-fraction)+values[index+1]*fraction for key,values in COEFFICIENTS.items()}


def legendre(theta,degree):
    """Schmidt semi-normalized associated Legendre and theta derivatives.

    Ordinary recurrence without Condon-Shortley phase; derivative propagated
    directly, so evaluation at a geographic pole never divides by sin(theta).
    """
    s,c=math.sin(theta),math.cos(theta)
    p=[[0.]*(degree+1) for _ in range(degree+1)]
    d=[[0.]*(degree+1) for _ in range(degree+1)]
    p[0][0]=1.
    for m in range(degree+1):
        if m:
            factor=2*m-1;p[m][m]=factor*s*p[m-1][m-1]
            d[m][m]=factor*(c*p[m-1][m-1]+s*d[m-1][m-1])
        if m<degree:
            factor=2*m+1;p[m+1][m]=factor*c*p[m][m]
            d[m+1][m]=factor*(-s*p[m][m]+c*d[m][m])
        for n in range(m+2,degree+1):
            p[n][m]=((2*n-1)*c*p[n-1][m]-(n+m-1)*p[n-2][m])/(n-m)
            d[n][m]=((2*n-1)*(-s*p[n-1][m]+c*d[n-1][m])-(n+m-1)*d[n-2][m])/(n-m)
    for n in range(degree+1):
        for m in range(n+1):p[n][m]*=SCHMIDT[n,m];d[n][m]*=SCHMIDT[n,m]
    return p,d


def spherical(year,radius_m,colatitude_rad,longitude_rad,degree=13,secular=False):
    if radius_m<=0 or not math.isfinite(radius_m):raise ValueError('Raio geocêntrico inválido.')
    if degree not in (1,13):raise ValueError('Truncamento disponível:grau1 ou13.')
    coeff=coefficients(year,secular);p,d=legendre(colatitude_rad,degree)
    s,c=math.sin(colatitude_rad),math.cos(colatitude_rad)
    br=bt=bp=0.
    for n in range(1,degree+1):
        scale=(REFERENCE_RADIUS_M/radius_m)**(n+2)
        for m in range(n+1):
            g,h=coeff['g',n,m],coeff.get(('h',n,m),0.)
            cm,sm=math.cos(m*longitude_rad),math.sin(m*longitude_rad)
            value=g*cm+h*sm
            br+=(n+1)*scale*value*p[n][m]
            bt-=scale*value*d[n][m]
            if m:
                quotient=p[n][m]/s if abs(s)>1e-10 else d[n][m]/c
                bp+=scale*m*(g*sm-h*cm)*quotient
    return br,bt,bp  # nT (or nT/year if secular)


def geodetic_position(latitude,longitude,altitude_m):
    if not all(math.isfinite(x) for x in (latitude,longitude,altitude_m)) or not -90<=latitude<=90 or not -180<=longitude<=180 or not 0<=altitude_m<=1e6:
        raise ValueError('Informe latitude±90°, longitude±180° e altitudeWGS84entre0 e1000km.')
    phi,lam=math.radians(latitude),math.radians(longitude)
    e2=WGS_F*(2-WGS_F);n=WGS_A/math.sqrt(1-e2*math.sin(phi)**2)
    return ((n+altitude_m)*math.cos(phi)*math.cos(lam),(n+altitude_m)*math.cos(phi)*math.sin(lam),(n*(1-e2)+altitude_m)*math.sin(phi))


def field_at(year,latitude,longitude,altitude_m,degree=13,secular=False):
    x,y,z=geodetic_position(latitude,longitude,altitude_m)
    radius=math.sqrt(x*x+y*y+z*z)
    theta=math.atan2(math.hypot(x,y),z);lam=math.radians(longitude);phi=math.radians(latitude)
    br,bt,bp=spherical(year,radius,theta,lam,degree,secular)
    s,c=math.sin(theta),math.cos(theta);cl,sl=math.cos(lam),math.sin(lam)
    ecef=((br*s+bt*c)*cl-bp*sl,(br*s+bt*c)*sl+bp*cl,br*c-bt*s)
    north=(-math.sin(phi)*cl,-math.sin(phi)*sl,math.cos(phi));east=(-sl,cl,0.);down=(-math.cos(phi)*cl,-math.cos(phi)*sl,-math.sin(phi))
    ned=tuple(sum(a*b for a,b in zip(ecef,direction)) for direction in (north,east,down))
    horizontal=math.hypot(ned[0],ned[1]);total=math.sqrt(sum(v*v for v in ned))
    return {'latitude_deg':latitude,'longitude_deg':longitude,'altitude_m':altitude_m,
            'position_ecef_m':[x,y,z], 'field_ecef_T':[v*1e-9 for v in ecef],
            'field_ned_nT':list(ned),'field_ned_T':[v*1e-9 for v in ned],
            'H_nT':horizontal,'F_nT':total,'D_deg':math.degrees(math.atan2(ned[1],ned[0])) if horizontal>1e-6 else None,
            'I_deg':math.degrees(math.atan2(ned[2],horizontal)),
            'frame_note':'Norte/leste nos polos dependem do meridiano informado; vetorECEF é único.' if abs(latitude)==90 else 'Componentes geodéticas norte,leste,baixo.',
            'degree':degree,'year_decimal':year,'secular':secular}


@lru_cache(maxsize=8)
def world_grid(year,altitude_m):
    # Data remain reference values when operators/visibility are suppressed.
    return tuple({'full':field_at(year,lat,lon,altitude_m),
                  'dipole':field_at(year,lat,lon,altitude_m,degree=1)}
                 for lat in range(-90,91,10) for lon in range(-180,181,10))


def experiment(params,controls):
    from scipy.constants import elementary_charge,proton_mass
    year,latitude,longitude,altitude=params['year'],params['latitude_deg'],params['longitude_deg'],params['altitude_km']*1000
    full=field_at(year,latitude,longitude,altitude);dipole=field_at(year,latitude,longitude,altitude,degree=1)
    velocity=[params[key]*1000 for key in ('velocity_north_km_s','velocity_east_km_s','velocity_down_km_s')]
    acting=controls['electromagnetic']['acting'] and controls['electromagnetic']['effects']['magnetic_deflection']
    charge=params['charge_sign']*elementary_charge
    def with_force(point):
        b=point['field_ned_T'];u,v,w=velocity;bx,by,bz=b
        force=[charge*(v*bz-w*by)*acting,charge*(w*bx-u*bz)*acting,charge*(u*by-v*bx)*acting]
        return {**point,'magnetic_force_ned_N':force,'magnetic_power_W':sum(a*b for a,b in zip(force,velocity))}
    full,dipole=with_force(full),with_force(dipole)
    grid=[{key:with_force(value) for key,value in entry.items()} for entry in world_grid(year,altitude)]
    difference=math.sqrt(sum((a-b)**2 for a,b in zip(full['field_ned_nT'],dipole['field_ned_nT'])))
    return {'model':'IGRF14: síntese harmônica própria dos coeficientesIAGAfixados, normalizaçãoSchmidt, geodesiaWGS84. Comparação por truncamento de grau1.',
            'domain':'Campo principal interno terrestre,1900–2030, altitudeWGS84de0–1000km neste instrumento. Omite tempestades e detalhes locais da crosta. A forçaqv×B é instantânea numa partícula clássica; não integra órbita nem plasma.',
            'parameter_note':'Ano decimal explícito;2025–2030 usa previsão de variação secular. Diferença entre códigos não é precisão do campo observado. Componentes locais são norte,leste,baixo; velocidade prescrita relativa a esse referencial.',
            'influences':['electromagnetic'], 'time_s':[], 'geomagnetic':{'full':full,'dipole':dipole,'grid':grid,
                'year_decimal':year,'altitude_m':altitude,'velocity_ned_m_s':velocity,'charge_C':charge,
                'mass_kg':proton_mass,'kinetic_energy_J':.5*proton_mass*sum(v*v for v in velocity),
                'magnetic_applied':acting,'secular_ned_nT_year':field_at(year,latitude,longitude,altitude,secular=True)['field_ned_nT']},
            'reference':{'coefficient_sha256':EXPECTED_SHA,'reference_radius_m':REFERENCE_RADIUS_M,
                         'WGS84':{'semi_major_axis_m':WGS_A,'inverse_flattening':1/WGS_F},
                         'epoch':'decimal Gregorian year, explicit model epoch; not inherited from Atlas',
                         'coverage_year':[1900,2030],'altitude_domain_m':[0,1e6],
                         'full_degree':10 if year<1995 else 13,'comparison_degree':1,
                         'uncertainty':'Observational model uncertainty is not propagated locally; not zero. Global historical BGS statistics are not a point-specific error bar.',
                         'channel_dependencies':'Operador magnético instantâneo sobre velocidade local prescrita. Desligar atuação mantém coeficientes, planeta e campo; demais forças têm palcos próprios.'},
            'measurements':[{'label':'Campo principal total no ponto','value':full['F_nT']*1e-9,'unit':'T'},
                            {'label':'Declinação leste','value':full['D_deg'],'unit':'graus'},
                            {'label':'Inclinação para baixo','value':full['I_deg'],'unit':'graus'},
                            {'label':'Força magnética aplicada','value':math.sqrt(sum(v*v for v in full['magnetic_force_ned_N'])),'unit':'N'},
                            {'label':'Diferença vetorial completo−dipolo','value':difference,'unit':'nT'}],
            'sources':SOURCES}
