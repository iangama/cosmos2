"""Measure reduced-model discrepancy against pinned JPL geometric states."""
from pathlib import Path
import argparse
import datetime as dt
import json
import sys
import traceback
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is12-solar-product/app'
sys.path.insert(0, str(APP))
import atlas
from solar_catalog import states
from solar_contract import SUBSET, sha
from physics import PHYSICAL_SCALE as U


def metrics(delta, seconds):
    positions = np.linalg.norm(delta[:, :3], axis=1)
    velocities = np.linalg.norm(delta[:, 3:], axis=1)
    return {'max_position_norm_m': float(positions.max()),
            'max_position_elapsed_s': float(seconds[int(positions.argmax())]),
            'max_velocity_norm_m_s': float(velocities.max()),
            'max_position_component_m': float(np.abs(delta[:, :3]).max()),
            'max_velocity_component_m_s': float(np.abs(delta[:, 3:]).max()),
            'final_position_vector_m': delta[-1, :3].tolist(),
            'final_velocity_vector_m_s': delta[-1, 3:].tolist(),
            'final_position_norm_m': float(positions[-1]), 'final_velocity_norm_m_s': float(velocities[-1])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label.')
    receipt = ROOT / ('evidence/is2-jpl-model-' + args.label + '.json')
    folder = ROOT / ('output/is2-jpl-model-' + args.label)
    if receipt.exists() or folder.exists():
        raise FileExistsError('Preserve existing evidence.')
    folder.mkdir()
    source_path = ROOT / 'evidence/is12-solar-check-20261023b.json'
    audit_path = ROOT / 'evidence/is12-solar-audit-20261023b.json'
    source, audit = [json.loads(p.read_text(encoding='utf-8')) for p in [source_path, audit_path]]
    series_path = ROOT / source['propagation']['series_file']
    initial_path = ROOT / 'output/is12-solar-check-20261023b/initial.json'
    files = [Path(__file__).resolve(), ROOT / 'IS-2-COMPARACAO-JPL-PREVIA.md', source_path, audit_path,
             initial_path, APP / 'atlas.py', APP / 'solar_catalog.py', APP / 'solar_contract.py', APP / 'physics.py']
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    archive = folder / 'executed-sources-and-recipe.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
    report = {'schema': 1, 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'sources_sha256': hashes, 'series_sha256': sha(series_path),
              'source_archive_sha256': sha(archive), 'completed': False,
              'scope': 'Measured discrepancy from the pinned JPL ephemerides, not integrator error or observational accuracy. No model-fit threshold.'}

    def persist():
        receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')

    persist()
    try:
        assert audit['accepted'] is True and audit['input_receipt_sha256'] == sha(source_path)
        assert report['series_sha256'] == source['propagation']['series_sha256']
        initial = json.loads(initial_path.read_text(encoding='utf-8'))
        catalog = states(initial['source']['epoch']['utc'])
        prior_catalog = initial['reference_catalog']
        report['catalog_code_generations'] = {'saved': prior_catalog['provenance']['catalog_code_sha256'],
                                               'current': catalog['provenance']['catalog_code_sha256']}
        assert {k: v for k, v in catalog.items() if k != 'provenance'} == {k: v for k, v in prior_catalog.items() if k != 'provenance'}
        assert {k: v for k, v in catalog['provenance'].items() if k != 'catalog_code_sha256'} == {k: v for k, v in prior_catalog['provenance'].items() if k != 'catalog_code_sha256'}
        kernels = catalog['provenance']['kernel_sha256']
        assert all(sha(ROOT / path) == expected for path, expected in kernels.items())
        report['kernel_sha256'] = kernels
        report['initial_epoch'] = initial['source']['epoch']
        report['recipe'] = {'reference': 'SSB/J2000/NONE, exact ET0 + elapsed seconds',
                            'inverse': 'r_SSB = L*r + r0 + v0*elapsed; v_SSB = V*v + v0',
                            'position_initial_limit_m': .001, 'velocity_initial_limit_m_s': 1e-8}
        persist()
        data = json.loads(series_path.read_text(encoding='utf-8'))
        seconds = np.array(data['seconds'])
        phase = np.array(data['canonical_IAS15'], dtype=float)
        assert phase.shape == (121, 4, 6) and np.array_equal(seconds, np.arange(0, 30*86400+1, 21600))
        evolved = phase.copy()
        origin = np.array(initial['initial_ssb_origin_m'])
        velocity = np.array(initial['inertial_origin_velocity_m_s'])
        evolved[:, :, :3] = phase[:, :, :3] * U['length_unit_m'] + origin + seconds[:, None, None]*velocity
        evolved[:, :, 3:] = phase[:, :, 3:] * U['velocity_unit_m_s'] + velocity
        reference = []
        with atlas.LOCK:
            atlas.SPICE.furnsh(str(ROOT / SUBSET))
            try:
                for elapsed in seconds:
                    et = initial['source']['epoch']['et_tdb_s'] + float(elapsed)
                    reference.append([atlas.SPICE.spkezr(b['naif_id'], et, 'J2000', 'NONE', '0')[0].tolist()
                                      for b in catalog['bodies']])
            finally:
                atlas.SPICE.unload(str(ROOT / SUBSET))
        reference = np.array(reference)*1000.
        delta = evolved-reference
        assert np.max(np.abs(delta[0, :, :3])) <= .001
        assert np.max(np.abs(delta[0, :, 3:])) <= 1e-8
        report['bodies'] = {b['reference_id']: metrics(delta[:, i], seconds) for i, b in enumerate(initial['bodies'])}
        report['relative_pairs'] = {}
        for name, target, center in [('Moon-Earth', 2, 1), ('Earth-Sun', 1, 0), ('Jupiter-Sun', 3, 0)]:
            relative_delta = (evolved[:, target]-evolved[:, center])-(reference[:, target]-reference[:, center])
            report['relative_pairs'][name] = metrics(relative_delta, seconds)
        result = folder / 'all-reference-states-and-residuals-si.json'
        result.write_text(json.dumps({'seconds': seconds.tolist(), 'reference_SSB_SI': reference.tolist(),
                                     'evolved_SSB_SI': evolved.tolist(), 'evolved_minus_reference_SI': delta.tolist()}, allow_nan=False)+'\n')
        report['series_file'] = result.relative_to(ROOT).as_posix()
        report['result_sha256'] = sha(result)
        assert sha(series_path) == report['series_sha256']
        assert all(sha(ROOT / path) == expected for path, expected in hashes.items())
        report['completed'] = True
    except Exception:
        report['failure'] = traceback.format_exc()
    finally:
        persist()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
