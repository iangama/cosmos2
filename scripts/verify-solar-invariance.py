"""Check translation and Galilean boosts in the reduced four-center model."""
from pathlib import Path
import argparse
import json
import sys
import traceback
import zipfile
import numpy as np
import rebound

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is12-solar-product/app'
sys.path.insert(0, str(APP))
from physics import PHYSICAL_SCALE as U
from solar_contract import sha

LIMITS = {'position_component_m': 10., 'velocity_component_m_s': 1e-5}
TRANSLATION = np.array([2e11, -3e11, 1e11])
BOOST = np.array([1234., -5678., 910.])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label.')
    folder = ROOT / ('output/is2-invariance-' + args.label)
    receipt = ROOT / ('evidence/is2-invariance-' + args.label + '.json')
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve prior evidence.')
    folder.mkdir()
    initial_path = ROOT / 'output/is12-solar-check-20261023b/initial.json'
    files = [Path(__file__).resolve(), ROOT / 'IS-2-INVARIANCIA-PREVIA.md', initial_path,
             APP / 'physics.py', ROOT / 'data/science/canonical-units.json']
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    archive = folder / 'executed-sources-and-recipe.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
    report = {'schema': 1, 'source_sha256': hashes, 'source_archive_sha256': sha(archive),
              'rebound_version': rebound.__version__, 'limits_before_execution': LIMITS,
              'translation_m': TRANSLATION.tolist(), 'boost_m_s': BOOST.tolist(),
              'completed': False, 'accepted': False, 'checks': {},
              'scope': 'Numerical invariance in the same reduced Newtonian model; no native UI or relativistic acceptance.'}

    def persist():
        receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')

    persist()
    try:
        initial = json.loads(initial_path.read_text(encoding='utf-8'))
        seconds = np.arange(0., 30*86400+1, 21600)
        series = {}
        for label, offset, boost in [('original', np.zeros(3), np.zeros(3)),
                                     ('translated', TRANSLATION, np.zeros(3)),
                                     ('translated_and_boosted', TRANSLATION, BOOST)]:
            sim = rebound.Simulation()
            sim.G = 1.; sim.integrator = 'ias15'; sim.integrator.epsilon = 1e-9
            for b in initial['bodies']:
                p = np.array(b['position']) + offset/U['length_unit_m']
                v = np.array(b['velocity']) + boost/U['velocity_unit_m_s']
                sim.add(m=b['mass'], x=p[0], y=p[1], z=p[2], vx=v[0], vy=v[1], vz=v[2])
            rows = []
            for t in seconds:
                sim.integrate(t/U['time_unit_s'])
                rows.append([[p.x, p.y, p.z, p.vx, p.vy, p.vz] for p in sim.particles])
            series[label] = np.array(rows)
            if label == 'original':
                continue
            restored = series[label].copy()
            restored[:, :, :3] -= (offset + seconds[:, None, None]*boost)/U['length_unit_m']
            restored[:, :, 3:] -= boost/U['velocity_unit_m_s']
            delta = restored-series['original']
            values = {'position_component_m': float(np.abs(delta[:, :, :3]).max()*U['length_unit_m']),
                      'velocity_component_m_s': float(np.abs(delta[:, :, 3:]).max()*U['velocity_unit_m_s'])}
            pair_error = 0.
            for i in range(4):
                for j in range(i+1, 4):
                    pair_error = max(pair_error, float(np.abs((restored[:, i, :3]-restored[:, j, :3])-
                        (series['original'][:, i, :3]-series['original'][:, j, :3])).max()*U['length_unit_m']))
            values['relative_pair_component_m'] = pair_error
            report['checks'][label] = values
            assert values['position_component_m'] <= LIMITS['position_component_m']
            assert values['velocity_component_m_s'] <= LIMITS['velocity_component_m_s']
            assert pair_error <= 2*LIMITS['position_component_m']
        result = folder / 'all-canonical-series.json'
        result.write_text(json.dumps({'seconds': seconds.tolist(), **{k: v.tolist() for k, v in series.items()}}, allow_nan=False)+'\n', encoding='utf-8')
        report['series_file'] = result.relative_to(ROOT).as_posix()
        report['series_sha256'] = sha(result)
        assert all(sha(ROOT / name) == value for name, value in hashes.items())
        report['completed'] = report['accepted'] = True
    except Exception:
        report['failure'] = traceback.format_exc()
    finally:
        persist()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
