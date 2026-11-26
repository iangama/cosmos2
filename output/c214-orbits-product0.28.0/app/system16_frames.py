"""Keep a uniform inertial origin separate from the local Newtonian solver phase."""
import copy
import math

import system16_import


def vector(value, bound):
    if not isinstance(value,list) or len(value)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>bound for x in value):
        raise ValueError('Origem/velocidade do referencial inválida.')
    return list(value)


class Frame:
    def __init__(self, initial, origin_m, velocity_m_s):
        self.origin_m=vector(origin_m,1e17)
        self.velocity_m_s=vector(velocity_m_s,1e7)
        self.initial=system16_import.validate(initial)
        self.sim=system16_import.simulation(self.initial)

    def integrate(self, canonical_time):
        self.sim.integrate(canonical_time)

    def state(self):
        seconds=self.sim.t*system16_import.U['time_unit_s']
        return dict(schema=1,encoding='split_inertial_origin',elapsed_s=seconds,
                    origin_m=[x+v*seconds for x,v in zip(self.origin_m,self.velocity_m_s)],
                    origin_velocity_m_s=list(self.velocity_m_s),
                    canonical_internal=[[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in self.sim.particles],
                    units=copy.deepcopy(system16_import.U),
                    meaning='World position = origin_m + local_position*length_unit_m; keep components separate for numerical evolution.')
