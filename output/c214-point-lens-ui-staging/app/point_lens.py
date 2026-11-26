"""Static point-mass thin lens in a declared Euclidean observer/lens/source geometry."""
from decimal import Decimal, localcontext
from pathlib import Path
import copy
import hashlib
import json
import math

C_M_S=299792458
PRECISION=80
MAX_COORDINATE_M=1e25
MIN_IMPACT_RS=1000
MAX_ANGLE_RAD=.01
MIN_FINITE_U=1e-6
MAX_FINITE_U=1e4
SOURCE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SOURCES=[
    'https://arxiv.org/abs/astro-ph/9912508',
    'https://arxiv.org/abs/astro-ph/9812021',
]
DEFAULT=dict(GM_m3_s2=1.3271244e20,observer_m=[0.,0.,0.],lens_m=[0.,0.,1e20],source_m=[1e12,0.,2e20])


def require(condition,message):
    if not condition:raise ValueError(message)


def number(value,name):
    require(type(value) in (int,float),name+' precisa ser um número real finito.')
    try:result=float(value)
    except (OverflowError,ValueError):raise ValueError(name+' excede a representação numérica.')
    require(math.isfinite(result),name+' excede a representação numérica.')
    return 0. if result==0 else result


def configuration(value=None):
    value=copy.deepcopy(DEFAULT if value is None else value)
    require(type(value) is dict and set(value)==set(DEFAULT),'Informe somente GM e as três posições cartesianas em metros.')
    result=dict(GM_m3_s2=number(value['GM_m3_s2'],'GM'))
    require(result['GM_m3_s2']>0,'GM precisa ser positivo; a referência material permanece definida.')
    for name in ['observer_m','lens_m','source_m']:
        vector=value[name]
        require(type(vector) in (list,tuple) and len(vector)==3,name+' precisa ter três coordenadas.')
        result[name]=[number(x,name) for x in vector]
        require(all(abs(x)<=MAX_COORDINATE_M for x in result[name]),'Coordenada fora do orçamento de1e25m.')
    return result


def generation():
    return dict(id='cosmos2:point-mass-thin-lens',version='0.1.0',code_sha256=SOURCE_SHA256,
      decimal_precision=PRECISION,c_m_s=C_M_S,c_definition='Exact SI speed of light in vacuum; GM supplied in SI.')


def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def mul(s,a):return tuple(s*x for x in a)
def dot(a,b):return sum((x*y for x,y in zip(a,b)),Decimal(0))
def norm(a):return dot(a,a).sqrt()
def unit(a):
    length=norm(a);require(length>0,'Direção geométrica indefinida.')
    return mul(1/length,a)
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def json_values(value):
    if isinstance(value,Decimal):
        result=float(value)
        require(math.isfinite(result) and not(result==0 and value!=0),'Uma grandeza excede a precisão finita de saída; revise as escalas.')
        return 0. if result==0 else result
    if isinstance(value,dict):return {k:json_values(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [json_values(v) for v in value]
    return value


def _experiment(cfg,bending):
    D=lambda v:Decimal.from_float(v)
    gm=D(cfg['GM_m3_s2']);rs=2*gm/Decimal(C_M_S)**2
    observer,lens,source=[tuple(D(x) for x in cfg[name]) for name in ['observer_m','lens_m','source_m']]
    lv,sv=sub(lens,observer),sub(source,observer)
    dl=norm(lv);require(dl>=1,'Separe observador e lente por pelo menos1m.')
    n=mul(1/dl,lv);ds=dot(sv,n);dls=ds-dl
    require(dls>=1,'A fonte deve estar atrás do plano da lente, com separação de pelo menos1m.')
    seed=tuple(Decimal(int(i==min(range(3),key=lambda j:abs(n[j])))) for i in range(3))
    ex=unit(sub(seed,mul(dot(seed,n),n)));ey=cross(n,ex)
    aligned=all(x==0 for x in cross(lv,sv))
    beta=(Decimal(0),Decimal(0)) if aligned else (dot(sv,ex)/ds,dot(sv,ey)/ds)
    beta_size=norm(beta)
    require(beta_size<=Decimal(str(MAX_ANGLE_RAD)),'A posição da fonte excede o limite paraxial de0.01rad.')
    te2=(2*rs/dl)*(dls/ds);te=te2.sqrt();u=beta_size/te
    if not aligned:
        require(Decimal(str(MIN_FINITE_U))<=u<=Decimal(str(MAX_FINITE_U)),
          'O desalinhamento precisa estar entre1e-6 e1e4 raios de Einstein. Perto da caústica, afaste a fonte ou use alinhamento exato para consultar o limite do anel.')
    limits=dict(minimum_impact_rs=MIN_IMPACT_RS,maximum_paraxial_angle_rad=MAX_ANGLE_RAD,
      minimum_finite_u=MIN_FINITE_U,maximum_finite_u=MAX_FINITE_U)
    def domain(theta):
        impact=dl*abs(theta)
        require(abs(theta)<=Decimal(str(MAX_ANGLE_RAD)),'Uma imagem excede o limite paraxial de0.01rad.')
        require(impact/rs>=MIN_IMPACT_RS,'Uma imagem passa a menos de1000rs; a aproximação fraca não admite esse caso.')
        return impact
    def point(theta_sky):return add(lens,mul(dl,add(mul(theta_sky[0],ex),mul(theta_sky[1],ey))))
    def direction(theta_sky):return unit(add(n,add(mul(theta_sky[0],ex),mul(theta_sky[1],ey))))
    if aligned:
        impact=domain(te)
        reference=dict(status='aligned_point_source_caustic',images=[],magnification_total=None,
          magnification_total_minus_unity=None,magnification_status='unbounded_geometric_point_source_limit',
          ring=dict(paraxial_angular_radius_rad=te,lens_plane_radius_m=impact,center_world_m=lens,
                    physical_deflection_rad=2*rs/impact),image_separation_rad=None)
    else:
        axis=mul(1/beta_size,beta)
        theta_plus=(beta_size+(beta_size**2+4*te2).sqrt())/2
        theta_minus=-te2/theta_plus
        images=[]
        for label,theta,parity in [('outer',theta_plus,1),('inner',theta_minus,-1)]:
            impact=domain(theta);theta_sky=mul(theta,axis);q=te2/theta**2
            radial,tangential=1+q,1-q;det=radial*tangential;mu=1/det
            require((mu>0)==(parity==1),'A paridade da imagem difere do Jacobiano.')
            jacobian=[[(1-q if i==j else 0)+2*q*axis[i]*axis[j] for j in range(2)] for i in range(2)]
            deflection_sky=mul((2*rs/impact)*(1 if theta>0 else -1),axis)
            residual=sub(beta,sub(theta_sky,mul(dls/ds,deflection_sky)))
            ray_point=point(theta_sky)
            images.append(dict(label=label,parity=parity,theta_signed_rad=theta,sky_paraxial_rad=theta_sky,
              observer_direction_unit=direction(theta_sky),impact_m=impact,impact_rs=impact/rs,
              physical_deflection_rad=2*rs/impact,lens_equation_deflection_sky_rad=deflection_sky,
              propagating_turn_sky_rad=mul(Decimal(-1),deflection_sky),
              reduced_deflection_sky_rad=mul(dls/ds,deflection_sky),
              magnification_signed=mu,magnification_abs=abs(mu),jacobian=jacobian,
              jacobian_eigenvalues=dict(radial=radial,tangential=tangential),jacobian_determinant=det,
              lens_equation_residual_thetaE=norm(residual)/te,
              lens_plane_world_m=ray_point,
              ray_vertices_world_m=[observer,ray_point,source]))
        total=sum((im['magnification_abs'] for im in images),Decimal(0))
        reference=dict(status='two_images',images=images,magnification_total=total,
          magnification_total_minus_unity=total-1,magnification_status='finite_point_source_geometric_optics',ring=None,
          image_separation_rad=theta_plus-theta_minus,
          root_product_normalized=theta_plus*theta_minus/te2,
          signed_magnification_sum=sum((im['magnification_signed'] for im in images),Decimal(0)),
          outer_magnification_minus_unity=images[0]['magnification_signed']-1)
    if bending:actual=copy.deepcopy(reference)
    else:
        direct=dict(label='direct_intervention',parity=1,theta_signed_rad=beta_size,sky_paraxial_rad=beta,
          observer_direction_unit=unit(sv),magnification_abs=Decimal(1),magnification_signed=Decimal(1),
          physical_deflection_rad=Decimal(0),lens_plane_world_m=point(beta),
          ray_vertices_world_m=[observer,point(beta),source])
        actual=dict(status='unlensed_intervention',images=[direct],ring=None,magnification_total=Decimal(1),
          magnification_total_minus_unity=Decimal(0),magnification_status='unit_direct_intervention',image_separation_rad=None)
    result=json_values(dict(schema=1,model='point_mass_thin_lens_euclidean',generation=generation(),configuration=cfg,
      acting=dict(ray_bending=bending),geometry=dict(Dl_m=dl,Ds_m=ds,Dls_m=dls,schwarzschild_radius_m=rs,
        optical_axis_unit=n,sky_x_unit=ex,sky_y_unit=ey,source_paraxial_beta_rad=beta,
        source_paraxial_beta_norm_rad=beta_size,einstein_angle_rad=te,einstein_radius_m=dl*te,u=u,
        exact_stored_coordinate_alignment=aligned),reference=reference,actual=actual,limits=limits,sources=SOURCES))
    result['geometry']['source_geometric_angle_rad']=math.atan(result['geometry']['source_paraxial_beta_norm_rad'])
    result['input_resolution']=dict(maximum_coordinate_ulp_m=max(math.ulp(x) for name in ['observer_m','lens_m','source_m'] for x in cfg[name]),
      meaning='Binary coordinate spacing, not observational uncertainty. Decimal arithmetic does not recover information absent from input.')
    result['scope']=dict(frame='Static Euclidean Cartesian positions; no cosmological distance/redshift model or Atlas epoch.',
      rays='Thin-lens broken-line construction, not integrated null geodesics. Angles in the lens equation are paraxial slopes.',
      vector_sign='Lens-equation alpha points along the lens-plane impact vector. The propagating S-to-O photon turns toward the lens, with opposite transverse sign.',
      magnification='Geometric point source, transparent point lens; no finite-source, diffraction, absorption or occultation.',
      intervention='Turning bending off keeps material geometry and the full reference; a direct image is a counterfactual.',
      accuracy='Declared approximation and numerical domain; no claim of observed-body fit or propagated observational errors.')
    # A final strict serialization also catches non-Decimal accidental nonfinite values.
    json.dumps(result,allow_nan=False)
    return result


def experiment(value=None,*,bending=True):
    require(type(bending) is bool,'O controle de deflexão precisa ser booleano.')
    cfg=configuration(value)
    with localcontext() as context:
        context.prec=PRECISION
        return _experiment(cfg,bending)
