"""Wait for F's real host completion, then preserve its immutable results locally, without a push."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT.parent / 'cosmos2-github-snapshot-20261103'
PROFILE = '20261114b'
LABEL = '20261114c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    progress = ROOT / f'output/is6-residency-followup-{PROFILE}.json'
    assert not progress.exists(), 'Preserve follow-up progress'
    state = dict(state='awaiting_host', profile=PROFILE, backup_label=LABEL, local_only=True, push=False,
                 source_sha256=sha(Path(__file__)), started_utc=dt.datetime.now(dt.timezone.utc).isoformat())

    def persist():
        temporary = progress.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
        temporary.replace(progress)

    persist()
    try:
        host_path = ROOT / f'evidence/is6-expanded-residency-host-{PROFILE}.json'
        deadline = time.monotonic()+7200
        while True:
            try:
                host = json.loads(host_path.read_text())
                if host.get('state') in ['complete', 'failed']:
                    break
            except (FileNotFoundError, ValueError):
                pass
            assert time.monotonic() < deadline, 'Host completion deadline exceeded; never start backup during collection'
            time.sleep(5)
        assert len(host['processes']) == 4 and all(p['code'] == 0 for p in host['processes'].values())
        assert host.get('owner_app_kept_open') is True and not host.get('cleanup_failure')
        state.update(state='checking_originals', profile_accepted=host['accepted'], host_sha256=sha(host_path))
        persist()
        assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=BACKUP)
        raw = ROOT / f'output/is6-expanded-residency-{PROFILE}/memory.jsonl'
        if raw.exists() and raw.stat().st_size >= 48*2**20:
            state['state'] = 'splitting_completed_raw'
            persist()
            subprocess.run([sys.executable, '-Xutf8', str(ROOT/'scripts/split-source-evidence-jsonl.py'),
                            '--label', '20261114f', '--source', raw.relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
        state['state'] = 'copying'
        persist()
        subprocess.run([sys.executable, '-Xutf8', str(ROOT/'scripts/sync-github-source-snapshot-v22.py'),
                        '--label', LABEL], cwd=ROOT, check=True)
        sync_path = ROOT / f'evidence/github-source-sync-{LABEL}.json'
        sync = json.loads(sync_path.read_text())
        assert sync['accepted'] and sync['completed']
        state['state'] = 'committing'
        persist()
        subprocess.run(['git', 'add', '-A'], cwd=BACKUP, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'Preserva RAM nativa e resultados originais da residencia F'], cwd=BACKUP, check=True)
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BACKUP, text=True).strip()
        assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=BACKUP)
        receipt = ROOT / f'evidence/github-source-local-{LABEL}.json'
        assert not receipt.exists()
        proof = dict(accepted=True, completed=True, local_only=True, push=False, revision=22,
                     commit=commit, files=sync['files'], sync_receipt_sha256=sha(sync_path),
                     profile_accepted=host['accepted'], host_sha256=sha(host_path),
                     scope='Local partial source/evidence backup after the host finished. This receipt never changes profile admission.')
        receipt.write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
        state.update(state='complete', commit=commit, files=sync['files'], receipt=receipt.relative_to(ROOT).as_posix())
    except Exception:
        state.update(state='failed', failure=traceback.format_exc())
    persist()
    print(json.dumps(state, ensure_ascii=False), flush=True)
    return 0 if state['state'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
