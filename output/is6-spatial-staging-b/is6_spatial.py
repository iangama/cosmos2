"""Source-relative spatial Schwarzschild slice, static clocks and Flamm embedding.

Pure model; no scene, orbital backreaction, optical metric or combined sources.
"""
from pathlib import Path
import hashlib
import math
import platform

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
C_M_S=299792458
SOURCE_KEYS={'GM_m3_s2','material_radius_m'}
IDENTITY=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
FILES=[Path(__file__),ROOT/'IS-6-MALHA-ESPACIAL-RELOGIOS-C.md',ROOT/'IS-6-MALHA-ESPACIAL-CONTRATO-PREVIO.md',
       ROOT/'IS-6-MALHA-ESPACIAL-PREPARACAO-20261101.md',
       ROOT/'output/is6-spatial-research-20261101/acquisition.json',
       ROOT/'output/is6-spatial-research-20261101/oist-gr-lecture8.pdf']
IMPORTED={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}


def generation():
    if any(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=v for n,v in IMPORTED.items()):
        raise ValueError('Restart after spatial-model source changes')
    return dict(id='cosmos2:is6-static-Schwarzschild-spatial-slice',schema=1,version='0.1.1',
                source_sha256=dict(IMPORTED),c_m_s=C_M_S,python=platform.python_version(),
                coordinates='ct_m,r_areal_m,theta_rad,phi_rad',slice='constant_t_equatorial',
                scope='Single isolated spherical exterior reference; no orbital dynamics or optical embedding.')


def number(value):
    if type(value) not in (int,float):raise ValueError('Finite numeric SI value required')
    try:value=float(value)
    except (ValueError,OverflowError):raise ValueError('Finite numeric SI value required') from None
    if not math.isfinite(value):raise ValueError('Finite numeric SI value required')
    return value


def source(value):
    if not isinstance(value,dict) or set(value)!=SOURCE_KEYS:raise ValueError('Exact spherical-source fields required')
    gm=number(value['GM_m3_s2']);material=number(value['material_radius_m'])
    if not (gm==0 or 1<=gm<=1e26) or not 0<=material<=1e20:raise ValueError('Spherical source outside adopted domain')
    return dict(GM_m3_s2=gm,material_radius_m=material)


def radius(value,configuration):
    r=number(value);rs=2*configuration['GM_m3_s2']/(C_M_S*C_M_S)
    if not 1<=r<=1e20 or r<configuration['material_radius_m'] or r<1.01*rs:
        raise ValueError('Point outside adopted spherical exterior')
    return r,rs


def sample(configuration,r_areal_m):
    p=source(configuration);r,rs=radius(r_areal_m,p);u=rs/r;f=1-u;s=math.sqrt(f)
    return dict(radius_areal_m=r,schwarzschild_radius_m=rs,compactness=u,
                metric_ct_ct=-f,metric_rr=1/f,metric_theta_theta_m2=r*r,metric_phi_phi_m2=r*r,
                static_clock_ratio=s,static_clock_deficit=u/(1+s),
                radial_stretch_excess=u/(s*(1+s)),circumference_m=2*math.pi*r,
                embedding_gradient=math.sqrt(rs/(r-rs)),Kretschmann_m_inverse4=12*rs*rs/(r**6))


def compare_clocks(configuration,emitter_radius_m,receiver_radius_m):
    p=source(configuration);r1,rs=radius(emitter_radius_m,p);r2,_=radius(receiver_radius_m,p)
    relative_difference=rs*(r1-r2)/(r1*r2*(1-rs/r2))
    log_ratio=.5*math.log1p(relative_difference)
    return dict(emitter_radius_m=r1,receiver_radius_m=r2,
                received_over_emitted_frequency=math.exp(log_ratio),
                fractional_frequency_shift=math.expm1(log_ratio),
                observers='Both static and supported; coordinate time normalized at infinity.')


def radial_distance(configuration,inner_radius_m,outer_radius_m):
    p=source(configuration);a,rs=radius(inner_radius_m,p);b,_=radius(outer_radius_m,p)
    if b<a:raise ValueError('Radial interval must be ordered')
    dr=b-a
    if rs==0 or dr==0:excess=0.
    else:
        ua,ub=rs/a,rs/b;sa,sb=math.sqrt(1-ua),math.sqrt(1-ub)
        # Rationalize the primitive's differences; the small excess is never
        # recovered by subtracting two nearly equal macroscopic lengths.
        root_excess=dr*(rs/2)*(ua/(1+sa)**2+ub/(1+sb)**2)/(a*sa+b*sb)
        ra,rb=math.sqrt(a),math.sqrt(b);qa,qb=math.sqrt(a-rs),math.sqrt(b-rs)
        log_increment=math.log1p(dr*(1/(rb+ra)+1/(qb+qa))/(ra+qa))
        excess=root_excess+rs*log_increment
    return dict(inner_radius_m=a,outer_radius_m=b,coordinate_interval_m=dr,
                proper_length_m=dr+excess,proper_length_excess_m=excess)


def orientation(value):
    if not isinstance(value,list) or len(value)!=3 or any(not isinstance(row,list) or len(row)!=3 for row in value):
        raise ValueError('Three explicit orientation vectors required')
    basis=[[number(x) for x in row] for row in value]
    for i in range(3):
        for j in range(3):
            if abs(math.fsum(basis[i][k]*basis[j][k] for k in range(3))-(1 if i==j else 0))>1e-13:
                raise ValueError('Orientation must be orthonormal without normalization')
    u,v,n=basis
    cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    if abs(math.fsum(x*y for x,y in zip(cross,n))-1)>1e-13:raise ValueError('Right-handed orientation required')
    return basis


def transform(vector,basis):
    return [math.fsum(vector[j]*basis[j][i] for j in range(3)) for i in range(3)]


def mesh(configuration,options):
    p=source(configuration)
    keys={'inner_radius_m','outer_radius_m','radial_count','azimuth_sectors','orientation','center_m','vertical_amplification'}
    if not isinstance(options,dict) or set(options)!=keys:raise ValueError('Exact spatial mesh fields required')
    a,rs=radius(options['inner_radius_m'],p);b,_=radius(options['outer_radius_m'],p)
    if not b>a:raise ValueError('Mesh outer radius must exceed its inner radius')
    nr,na=options['radial_count'],options['azimuth_sectors']
    if type(nr) is not int or nr not in [33,65,129,257] or type(na) is not int or na!=96:
        raise ValueError('Spatial mesh resolution outside declared budget')
    basis=orientation(options['orientation']);center=options['center_m'];amp=number(options['vertical_amplification'])
    if not isinstance(center,list) or len(center)!=3:raise ValueError('Explicit source center required')
    center=[number(x) for x in center]
    if any(abs(x)>1e20 for x in center) or not 0<=amp<=1000:raise ValueError('Display transform outside adopted domain')
    gen=generation();radii=[];heights=[];physical=[];display=[]
    log_ratio=math.log(b/a)
    for i in range(nr):
        r=a if i==0 else b if i==nr-1 else a*math.exp(log_ratio*i/(nr-1))
        z=0. if rs==0 else -2*math.sqrt(rs)*(b-r)/(math.sqrt(b-rs)+math.sqrt(r-rs))
        radii.append(r);heights.append(z)
        for j in range(na+1):
            phi=2*math.pi*j/na;x,y=(r,0.) if j==na else (r*math.cos(phi),r*math.sin(phi))
            physical.append(transform([x,y,z],basis));display.append(transform([x,y,amp*z],basis))
    if generation()!=gen:raise ValueError('Spatial source changed during mesh construction')
    return dict(kind='is6_static_spatial_slice',scientific_generation=gen,source=p,
                meridian_radius_m=radii,meridian_embedding_height_m=heights,
                physical_vertices_relative_m=physical,display_vertices_relative_m=display,
                radial_count=nr,azimuth_sectors=na,vertices_per_ring=na+1,
                orientation=basis,center_m=center,vertical_amplification=amp,
                probe_basis='Original intrinsic metric; center and graphical height amplification do not alter readings.')
