"""Bounded exterior J2, fixed inertial axes, explicit linear reactions/energy."""
import copy
import ctypes
import math
import warnings
import numpy as np
import rebound

from physics import PHYSICAL_SCALE as U
from j2_field import correction,_evaluate,_parameters

POLICY = ('J2 exterior com eixos inerciais prescritos; reação linear e energia quadrupolar '
          'incluídas. Spin, reação do torque no spin, interior e deformação material não evoluem.')
POINTER_WARNING = 'You have to reset function pointers after creating a reb_simulation struct with a binary file.'
_PHASE_DTYPE=np.dtype({'names':['x','y','z','m','ax','ay','az'],
    'formats':['f8']*7,'offsets':[getattr(rebound.Particle,k).offset for k in ('x','y','z','m','ax','ay','az')],
    'itemsize':ctypes.sizeof(rebound.Particle)})


def parameters(value):
    if not isinstance(value, dict) or set(value) != {'j2','radius_eq_m','axis','provenance'}:
        raise ValueError('Informe J2, raio equatorial, eixo inercial e procedência explicitamente.')
    if (not isinstance(value['provenance'], str) or not 1<=len(value['provenance'].strip())<=240
            or any(ord(c)<32 for c in value['provenance'])):
        raise ValueError('Identifique a procedência dos parâmetros J2 em1–240caracteres.')
    radius=value['radius_eq_m']
    correction(1.,radius,value['j2'],value['axis'],[radius,0.,0.],tensor=False)
    if value['j2']==0:
        raise ValueError('Para desativar J2, remova explicitamente a configuração da fonte.')
    norm=math.hypot(*value['axis'])
    # Preserve a normalized saved direction exactly, avoiding cumulative drift
    # from normalization at every read/save/load cycle.
    axis=list(value['axis']) if abs(norm-1.)<=4e-15 else [v/norm for v in value['axis']]
    return {**copy.deepcopy(value),'axis':axis,'provenance':value['provenance'].strip()}


def validate(configuration, active_ids):
    if not isinstance(configuration,dict) or len(configuration)>4 or any(k not in active_ids for k in configuration):
        raise ValueError('J2 admite até4fontes identificadas entre os corpos ativos.')
    checked={identifier:parameters(value) for identifier,value in configuration.items()}
    if checked!=configuration:
        raise ValueError('Parâmetros J2 salvos não estão normalizados.')
    return checked


def bodies(sim, registry, configuration):
    return [{'id':meta['id'],'mass':p.m,'position':[p.x,p.y,p.z],'velocity':[p.vx,p.vy,p.vz],
             **({'j2':configuration[meta['id']]} if meta['id'] in configuration else {})}
            for p,meta in zip(sim.particles,registry)]


def terms(population):
    """All pair contributions use the very same SI field/force kernel."""
    positions=np.asarray([b['position'] for b in population])*U['length_unit_m']
    masses=np.asarray([b['mass'] for b in population])
    models=[(i,b['j2']) for i,b in enumerate(population) if 'j2' in b]
    acceleration,energy=_array_terms(positions,masses,models)
    return acceleration.tolist(),energy


def _prepare(masses,models):
    gm=U['nominal_GM_unit_m3_s2']
    if len(masses)<2 or not models:return None
    sources=np.repeat([i for i,_ in models],len(masses)-1)
    targets=np.concatenate([np.delete(np.arange(len(masses)),i) for i,_ in models])
    radius=np.repeat([model['radius_eq_m'] for _,model in models],len(masses)-1)
    j2=np.repeat([model['j2'] for _,model in models],len(masses)-1)
    axes=np.repeat([_parameters(float(masses[i])*gm,model['radius_eq_m'],model['j2'],model['axis']) for i,model in models],len(masses)-1,axis=0)
    return sources,targets,radius,j2,axes,masses[sources]*gm


def _array_terms(positions,masses,models,prepared=None,*,energy_required=True):
    length=U['length_unit_m'];gm=U['nominal_GM_unit_m3_s2'];accel_unit=gm/length**2
    accelerations=np.zeros((len(masses),3));energy=[]
    prepared=_prepare(masses,models) if prepared is None else prepared
    if prepared is None:return accelerations,0.
    sources,targets,radius,j2,axes,source_GM=prepared
    phi,g,_=_evaluate(source_GM,radius,j2,axes,positions[targets]-positions[sources])
    a=g/accel_unit;np.add.at(accelerations,targets,a)
    reaction=a*(masses[targets]/masses[sources])[:,None]
    summed=np.sum(reaction.reshape(len(models),len(masses)-1,3),axis=1)
    for row,(i,_) in enumerate(models):accelerations[i]-=summed[row]
    if energy_required:energy.append(math.fsum(masses[targets]*phi/(gm/length)))
    return accelerations,math.fsum(energy)


def copied(action,allow_pointer_warning=True):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');result=action()
    if any(not allow_pointer_warning or w.category is not RuntimeWarning or str(w.message)!=POINTER_WARNING for w in caught):
        raise ValueError('O arquivo/clone REBOUND emitiu aviso incompatível: '+'; '.join(str(w.message) for w in caught))
    return result


class Controller:
    def __init__(self,sim,registry,configuration):
        if bool(sim._additional_forces):raise ValueError('Uma força adicional desconhecida já está instalada.')
        validate(configuration,[b['id'] for b in registry])
        self.sim=sim;self.registry=copy.deepcopy(registry);self.configuration=copy.deepcopy(configuration);self.error=None
        terms(bodies(sim,registry,configuration))
        models=[(i,configuration[b['id']]) for i,b in enumerate(registry) if b['id'] in configuration]
        masses=np.asarray([p.m for p in sim.particles]);prepared=_prepare(masses,models)
        def callback(pointer):
            current=pointer.contents
            if self.error:current.stop();return
            try:
                if current.N!=len(self.registry):raise ValueError('População mudou durante callback J2.')
                # A fresh bounded view is created for this callback only. No
                # particle pointer or array view survives clone/load/reallocation.
                buffer=(ctypes.c_char*(current.N*ctypes.sizeof(rebound.Particle))).from_address(ctypes.addressof(current._particles.contents))
                phase=np.ndarray(current.N,dtype=_PHASE_DTYPE,buffer=buffer)
                if not np.array_equal(phase['m'],masses):raise ValueError('Massas mudaram durante callback J2.')
                positions=np.column_stack((phase['x'],phase['y'],phase['z']))*U['length_unit_m']
                accelerations,_=_array_terms(positions,masses,models,prepared,energy_required=False)
                for k,name in enumerate(('ax','ay','az')):phase[name]+=accelerations[:,k]
            except Exception as error:
                self.error=str(error);current.stop()
        sim.additional_forces=callback;sim.force_is_velocity_dependent=0
        self.pointer=ctypes.cast(sim._additional_forces,ctypes.c_void_p).value

    def check(self,sim,registry,configuration):
        if (ctypes.addressof(sim)!=ctypes.addressof(self.sim) or registry!=self.registry
                or configuration!=self.configuration
                or sim.force_is_velocity_dependent!=0
                or bool(sim._pre_timestep_modifications) or bool(sim._post_timestep_modifications)
                or ctypes.cast(sim._additional_forces,ctypes.c_void_p).value!=self.pointer):
            raise ValueError('Callback J2 não corresponde ao estado e aos parâmetros confirmados.')


def restore(manifest,original_ids,events,registry):
    """Replay physical parameter interventions; a seal alone is insufficient."""
    configuration={};active=set(original_ids)
    for event in events:
        kind=event['type'];identifier=event['body']
        if kind=='create_body':active.add(identifier)
        elif kind=='remove_body':
            if identifier in configuration:raise ValueError('Fonte J2 removida sem desativar o modelo.')
            active.remove(identifier)
        elif kind=='set_j2':
            if identifier not in active or event.get('old_j2')!=configuration.get(identifier):
                raise ValueError('Histórico físico de J2 incompatível.')
            new=event.get('new_j2')
            if new is None:configuration.pop(identifier,None)
            else:
                if parameters(new)!=new:raise ValueError('Parâmetros J2 históricos inválidos.')
                configuration[identifier]=new
            validate(configuration,active)
    modern=manifest['saved_generation']['model_version'] in ('3.9.0','3.9.1','3.10.0','3.11.0','3.12.0','3.13.0')
    if modern:
        if manifest.get('gravity_effects')!=configuration:raise ValueError('J2 salvo diverge das intervenções físicas.')
    elif configuration or any(e['type']=='set_j2' for e in events) or manifest.get('gravity_effects',{})!={}:
        raise ValueError('Geração antiga não pode declarar força J2.')
    return validate(configuration,[b['id'] for b in registry])


def contract(base,configuration):
    if not configuration:return base
    result={**base,'model':'newtonian_monopoles_plus_exterior_J2','gravity':'monopoles_plus_exterior_J2','j2_policy':POLICY}
    if 'excluded_influences' in base:
        result['excluded_influences']=['deformações materiais e dissipação por maré' if v=='J2 e deformações de maré' else v for v in base['excluded_influences']]
    return result


def monopole_contract(value):
    if value.get('gravity')!='monopoles_plus_exterior_J2':return value
    result={k:v for k,v in value.items() if k not in ('gravity','j2_policy')}
    result['model']='newtonian_point_masses'
    if 'excluded_influences' in result:
        result['excluded_influences']=['J2 e deformações de maré' if v=='deformações materiais e dissipação por maré' else v for v in result['excluded_influences']]
    return result


def conservation(value,configuration):
    if not configuration:return value
    value['scope']=POLICY
    # Vector orbital angular change is physical under a prescribed quadrupole
    # axis. Never label it a numerical conservation error or include spin.
    value['orbital_angular_change_normalized']=value['angular_momentum_error_normalized']
    value['angular_momentum_error_normalized']=None
    value['SI']['orbital_angular_change_norm_kg_m2_s']=value['SI']['angular_momentum_error_norm_kg_m2_s']
    value['SI']['angular_momentum_error_norm_kg_m2_s']=None
    axes=[row['axis'] for row in configuration.values()];axis=axes[0]
    parallel=all(math.hypot(*(a-b for a,b in zip(axis,other)))<1e-12
                 or math.hypot(*(a+b for a,b in zip(axis,other)))<1e-12 for other in axes[1:])
    if parallel:
        before=math.fsum(a*b for a,b in zip(axis,value['reference']['angular_momentum']))
        now=math.fsum(a*b for a,b in zip(axis,value['current']['angular_momentum']))
        scale=value['reference']['angular_momentum_scale']
        value['J2_axial_angular']={'axis':list(axis),'reference':before,'current':now,
                                 'normalized_error':abs(now-before)/scale if scale else None}
    else:value['J2_axial_angular']=None
    return value
