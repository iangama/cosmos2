"""Append the completed v32 copy receipt safely."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT.parent/'cosmos2-github-snapshot-20261103'
OUT=ROOT/'evidence/github-source-sync-20261121h.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists()
    prior=json.loads((ROOT/'evidence/github-source-sync-20261121g.json').read_text(encoding='utf8'))
    inventory_path=TARGET/'snapshot-inventory.json';assert sha(inventory_path)==prior['inventory_sha256']
    inventory=json.loads(inventory_path.read_text(encoding='utf8'));rows={row['path']:row for row in inventory['files']}
    assert len(rows)==prior['files']
    names=['evidence/github-source-sync-20261121g.json','scripts/append-source-backup-receipt-v6.py']
    names += ['scripts/point-lens-view-v2.js', 'scripts/prepare-c214-point-lens-ui-v2.py', 'scripts/verify-c214-point-lens-ui-v2.py', 'evidence/c214-point-lens-ui-20261121b.json', 'scripts/prepare-working-product-v10.py', 'scripts/open-working-cosmos2-v4.py', 'scripts/launch-working-cosmos2-v4.py', 'scripts/switch-working-product-0290.py', 'scripts/preserve-working-session-for-upgrade-v5.py', 'scripts/verify-native-point-lens.py', 'evidence/point-lens-session-preservation-20261121a.json', 'evidence/working-product-switch-20261121d.json', 'evidence/original-flow-entry-point-lens-20261121a.json', 'config/local-working-product.json', 'Iniciar-Cosmos2.cmd', 'Abrir-Planetas.cmd', 'Abrir-Planetas-e-Luas.cmd']
    for base in ['output/c214-point-lens-ui-staging-v2','output/original-flow-hotfix-product0.29.0']:
        for folder in ['app','data']:
            names += [p.relative_to(ROOT).as_posix() for p in (ROOT/base/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        names += [p.relative_to(ROOT).as_posix() for p in (ROOT/base).glob('*.json')]
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT/'output/c214-point-lens-ui-20261121b').glob('*.png')]
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
    (ROOT/'output/point-lens-backup-20261121a-paths.txt').write_text('\n'.join(paths)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,files=len(rows),stage_paths=len(paths))))


if __name__=='__main__':main()
