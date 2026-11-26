"""Pinned geometric reference states for eight physical planets, Sun and seven moons."""
import copy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

import atlas
from solar_catalog import _coverage, _intersection

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
DATA = ROOT / 'output/is6-principal-moons-model-20261111a/catalog-data.json'
DATA_SHA256 = 'a4d07b2c9da66036740ad0f40a2427e41c813e2f7805a48950229f020cd4048d'
MODELS = {'499': 'MAR099', '599': 'JUP365', '699': 'SAT441',
          '799': 'URA182', '899': 'NEP097', '501': 'JUP365', '502': 'JUP365', '503': 'JUP365',
          '504': 'JUP365', '602': 'SAT441', '606': 'SAT441'}


@lru_cache(maxsize=64)
def _verify(relative, expected, size, modified_ns, changed_ns):
    path = ROOT / relative
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != expected:
        raise ValueError('Fonte do catálogo difere da geração fixada: ' + relative)
    stat = path.stat()
    if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != (size, modified_ns, changed_ns):
        raise ValueError('Fonte do catálogo mudou durante a verificação: ' + relative)


def _data():
    raw = DATA.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATA_SHA256:
        raise ValueError('Metadados do catálogo diferem da geração fixada.')
    result = json.loads(raw)
    for relative, expected in result['runtime_sha256'].items():
        stat = (ROOT / relative).stat()
        _verify(relative, expected, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    return result


def capabilities(target):
    magnetic = {'399': 'IGRF14', '599': 'JRM33'}.get(target)
    return {
        'gravity': dict(status='available_reference', model='Geometric state and physical-body GM'),
        'magnetism': dict(status='available_bench' if magnetic else 'unavailable', model=magnetic,
                          reason='Instrumento próprio com domínio e época específicos.' if magnetic
                          else 'Modelo magnético ainda sem adoção para este corpo neste catálogo.'),
        'strong_processes': dict(status='available_bench', model='pp/CNO' if target == '10' else 'nuclear reference benches',
                                reason='Processos e composição pertencem ao instrumento escolhido.'),
        'weak_processes': dict(status='available_bench', model='pp/CNO and beta decay' if target == '10' else 'beta decay',
                              reason='Inventário isotópico do corpo ainda sem adoção.'),
    }


def states(utc=None, et=None):
    if utc is not None and et is not None:
        raise ValueError('Escolha uma época UTC ou ET/TDB.')
    normalized = None
    if utc is not None:
        normalized = atlas.normalize_epoch(utc)
    elif type(et) not in (int, float) or not math.isfinite(et):
        raise ValueError('Informe uma época UTC ou ET/TDB finita.')
    with atlas.LOCK:
        data = _data()
        atlas.initialize()
        spice = atlas.SPICE
        et = float(spice.str2et(normalized)) if normalized is not None else float(et)
        start, end = [float(spice.str2et(t)) for t in data['application_utc']]
        if not start <= et <= end:
            raise ValueError('Catálogo ampliado disponível de 01/01/1995 a 30/12/2049.')
        epoch = dict(utc=spice.et2utc(et, 'ISOC', 3) + 'Z', et_tdb_s=et,
                     utc_conversion='naif0012 fixed leap-second table; future leap seconds unknown')
        before = {Path(spice.kdata(i, 'SPK')[0]).resolve() for i in range(spice.ktotal('SPK'))}
        loaded = []
        try:
            for relative in data['extra_spk']:
                path = ROOT / relative
                if path.resolve() not in before:
                    spice.furnsh(str(path))
                    loaded.append(path)
            render = spice.pxform('J2000', 'GALACTIC', et)
            bodies = []
            for item in data['bodies']:
                target = item['naif_id']
                coverage = [[start, end]]
                for index, link in enumerate(item['chain_naif_ids'][:-1]):
                    path = ROOT / (item['relative_kernel'] if index == 0 else 'data/spice/de442s.bsp')
                    coverage = _intersection(coverage, _coverage(path, link))
                if not any(a <= et <= b for a, b in coverage):
                    raise ValueError('Época fora da cadeia de estados de ' + item['name'])
                vector, _ = spice.spkezr(target, et, 'J2000', 'NONE', '0')
                frame = item['rotation_frame']
                bodies.append(dict(
                    id=item['id'], naif_id=target, scene_node=item['node'], name=item['name'],
                    entity_kind=item['entity_kind'], body_kind=item['body_kind'],
                    position_m=(vector[:3] * 1000).tolist(), velocity_m_s=(vector[3:] * 1000).tolist(),
                    position_render_m=(render @ vector[:3] * 1000).tolist(),
                    GM=copy.deepcopy(item['GM']), coverage_et_s=coverage,
                    state_provider=dict(chain_naif_ids=item['chain_naif_ids'],
                                        model=MODELS.get(target, 'DE442s'),
                                        relative_kernel=item['relative_kernel']),
                    shape=dict(radii_m=(spice.bodvrd(target, 'RADII', 3)[1] * 1000).tolist(),
                               model='PCK00011 reference radii', frame=frame),
                    rotation=dict(frame=frame, body_to_j2000=spice.pxform(frame, 'J2000', et).tolist() if frame else None,
                                  model='PCK00011 general IAU rotation' if frame else None,
                                  precise_orientation=False),
                    capabilities=capabilities(target)
                ))
            return dict(
                schema=1, kind='eight_planets_and_principal_moons_geometric_reference', version='0.3.0',
                epoch=epoch, frame='J2000/ICRF', center_naif_id='0', aberration='NONE',
                position_unit='m', velocity_unit='m/s', render_frame='GALACTIC',
                j2000_to_render_frame=render.tolist(), bodies=bodies,
                application_coverage_utc=[t + 'Z' for t in data['application_utc']],
                provenance=dict(data_sha256=DATA_SHA256,
                                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                kernels_sha256={p: seal for p, seal in data['runtime_sha256'].items()
                                                if p.endswith(('.bsp', '.tls', '.tpc'))},
                                toolkit=spice.tkvrsn('TOOLKIT')),
                physical_coupling=False, uncertainty=None,
                uncertainty_reason='Source uncertainties and correlations were not propagated.',
                observation=dict(kind='simultaneous_geometric_coordinates', light_time_applied=False)
            )
        finally:
            for path in reversed(loaded):
                spice.unload(str(path))
