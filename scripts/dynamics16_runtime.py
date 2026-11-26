"""Service adapter for the accepted, immutable sixteen-center Newtonian base."""
import copy
from functools import lru_cache
import hashlib
import math
from pathlib import Path

import system16_import as model
from physics import PHYSICAL_SCALE as U


def active(initial):
    return initial is not None and initial.get('kind') == model.KIND


@lru_cache(maxsize=1)
def extension():
    files = ['dynamics16_runtime.py', 'system16_import.py', 'system16_frames.py']
    return dict(id='is6-sixteen-center-dynamics', version='0.26.0',
                initial_format=model.KIND + '/' + model.VERSION,
                numerical_generation=model.generation(),
                code_sha256={n: hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in files},
                electromagnetic_coupling=False, nuclear_coupling=False)


def generation(base, initial):
    if not active(initial):
        return base
    return {**base, 'candidate_extension': copy.deepcopy(extension())}


def split_frame(initial, sim):
    if not active(initial):
        return None
    seconds = sim.t * U['time_unit_s']
    velocity = initial['inertial_origin_velocity_m_s']
    return dict(schema=1, encoding='split_inertial_origin', elapsed_s=seconds,
                initial_origin_m=list(initial['initial_ssb_origin_m']),
                origin_m=[x + v * seconds for x, v in zip(initial['initial_ssb_origin_m'], velocity)],
                origin_velocity_m_s=list(velocity),
                local_frame=initial['contract']['frame'], world_frame='SSB/J2000',
                meaning='World position = origin_m + local_position*length_unit_m; components remain separate from the solver.')


def metadata(initial, sim, revision):
    if not active(initial):
        return None
    return dict(model_id=extension()['numerical_generation']['model_id'],
                initial_format=model.KIND + '/' + model.VERSION,
                initial_body_count=16, active_body_count=sim.N,
                epoch=copy.deepcopy(initial['source']['epoch']),
                elapsed_s=sim.t * U['time_unit_s'], revision=revision,
                inertial_frame=split_frame(initial, sim),
                electromagnetic_coupling=False, nuclear_coupling=False,
                excluded_influences=list(model.EXCLUDED),
                evolution='IAS15 Newtonian point masses; ephemerides initialize the model only',
                mass_meaning='Model mass derived from source GM/G, with unknown source uncertainty; edits are external interventions.')


def create(request, laboratory, atlas):
    if not isinstance(request, dict) or set(request) != {'utc'} or not isinstance(request['utc'], str):
        raise ValueError('A cópia de16centros aceita somente uma época UTC; estados e GM vêm do catálogo fixado.')
    if laboratory.status()['mode'] != 'atlas':
        raise ValueError('Volte ao Atlas antes de criar outra cópia dos16centros.')
    reference = model.catalog.states(utc=request['utc'])
    confirmed = atlas.status()['epoch']
    if reference['epoch']['et_tdb_s'] != confirmed['et_tdb_s']:
        raise ValueError('A época do Atlas mudou; confirme a época exibida antes de criar a cópia.')
    initial = model.prepare(reference)
    return laboratory.command(dict(command='import_atlas', initial_state=initial))


def reading(session, request):
    session._expect(request)
    required = {'system_id', 'edit_token', 'revision', 'expected_time', 'frame', 'body_id'}
    if not required <= set(request) or set(request) - required - {'command', 'id'}:
        raise ValueError('A contribuição dos16centros exige identidade, fase e corpo, sem campos extras.')
    if not active(session.atlas_initial):
        raise ValueError('Abra a cópia dos16centros para consultar este instrumento.')
    bodies = session._physical_bodies()
    selected = next((b for b in bodies if b['id'] == request['body_id']), None)
    if selected is None:
        raise ValueError('Corpo selecionado não está ativo.')
    # Subtract local solver coordinates before converting to SI. Never combine
    # the large SSB origin with the phase to recover a small relative vector.
    relative = [{**b, 'position': [b['position'][k] - selected['position'][k] for k in range(3)]}
                for b in bodies if b['id'] != selected['id']]
    from gravity_field import evaluate
    result = evaluate(relative, [0., 0., 0.])
    names = {b['id']: b for b in session.registry}
    for row in result['sources']:
        row.update(name=names[row['id']]['name'], reference_id=names[row['id']].get('reference_id'))
    return {**result, 'schema': 1, 'kind': 'sixteen_center_gravity_reading',
            'position_m': [v * U['length_unit_m'] for v in selected['position']],
            'system_id': session.system_id, 'edit_token': session.edit_token,
            'revision': session.revision, 'time': session.sim.t, 'body_id': selected['id'],
            'frame': session.contract()['frame'],
            'epoch_et_tdb_s': session.atlas_initial['source']['epoch']['et_tdb_s'] + session.sim.t * U['time_unit_s'],
            'scientific_generation': session.scientific_generation(),
            'scope': 'External active Newtonian sources at the selected center; singular self field omitted; no EM or nuclear coupling.'}
