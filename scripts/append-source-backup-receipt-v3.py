"""Append the completed v29 copy receipt and completed roundtrip observation safely."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT.parent/'cosmos2-github-snapshot-20261103'
OUT=ROOT/'evidence/github-source-sync-20261121b.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists()
    prior=json.loads((ROOT/'evidence/github-source-sync-20261121a.json').read_text(encoding='utf8'))
    inventory_path=TARGET/'snapshot-inventory.json';assert sha(inventory_path)==prior['inventory_sha256']
    inventory=json.loads(inventory_path.read_text(encoding='utf8'));rows={row['path']:row for row in inventory['files']}
    assert len(rows)==prior['files']
    names=['evidence/github-source-sync-20261121a.json','scripts/append-source-backup-receipt-v3.py']
    diagnostic=ROOT/'evidence/native-spatial-roundtrip-20261121a.json'
    if diagnostic.exists() and json.loads(diagnostic.read_text(encoding='utf8')).get('completed'):
        names.append(diagnostic.relative_to(ROOT).as_posix())
        image=ROOT/'output/native-spatial-roundtrip-20261121a/current-export-preview-result.png'
        if image.exists():names.append(image.relative_to(ROOT).as_posix())
    changed=[]
    for name in names:
        source=ROOT/name;destination=TARGET/name;digest=sha(source)
        if name in rows:
            assert sha(destination)==rows[name]['sha256']
            if digest==rows[name]['sha256']:continue
        elif destination.exists():assert sha(destination)==digest,'Preserve an unrelated untracked file: '+name
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
        assert sha(destination)==digest==sha(source)
        rows[name]=dict(path=name,bytes=destination.stat().st_size,sha256=digest);changed.append(name)
    inventory['files']=[rows[name] for name in sorted(rows)]
    inventory_path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    proof=dict(accepted=True,completed=True,files=len(rows),changed=changed,inventory_sha256=sha(inventory_path),script_sha256=sha(Path(__file__)),
      scope='Incremental append only. Existing inventoried helper source is verified and retained; completed diagnostic evidence added if available. No private session or Windows home-directory image, no scientific rerun or publication.')
    OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    paths=sorted(set(prior['changed']+changed+['snapshot-inventory.json']))
    (ROOT/'output/original-flow-hotfix-review-20261120a/backup-paths.txt').write_text('\n'.join(paths)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,files=len(rows),stage_paths=len(paths))))


if __name__=='__main__':main()
