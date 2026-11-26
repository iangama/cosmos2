"""Seal the narrow Windows control/status reader change after its concurrency fixture."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    assert args.label and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    folder=ROOT/f'output/is6-expanded-residency-ipc-preparation-{args.label}';out=ROOT/f'evidence/is6-expanded-residency-ipc-preparation-{args.label}.json'
    assert not folder.exists() and not out.exists()
    fixture_path=ROOT/'evidence/is6-shared-json-fixture-20261113b.json';fixture=json.loads(fixture_path.read_text())
    assert fixture['accepted'] and fixture['completed'] and fixture['reads']>=1000 and fixture['writes']==1000 and fixture['large_control_bytes']>2**20 and len(fixture['refusals'])==1
    sources=dict(fixture['source_sha256'])
    assert all(sha(ROOT/name)==seal for name,seal in sources.items())
    for name in ['scripts/prepare-expanded-residency-ipc.py','scripts/collect_expanded_residency_v5.py','scripts/profile-expanded-residency-v4.py',
                 'scripts/run-expanded-residency-v4.py','IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-E.md',
                 'evidence/is6-shared-json-fixture-20261113b.json','evidence/is6-expanded-residency-20261113c.json',
                 'evidence/is6-expanded-residency-collector-20261113c.json','evidence/is6-expanded-residency-host-20261113c.json']:
        path=ROOT/name
        if path.suffix=='.py':ast.parse(path.read_text())
        sources[name]=sha(path)
    folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in sources:archive.write(ROOT/name,name)
    result=dict(accepted=True,completed=True,source_sha256=sources,refusals=fixture['refusals'],scope='IPC preparation and executed concurrent reader fixture only; original C remains refused, no new GPU/FPS acceptance.')
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,source_files=len(sources),reads=fixture['reads'],writes=fixture['writes'])),flush=True)


if __name__=='__main__':main()
