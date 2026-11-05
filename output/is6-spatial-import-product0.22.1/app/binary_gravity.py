"""Spatial circular restricted three-body problem; prescribed circular primaries.

Rotating units: separation a=1, n=1, GMtotal=1. A test particle exerts
no reaction on the primaries. Gates remove individual test-particle terms;
the original binary ephemeris and full reference field stay prescribed.
"""
import math
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

EXCLUSION=.02  # a numerical model boundary, not a stellar radius/collision

def source_positions(mu):
    return np.array([[-mu,0,0],[1-mu,0,0]])

def field(position,mu,gates=(True,True)):
    offsets=np.asarray(position)-source_positions(mu)
    distances=np.linalg.norm(offsets,axis=1)
    if np.any(distances==0):raise ValueError('Campo singular na fonte pontual.')
    weights=np.array([1-mu,mu])*gates
    components=-weights[:,None]*offsets/distances[:,None]**3
    tidal=sum(w*(3*np.outer(d,d)/r**5-np.eye(3)/r**3)
              for w,d,r in zip(weights,offsets,distances))
    return components.sum(axis=0),float(-np.sum(weights/distances)),tidal,components

def jacobi(y,mu,gates):
    return y[0]**2+y[1]**2-2*field(y[:3],mu,gates)[1]-float(y[3:]@y[3:])

def integrate(initial,mu,duration,gates=(True,True),tolerance=1e-11):
    if np.min(np.linalg.norm(np.asarray(initial[:3])-source_positions(mu),axis=1))<=EXCLUSION:
        raise ValueError('Posição inicial precisa ficar a mais de 0,02 separação de cada fonte.')
    weights=np.array([1-mu,mu])*gates
    sources=source_positions(mu)
    def rhs(_,y):
        d=y[:3]-sources;r=np.linalg.norm(d,axis=1)
        g=(-weights[:,None]*d/r[:,None]**3).sum(axis=0)
        return np.r_[y[3:],g+[y[0]+2*y[4],y[1]-2*y[3],0]]
    def boundary(_,y):
        return np.min(np.linalg.norm(y[:3]-sources,axis=1))-EXCLUSION
    boundary.terminal=True;boundary.direction=-1
    result=solve_ivp(rhs,(0,duration),initial,method='DOP853',dense_output=True,
                     events=boundary,rtol=tolerance,atol=tolerance*.01,max_step=.04)
    if not result.success:raise RuntimeError('O problema binário não convergiu: '+result.message)
    return result

def lagrange_points(mu):
    def f(x):return x+field([x,0,0],mu)[0][0]
    eps=1e-9
    return [{'name':'L1','position':[brentq(f,-mu+eps,1-mu-eps,xtol=1e-14),0,0]},
            {'name':'L2','position':[brentq(f,1-mu+eps,4,xtol=1e-14),0,0]},
            {'name':'L3','position':[brentq(f,-4,-mu-eps,xtol=1e-14),0,0]},
            {'name':'L4','position':[.5-mu,math.sqrt(3)/2,0]},
            {'name':'L5','position':[.5-mu,-math.sqrt(3)/2,0]}]

def rotate(points,phases):
    p=np.asarray(points);phase=np.asarray(phases)
    return np.stack((p[...,0]*np.cos(phase)-p[...,1]*np.sin(phase),
                     p[...,0]*np.sin(phase)+p[...,1]*np.cos(phase),p[...,2]),axis=-1)

def experiment(params,controls):
    from forces import AU,GM_SUN
    a=params['separation_au']*AU;gm=GM_SUN*params['primary_solar']*(1+params['mass_ratio'])
    n=math.sqrt(gm/a**3);mu=params['mass_ratio']/(1+params['mass_ratio'])
    duration=2*math.pi*params['periods']
    mode=params['initial_mode']
    if mode in ('l4','l5'):
        initial=[.5-mu,(1 if mode=='l4' else -1)*math.sqrt(3)/2,0,0,0,0]
    else:
        initial=[params[k] for k in ('x','y','z','vx','vy','vz')]
    control=controls['gravity']
    gates=tuple(control['acting'] and control['effects'][key] for key in ('primary_attraction','secondary_attraction'))
    baseline=integrate(initial,mu,duration)
    actual=baseline if all(gates) else integrate(initial,mu,duration,gates)
    end=min(baseline.t[-1],actual.t[-1])
    phases=np.linspace(0,end,241);values=actual.sol(phases).T;ref=baseline.sol(phases).T
    c_values=np.array([jacobi(y,mu,gates) for y in values])
    c_error=float(np.max(np.abs(c_values-c_values[0]))/max(1,abs(c_values[0])))
    physical_scale=n*n*a
    def reading(p):
        g,potential,tide,components=field(p,mu)
        applied=field(p,mu,gates)[0]
        return {'position':list(p),'vector':(g*physical_scale).tolist(),
                'applied_vector':(applied*physical_scale).tolist(),
                'potential_m2_s2':potential*n*n*a*a,
                'tidal_eigenvalues_s2':(np.linalg.eigvalsh(tide)*n*n).tolist(),
                'source_components_m_s2':(components*physical_scale).tolist()}
    arrows=[]
    for radius in (.7,1.4,2.2):
        for i in range(32):
            z=1-2*(i+.5)/32;angle=i*math.pi*(3-math.sqrt(5))
            p=np.array([math.sqrt(1-z*z)*math.cos(angle),math.sqrt(1-z*z)*math.sin(angle),z])*radius
            if np.min(np.linalg.norm(p-source_positions(mu),axis=1))>EXCLUSION:arrows.append(reading(p))
    probe=np.array([params[k] for k in ('probe_x','probe_y','probe_z')])
    if np.min(np.linalg.norm(probe-source_positions(mu),axis=1))<=EXCLUSION:
        raise ValueError('A sonda precisa ficar fora da fronteira de 0,02 separação.')
    probe_reading=reading(probe)
    initial_g=field(initial[:3],mu,gates)[0]*physical_scale
    return {'model':'Problema circular restrito de três corpos, espacial; DOP853 em referencial girante.',
            'domain':'Duas fontes pontuais em órbita circular prescrita; partícula sem retroação. Unidades de distância a e tempo 1/n. A velocidade inicial é relativa ao referencial girante, em n·a. Fronteira 0,02a é limite do modelo, não raio, colisão ou captura. Sem marés materiais, GR ou efemérides observadas.',
            'parameter_note':'Desligar uma fonte suprime sua atração sobre a partícula, mantendo a órbita binária de referência prescrita. L1–L5 mostrados pertencem ao modelo completo. Trocar de referencial muda apenas a vista.',
            'influences':['gravity'],'time_s':(phases/n).tolist(),'time_display':{'unit':'períodos binários','seconds_per_unit':2*math.pi/n},
            'positions':values[:,:3].tolist(),'reference_positions':ref[:,:3].tolist(),
            'inertial_positions':rotate(values[:,:3],phases).tolist(),
            'inertial_reference_positions':rotate(ref[:,:3],phases).tolist(),
            'phase_rad':phases.tolist(),'velocities_rotating':values[:,3:].tolist(),
            'position_unit_m':a,'view_extent':2.6,'field':arrows,'field_unit':'m/s²',
            'binary':{'mu':mu,'n_rad_s':n,'source_positions':source_positions(mu).tolist(),
                      'lagrange_points':lagrange_points(mu),'gates':list(gates),'probe':probe_reading,
                      'status':'model_boundary' if end<duration-1e-10 else 'duration_complete',
                      'duration_requested_s':duration/n,'jacobi_initial':float(c_values[0]),
                      'jacobi_relative_error':c_error,'solver_nfev':actual.nfev,
                      'linear_triangular_stability':27*mu*(1-mu)<1},
            'reference':{'probe':{k:v for k,v in probe_reading.items() if k!='applied_vector'},'binary_period_s':2*math.pi/n,
                         'channel_dependencies':'Fontes circulares prescritas; gravidade superposta atua na partícula de teste. Coriolis e termo centrífugo são de coordenadas, não forças adicionais físicas. Forte/fraca/EM têm seus próprios palcos.'},
            'measurements':[{'label':'Campo completo na sonda girante','value':float(np.linalg.norm(probe_reading['vector'])),'unit':'m/s²'},
                            {'label':'Aceleração aplicada inicial','value':float(np.linalg.norm(initial_g)),'unit':'m/s²'},
                            {'label':'Potencial na sonda, zero no infinito','value':probe_reading['potential_m2_s2'],'unit':'m²/s²'},
                            {'label':'Maior autovalor de maré na sonda','value':max(probe_reading['tidal_eigenvalues_s2']),'unit':'s⁻²'},
                            {'label':'Deriva do invariante de Jacobi','value':c_error,'unit':'normalizada'},
                            {'label':'Período das fontes','value':2*math.pi/n,'unit':'s'}],
            'sources':['https://farside.ph.utexas.edu/teaching/celestial/Celestial/node80.html',
                       'https://link.springer.com/article/10.1007/s10569-022-10118-z',
                       'https://iauarchive.eso.org/static/resolutions/IAU2015_English.pdf']}
