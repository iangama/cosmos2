"""Aggregate immutable Coulomb evidence without repeating accepted integrations."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    path = ROOT/f'evidence/is5-coulomb-science-{args.label}.json'
    archive = ROOT/f'output/is5-coulomb-science-{args.label}.zip'
    if path.exists() or archive.exists():
        raise FileExistsError('Preserve scientific aggregation')
    accepted = ['is5-coulomb-foundation-20261028b','is5-coulomb-mixture-20261028b',
                'is5-coulomb-mixture-composition-20261028a','is5-coulomb-screening-20261028a',
                'is5-coulomb-evolution-controls-20261028b']
    receipts = {}
    hashes = {Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))}
    for name in accepted:
        file = ROOT/f'evidence/{name}.json'
        obj = json.loads(file.read_text(encoding='utf-8'))
        assert obj['accepted'] and obj['completed'], name
        receipts[name] = obj
        hashes[file.relative_to(ROOT).as_posix()] = sha(file)
        for n,h in obj['source_sha256'].items():
            if n in hashes:
                assert hashes[n] == h, n
            hashes[n] = h
    screening = receipts[accepted[3]]
    evolution = receipts[accepted[4]]
    assert screening['generation'] == evolution['generation']
    assert screening['generation']['Coulomb_EOS'] == receipts[accepted[1]]['generation']
    assert len(evolution['reused_cases']) == 5 and len(evolution['reused_controls']) == 3
    assert len(evolution['controls']) == 3 and len(evolution['refusals']) == 7
    assert len(screening['cases']) == 4 and all(len(v['pairs']) == 13 for v in screening['cases'])
    assert all(sha(ROOT/n) == h for n,h in hashes.items())
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:
            z.write(ROOT/n,n)
    r = dict(accepted=True,completed=True,source_sha256=hashes,archive_sha256=sha(archive),
             generation=screening['generation'],accepted_receipts=accepted,
             evolution_cases=evolution['reused_cases'],
             original_rejections_preserved=['is5-coulomb-foundation-20261028a: test derivative scale',
               'is5-coulomb-mixture-20261028a: original rounded CTF reference',
               'is5-coulomb-evolution-20261028a: incomplete weakoff test request'],
             scope='Local classical-ion Coulomb EOS, static thermodynamic screening and coupled isochoric/prescribed CNO-II zone science only. No worker, CEF, visual, native performance or stellar structure acceptance.')
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(accepted=True,source_files=len(hashes),receipts=len(accepted),evolution_cases=5)))


if __name__ == '__main__':
    main()
