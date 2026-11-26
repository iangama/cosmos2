"""Isolated exterior-J2 driver, deliberately separate from installed Session.

All bodies are active point masses. The additional potential sums the J2
contribution of each selected source against every other point mass. Forces
include equal and opposite linear reactions; symmetry axes remain prescribed.
No spin angular momentum, deformation, dissipation or interior model is used.
"""
from pathlib import Path
import copy
import hashlib
import json
import math
import uuid
import warnings

import rebound
from physics import PHYSICAL_SCALE
from j2_field import correction

POINTER_WARNING = 'You have to reset function pointers after creating a reb_simulation struct with a binary file.'
POLICY = ('Exterior J2 with prescribed inertial axes; linear reaction and quadrupole '
          'energy included; spin torque and material response not evolved. Full orbital '
          'angular momentum need not be conserved; an axial component is conserved '
          'only when all selected axes are parallel.')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def generation():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__), Path(__file__).with_name('j2_field.py'))}


def reset_pointers(action):
    """Handle only REBOUND's documented callback reset warning, reject all others."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        result = action()
    for warning in caught:
        if warning.category is not RuntimeWarning or str(warning.message) != POINTER_WARNING:
            raise ValueError('Unapproved REBOUND warning: ' + str(warning.message))
    return result


def settings(value, body_ids):
    if (not isinstance(body_ids, list) or not 2 <= len(body_ids) <= 128
            or any(not isinstance(x, str) or not x for x in body_ids)
            or len(set(body_ids)) != len(body_ids)):
        raise ValueError('Two to128 unique stable body IDs required')
    if not isinstance(value, list) or len(value) > 4:
        raise ValueError('At most four exterior J2 sources per candidate model')
    result = []
    used = set()
    for row in value:
        if not isinstance(row, dict) or set(row) != {'body_id', 'j2', 'radius_eq_m', 'axis', 'provenance'}:
            raise ValueError('Explicit J2 source, radius, axis and provenance required')
        if row['body_id'] not in body_ids or row['body_id'] in used:
            raise ValueError('J2 source must refer to one unique active stable ID')
        if (not isinstance(row['provenance'], str) or not 1 <= len(row['provenance'].strip()) <= 240
                or any(ord(c) < 32 for c in row['provenance'])):
            raise ValueError('J2 parameters require a bounded provenance description')
        radius = row['radius_eq_m']
        # This checks the same numeric domain as the field/force kernel.
        correction(1., radius, row['j2'], row['axis'], [radius, 0., 0.])
        norm = math.hypot(*row['axis'])
        result.append({**copy.deepcopy(row), 'axis': [v / norm for v in row['axis']]})
        used.add(row['body_id'])
    return result


def phase(sim):
    return {'time': sim.t, 'bodies': [[p.m, p.x, p.y, p.z, p.vx, p.vy, p.vz]
                                    for p in sim.particles]}


def validate_solver(sim, ids):
    if (sim.N != len(ids) or str(sim.integrator) != 'ias15'
            or not 0 < sim.integrator.epsilon <= 1e-9 or sim.G != 1.
            or str(sim.gravity) != 'basic' or str(sim.collision) != 'none'
            or sim.softening != 0. or sim.force_is_velocity_dependent != 0
            or sim.N_var != 0 or sim.N_active not in (2**64-1, sim.N)
            or sim.integrator.adaptive_mode != 'PRS23'):
        raise ValueError('Candidate requires isolated IAS15 active point-mass contract')
    for p in sim.particles:
        if (not 1e-12 <= p.m <= 100 or not all(math.isfinite(v) for v in
                (p.x, p.y, p.z, p.vx, p.vy, p.vz))):
            raise ValueError('Finite positive active masses and phase required')


class Driver:
    def __init__(self, sim, body_ids, configuration, *, reset_cache=True):
        checked = settings(configuration, body_ids)
        validate_solver(sim, body_ids)
        if bool(sim._additional_forces):
            raise ValueError('Cannot replace an unknown installed force callback')
        self.ids = list(body_ids)
        self.configuration = checked
        self.sim = reset_pointers(sim.copy)
        if reset_cache:
            epsilon = self.sim.integrator.epsilon
            self.sim.integrator = 'ias15'
            self.sim.integrator.epsilon = epsilon
        self.error = None
        self._terms(self.sim)  # Reject an initial interior point before attaching.
        self._attach(self.sim)
        self.reference_energy = self.energy()

    def _terms(self, sim):
        """Same SI kernel supplies quadrupole force and potential energy."""
        length = PHYSICAL_SCALE['length_unit_m']
        gm_unit = PHYSICAL_SCALE['nominal_GM_unit_m3_s2']
        acceleration_unit = gm_unit / length**2
        potential_unit = gm_unit / length
        ps = sim.particles
        accelerations = [[0., 0., 0.] for _ in self.ids]
        energies = []
        for row in self.configuration:
            i = self.ids.index(row['body_id'])
            source = ps[i]
            for j, target in enumerate(ps):
                if i == j:
                    continue
                delta = [target.x*length-source.x*length, target.y*length-source.y*length,
                         target.z*length-source.z*length]
                data = correction(source.m*gm_unit, row['radius_eq_m'], row['j2'],
                                  row['axis'], delta, tensor=False)
                for k in range(3):
                    a = data['acceleration_m_s2'][k] / acceleration_unit
                    accelerations[j][k] += a
                    accelerations[i][k] -= a * target.m / source.m
                energies.append(target.m * data['potential_J_kg'] / potential_unit)
        return accelerations, math.fsum(energies)

    def _attach(self, sim):
        def callback(pointer):
            current = pointer.contents
            if self.error:
                current.stop()
                return
            try:
                acceleration, _ = self._terms(current)
                for p, values in zip(current.particles, acceleration):
                    p.ax += values[0]
                    p.ay += values[1]
                    p.az += values[2]
            except Exception as error:
                # ctypes swallows uncaught Python exceptions. Always communicate
                # failure to the owner and stop the candidate integration.
                self.error = str(error)
                current.stop()
        sim.additional_forces = callback
        sim.force_is_velocity_dependent = 0

    def advance(self, target):
        if type(target) not in (int, float) or not math.isfinite(target) or target <= self.sim.t:
            raise ValueError('Finite forward target required')
        # Trial integration preserves the last confirmed phase and IAS15 cache
        # when an adaptive substage enters the invalid exterior domain.
        self.error = None
        trial = reset_pointers(self.sim.copy)
        self._attach(trial)
        trial.integrate(target)
        if self.error:
            raise ValueError('J2 exterior domain stopped before committing: ' + self.error)
        validate_solver(trial, self.ids)
        self._terms(trial)
        if trial.t != target:
            raise ValueError('Unconfirmed J2 integration target')
        self.sim = trial

    def energy(self):
        return self.sim.energy() + self._terms(self.sim)[1]

    def field_correction(self, body_id, point_m):
        row = next((row for row in self.configuration if row['body_id'] == body_id), None)
        if row is None:
            raise ValueError('Source is not configured for J2')
        p = self.sim.particles[self.ids.index(body_id)]
        length = PHYSICAL_SCALE['length_unit_m']
        return correction(p.m*PHYSICAL_SCALE['nominal_GM_unit_m3_s2'], row['radius_eq_m'],
                          row['j2'], row['axis'], [point_m[k]-v*length for k, v in enumerate((p.x,p.y,p.z))])

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        binary = directory / ('j2-' + uuid.uuid4().hex + '.bin')
        self.sim.save_to_file(str(binary))
        record = {'schema': 1, 'rebound': rebound.__version__, 'generation': generation(),
                  'ids': self.ids, 'configuration': self.configuration, 'binary': binary.name,
                  'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                  'phase': phase(self.sim), 'reference_energy': self.reference_energy,
                  'energy': self.energy(), 'policy': POLICY}
        record['receipt'] = digest(record)
        tmp = directory / 'latest.tmp'
        tmp.write_text(json.dumps(record, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        tmp.replace(directory / 'latest.json')
        return record

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        record = json.loads((directory / 'latest.json').read_text(encoding='utf-8'))
        if (set(record) != {'schema','rebound','generation','ids','configuration','binary',
                           'sha256','phase','reference_energy','energy','policy','receipt'}
                or record['schema'] != 1 or type(record['schema']) is not int
                or record['rebound'] != rebound.__version__ or record['generation'] != generation()
                or record['policy'] != POLICY
                or record['receipt'] != digest({k:v for k,v in record.items() if k != 'receipt'})):
            raise ValueError('Incompatible isolated J2 checkpoint')
        filename = record['binary']
        if (not isinstance(filename, str) or len(filename) != 39
                or not filename.startswith('j2-') or not filename.endswith('.bin')
                or any(c not in '0123456789abcdef' for c in filename[3:-4])):
            raise ValueError('Unsafe J2 binary basename')
        binary = directory / filename
        if hashlib.sha256(binary.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('J2 binary checksum mismatch')
        sim = reset_pointers(lambda: rebound.Simulation(str(binary)))
        if phase(sim) != record['phase']:
            raise ValueError('J2 phase receipt mismatch')
        candidate = cls(sim, record['ids'], record['configuration'], reset_cache=False)
        if candidate.energy() != record['energy']:
            raise ValueError('J2 energy receipt mismatch')
        if (type(record['reference_energy']) not in (int, float)
                or not math.isfinite(record['reference_energy'])):
            raise ValueError('J2 reference energy must be finite')
        candidate.reference_energy = record['reference_energy']
        return candidate
