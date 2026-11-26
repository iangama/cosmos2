"""Transactional SI interventions for the isolated EM 0.2 experiment.

Mechanical matter energy only: fixed source reservoirs, field energy, induction
and radiation are outside this model. Visual changes never reset diagnostics.
"""
from copy import deepcopy
from dataclasses import asdict
import math
import numpy as np
from em_fields import Model, Source, scalar, lorentz
from em_particles import Phase as TestPhase, boris_step
from em_mutual import System, Phase as MutualPhase

FRAME = 'EM_SI_FIXED_INERTIAL'
MAX_INTERVENTIONS = 64
UNITS = {'mechanical_energy_J': 'J', 'total_charge_C': 'C',
         'momentum_kg_m_s': 'kg m/s', 'angular_momentum_kg_m2_s': 'kg m²/s'}
OMITTED = 'fixed-source reservoirs, field energy, induced E and radiation'


def diagnostics(experiment):
    """Position and velocity refer to the same full-step time and fixed origin."""
    ex = experiment
    if ex.mode == 'test_particle':
        reading = lorentz(ex.model, ex.phase.position_m, ex.phase.velocity_m_s,
                          ex.charge_C, ex.mass_kg, **ex.controls)
        if not reading['valid']:
            raise ValueError('Diagnostic outside prescribed-source domain')
        p = np.array(ex.phase.velocity_m_s) * ex.mass_kg
        angular = np.cross(ex.phase.position_m, p)
        kinetic = .5 * ex.mass_kg * math.fsum(v*v for v in ex.phase.velocity_m_s)
        potential = ex.charge_C * reading['reference']['electric_potential_V'] if ex.controls['electric_acting'] else 0.
        fixed_charge = math.fsum(s.charge_C for s in ex.model.sources)
        moving_charge = ex.charge_C
    else:
        d = ex.model.diagnostics(ex.phase)
        kinetic = d['kinetic_J']
        potential = d['potential_J'] if ex.controls['acting'] else 0.
        p, angular = d['momentum_kg_m_s'], d['angular_momentum_kg_m2_s']
        fixed_charge = 0.
        moving_charge = math.fsum(ex.model.charge_C)
    result = {'kinetic_energy_J': kinetic, 'potential_energy_J': potential,
              'mechanical_energy_J': kinetic + potential,
              'total_charge_C': math.fsum((moving_charge, fixed_charge)),
              'moving_charge_C': moving_charge, 'fixed_source_charge_C': fixed_charge,
              'momentum_kg_m_s': list(p), 'angular_momentum_kg_m2_s': list(angular)}
    finite_tree(result)
    return result


def identities(ex):
    return [s.id for s in ex.model.sources] if ex.mode == 'test_particle' else list(ex.model.ids)


def default_editor(ex):
    return {'physics_revision': 0, 'interventions': [], 'dropped_interventions': 0,
            'origins': {i: 'synthetic_preset' for i in identities(ex)},
            'background_origin': 'synthetic_preset', 'particle_origin': 'synthetic_preset',
            'visual': {'electric_visible': True, 'magnetic_visible': True, 'selected_id': None,
                       'map_radius_m': 3., 'map_cut_z_m': 0., 'azimuth_rad': .6, 'elevation_rad': .4},
            'reference': {'time_s': ex.phase.time_s, 'physics_revision': 0, 'diagnostics': diagnostics(ex)},
            'migration': None}


def finite_tree(value, depth=0):
    if depth > 20:
        raise ValueError('Overly nested editor record')
    if type(value) is float and not math.isfinite(value):
        raise ValueError('Nonfinite editor record')
    if isinstance(value, dict):
        for v in value.values(): finite_tree(v, depth+1)
    elif isinstance(value, (list, tuple)):
        for v in value: finite_tree(v, depth+1)


def validate_diagnostics(value):
    expected = {'kinetic_energy_J', 'potential_energy_J', 'mechanical_energy_J', 'total_charge_C',
                'moving_charge_C', 'fixed_source_charge_C', 'momentum_kg_m_s', 'angular_momentum_kg_m2_s'}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('Exact mechanical diagnostic set required')
    from em_fields import vector
    for key, entry in value.items():
        vector(entry) if key in ('momentum_kg_m_s', 'angular_momentum_kg_m2_s') else scalar(entry)


def validate_migration(value,depth=0):
    if value is None:return
    if depth>=8 or not isinstance(value,dict) or type(value.get('schema')) is not int or value['schema'] not in (1,2):raise ValueError('Invalid EM migration lineage')
    expected={'schema','generation','source_sha256'}|({'previous'} if value['schema']==2 else set())
    if set(value)!=expected or not isinstance(value['generation'],dict) or not isinstance(value['source_sha256'],str) or len(value['source_sha256'])!=64 or any(c not in '0123456789abcdef' for c in value['source_sha256']):raise ValueError('Invalid EM migration provenance')
    if value['schema']==2:validate_migration(value['previous'],depth+1)


def validate_editor(ex, value):
    expected = set(default_editor(ex))
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('Unknown EM editor fields')
    finite_tree(value)
    rev, dropped = value['physics_revision'], value['dropped_interventions']
    if type(rev) is not int or rev < 0 or type(dropped) is not int or dropped < 0:
        raise ValueError('Nonnegative editor revision and history count required')
    if not isinstance(value['origins'], dict) or set(value['origins']) != set(identities(ex)) or any(
            v not in ('synthetic_preset', 'user_model') for v in value['origins'].values()):
        raise ValueError('One declared origin per identity required')
    if any(value[k] not in ('synthetic_preset', 'user_model') for k in ('background_origin', 'particle_origin')):
        raise ValueError('Declared model origins required')
    visual = value['visual']
    if not isinstance(visual, dict) or set(visual) != set(default_editor(ex)['visual']):
        raise ValueError('Exact EM visual configuration required')
    if any(type(visual[k]) is not bool for k in ('electric_visible', 'magnetic_visible')):
        raise ValueError('Boolean E/B visibility required')
    selected = visual['selected_id']
    if selected is not None and (not isinstance(selected, str) or selected not in identities(ex)):
        raise ValueError('Selected source must exist')
    for k in ('map_radius_m', 'map_cut_z_m', 'azimuth_rad', 'elevation_rad'): scalar(visual[k])
    if not 0 < visual['map_radius_m'] <= 1e9 or abs(visual['map_cut_z_m']) > 1e9 or abs(visual['azimuth_rad']) > 1e6 or abs(visual['elevation_rad']) > 1.4:
        raise ValueError('Visual coordinates outside supported domain')
    ref = value['reference']
    if not isinstance(ref, dict) or set(ref) != {'time_s', 'physics_revision', 'diagnostics'} or ref['physics_revision'] != rev or type(ref['physics_revision']) is not int or not 0 <= scalar(ref['time_s']) <= ex.phase.time_s:
        raise ValueError('Invalid conservation reference')
    validate_diagnostics(ref['diagnostics'])
    history = value['interventions']
    if not isinstance(history, list) or len(history) > MAX_INTERVENTIONS or dropped + len(history) != rev:
        raise ValueError('Bounded consecutive intervention history required')
    previous_time = 0.
    for index, event in enumerate(history, dropped+1):
        keys = {'command', 'time_s', 'revision_before', 'revision_after', 'frame', 'affected_ids',
                'values_before', 'values_after', 'diagnostics_before', 'diagnostics_after', 'delta', 'units', 'scope'}
        if not isinstance(event, dict) or set(event) != keys or event['frame'] != FRAME or event['units'] != UNITS or event['scope'] != OMITTED:
            raise ValueError('Invalid intervention envelope')
        if type(event['revision_after']) is not int or type(event['revision_before']) is not int or event['revision_after'] != index or event['revision_before'] != index-1:
            raise ValueError('Discontinuous intervention revisions')
        t = scalar(event['time_s'])
        if not previous_time <= t <= ex.phase.time_s: raise ValueError('Invalid intervention time')
        previous_time = t
        if not isinstance(event['command'], dict) or event['command'].get('operation') not in OPERATIONS:
            raise ValueError('Unknown recorded edit command')
        if not isinstance(event['affected_ids'], list) or len(event['affected_ids']) > 1 or any(not isinstance(i, str) or not 1 <= len(i) <= 128 for i in event['affected_ids']):
            raise ValueError('Bounded affected identity required')
        for key in ('values_before', 'values_after'):
            if not isinstance(event[key], dict): raise ValueError('Explicit before/after values required')
        for key in ('diagnostics_before', 'diagnostics_after'): validate_diagnostics(event[key])
        if event['delta'] != differences(event['diagnostics_before'], event['diagnostics_after']):
            raise ValueError('Intervention delta does not match diagnostics')
    if history and (history[-1]['diagnostics_after'] != ref['diagnostics'] or history[-1]['time_s'] != ref['time_s']):
        raise ValueError('Reference must match last physical intervention')
    migration = value['migration']
    validate_migration(migration)
    return deepcopy(value)


def differences(before, after):
    result = {}
    for key in UNITS:
        a, b = before[key], after[key]
        result[key] = [y-x for x,y in zip(a,b)] if isinstance(a, list) else b-a
    finite_tree(result)
    return result


OPERATIONS = {'create_source', 'update_source', 'remove_source', 'set_background',
              'update_test_particle', 'create_body', 'update_body', 'remove_body', 'set_controls'}


def exact_keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('Exact edit command fields required')


def patch_fields(value, allowed):
    if not isinstance(value, dict) or not value or not set(value) <= set(allowed):
        raise ValueError('Nonempty supported property patch required')


def apply_intervention(ex, request):
    """Build a complete candidate; never mutate ex, including on validation errors."""
    from em_experiment import Experiment
    if not isinstance(request, dict) or request.get('operation') not in OPERATIONS:
        raise ValueError('Unknown EM edit operation')
    op = request['operation']; data = deepcopy(ex.payload()); affected = []; before = {}; after = {}
    editor = deepcopy(ex.editor)
    if op == 'set_controls':
        exact_keys(request, ('operation', 'controls'))
        before = {'controls': data['controls']}; data['controls'] = deepcopy(request['controls']); after = {'controls': data['controls']}
    elif ex.mode == 'test_particle':
        sources = data['model']['sources'] = list(data['model']['sources'])
        if op in ('create_source', 'update_source', 'remove_source'):
            if op == 'create_source':
                exact_keys(request, ('operation', 'source'))
                source = asdict(Source(**request['source'])); sid = source['id']
                if sid in identities(ex): raise ValueError('Source identity already exists')
                sources.append(source); after = source
            else:
                exact_keys(request, ('operation', 'id', 'changes') if op == 'update_source' else ('operation', 'id'))
                sid = request['id']
                if sid not in identities(ex): raise ValueError('Unknown source identity')
                index = identities(ex).index(sid); before = sources[index]
                if op == 'remove_source': sources.pop(index)
                else:
                    patch_fields(request['changes'], ('position_m', 'charge_C', 'magnetic_moment_A_m2', 'exclusion_radius_m'))
                    after = asdict(Source(**(before | request['changes']))); sources[index] = after
            affected = [sid]
            if op == 'remove_source': editor['origins'].pop(sid)
            else: editor['origins'][sid] = 'user_model'
        elif op == 'set_background':
            exact_keys(request, ('operation', 'changes'))
            patch_fields(request['changes'], ('uniform_E_V_m', 'uniform_B_T'))
            before = {k: data['model'][k] for k in request['changes']}
            data['model'].update(deepcopy(request['changes'])); after = {k: data['model'][k] for k in request['changes']}
            editor['background_origin'] = 'user_model'
        elif op == 'update_test_particle':
            exact_keys(request, ('operation', 'changes'))
            patch_fields(request['changes'], ('position_m', 'velocity_m_s', 'charge_C', 'mass_kg'))
            before = dict(data['particle']) | {k: data['phase'][k] for k in ('position_m', 'velocity_m_s')}
            after = before | deepcopy(request['changes'])
            for k in ('charge_C', 'mass_kg'): data['particle'][k] = after[k]
            for k in ('position_m', 'velocity_m_s'): data['phase'][k] = after[k]
            editor['particle_origin'] = 'user_model'
        else: raise ValueError('Active-body operations require mutual electrostatics')
    else:
        if op not in ('create_body', 'update_body', 'remove_body'):
            raise ValueError('Prescribed-source operations require test-particle mode')
        bodies = [dict(id=sid, charge_C=q, mass_kg=m, exclusion_radius_m=r, position_m=x, velocity_m_s=v)
                  for sid,q,m,r,x,v in zip(ex.model.ids, ex.model.charge_C, ex.model.mass_kg,
                    ex.model.exclusion_radius_m, ex.phase.position_m, ex.phase.velocity_m_s)]
        if op == 'create_body':
            exact_keys(request, ('operation', 'body')); exact_keys(request['body'], bodies[0].keys())
            after = deepcopy(request['body']); sid = after['id']
            if sid in ex.model.ids: raise ValueError('Charge identity already exists')
            bodies.append(after)
        else:
            exact_keys(request, ('operation', 'id', 'changes') if op == 'update_body' else ('operation', 'id'))
            sid = request['id']
            if sid not in ex.model.ids: raise ValueError('Unknown active charge')
            index = ex.model.ids.index(sid); before = bodies[index]
            if op == 'remove_body': bodies.pop(index)
            else:
                patch_fields(request['changes'], set(before)-{'id'})
                after = before | deepcopy(request['changes']); bodies[index] = after
        affected = [sid]
        if op == 'remove_body': editor['origins'].pop(sid)
        else: editor['origins'][sid] = 'user_model'
        data['system'] = {k: [b[('id' if k == 'ids' else k)] for b in bodies] for k in ('ids', 'charge_C', 'mass_kg', 'exclusion_radius_m')}
        for k in ('position_m', 'velocity_m_s'): data['phase'][k] = [b[k] for b in bodies]
    trial = Experiment.from_payload(data)
    # Verify representable diagnostics and one proposed next step without committing it.
    if trial.mode == 'test_particle':
        boris_step(trial.model, trial.phase, trial.charge_C, trial.mass_kg, trial.dt_s, **trial.controls)
    else: trial.model.step(trial.phase, trial.dt_s, **trial.controls)
    d0, d1 = diagnostics(ex), diagnostics(trial)
    if trial.payload() == ex.payload(): raise ValueError('Edit has no physical change')
    revision = editor['physics_revision']+1
    event = {'command': deepcopy(request), 'time_s': ex.phase.time_s,
             'revision_before': revision-1, 'revision_after': revision, 'frame': FRAME,
             'affected_ids': affected, 'values_before': deepcopy(before), 'values_after': deepcopy(after),
             'diagnostics_before': d0, 'diagnostics_after': d1, 'delta': differences(d0, d1),
             'units': dict(UNITS), 'scope': OMITTED}
    editor['physics_revision'] = revision; editor['interventions'].append(event)
    if len(editor['interventions']) > MAX_INTERVENTIONS:
        editor['interventions'].pop(0); editor['dropped_interventions'] += 1
    editor['reference'] = {'time_s': trial.phase.time_s, 'physics_revision': revision, 'diagnostics': d1}
    if editor['visual']['selected_id'] not in identities(trial): editor['visual']['selected_id'] = None
    trial.editor = validate_editor(trial, editor)
    return trial


def apply_visual(ex, changes):
    patch_fields(changes, ex.editor['visual'])
    trial = deepcopy(ex.editor); trial['visual'].update(deepcopy(changes))
    ex.editor = validate_editor(ex, trial)
