"""Passive population lifecycle; active-source registry and conservation stay separate."""
import copy
import hashlib
import math
import re
from pathlib import Path

from cloud_driver import Driver, VERSION, settings
from physics import PHYSICAL_SCALE as U

POLICY = ('One active Newtonian source plus massless test particles in one IAS15; '
          'no test-test force or backreaction. Source mirror is never independently advanced. '
          'Synthetic circular annulus, not observed matter or an interacting plasma.')
_ORIGIN_KEYS = ('model', 'source_id', 'configuration', 'epoch', 'initial_source')


def identity(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value):
        raise ValueError('Identidade de nuvem inválida.')
    return value


class Cloud:
    def __init__(self, mirror, source_id, configuration, cloud_id):
        self.id = identity(cloud_id)
        self.driver = Driver(mirror, source_id, configuration)

    @classmethod
    def restore(cls, mirror, source_id, descriptor, directory):
        if not isinstance(descriptor, dict) or set(descriptor) != {'schema','cloud_id','binary','driver'} or type(descriptor['schema']) is not int or descriptor['schema'] != 1:
            raise ValueError('Declaração de checkpoint da nuvem inválida.')
        name = descriptor['binary']
        if not isinstance(name, str) or not re.fullmatch(r'[0-9a-f]{32}\.cloud\.bin', name):
            raise ValueError('Nome de arquivo binário da nuvem inválido.')
        path = Path(directory)/name
        if not 1 <= path.stat().st_size <= 100_000_000:
            raise ValueError('Tamanho de checkpoint da nuvem inválido.')
        result = object.__new__(cls)
        result.id = identity(descriptor['cloud_id'])
        result.driver = Driver.restore(mirror, source_id, descriptor['driver'], path.read_bytes())
        return result

    def check(self):
        identity(self.id)
        self.driver.check()

    def origin(self):
        d = self.driver
        return {'cloud_id':self.id, 'model':VERSION, 'source_id':d.source_id,
                'configuration':copy.deepcopy(d.configuration), 'epoch':d.epoch,
                'initial_source':copy.deepcopy(d.initial_source)}

    def save(self, destination, identifier):
        metadata, binary = self.driver.checkpoint()
        name = identity(identifier)+'.cloud.bin'
        # A unique unreferenced binary is complete before latest.json is replaced.
        with (Path(destination)/name).open('xb') as stream:
            stream.write(binary)
        return {'schema':1, 'cloud_id':self.id, 'binary':name, 'driver':metadata}

    def public(self):
        return {**self.driver.public(), 'cloud_id':self.id, 'policy':POLICY,
                'particle_ids':'tp:'+self.id+':index0..count-1',
                'conservation_scope':'active source only; test particles have specific energy/angular momentum',
                'phase_transport':'separate confirmed binary packet; no per-particle JSON in snapshots'}

    def point(self, index, frame, system_id, edit_token):
        p = self.driver.point(index)
        u = U['velocity_unit_m_s']
        return {'schema':1, 'id':'tp:'+self.id+':'+str(index), 'index':index,
                'cloud_id':self.id, 'system_id':system_id, 'edit_token':edit_token,
                'source_id':self.driver.source_id, 'role':'massless_test_particle',
                'mass_kg':0., 'time_model':p['time'], 'time_s':p['time']*U['time_unit_s'],
                'frame':frame, 'position_m':[x*U['length_unit_m'] for x in p['position']],
                'velocity_m_s':[x*u for x in p['velocity']],
                'specific_energy_J_kg':p['specific_energy']*u*u,
                'specific_angular_momentum_m2_s':[x*u*U['length_unit_m'] for x in p['specific_angular_momentum']],
                'specific_integral_frame':'relative to the inertially moving active source',
                'observational_source':None}


def public(cloud):
    return None if cloud is None else cloud.public()


def contract(base, active):
    if not active:
        return base
    return {**base, 'test_cloud_base_contract':copy.deepcopy(base),
            'test_particle_policy':POLICY, 'test_particle_model':VERSION}


def base_contract(value):
    return copy.deepcopy(value.get('test_cloud_base_contract', value))


def replay(manifest, events, registry, original_ids):
    active = None
    ids = list(original_ids)
    seen = set()
    for event in events:
        kind = event['type']
        if kind == 'set_cloud':
            if event.get('old_cloud_origin') != active:
                raise ValueError('Histórico da nuvem difere da origem anterior.')
            new = event.get('new_cloud_origin')
            if new is not None:
                if active is not None or not isinstance(new, dict) or set(new) != {'cloud_id', *_ORIGIN_KEYS}:
                    raise ValueError('Ativação de nuvem incompatível.')
                identity(new['cloud_id'])
                if new['cloud_id'] in seen or new['model'] != VERSION or new['source_id'] != event['body'] or ids != [event['body']] or new['epoch'] != event['time']:
                    raise ValueError('Identidade/época da nuvem incompatível com a intervenção.')
                settings(new['configuration'])
                source = new['initial_source']
                if not isinstance(source,list) or len(source)!=7 or any(type(x) not in (int,float) or not math.isfinite(x) for x in source):
                    raise ValueError('Fase inicial da fonte da nuvem inválida.')
                seen.add(new['cloud_id'])
            elif active is None:
                raise ValueError('Não há nuvem para desativar.')
            if event.get('external_energy_delta') != 0 or event.get('external_momentum_delta') != [0.,0.,0.]:
                raise ValueError('Partículas sem massa não podem injetar energia/momento nas fontes.')
            active = copy.deepcopy(new)
        elif active is not None and kind in ('set_mass','set_body_si','create_body','remove_body','set_j2','set_tides'):
            raise ValueError('Fonte ou força alterada sem desativar a nuvem de teste.')
        if kind == 'create_body':
            ids.append(event['body'])
        elif kind == 'remove_body':
            ids.remove(event['body'])
    modern = manifest['saved_generation']['model_version'] == '3.13.0'
    if modern and 'test_particle_cloud' not in manifest:
        raise ValueError('Declaração de nuvem ausente no checkpoint3.13.')
    saved = manifest.get('test_particle_cloud')
    if not modern and (saved is not None or active is not None):
        raise ValueError('Geração anterior não declara nuvem de teste.')
    if (saved is None) != (active is None):
        raise ValueError('Checkpoint da nuvem difere do histórico de intervenções.')
    if saved is not None:
        if not isinstance(saved,dict) or not isinstance(saved.get('driver'),dict):
            raise ValueError('Checkpoint da nuvem inválido.')
        origin = {'cloud_id':saved.get('cloud_id'), **{k:saved['driver'].get(k) for k in _ORIGIN_KEYS}}
        if origin != active or ids != [active['source_id']] or len(registry) != 1:
            raise ValueError('Origem da nuvem incompatível com a fonte ativa.')
    return saved
