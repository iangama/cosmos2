"""Read-only candidate reference API using the pinned minimal 599/5 subset."""
import copy
import hashlib
from pathlib import Path

import atlas
from solar_contract import ROOT, TARGETS, SUBSET, parameters, providers, capabilities, validate_catalog


def _coverage(path, target):
    cell = atlas.SPICE.spkcov(str(path), int(target))
    return [list(atlas.SPICE.wnfetd(cell, i)) for i in range(atlas.SPICE.wncard(cell))]


def _intersection(a, b):
    return [[max(x, z), min(y, w)] for x, y in a for z, w in b if max(x, z) <= min(y, w)]


def states(utc):
    with atlas.LOCK:
        atlas.initialize()
        et = float(atlas.SPICE.str2et(atlas.normalize_epoch(utc)))
        metadata = providers()  # Hashes checked before the additional kernel can affect the pool.
        start, end = [float(atlas.SPICE.str2et(t.removesuffix('Z')))
                      for t in metadata['10']['application_coverage_utc']]
        if not start <= et <= end:
            raise ValueError('Época fora da cobertura solar da aplicação.')
        epoch = {'utc': atlas.SPICE.et2utc(et, 'ISOC', 3) + 'Z', 'et_tdb_s': et,
                 'origin': 'explicit geometric coordinate epoch',
                 'utc_conversion': 'naif0012 fixed leap-second table; future leaps unknown; pre-1972 UTC follows SPICE convention'}
        subset = str(ROOT / SUBSET)
        atlas.SPICE.furnsh(subset)
        try:
            rows = []
            for target, name, frame in TARGETS:
                coverage = [[start, end]]
                chain = metadata[target]['chain_naif_ids']
                for link in chain[:-1]:
                    path = ROOT / SUBSET if link == '599' else ROOT / 'data/spice/de442s.bsp'
                    coverage = _intersection(coverage, _coverage(path, link))
                if not any(a <= et <= b for a, b in coverage):
                    raise ValueError('Época fora da cadeia de estados de ' + name)
                state, _ = atlas.SPICE.spkezr(target, et, 'J2000', 'NONE', '0')
                rows.append({
                    'id': 'sol:naif:' + target, 'naif_id': target, 'name': name, 'entity_kind': 'physical_body',
                    'position_m': (state[:3] * 1000).tolist(), 'velocity_m_s': (state[3:] * 1000).tolist(),
                    'GM': copy.deepcopy(parameters()[target]), 'state_provider': copy.deepcopy(metadata[target]),
                    'coverage_et_s': coverage,
                    'shape': {'value': None, 'reason': 'Geometria científica ainda não adotada para este cadastro; marcador gráfico separado.'},
                    'rotation': {'frame': frame, 'model': 'general PCK00011' if frame else None,
                                 'body_to_j2000': atlas.SPICE.pxform(frame, 'J2000', et).tolist() if frame else None,
                                 'precise_orientation': False,
                                 'reason': 'PCK geral; sem EOP/ITRF preciso e sem adoção das convenções magnéticas JRM33.'},
                    'capabilities': capabilities(target, epoch),
                })
            result = {'schema': 1, 'kind': 'solar_four_center_reference', 'version': '1.0.0',
                      'model': 'DE442s + original JUP365 planet599 subset', 'epoch': epoch,
                      'frame': 'J2000/ICRF', 'center_naif_id': '0', 'aberration': 'NONE',
                      'position_unit': 'm', 'velocity_unit': 'm/s', 'render_frame': 'GALACTIC',
                      'j2000_to_render_frame': atlas.SPICE.pxform('J2000', 'GALACTIC', et).tolist(),
                      'bodies': rows,
                      'provenance': {'origin': 'pinned geometric reference, not observations or an evolved experiment',
                                     'kernel_sha256': {p: sha for provider in metadata.values() for p, sha in provider['kernels_sha256'].items()},
                                     'catalog_code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                      'uncertainty': None, 'uncertainty_reason': 'Numerical agreement is not observational accuracy.'}
        finally:
            atlas.SPICE.unload(subset)
        return validate_catalog(result)
