"""Verify Unicode, ambiguous legacy byte sequences and corruption refusal independently."""
import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is6-principal-moons-navigation-staging-v2'
sys.path[:0]=[str(STAGE),str(ROOT/'output/is6-planet-navigation-product0.24.0/app')]
from moon_navigation import Navigation
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is6-principal-moons-favorites-20261111a';out=ROOT/'evidence/is6-principal-moons-favorites-20261111a.json'
    if folder.exists() or out.exists():raise FileExistsError('Preserve encoding proof')
    folder.mkdir();result=dict(accepted=False,cases=[],script_sha256=sha(Path(__file__)),module_sha256=sha(STAGE/'moon_navigation.py'))
    view=json.loads((ROOT/'evidence/is6-principal-moons-switch-20261111a.json').read_text())['view']
    try:
        for index,(encoding,name) in enumerate([('ascii','Jupiter'),('cp1252','Titã em órbita'),
                ('cp1252','Ã©'),('utf8','Io 🚀'),('utf8','星 e Lua')]):
            target=folder/str(index);target.mkdir();nav=Navigation(None,target)
            rows=[dict(id='prior',name=name,view=view)];payload=dict(schema=1,views=rows)
            envelope=dict(payload=payload,sha256=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest())
            raw=json.dumps(envelope,ensure_ascii=False,indent=2).encode(encoding);nav.path.write_bytes(raw)
            assert nav.favorites()==rows and nav.path.read_bytes()==raw
            nav._read=lambda:dict(flying=False);nav._capture=lambda:view
            updated=nav.save('Nova vista 🚀 de Titã');assert len(updated)==2 and updated[0]==rows[0]
            decoded=json.loads(nav.path.read_bytes().decode('utf8'))
            assert decoded['payload']['views']==updated and nav.favorites()==updated
            damaged=json.loads(nav.path.read_bytes().decode('utf8'));damaged['payload']['views'][0]['name']='alterado'
            nav.path.write_text(json.dumps(damaged,ensure_ascii=False),encoding='utf8');before=nav.path.read_bytes()
            try:nav.favorites()
            except ValueError:pass
            else:raise AssertionError('Corrupt favorite seal admitted')
            assert nav.path.read_bytes()==before
            result['cases'].append(dict(encoding=encoding,name=name,legacy_read_without_mutation=True,new_write_utf8=True,corruption_refused=True))
        result.update(accepted=True,completed=True)
    except Exception:result['failure']=traceback.format_exc()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'],cases=len(result['cases']),failure=result.get('failure'))))
    return 0 if result['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
