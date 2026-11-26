"""Seal own scientific inputs, executors and prerequisites before residence measurement."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import expanded_residency_contract_v3 as c

ROOT = Path(__file__).resolve().parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--preflight', required=True)
    args = parser.parse_args()
    for label in [args.label, args.preflight]:
        assert label and len(label) <= 20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in label)
    out = ROOT / f'evidence/is6-expanded-residency-plan-{args.label}.json'
    folder = ROOT / f'output/is6-expanded-residency-plan-{args.label}'
    assert not out.exists() and not folder.exists()
    seed_name = 'evidence/is6-expanded-journey-native-20261113a.json'
    service_name = 'evidence/is6-expanded-instruments-service-20261113c.json'
    prerequisites = [seed_name, service_name, 'evidence/is6-expanded-journey-native-host-recovery-20261113a.json',
                     'evidence/is6-expanded-journey-reopen-20261113a.json', 'evidence/is6-expanded-journey-reopen-host-20261113a.json',
                     'evidence/is6-expanded-journey-visual-20261113a.json', 'evidence/is6-expanded-residency-offline-20261113a.json',
                     'evidence/is6-expanded-residency-audit-offline-20261113b.json',
                     f'evidence/is6-expanded-residency-preflight-{args.preflight}.json', 'evidence/is6-expanded-history-offline-20261113a.json', 'evidence/is6-owned-history-fixture-20261113a.json', 'evidence/is6-expanded-residency-ipc-preparation-20261113a.json', 'evidence/is6-expanded-timing-offline-20261114b.json']
    sources = {}
    for name in prerequisites:
        proof = json.loads((ROOT / name).read_text())
        assert proof['accepted'] and proof.get('completed', True), name
        for relative, seal in proof.get('source_sha256', {}).items():
            assert sha(ROOT / relative) == seal, relative
            sources[relative] = seal
        sources[name] = sha(ROOT / name)
    seed = json.loads((ROOT / seed_name).read_text())
    protected = seed['protected_sha256'] | {item['original']: item['sha256'] for item in seed['archives']}
    # Discover every saved binary beside its manifest, including archived branches.
    # Never overwrite either sidecar or JSON; retain their original digest pair.
    for name in list(protected):
        path = ROOT / name
        assert sha(path) == protected[name]
        if path.suffix == '.json':
            content = json.loads(path.read_text())
            if isinstance(content, dict) and 'binary' in content:
                binary = (path.parent / content['binary']).resolve()
                assert binary.is_relative_to(ROOT) and sha(binary) == content['sha256']
                protected[binary.relative_to(ROOT).as_posix()] = content['sha256']
    for name in ['scripts/prepare-expanded-residency-v6.py', 'scripts/verify-native-is6-expanded-journey.py',
                 'scripts/cef_page_v2.py', 'scripts/benchmark-body-points-native.py', 'scripts/verify-native-solar-integration.py',
                 'scripts/engine-command.py', 'scripts/expanded_residency_processes.py', 'scripts/owned_process_snapshot.py',
                 'scripts/windows_gpu_pdh_v2.py', 'scripts/gpu_pdh_audit_dynamics16_base.py',
                 'scripts/launch-is6-expanded-journey-candidate.py', 'scripts/open-expanded-journey-app.py',
                 'config/window-1080.json', 'config/cosmos2.cfg']:
        sources[name] = sha(ROOT / name)
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve() == ROOT / 'output/is6-expanded-journey-product0.27.0/app/server.py'
    engine = Path(session['runtime']) / 'bin/OpenSpace.exe'
    assert all(sha(ROOT / name) == seal for name, seal in sources.items())
    folder.mkdir()
    with zipfile.ZipFile(folder / 'sealed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    plan = dict(accepted=True, candidate='0.27.0', windows=c.WINDOWS, limits=c.LIMITS, initialization_budget_s=10, collector_schema=7, warmup_s=30, capture_s=60,
                continuous_samples_per_window=66, seed=seed_name, service=service_name, source_sha256=sources,
                protected_sha256=protected, engine_sha256=sha(engine), source_archive_sha256=sha(folder / 'sealed-sources.zip'),
                scope='Preparation gate only; no residence or native-frame result has been measured by this plan.')
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=True, source_files=len(sources), protected_files=len(protected), windows=10)), flush=True)


if __name__ == '__main__':
    main()
