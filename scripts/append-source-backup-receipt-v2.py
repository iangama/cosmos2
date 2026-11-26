"""Append the completed v28 copy receipt without rehashing unrelated cohorts."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT.parent/'cosmos2-github-snapshot-20261103'
OUT=ROOT/'evidence/github-source-sync-20261120g.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists()
    source=ROOT/'evidence/github-source-sync-20261120f.json'
    previous=json.loads(source.read_text(encoding='utf8'))
    inventory_path=TARGET/'snapshot-inventory.json'
    assert sha(inventory_path)==previous['inventory_sha256']
    inventory=json.loads(inventory_path.read_text(encoding='utf8'))
    rows={row['path']:row for row in inventory['files']}
    assert len(rows)==previous['files']
    changed=['evidence/github-source-sync-20261120f.json','scripts/append-source-backup-receipt-v2.py']
    before=sha(inventory_path)
    for name in changed:
        destination=TARGET/name
        assert not destination.exists() and name not in rows
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,destination)
        assert sha(destination)==sha(ROOT/name)
        rows[name]=dict(path=name,bytes=destination.stat().st_size,sha256=sha(destination))
    inventory['files']=[rows[name] for name in sorted(rows)]
    inventory_path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    proof=dict(accepted=True,completed=True,files=len(rows),changed=changed,
      inventory_before_sha256=before,inventory_sha256=sha(inventory_path),script_sha256=sha(Path(__file__)),
      scope='Append the completed copy receipt and this script only. Existing entries retained without rerunning scientific drivers or rehashing unchanged source cohorts. Local snapshot only, no publication.')
    OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    paths=sorted(set(previous['changed']+changed+['snapshot-inventory.json']))
    (ROOT/'output/original-flow-hotfix-review-20261120a/backup-paths.txt').write_text('\n'.join(paths)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,files=len(rows),stage_paths=len(paths))))


if __name__=='__main__':main()
