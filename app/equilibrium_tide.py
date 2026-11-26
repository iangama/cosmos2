"""Isolated SI equilibrium tide: potential Love k2 and Leconte2010 time lag.

One deformable isotropic body, one point companion. Fixed radius/inertia;
no rotational bulge, J2 coupling, thermal radius evolution or interior model.
Shared by the joint material dynamics and frozen exterior field readings.
"""
import math
import numpy as np

G=6.67430e-11
POLICY='Linear exterior degree2 equilibrium tide; potential Love k2, constant time lag in seconds; spherical fixed inertia, spin reaction and dissipated heat. No rotational bulge, J2, surface displacement or thermal structure.'


def _number(value,name):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite '+name+' required')
    return float(value)


def _vector(value,name):
    if not isinstance(value,list) or len(value)!=3:raise ValueError('Three '+name+' components required')
    return np.asarray([_number(v,name) for v in value])


def response(source_mass_kg,companion_mass_kg,radius_m,love_k2,tau_s,inertia_kg_m2,spin_rad_s,displacement_m,relative_velocity_m_s):
    M=_number(source_mass_kg,'source mass');m=_number(companion_mass_kg,'companion mass')
    R=_number(radius_m,'radius');k=_number(love_k2,'Love k2');tau=_number(tau_s,'time lag');I=_number(inertia_kg_m2,'inertia')
    if not 1e3<=M<=1e32 or not 1e3<=m<=1e32 or not .001<=R<=1e12 or not 0<=k<=1.5 or not 0<=tau<=1e12 or not 0<I<=2*M*R*R/3:
        raise ValueError('Parameters outside bounded candidate domain')
    omega=_vector(spin_rad_s,'spin');r=_vector(displacement_m,'displacement');v=_vector(relative_velocity_m_s,'velocity')
    distance=math.hypot(*r)
    if not R<=distance<=1e17:raise ValueError('Exterior separation R≤r≤1e17 required')
    # Bound arithmetic before dot products and keep this Newtonian prototype
    # within a declared weak-field, slow-motion domain.
    if math.hypot(*v)>3e6 or math.hypot(*omega)*R>3e6 or G*(M+m)/(distance*299792458.**2)>1e-6:
        raise ValueError('Weak-field, slow-motion candidate domain exceeded')
    u=v-np.cross(omega,r);rv=float(np.dot(r,v));n=r/distance;vr=rv/distance
    strain=(m/M)*(R/distance)**3
    lag=tau*(math.hypot(*u)/distance+3*abs(rv)/distance**2)
    rotation=float(np.dot(omega,omega))*R**3/(G*M)
    if max(1.,k)*strain>.01 or lag>.05 or rotation>.01:
        raise ValueError('Small deformation, small lag and slow-rotation limits exceeded')
    C=3*G*k*m*m*R**5
    elastic=-C*r/distance**8
    dissipative=-C*tau/distance**10*(2*r*rv+distance**2*u)
    force=elastic+dissipative;torque=-np.cross(r,dissipative)
    heat=C*tau/distance**10*(2*rv*rv+distance**2*float(np.dot(u,u)))
    amplitude=k*m*R**5/distance**3
    Q=amplitude*((1+5*tau*vr/distance)*np.outer(n,n)
        -(1+3*tau*vr/distance)*np.eye(3)/3
        -tau/distance*(np.outer(u,n)+np.outer(n,u)))
    result={'force_on_companion_N':force.tolist(),'elastic_force_N':elastic.tolist(),
        'dissipative_force_N':dissipative.tolist(),'source_recoil_m_s2':(-force/M).tolist(),
        'spin_torque_N_m':torque.tolist(),'spin_derivative_rad_s2':(torque/I).tolist(),
        'heat_power_W':heat,'effective_induced_energy_J':-C/(6*distance**6),
        'quadrupole_stf_kg_m2':Q.tolist(),'domain':{'tidal_strain_parameter':strain,'lag_measure':lag,'rotation_parameter':rotation},'policy':POLICY}
    if not all(math.isfinite(float(x)) for x in [*force,*torque,heat,*Q.flat]):raise ValueError('Nonfinite tide response')
    return result


def frozen_field(quadrupole_stf_kg_m2,radius_m,displacement_m):
    """Passive field of one confirmed induced quadrupole; add monopole separately.

    Q stays frozen during spatial differentiation. The induced equilibrium
    energy of an active pair includes the response cost and is a separate
    quantity from m times this frozen specific potential.
    """
    R=_number(radius_m,'radius');x=_vector(displacement_m,'displacement')
    if not .001<=R<=1e12:raise ValueError('Bounded positive radius required')
    r=math.hypot(*x)
    if not R<=r<=1e17:raise ValueError('Exterior field only')
    Q=np.asarray(quadrupole_stf_kg_m2,dtype=float)
    if Q.shape!=(3,3) or not np.isfinite(Q).all():raise ValueError('Finite quadrupole3×3 required')
    scale=float(np.linalg.norm(Q))
    if np.linalg.norm(Q-Q.T)>1e-13*scale or abs(float(np.trace(Q)))>1e-13*scale:raise ValueError('Symmetric trace-free quadrupole required')
    qx=Q@x;S=float(np.dot(x,qx))
    phi=-1.5*G*S/r**5;g=3*G*qx/r**5-7.5*G*S*x/r**7
    T=3*G*Q/r**5-15*G*(np.outer(qx,x)+np.outer(x,qx))/r**7-7.5*G*S*np.eye(3)/r**7+52.5*G*S*np.outer(x,x)/r**9
    return {'potential_J_kg':phi,'acceleration_m_s2':g.tolist(),'tidal_tensor_s_2':T.tolist()}
