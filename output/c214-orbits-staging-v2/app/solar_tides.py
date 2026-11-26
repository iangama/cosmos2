"""Passive external differential gravity, in the snapshot's inertial J2000 axes."""
import math


def guarded_read(snapshot, request):
    required = {'system_id', 'edit_token', 'revision', 'expected_time', 'frame', 'body_id', 'offset_m'}
    if not isinstance(request, dict) or set(request) != required:
        raise ValueError('Pedido de maré incompleto ou com campos desconhecidos.')
    if request['system_id'] != snapshot['system_id'] or request['edit_token'] != snapshot['edit_token']:
        raise ValueError('A sessão foi reiniciada ou restaurada.')
    if type(request['revision']) is not int or request['revision'] != snapshot['revision']:
        raise ValueError('Revisão obsoleta.')
    time = request['expected_time']
    if type(time) not in (int, float) or not math.isfinite(time) or time != snapshot['time']:
        raise ValueError('Instante obsoleto ou inválido.')
    if request['frame'] != snapshot['contract']['frame']:
        raise ValueError('Referencial incompatível.')
    return evaluate(snapshot, request['body_id'], request['offset_m'])


def evaluate(snapshot, body_id, offset_m):
    if snapshot['contract']['model'] != 'newtonian_point_masses' or snapshot['contract']['frame'] != 'initial_subset_barycenter_inertial_axes_J2000':
        raise ValueError('Modelo ou referencial não contemplado.')
    if snapshot.get('gravity_effects') or snapshot.get('material_tides'):
        raise ValueError('Este instrumento contempla apenas monopolos.')
    if not isinstance(offset_m, list) or len(offset_m) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in offset_m) or math.hypot(*offset_m) > 1e12:
        raise ValueError('Deslocamento SI inválido ou fora do domínio.')
    bodies = snapshot['bodies']
    selected = next((b for b in bodies if b['id'] == body_id), None)
    if selected is None:
        raise ValueError('Centro desconhecido.')
    length = snapshot['physical_scale']['length_unit_m']
    gm_unit = snapshot['physical_scale']['nominal_GM_unit_m3_s2']
    rows = []
    for source in bodies:
        if source['id'] == body_id:
            continue
        delta = [(source['position'][k]-selected['position'][k])*length for k in range(3)]
        local = [delta[k]-offset_m[k] for k in range(3)]
        radius, local_radius = math.hypot(*delta), math.hypot(*local)
        if min(radius, local_radius) < .001:
            raise ValueError('Leitura no domínio singular de uma fonte externa.')
        gm = source['mass']*gm_unit
        eps = math.fsum(offset_m[k]**2-2*delta[k]*offset_m[k] for k in range(3))/radius**2
        if eps > -.5:
            factor_minus_one = math.expm1(-1.5*math.log1p(eps))
            exact = [gm/radius**3*(delta[k]*factor_minus_one-offset_m[k]*(1+factor_minus_one)) for k in range(3)]
        else:
            exact = [gm*(local[k]/local_radius**3-delta[k]/radius**3) for k in range(3)]
        projection = math.fsum(delta[k]*offset_m[k] for k in range(3))/radius**2
        linear = [gm/radius**3*(3*delta[k]*projection-offset_m[k]) for k in range(3)]
        rows.append({'id': source['id'], 'reference_id': source.get('reference_id'),
                     'exact_m_s2': exact, 'linear_m_s2': linear,
                     'nonlinear_residual_m_s2': [exact[k]-linear[k] for k in range(3)]})
    return {'schema': 1, 'kind': 'external_monopole_tide', 'body_id': body_id,
            **{k: snapshot[k] for k in ['system_id', 'edit_token', 'revision', 'time']},
            'frame': snapshot['contract']['frame'], 'offset_m': list(offset_m),
            'epoch_et_tdb_s': snapshot['atlas_initial']['source']['epoch']['et_tdb_s']+snapshot['time']*snapshot['physical_scale']['time_unit_s'],
            'sources': rows, 'excluded_source_ids': [body_id],
            'exact_m_s2': [math.fsum(row['exact_m_s2'][k] for row in rows) for k in range(3)],
            'linear_m_s2': [math.fsum(row['linear_m_s2'][k] for row in rows) for k in range(3)],
            'scope': 'External acceleration at offset minus external acceleration at center; passive monopoles only. No deformation or ocean response.'}
