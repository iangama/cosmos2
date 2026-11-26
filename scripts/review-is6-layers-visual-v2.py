"""Seal the six manually inspected 0.19.1 images, including scrolled readings."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'evidence/is6-layers-native-20261103b.json'
process=ROOT/'evidence/is6-layers-native-process-20261103b.json'
out=ROOT/'evidence/is6-layers-visual-20261103b.json'
if out.exists():raise FileExistsError('Preserve visual review')
r=json.loads(source.read_text());p=json.loads(process.read_text())
assert r['accepted'] and r['completed'] and p['accepted'] and len(r['captures'])==6
assert not r['page_errors'] and len(r['cases'])==2 and len(r['refusals'])==14
hashes=dict(r['source_sha256'])
for path in [source,process,Path(__file__)]:hashes[path.relative_to(ROOT).as_posix()]=sha(path)
for item in r['captures']:
    a,b=ROOT/item['path'],ROOT/item['RGB']
    assert sha(a)==item['sha256'] and sha(b)==item['RGB_sha256']
    first,reviewed=Image.open(a).convert('RGB'),Image.open(b).convert('RGB')
    assert first.size==reviewed.size==(1920,1080) and ImageChops.difference(first,reviewed).getbbox() is None
    assert item['layout']['scroll']==item['layout']['client']
    hashes[item['path']]=item['sha256'];hashes[item['RGB']]=item['RGB_sha256']
assert all(sha(ROOT/n)==seal for n,seal in hashes.items())
result=dict(accepted=True,completed=True,candidate='0.19.1',source_sha256=hashes,reviewed_count=6,captures=r['captures'],
    method='Manual inspection: Earth overview 100/150, Jupiter overview 100/150, then both scrolled magnetic readings at150; byte hashes and identical RGB pixels verified.',
    observations=['Malha, graticulado, seta e ponto visíveis juntos com legendas distintas e fase congelada.',
        'Déficit dos relógios legível e não nulo para Terra/Júpiter; razão arredondada não oculta mais a medida pequena.',
        'Leituras B, norma, coordenadas e referencial legíveis após rolagem150%; nenhuma rolagem horizontal.',
        'Botão de fechar permanece visível nas seis imagens; centro e amostra permanecem fora dos painéis.'],
    scope='K3 functional and visual slice only; no final UI profile, compound persistence, migration, promotion or full IS6/v1 acceptance.')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(accepted=True,reviewed_count=6)))
