"""Copy original planet-center records and verify every copied state component."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import traceback

import numpy as np
import spiceypy as spice

ROOT = Path(__file__).resolve().parents[1]
CENTERS = [('mar099s.bsp', 499, 4), ('ura182.bsp', 799, 7), ('nep097.bsp', 899, 8)]
UTC = ['1995-01-01T00:00:00', '2049-12-30T23:59:59']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative_states(path, target, center, epochs):
    spice.kclear()
    spice.furnsh(str(path))
    return np.array([spice.spkezr(str(target), float(t), 'J2000', 'NONE', str(center))[0]
                     for t in epochs])


def extract(source, destination, target, center, start, end):
    segments, comments = [], []
    input_handle = spice.dafopr(str(source))
    output_handle = spice.spkopn(str(destination), 'COSMOS2_PLANET_CENTER_SUBSET', 2048)
    try:
        done = False
        while not done:
            count, lines, done = spice.dafec(input_handle, 256, 8192)
            comments.extend(lines[:count])
        spice.dafac(output_handle, [
            f'Cosmos2 original records, target {target}, center {center}, J2000.',
            'Source SHA256: ' + sha(source),
            'CSPICE spksub; original coefficients and segment priority.'
        ])
        spice.dafbfs(input_handle)
        while spice.daffna():
            descriptor = spice.dafgs(5)
            times, ids = spice.dafus(descriptor, 2, 6)
            if int(ids[0]) != target or times[1] < start or times[0] > end:
                continue
            assert int(ids[1]) == center and int(ids[2]) == 1
            first, last = max(start, float(times[0])), min(end, float(times[1]))
            identity = spice.dafgn()
            spice.spksub(input_handle, descriptor, identity, first, last, output_handle)
            segments.append(dict(target=target, center=center, frame_id=1, type=int(ids[3]),
                                 identifier=identity, source_et=times.tolist(), subset_et=[first, last]))
    finally:
        spice.dafcls(input_handle)
        spice.spkcls(output_handle)
    assert segments and list(spice.spkobj(str(destination))) == [target]
    coverage = spice.spkcov(str(destination), target)
    intervals = [list(spice.wnfetd(coverage, i)) for i in range(spice.wncard(coverage))]
    assert any(a <= start and b >= end for a, b in intervals)
    comment_path = destination.with_suffix('.comments.txt')
    comment_path.write_text('\n'.join(comments) + '\n', encoding='ascii')
    return segments, intervals, comment_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    label = parser.parse_args().label
    if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        parser.error('Invalid label')
    folder = ROOT / 'output' / f'is6-planet-catalog-data-{label}'
    out = ROOT / 'evidence' / f'is6-planet-catalog-data-{label}.json'
    if folder.exists() or out.exists():
        raise FileExistsError('Preserve previous data preparation')
    acquired_path = ROOT / 'evidence' / f'is6-planet-catalog-acquisition-{label}.json'
    acquired = json.loads(acquired_path.read_text())
    assert acquired['completed']
    folder.mkdir()
    result = dict(accepted=False, completed=False, sources={}, centers=[],
                  created_utc=datetime.now(timezone.utc).isoformat(),
                  script_sha256=sha(Path(__file__)), acquisition_sha256=sha(acquired_path),
                  application_utc=UTC, comparison_uniform_epochs=201,
                  contract_sha256=sha(ROOT / 'IS-6-CATALOGO-OITO-PLANETAS-CONTRATO.md'))
    base = ROOT / 'data/spice/de442s.bsp'
    try:
        spice.furnsh(str(ROOT / 'data/spice/naif0012.tls'))
        start, end = [spice.str2et(t) for t in UTC]
        base_epochs = np.linspace(start, end, 201)
        for filename, target, center in CENTERS:
            source = ROOT / acquired['files'][filename]['path']
            assert sha(source) == acquired['files'][filename]['sha256']
            result['sources'][source.relative_to(ROOT).as_posix()] = sha(source)
            destination = folder / f'center-{target}.bsp'
            segments, coverage, comments = extract(source, destination, target, center, start, end)
            epochs = set(base_epochs.tolist())
            for segment in segments:
                for boundary in segment['subset_et']:
                    epochs.update(t for t in (np.nextafter(boundary, -np.inf), boundary,
                                             np.nextafter(boundary, np.inf)) if start <= t <= end)
            epochs = sorted(epochs)
            original = relative_states(source, target, center, epochs)
            copied = relative_states(destination, target, center, epochs)
            assert np.array_equal(original, copied)
            spice.kclear()
            spice.furnsh(str(base))
            originals = {t: np.array([spice.spkezr(str(t), float(et), 'J2000', 'NONE', '0')[0]
                                      for et in epochs]) for t in (10, 399, 301, 4, 5, 6, 7, 8)}
            spice.furnsh(str(destination))
            for t, expected in originals.items():
                current = np.array([spice.spkezr(str(t), float(et), 'J2000', 'NONE', '0')[0]
                                    for et in epochs])
                assert np.array_equal(current, expected)
            state = np.array([spice.spkezr(str(target), float(et), 'J2000', 'NONE', '0')[0] for et in epochs])
            error = np.max(np.abs(state - (originals[center] + copied)), axis=0) * 1000
            assert np.max(error[:3]) <= .001 and np.max(error[3:]) <= .000001
            assert sha(source) == acquired['files'][filename]['sha256']
            entry = dict(target=target, center=center, source=source.relative_to(ROOT).as_posix(),
                         file=destination.relative_to(ROOT).as_posix(), sha256=sha(destination),
                         bytes=destination.stat().st_size, segments=segments, coverage_et_s=coverage,
                         comments=dict(path=comments.relative_to(ROOT).as_posix(), sha256=sha(comments)),
                         comparison_epochs=len(epochs), relative_states_bit_identical=True,
                         old_DE442s_states_bit_identical=True, chain_difference_SI=error.tolist())
            result['centers'].append(entry)
            print(json.dumps(dict(target=target, bytes=entry['bytes'], epochs=len(epochs),
                                  chain_difference_SI=entry['chain_difference_SI'])), flush=True)
        result['base_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in
                                 (base, ROOT / 'data/spice/naif0012.tls', ROOT / 'data/spice/pck00011.tpc')}
        result.update(accepted=True, completed=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        spice.kclear()
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], completed=result['completed'],
                          failure=result.get('failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
