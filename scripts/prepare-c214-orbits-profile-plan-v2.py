"""Seal the implemented C2-14 native profile recipe and all local Python helpers."""
import argparse
import hashlib
import json
from pathlib import Path

import c214_profile_contract as c

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    c.require(args.label and len(args.label)<=20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label),'Invalid label')
    out=ROOT/f'evidence/c214-orbits-profile-plan-{args.label}.json'
    c.require(not out.exists(),'Preserve sealed plans')
    sources={}
    for name in ['c214-orbits-native-20261114c.json','c214-orbits-visual-20261114c.json','c214-profile-admission-20261114a.json','c214-ui-cancel-state-20261114a.json','c214-profile-gpu-lifetimes-20261114a.json']:
        path=ROOT/'evidence'/name
        receipt=json.loads(path.read_text())
        c.require(receipt['accepted'] and receipt['completed'],'Native/visual/offline gate refused')
        sources.update(receipt.get('source_sha256',{}))
        sources[path.relative_to(ROOT).as_posix()]=sha(path)
    for path in list((ROOT/'scripts').glob('*.py'))+list(ROOT.glob('C2-14-ORBITAS-PERFIL*.md'))+[ROOT/'scripts/verify-c214-ui-cancel-state.mjs']:
        sources[path.relative_to(ROOT).as_posix()]=sha(path)
    c.require(all(sha(ROOT/name)==seal for name,seal in sources.items()),'Gate/source changed')
    engine=ROOT/'.runtime-is4-stream/bin/OpenSpace.exe'
    result=dict(accepted=True,completed=True,measurement_accepted=False,candidate='0.28.2',
                source_sha256=sources,engine_sha256=sha(engine),windows=c.WINDOWS,limits=c.LIMITS,
                warmup_s=30,frame_window_s=60,stable_samples=66,
                scope='Admission to execute the sealed profile only; this receipt contains no performance measurements')
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,sources=len(sources),windows=len(c.WINDOWS))))


if __name__=='__main__':main()
