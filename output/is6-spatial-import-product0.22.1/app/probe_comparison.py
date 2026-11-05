"""Two simultaneous probe readings, with explicit source-selection compatibility."""
import math
import numpy as np


def compare(reading, first_id, second_id):
    if not isinstance(first_id, str) or not isinstance(second_id, str) or first_id == second_id:
        raise ValueError('Selecione duas sondas distintas do mesmo instante.')
    rows = {r['id']: r for r in reading['readings']}
    if first_id not in rows or second_id not in rows:
        raise ValueError('Sonda não pertence a esta leitura confirmada.')
    a, b = rows[first_id], rows[second_id]
    if not a['available'] or not b['available']:
        raise ValueError('As duas sondas devem ter leituras disponíveis.')
    delta = [b['position_m'][k] - a['position_m'][k] for k in range(3)]
    dg = [b['acceleration_m_s2'][k] - a['acceleration_m_s2'][k] for k in range(3)]
    linear = [math.fsum(a['tidal_tensor_s_2'][j][k] * delta[k] for k in range(3)) for j in range(3)]
    residual = [dg[k] - linear[k] for k in range(3)]
    common = a['excluded_source_ids'] == b['excluded_source_ids']
    eigenvalues, eigenvectors = np.linalg.eigh(np.array(a['tidal_tensor_s_2']))
    # Eigenspaces can be degenerate. Axis sign and ordering within that space
    # are not physical choices; no deformation or torque is inferred here.
    return {**{k: reading[k] for k in ('system_id', 'edit_token', 'revision', 'time', 'frame', 'instruments_revision')},
            'first_id': first_id, 'second_id': second_id, 'displacement_m': delta,
            'distance_m': math.hypot(*delta), 'delta_acceleration_m_s2': dg,
            'delta_acceleration_norm_m_s2': math.hypot(*dg),
            'delta_potential_J_kg': b['potential_J_kg'] - a['potential_J_kg'],
            'same_included_sources': common, 'first_excluded_ids': a['excluded_source_ids'],
            'second_excluded_ids': b['excluded_source_ids'],
            'first_tidal_eigenvalues_s_2': eigenvalues.tolist(),
            'first_tidal_eigenvectors_columns': eigenvectors.tolist(),
            'linear_tidal_prediction_m_s2': linear if common else None,
            'linear_tidal_residual_m_s2': residual if common else None,
            'linear_tidal_residual_norm_m_s2': math.hypot(*residual) if common else None,
            'policy': 'difference of simultaneous confirmed accelerations; local T·dx is a first-order approximation only for identical included sources; eigen-axis signs are arbitrary; no material deformation'}
