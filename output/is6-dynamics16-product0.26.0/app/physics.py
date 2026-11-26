"""Deterministic canonical-unit REBOUND fixtures, separate from atlas ephemerides."""
import math
import json
from pathlib import Path
import rebound

_UNIT_FILE=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())/'data/science/canonical-units.json'
_UNITS=json.loads(_UNIT_FILE.read_text(encoding='utf-8'))
PHYSICAL_SCALE={**_UNITS,
    'time_unit_s':math.sqrt(_UNITS['length_unit_m']**3/_UNITS['nominal_GM_unit_m3_s2']),
    'mass_unit_kg':_UNITS['nominal_GM_unit_m3_s2']/_UNITS['G_m3_kg_s2'],
    'mass_unit_relative_standard_uncertainty':_UNITS['G_standard_uncertainty']/_UNITS['G_m3_kg_s2']}
PHYSICAL_SCALE['velocity_unit_m_s']=PHYSICAL_SCALE['length_unit_m']/PHYSICAL_SCALE['time_unit_s']

CONTRACT = {
    "schema": 1, "frame": "initial_barycenter_inertial",
    "units": {"system": "canonical", "G": 1.0, "initial_central_mass": 1.0,
              "reference_circular_period": 2 * math.pi},
    "model": "newtonian_point_masses", "collisions": "disabled",
    "integrator": "IAS15", "epsilon": 1e-9,
}

def fixture(count=32):
    if type(count) is not int or count not in (2, 32, 128, 256):
        raise ValueError("Supported fixtures: 2, 32, 128, 256 bodies")
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.integrator = "ias15"
    sim.integrator.epsilon = 1e-9
    sim.add(m=1.0)
    orbiters = count - 1
    for i in range(orbiters):
        radius = 1.0 if count == 2 else 0.5 * 60 ** (i / (orbiters - 1))
        angle = 2 * math.pi * i / orbiters
        velocity = math.sqrt((1 + 1e-8) / radius)
        sim.add(m=1e-8, x=radius*math.cos(angle), y=radius*math.sin(angle),
                vx=-velocity*math.sin(angle), vy=velocity*math.cos(angle))
    sim.move_to_com()
    return sim

def snapshot(sim, initial_energy):
    return {
        "time": sim.t, "units": "canonical", "G": sim.G,
        "physical_scale": PHYSICAL_SCALE,
        "integrator": "IAS15", "epsilon": 1e-9,
        "energy_error": abs((sim.energy() - initial_energy) / initial_energy) if initial_energy else None,
        "energy_error_absolute": abs(sim.energy()-initial_energy),
        "bodies": [{"id": f"p{i}", "mass": p.m,
                    "position": [p.x, p.y, p.z], "velocity": [p.vx, p.vy, p.vz]}
                   for i, p in enumerate(sim.particles)],
    }
