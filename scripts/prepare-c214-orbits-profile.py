"""Prepare a C2-14 profile inventory; this does not admit or run a profile."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    out = ROOT / f'evidence/c214-orbits-profile-preparation-{args.label}.json'
    assert not out.exists(), 'Preserve previous preparation'
    sources = {}
    for name in ['c214-orbits-native-20261114b.json', 'c214-orbits-visual-20261114b.json']:
        path = ROOT / 'evidence' / name
        proof = json.loads(path.read_text(encoding='utf8'))
        assert proof['accepted'] and proof['completed']
        if 'native-' in name:
            assert proof['owner_restored'] and len(proof['closures']) == 2
            assert all(len(row['exits']) == 4 and all(p['code'] == 0 for p in row['exits'].values()) for row in proof['closures'])
            sources.update(proof['source_sha256'])
        else:
            assert len(proof['captures']) == 4
            for capture in proof['captures']:
                assert sha(ROOT / capture['path']) == capture['sha256']
                sources[capture['path']] = capture['sha256']
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    for name in ['scripts/prepare-c214-orbits-profile.py', 'C2-14-ORBITAS-PERFIL-CONTRATO-20261114.md',
                 'scripts/expanded_residency_timing.py', 'scripts/owned_process_memory.py',
                 'scripts/expanded_residency_memory_audit.py', 'scripts/expanded_residency_history_audit_v2.py',
                 'scripts/owned_process_history.py', 'scripts/windows_shared_json_v2.py']:
        path = ROOT / name
        if path.exists():
            sources[name] = sha(path)
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    common = dict(mass_solar=10, semi_latus_rectum_rs=1000, eccentricity=.6,
                  radial_cycles=8, orientation='positive')
    recipes = []
    for name, view, orbit, kind in [('eccentric-orbit', 'orbits', True, 'eccentric'),
                                    ('eccentric-clocks', 'clocks', True, 'eccentric'),
                                    ('straight-clocks', 'clocks', False, 'eccentric'),
                                    ('circular-orbit', 'orbits', True, 'circular')]:
        recipes.append(dict(name=name, view=view, parameters=common | dict(orbit_kind=kind),
                            gravity=dict(acting=True, visible=True, effects=dict(orbital_acceleration=orbit, proper_clock_rate=True)),
                            animation=True, css_zoom=1, warmup_s=30, frame_window_s=60, memory_samples=66))
    result = dict(prepared=True, completed=True, accepted=False, measurement_accepted=False,
                  scope='Preparation only; no measurements. Collector/controller/auditor must be implemented and sealed before execution.',
                  candidate='0.28.1', source_sha256=sources, windows=recipes,
                  limits=dict(median_ms=16.7, p95_ms=25, p99_ms=50, over_100ms=0,
                              frame_coverage_min=.9, RAM_bytes=8*2**30, GPU_bytes=5.5*2**30,
                              bootstrap_s_max=10, raw_sample_s_max=1, cadence_s_min=.85, cadence_s_max=1.15),
                  pending=['C2-14 collector with native RAM/history and exact CEF job/result identity',
                           'Native controller with continuous animations and engine frame capture',
                           'Independent audit and retained-handle closure/restoration host',
                           'Final source seal before collecting any new raw data'])
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(prepared=True, accepted=False, sources=len(sources), windows=len(recipes))))


if __name__ == '__main__':
    main()
