"""Explicit two-body material contract shared by dynamics and frozen readings."""
import copy
import math
import numpy as np

from equilibrium_tide import response,frozen_field
from material_driver import Driver,parameters,POLICY
from physics import PHYSICAL_SCALE as U

EUNIT=U['mass_unit_kg']*U['velocity_unit_m_s']**2
LUNIT=U['mass_unit_kg']*U['velocity_unit_m_s']*U['length_unit_m']


def synthetic_pair():
    """Explicit verification-scale teaching preset; no observational identity."""
    M=1e25;a=1e8;n=math.sqrt(U['G_m3_kg_s2']*2*M/a**3)
    speed=.5*math.sqrt(1.5)*a*n/U['velocity_unit_m_s']
    bodies=[{'name':'Corpo material sintético','mass':M/U['mass_unit_kg'],'position':[-.4*a/U['length_unit_m'],0.,0.],'velocity':[0.,-speed,0.]},
        {'name':'Companheiro pontual','mass':M/U['mass_unit_kg'],'position':[.4*a/U['length_unit_m'],0.,0.],'velocity':[0.,speed,0.]}]
    configuration={'radius_m':1e7,'love_k2':.3,'time_lag_s':.003/n,'inertia_kg_m2':.33*M*1e14,'spin_rad_s':[.25*n,.1*n,1.4*n],
        'provenance':'Par didático sintético: massas1e25kg, a1e8m, e0.2; k2 potencial0.3, R1e7m, I0.33MR², tau0.003/n. Sem interior observado.'}
    return bodies,configuration


def origin(checkpoint):
    return {k:copy.deepcopy(checkpoint[k]) for k in ('model','ids','source_id','configuration','masses_kg','epoch','initial_phase','length_m','time_s','energy_J','center','center_velocity','reference')}


def contract(base,active):
    if not active:return base
    result={**base,'model':'newtonian_two_body_equilibrium_tide_CTL','integrator':'BS joint orbit/spin/heat','epsilon':None,'material_tide_policy':POLICY,'material_base_contract':copy.deepcopy(base),'bs_eps_abs':1e-13,'bs_eps_rel':1e-13}
    if 'excluded_influences' in result:
        result['excluded_influences']=[v for v in result['excluded_influences'] if v not in ('J2 e deformações de maré','deformações materiais e dissipação por maré')]+['J2 prescrito, bulbo rotacional, deslocamento de superfície e resposta térmica do raio']
    return result


def base_contract(value):
    if 'material_tide_policy' not in value:return value
    return copy.deepcopy(value['material_base_contract'])


def body_snapshot(driver):
    d=driver.material();y=driver.values()
    return {'companion_id':driver.ids[1-driver.index], 'parameters':copy.deepcopy(driver.configuration),
        'spin_rad_s':(y[6:9]/driver.time).tolist(),'dissipated_heat_J':float(y[9]*driver.energy),
        'quadrupole_stf_kg_m2':d['quadrupole_stf_kg_m2']}


def enrich(bodies,driver):
    if driver is None:return bodies
    for b in bodies:
        if b['id']==driver.source_id:b['tide']=body_snapshot(driver)
    return bodies


def snapshot_response(bodies):
    models=[b for b in bodies if 'tide' in b]
    if not models:return None
    if len(models)!=1 or len(bodies)!=2 or any('j2' in b for b in bodies):raise ValueError('Material snapshot requires exactly two bodies and no prescribed J2')
    source=models[0];model=source['tide']
    if not isinstance(model,dict) or set(model)!={'companion_id','parameters','spin_rad_s','dissipated_heat_J','quadrupole_stf_kg_m2'}:raise ValueError('Invalid material snapshot')
    cfg=parameters(model['parameters']);other=next((b for b in bodies if b['id']==model['companion_id'] and b['id']!=source['id']),None)
    if other is None:raise ValueError('Material companion missing from snapshot')
    heat=model['dissipated_heat_J']
    if type(heat) not in (int,float) or not math.isfinite(heat) or heat<0:raise ValueError('Invalid material heat snapshot')
    r=[(other['position'][j]-source['position'][j])*U['length_unit_m'] for j in range(3)]
    v=[(other['velocity'][j]-source['velocity'][j])*U['velocity_unit_m_s'] for j in range(3)]
    d=response(source['mass']*U['mass_unit_kg'],other['mass']*U['mass_unit_kg'],cfg['radius_m'],cfg['love_k2'],cfg['time_lag_s'],cfg['inertia_kg_m2'],model['spin_rad_s'],r,v)
    q=np.asarray(model['quadrupole_stf_kg_m2']);expected=np.asarray(d['quadrupole_stf_kg_m2'])
    if q.shape!=(3,3) or not np.isfinite(q).all() or np.linalg.norm(q-expected)>2e-12*max(np.linalg.norm(expected),1e-300):raise ValueError('Frozen material quadrupole does not match phase/spin')
    return source,model,d


def extra_integrals(bodies):
    data=snapshot_response(bodies)
    if data is None:return 0.,np.zeros(3),0.
    source,model,d=data;I=model['parameters']['inertia_kg_m2'];spin=np.asarray(model['spin_rad_s'])
    extra={'induced_energy':d['effective_induced_energy_J']/EUNIT,'spin_kinetic_energy':.5*I*float(spin@spin)/EUNIT,'heat_energy':model['dissipated_heat_J']/EUNIT}
    angular=I*spin/LUNIT
    return extra,angular,float(np.linalg.norm(angular))


def active_corrections(bodies):
    data=snapshot_response(bodies);result=np.zeros((len(bodies),3))
    if data is None:return result
    source,model,d=data;i=bodies.index(source);j=1-i
    acceleration_unit=U['velocity_unit_m_s']/U['time_unit_s']
    force=np.asarray(d['force_on_companion_N'])
    result[i]=-force/(source['mass']*U['mass_unit_kg'])/acceleration_unit
    result[j]=force/(bodies[j]['mass']*U['mass_unit_kg'])/acceleration_unit
    return result


def energy(driver):
    balances=driver.balances()
    # Relative solver balances omit inertial center-of-mass kinetic energy.
    center_v=np.asarray(driver.center_velocity)*U['velocity_unit_m_s']
    return (balances['energy_plus_heat_J']+.5*(driver.M+driver.m)*float(center_v@center_v))/EUNIT


def public(driver):
    if driver is None:return None
    d=driver.material();b=driver.balances()
    return {'body':driver.source_id,'companion':driver.ids[1-driver.index],
        'parameters':copy.deepcopy(driver.configuration),'spin_rad_s':(driver.values()[6:9]/driver.time).tolist(),
        **b,'heat_power_W':d['heat_power_W'],'effective_induced_energy_J':d['effective_induced_energy_J'],
        'domain':d['domain'],'policy':POLICY,
        'radius_policy':'Fixed material reference radius; geometric radius and kinematic orientation are separate. k2 does not define surface displacement h2.'}


def replay(manifest,events,registry,original_ids):
    active=None;ids=list(original_ids)
    for e in events:
        if e['type']=='set_tides':
            if e.get('old_material_origin')!=active:raise ValueError('Material intervention history differs from prior origin')
            active=copy.deepcopy(e.get('new_material_origin'))
            if active is not None:
                if active.get('source_id')!=e['body'] or active.get('epoch')!=e['time'] or active.get('ids')!=ids:raise ValueError('Material activation identity/epoch mismatch')
                parameters(active.get('configuration'))
        elif active is not None and e['type'] in ('set_mass','set_body_si','create_body','remove_body','set_j2'):
            raise ValueError('Phase/mass/topology/J2 edited without disabling material model')
        if e['type']=='create_body':ids.append(e['body'])
        elif e['type']=='remove_body':ids.remove(e['body'])
    saved=manifest.get('material_tides')
    modern=manifest['saved_generation']['model_version'] in ('3.10.0','3.11.0','3.12.0','3.13.0')
    if modern and 'material_tides' not in manifest:raise ValueError('Missing modern material checkpoint declaration')
    if not modern and (saved is not None or active is not None):raise ValueError('Old generation cannot declare material tides')
    if (saved is None)!=(active is None) or saved is not None and origin(saved)!=active:raise ValueError('Saved material model differs from physical intervention history')
    return saved
