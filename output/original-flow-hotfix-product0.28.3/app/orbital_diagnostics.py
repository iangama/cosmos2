"""Instantaneous pair conics and translational integrals; no N-body prediction."""
import math
import numpy as np
from physics import PHYSICAL_SCALE as U


def pair(bodies,body_id,primary_id,points=129):
    if type(points) is not int or not 17<=points<=513 or points%2!=1:raise ValueError('Amostragem orbital exige17–513 pontos e quantidade ímpar.')
    by_id={b['id']:b for b in bodies}
    if body_id==primary_id or body_id not in by_id or primary_id not in by_id:raise ValueError('Selecione dois corpos ativos distintos.')
    body,primary=by_id[body_id],by_id[primary_id];r=np.array(body['position'])-primary['position'];v=np.array(body['velocity'])-primary['velocity']
    distance=float(np.linalg.norm(r));speed=float(np.linalg.norm(v));mu=body['mass']+primary['mass']
    if not distance or not math.isfinite(distance) or mu<=0:raise ValueError('Par orbital degenerado.')
    radial=float(np.dot(r,v)/distance);h=np.cross(r,v);hnorm=float(np.linalg.norm(h));rhat=r/distance;energy=.5*speed**2-mu/distance
    evec=np.cross(v,h)/mu-rhat;ecc=float(np.linalg.norm(evec));parameter=hnorm**2/mu
    radial_case=not speed or hnorm<=1e-10*distance*speed;near_parabolic=abs(energy)<=1e-10*mu/distance
    kind='radial_degenerate' if radial_case else 'near_parabolic' if near_parabolic else 'elliptic' if energy<0 else 'hyperbolic'
    a=None if near_parabolic else -mu/(2*energy);peri=None if radial_case else parameter/(1+ecc)
    apo=a*(1+ecc) if kind=='elliptic' else None;period=2*math.pi*math.sqrt(a**3/mu) if kind=='elliptic' else None
    q=np.zeros(3)
    for other in bodies:
        if other['id'] in (body_id,primary_id):continue
        db=np.array(other['position'])-body['position'];dp=np.array(other['position'])-primary['position'];rb=float(np.linalg.norm(db));rp=float(np.linalg.norm(dp))
        if rb==0 or rp==0:raise ValueError('Fonte coincidente no diagnóstico.')
        q+=other['mass']*(db/rb**3-dp/rp**3)
    if any(b.get('j2') for b in bodies):
        from gravity_harmonics import terms
        corrections,_=terms(bodies)
        q+=np.array(corrections[bodies.index(body)])-corrections[bodies.index(primary)]
    if any(b.get('tide') for b in bodies):
        from material_tides import active_corrections
        corrections=active_corrections(bodies)
        q+=corrections[bodies.index(body)]-corrections[bodies.index(primary)]
    segments=[];current=[];radius_limit=8*distance;clipped=False
    if not radial_case:
        tangent=np.cross(h/hnorm,rhat)
        for theta in np.linspace(-math.pi,math.pi,points):
            direction=math.cos(theta)*rhat+math.sin(theta)*tangent;denominator=1+float(np.dot(evec,direction))
            radius=parameter/denominator if denominator>0 else math.inf
            if radius<=radius_limit:
                current.append((np.array(primary['position'])+radius*direction).tolist())
            else:
                clipped=True
                if len(current)>1:segments.append(current)
                current=[]
        if len(current)>1:segments.append(current)
    else:clipped=True
    inclination=math.acos(float(np.clip(h[2]/hnorm,-1,1))) if not radial_case else None
    return {'body':body_id,'primary':primary_id,'classification':kind,'distance_m':distance*U['length_unit_m'],
            'relative_velocity_m_s':(v*U['velocity_unit_m_s']).tolist(),'relative_speed_m_s':speed*U['velocity_unit_m_s'],
            'radial_speed_m_s':radial*U['velocity_unit_m_s'],'transverse_speed_m_s':hnorm/distance*U['velocity_unit_m_s'],
            'mu_m3_s2':mu*U['nominal_GM_unit_m3_s2'],'specific_energy_J_kg':energy*U['velocity_unit_m_s']**2,
            'specific_angular_momentum_m2_s':(h*U['length_unit_m']*U['velocity_unit_m_s']).tolist(),
            'eccentricity_vector':evec.tolist(),'eccentricity':ecc,'parameter_m':parameter*U['length_unit_m'],
            'semimajor_axis_m':a*U['length_unit_m'] if a is not None else None,'periapsis_m':peri*U['length_unit_m'] if peri is not None else None,
            'apoapsis_m':apo*U['length_unit_m'] if apo is not None else None,'period_s':period*U['time_unit_s'] if period is not None else None,
            'inclination_rad':inclination,'periapsis_direction_defined':not radial_case and ecc>1e-10,
            'ascending_node_defined':not radial_case and math.hypot(h[0],h[1])>1e-10*hnorm,
            'escape_speed_pair_m_s':math.sqrt(2*mu/distance)*U['velocity_unit_m_s'],
            'perturbation_relative_acceleration_ratio':float(np.linalg.norm(q))/(mu/distance**2),
            'preview':{'segments_model_units':segments,'radius_limit_m':radius_limit*U['length_unit_m'],'clipped':clipped,
                       'closed':kind=='elliptic' and not clipped,'primary_frozen':True,'time_parameterized':False,
                       'primary_position_model_units':list(primary['position'])},
            'model':'instantaneous monopole osculating conic under material tide perturbations; joint orbit/spin/heat evolution is not this frozen conic' if any(b.get('tide') for b in bodies) else 'instantaneous monopole osculating conic under J2 perturbations, not a trajectory prediction; mu includes both masses' if any(b.get('j2') for b in bodies) else 'instantaneous isolated pair conic, not an N-body/JPL forecast; mu includes both masses',
            'undefined_reason':'radial state has no orbital plane' if radial_case else 'semimajor axis/period unstable near parabola' if near_parabolic else None}


def integrals(bodies,time,energy=None):
    masses=np.array([b['mass'] for b in bodies]);positions=np.array([b['position'] for b in bodies]);velocities=np.array([b['velocity'] for b in bodies]);total=math.fsum(masses)
    momentum=np.array([math.fsum(masses[i]*velocities[i,k] for i in range(len(masses))) for k in range(3)])
    cross=np.cross(positions,velocities);angular=np.array([math.fsum(masses[i]*cross[i,k] for i in range(len(masses))) for k in range(3)])
    center=np.array([math.fsum(masses[i]*positions[i,k] for i in range(len(masses)))/total for k in range(3)])
    kinetic=math.fsum(.5*m*float(np.dot(v,v)) for m,v in zip(masses,velocities))
    extra_energy=None;extra_scale=0.
    if any(b.get('tide') for b in bodies):
        from material_tides import extra_integrals
        extra_energy,spin,extra_scale=extra_integrals(bodies);angular+=spin
    if energy is None:
        potential=-math.fsum(masses[i]*masses[j]/float(np.linalg.norm(positions[i]-positions[j])) for i in range(len(masses)) for j in range(i))
        if any(b.get('j2') for b in bodies):
            from gravity_harmonics import terms
            potential+=terms(bodies)[1]
        if extra_energy:potential+=extra_energy['induced_energy']
        energy=kinetic+potential+(extra_energy['spin_kinetic_energy']+extra_energy['heat_energy'] if extra_energy else 0.)
    elif extra_energy:
        potential=-math.fsum(masses[i]*masses[j]/float(np.linalg.norm(positions[i]-positions[j])) for i in range(len(masses)) for j in range(i))+extra_energy['induced_energy']
    else:potential=energy-kinetic
    return {'time':time,'total_mass':total,'energy':energy,'kinetic_energy':kinetic,'potential_energy':potential,
            **({'material_energy':extra_energy} if extra_energy else {}),
            'momentum':momentum.tolist(),'angular_momentum':angular.tolist(),'barycenter':center.tolist(),'barycenter_velocity':(momentum/total).tolist(),
            'momentum_scale':math.fsum(m*float(np.linalg.norm(v)) for m,v in zip(masses,velocities)),
            'angular_momentum_scale':math.fsum(m*float(np.linalg.norm(c)) for m,c in zip(masses,cross))+extra_scale}

def validate_reference(value,bodies,time,energy_reference):
    keys=set(integrals(bodies,time,energy_reference))|{'policy','active_ids','energy_reference_time'}
    if not isinstance(value,dict) or set(value)!=keys or value.get('policy') not in ('initial_condition','external_intervention','legacy_checkpoint_new_momentum_reference'):raise ValueError('Referência de conservação inválida.')
    if value['active_ids']!=[b['id'] for b in bodies]:raise ValueError('Referência de conservação tem outra população.')
    for key in ('time','total_mass','energy','kinetic_energy','potential_energy','momentum_scale','angular_momentum_scale'):
        v=value[key]
        if type(v) not in (int,float) or not math.isfinite(v):raise ValueError('Escalar da referência inválido.')
    for key in ('momentum','angular_momentum','barycenter','barycenter_velocity'):
        v=value[key]
        if not isinstance(v,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):raise ValueError('Vetor da referência inválido.')
    if not 0<=value['time']<=time or value['total_mass']<=0 or value['kinetic_energy']<0 or value['potential_energy']>0 or min(value['momentum_scale'],value['angular_momentum_scale'])<0:raise ValueError('Domínio da referência inválido.')
    expected_mass=math.fsum(b['mass'] for b in bodies)
    if not math.isclose(value['total_mass'],expected_mass,rel_tol=1e-14):raise ValueError('Massa de referência incompatível.')
    if value['policy']=='legacy_checkpoint_new_momentum_reference':
        if value['energy_reference_time'] is not None:raise ValueError('Época antiga de energia não é conhecida.')
    elif value['energy_reference_time']!=value['time'] or value['energy']!=energy_reference:raise ValueError('Baseline de energia incompatível com a referência.')
    if max(abs(a-value['total_mass']*v) for a,v in zip(value['momentum'],value['barycenter_velocity']))>1e-13*max(value['momentum_scale'],1e-30):raise ValueError('Momento e velocidadeCOM incompatíveis.')
    internal=0.
    if 'material_energy' in value:
        extra=value['material_energy']
        if not isinstance(extra,dict) or set(extra)!={'induced_energy','spin_kinetic_energy','heat_energy'} or any(type(x) not in (int,float) or not math.isfinite(x) for x in extra.values()) or extra['induced_energy']>0 or min(extra['spin_kinetic_energy'],extra['heat_energy'])<0:raise ValueError('Energias materiais da referência inválidas.')
        internal=extra['spin_kinetic_energy']+extra['heat_energy']
    if abs(value['energy']-value['kinetic_energy']-value['potential_energy']-internal)>1e-13*max(value['kinetic_energy'],abs(value['potential_energy']),internal,1e-30):raise ValueError('Energias da referência incompatíveis.')
    return value

def conservation(bodies,time,reference,energy_reference,energy=None):
    current=integrals(bodies,time,energy);punit=U['mass_unit_kg']*U['velocity_unit_m_s'];lunit=punit*U['length_unit_m'];eunit=punit*U['velocity_unit_m_s']
    dp=[a-b for a,b in zip(current['momentum'],reference['momentum'])];dl=[a-b for a,b in zip(current['angular_momentum'],reference['angular_momentum'])]
    expected=[r+v*(time-reference['time']) for r,v in zip(reference['barycenter'],reference['barycenter_velocity'])]
    drift=[r-e for r,e in zip(current['barycenter'],expected)];de=current['energy']-energy_reference
    return {'scope':'translational Newtonian centers; kinematic spin/internal energy excluded','reference':reference,
            'current':current,'SI':{'total_mass_kg':current['total_mass']*U['mass_unit_kg'],'energy_J':current['energy']*eunit,
            'kinetic_energy_J':current['kinetic_energy']*eunit,'potential_energy_J':current['potential_energy']*eunit,
            'momentum_kg_m_s':[v*punit for v in current['momentum']],'angular_momentum_kg_m2_s':[v*lunit for v in current['angular_momentum']],
            'barycenter_m':[v*U['length_unit_m'] for v in current['barycenter']],'barycenter_velocity_m_s':[v*U['velocity_unit_m_s'] for v in current['barycenter_velocity']],
            'expected_barycenter_m':[v*U['length_unit_m'] for v in expected],'barycenter_drift_m':[v*U['length_unit_m'] for v in drift],
            'energy_error_absolute_J':abs(de)*eunit,'momentum_error_norm_kg_m_s':math.hypot(*dp)*punit,
            'angular_momentum_error_norm_kg_m2_s':math.hypot(*dl)*lunit,'barycenter_drift_norm_m':math.hypot(*drift)*U['length_unit_m']},
            'momentum_error_normalized':math.hypot(*dp)/reference['momentum_scale'] if reference['momentum_scale'] else None,
            'angular_momentum_error_normalized':math.hypot(*dl)/reference['angular_momentum_scale'] if reference['angular_momentum_scale'] else None}

def escape_test_particle(bodies,identifier):
    body=next((b for b in bodies if b['id']==identifier),None)
    if body is None:raise ValueError('Corpo desconhecido para escape.')
    if any(b.get('j2') or b.get('tide') for b in bodies):
        import gravity_field
        data=gravity_field.evaluate([b for b in bodies if b['id']!=identifier],[v*U['length_unit_m'] for v in body['position']])
        return {'potential_J_kg':data['potential_J_kg'],'escape_speed_m_s':math.sqrt(-2*data['potential_J_kg']),
                'model':'massless point in the frozen selected monopole/quadrupole field; no new induced response; not an active-body escape guarantee','excludes_self':True}
    potential=0.
    for other in bodies:
        if other['id']==identifier:continue
        distance=math.dist(body['position'],other['position'])
        if not distance:raise ValueError('Fontes coincidentes no escape.')
        potential-=other['mass']/distance
    return {'potential_J_kg':potential*U['velocity_unit_m_s']**2,'escape_speed_m_s':math.sqrt(-2*potential)*U['velocity_unit_m_s'],
            'model':'massless test particle in frozen instantaneous source potential; not an N-body escape guarantee','excludes_self':True}
