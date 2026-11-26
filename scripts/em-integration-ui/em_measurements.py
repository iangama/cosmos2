"""Read-only SI instrumentation derived from one confirmed core0.4 snapshot."""
from copy import deepcopy
import math
import numpy as np
from em_experiment import Experiment
from em_fields import lorentz


def measure(state):
    ex=Experiment.from_payload(state['experiment'])
    selected=state['editor']['visual']['selected_id']
    if ex.mode=='test_particle':
        particle={'id':'test-particle','position_m':list(ex.phase.position_m),
                  'velocity_m_s':list(ex.phase.velocity_m_s),'charge_C':ex.charge_C,'mass_kg':ex.mass_kg}
        force=lorentz(ex.model,ex.phase.position_m,ex.phase.velocity_m_s,ex.charge_C,ex.mass_kg,**ex.controls)
        assert force['valid']
    else:
        index=ex.model.ids.index(selected) if selected is not None else 0
        particle={'id':ex.model.ids[index],'position_m':list(ex.phase.position_m[index]),
                  'velocity_m_s':list(ex.phase.velocity_m_s[index]),
                  'charge_C':ex.model.charge_C[index],'mass_kg':ex.model.mass_kg[index]}
        model=ex.model.field_snapshot(ex.phase,exclude_id=particle['id'])
        force=lorentz(model,particle['position_m'],particle['velocity_m_s'],
                      particle['charge_C'],particle['mass_kg'],electric_acting=ex.controls['acting'],magnetic_acting=False)
        assert force['valid']
    diagnostics=state['diagnostics'];reference=state['editor']['reference']
    work=reference['diagnostics']['potential_energy_J']-diagnostics['potential_energy_J']
    kinetic=diagnostics['kinetic_energy_J']-reference['diagnostics']['kinetic_energy_J']
    result={'schema':1,'kind':'cosmos2_em_matter_measurement',
            **{k:deepcopy(state[k]) for k in ('system_id','edit_token','revision','time_s','frame','scientific_generation','execution_generation')},
            'mode':ex.mode,'particle':particle,'force':force,'controls':deepcopy(ex.controls),
            'source_snapshot':deepcopy(state['experiment']),
            'energy':{k:diagnostics[k] for k in ('kinetic_energy_J','potential_energy_J','mechanical_energy_J')},
            'balance':{'reference_time_s':reference['time_s'],'reference_physics_revision':reference['physics_revision'],
                       'electric_work_from_static_potential_J':work,'kinetic_change_J':kinetic,'residual_J':kinetic-work,
                       'method':'U(reference)-U(current), static conservative electric field; total matter energy in mutual mode'},
            'electric_power_W':math.fsum(f*v for f,v in zip(force['electric_force_N'],particle['velocity_m_s'])),
            'units':{'position_m':'m','velocity_m_s':'m/s','charge_C':'C','mass_kg':'kg','force_N':'N',
                     'electric_force_N':'N','magnetic_force_N':'N','electric_power_W':'W',
                     'energy':'J','balance_work':'J','time_s':'s'},
            'gyro_reference':None,
            'omitted':'Fixed-source reservoirs, field energy, induced electric fields and radiation. No self-field in the selected-particle force.'}
    if ex.mode=='test_particle' and ex.controls['magnetic_acting']:
        field=np.asarray(force['reference']['magnetic_field_T']);strength=math.hypot(*field)
        omega=abs(ex.charge_C)*strength/ex.mass_kg
        if omega>0 and math.isfinite(omega):
            perpendicular=math.hypot(*np.cross(particle['velocity_m_s'],field/strength))
            radius=perpendicular/omega;period=2*math.pi/omega
            if math.isfinite(radius) and math.isfinite(period):
                result['gyro_reference']={'radius_m':radius,'period_s':period,'angular_frequency_rad_s':omega,
                    'scope':'Referência local para B uniforme. A hélice de referência exige B uniforme e ausência de força elétrica.'}
    return result
