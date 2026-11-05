"""Own Schmidt recurrence for the pinned JRM33 internal component; staging only."""
from pathlib import Path
import hashlib
import json
import math

DATA_SHA='71ce7abeaa4d35f261a14de4816699496a8f7ed86ee8c83f043ceb8f46e024b8'
DATA_PATH=Path(__file__).with_name('jrm33-coefficients.json')
raw=DATA_PATH.read_bytes()
if hashlib.sha256(raw).hexdigest()!=DATA_SHA:raise ValueError('Coeficientes JRM33 diferentes da fonte fixada.')
DATA=json.loads(raw)
R=71492000.
COEFFICIENTS={(v['kind'],v['n'],v['m']):v['value_nT'] for v in DATA['internal_coefficients']}
SCHMIDT={(n,m):math.sqrt((2 if m else 1)*math.factorial(n-m)/math.factorial(n+m)) for n in range(31) for m in range(n+1)}


def validate(radius,theta,phi,degree):
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in [radius,theta,phi]):
        raise ValueError('Coordenadas devem ser números finitos.')
    if type(degree) is not int or degree not in (1,13,18):raise ValueError('Grau disponível:1,13 ou18.')
    if not R*(1-2e-15)<=radius<=20*R*(1+2e-15):raise ValueError('Raio fora de1..20Rj neste instrumento.')
    if not 0<=theta<=math.pi or not 0<=phi<=2*math.pi:raise ValueError('Ângulos fora do domínio adotado.')


def spherical(radius_m,colatitude_rad,east_longitude_rad,degree=13):
    validate(radius_m,colatitude_rad,east_longitude_rad,degree)
    p,d=legendre(colatitude_rad,degree)
    s,c=math.sin(colatitude_rad),math.cos(colatitude_rad)
    radial=[];polar=[];azimuthal=[];potential=[]
    for n in range(1,degree+1):
        scale=(R/radius_m)**(n+2)
        for m in range(n+1):
            g=COEFFICIENTS['g',n,m];h=COEFFICIENTS.get(('h',n,m),0.)
            cm,sm=math.cos(m*east_longitude_rad),math.sin(m*east_longitude_rad)
            value=g*cm+h*sm
            radial.append((n+1)*scale*value*p[n][m])
            polar.append(-scale*value*d[n][m])
            potential.append(R*(R/radius_m)**(n+1)*value*p[n][m])
            if m:
                quotient=p[n][m]/s if abs(s)>1e-10 else d[n][m]/c
                azimuthal.append(scale*m*(g*sm-h*cm)*quotient)
    return [math.fsum(radial)*1e-9,math.fsum(polar)*1e-9,math.fsum(azimuthal)*1e-9],math.fsum(potential)*1e-9


def sample(position_m,degree=13):
    if not isinstance(position_m,(list,tuple)) or len(position_m)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in position_m):
        raise ValueError('Informe três coordenadas cartesianas SI finitas.')
    x,y,z=position_m;radius=math.hypot(x,y,z)
    theta=math.atan2(math.hypot(x,y),z);phi=math.atan2(y,x)%(2*math.pi)
    field,potential=spherical(radius,theta,phi,degree)
    br,bt,bp=field;s,c=math.sin(theta),math.cos(theta);cl,sl=math.cos(phi),math.sin(phi)
    cart=[(br*s+bt*c)*cl-bp*sl,(br*s+bt*c)*sl+bp*cl,br*c-bt*s]
    return {'schema':1,'model':'JRM33_internal_staging','degree':degree,
        'frame':'right_handed_System_III_1965','position_m':list(position_m),'radius_m':radius,
        'field_SystemIII_T':cart,'field_spherical_T':field,'field_norm_T':math.hypot(*cart),
        'scalar_potential_T_m':potential,'reference_radius_m':R,
        'coefficient_epoch_decimal_year':2019.,'secular_variation_applied':False,
        'external_current_component_included':False,'coefficients_sha256':DATA_SHA,
        'uncertainty':None,'scope':'Static prescribed internal component in model coordinates; no scene orientation, dynamics or external currents.'}


# The project-owned Legendre recurrence is appended below from geomagnetism.py.


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
