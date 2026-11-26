"""Acquire the original JUP365 and SAT441 kernels for six principal moons."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import traceback

ROOT = Path(__file__).resolve().parents[1]
NAIF = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/'
FILES = {
    'aa_checksums.txt': (NAIF + 'aa_checksums.txt', 1024 * 1024),
    'jup365.cmt': (NAIF + 'jup365.cmt', 1024 * 1024),
    'jup365.mrg': (NAIF + 'jup365.mrg', 1024 * 1024),
    'jup365.bsp': (NAIF + 'jup365.bsp', 1300 * 1024 * 1024),
    'sat441.cmt': (NAIF + 'sat441.cmt', 1024 * 1024),
    'sat441.mrg': (NAIF + 'sat441.mrg', 1024 * 1024),
    'sat441.bsp': (NAIF + 'sat441.bsp', 700 * 1024 * 1024),
}


def seal(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    label = parser.parse_args().label
    if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        parser.error('Invalid label')
    profile = ROOT / 'evidence/is6-planet-navigation-profile-20261111a.json'
    if profile.exists():
        active = json.loads(profile.read_text())
        assert active['completed'] or active.get('failure'), 'Wait for the native profile before acquisition'
    folder = ROOT / 'output' / f'is6-principal-moons-acquisition-{label}'
    receipt = ROOT / 'evidence' / f'is6-principal-moons-acquisition-{label}.json'
    folder.mkdir(exist_ok=True)
    script_sha = seal(Path(__file__))
    report = dict(completed=False, script_sha256=script_sha, files={},
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  contract_sha256=seal(ROOT / 'IS-6-LUAS-PRINCIPAIS-CONTRATO.md'))
    if receipt.exists():
        report = json.loads(receipt.read_text())
        if report['completed'] or report['script_sha256'] != script_sha:
            raise FileExistsError('Preserve completed acquisition or original downloader')
        report.pop('failure', None)

    def persist():
        temporary = receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        temporary.replace(receipt)

    persist()
    try:
        for name, (url, maximum) in FILES.items():
            destination = folder / name
            previous = report['files'].get(name)
            if previous:
                assert destination.is_file() and seal(destination) == previous['sha256']
                continue
            partial = destination.with_suffix(destination.suffix + '.partial')
            if not destination.exists():
                print('Acquiring ' + name, flush=True)
                subprocess.run(
                    ['curl', '--fail', '--location', '--silent', '--show-error',
                     '--retry', '2', '--retry-delay', '1', '--connect-timeout', '20',
                     '--max-time', '1200', '--max-filesize', str(maximum),
                     '--continue-at', '-', '--output', str(partial), url],
                    check=True
                )
                partial.replace(destination)
            assert 0 < destination.stat().st_size <= maximum
            if name.endswith('.bsp'):
                with destination.open('rb') as stream:
                    assert stream.read(8) == b'DAF/SPK '
            report['files'][name] = dict(path=destination.relative_to(ROOT).as_posix(),
                                          url=url, bytes=destination.stat().st_size,
                                          sha256=seal(destination))
            persist()
        checksums = {}
        for line in (folder / 'aa_checksums.txt').read_text().splitlines():
            fields = line.split()
            if len(fields) == 2:
                checksums[fields[1].lstrip('*')] = fields[0]
        for name in ('jup365.bsp', 'sat441.bsp'):
            with (folder / name).open('rb') as stream:
                md5 = hashlib.file_digest(stream, 'md5').hexdigest()
            assert md5 == checksums[name], name
            report['files'][name]['published_md5'] = md5
        report.update(completed=True, completed_utc=datetime.now(timezone.utc).isoformat())
    except Exception:
        report['failure'] = traceback.format_exc()
    persist()
    print(json.dumps(dict(completed=report['completed'], files=len(report['files']),
                          failure=report.get('failure'))), flush=True)
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
