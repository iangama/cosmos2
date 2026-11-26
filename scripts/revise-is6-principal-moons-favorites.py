"""Prepare explicit UTF8 favorites with checksum-disambiguated legacy Windows decoding."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is6-principal-moons-navigation-staging'
TARGET=ROOT/'output/is6-principal-moons-navigation-staging-v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if TARGET.exists():raise FileExistsError('Preserve favorites revision staging')
    shutil.copytree(BASE,TARGET,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    path=TARGET/'moon_navigation.py';source=path.read_text()
    start=source.index('    def favorites(self):');end=source.index('    def save(',start)
    reader='''    def favorites(self):
        if not self.path.exists():return []
        raw=self.path.read_bytes()
        for encoding in ('utf8','cp1252'):
            try:
                envelope=json.loads(raw.decode(encoding));payload=envelope['payload']
                seal=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True,allow_nan=False).encode('utf8')).hexdigest()
                if seal!=envelope['sha256']:continue
            except (UnicodeError,ValueError,KeyError,TypeError):continue
            if payload.get('schema')!=1 or not isinstance(payload.get('views'),list) or len(payload['views'])>64:raise ValueError('Arquivo de favoritos inválido.')
            return payload['views']
        raise ValueError('Integridade dos favoritos inválida.')
'''
    source=source[:start]+reader+source[end:]
    before="tmp.write_text(json.dumps(sealed,ensure_ascii=False,indent=2)+'\\n')"
    assert source.count(before)==1
    source=source.replace(before,"tmp.write_text(json.dumps(sealed,ensure_ascii=False,indent=2)+'\\n',encoding='utf8')")
    ast.parse(source);path.write_text(source,encoding='utf8')
    profile_path=TARGET/'atlas.profile';profile=json.loads(profile_path.read_text());profile['meta']['version']='0.25.1'
    profile_path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    cfg=(TARGET/'cosmos2.cfg').read_text().replace('is6-principal-moons-navigation-staging/atlas.profile','is6-principal-moons-navigation-staging-v2/atlas.profile')
    (TARGET/'cosmos2.cfg').write_text(cfg,encoding='utf8')
    scene_path=TARGET/'planet_scene.json';scene=json.loads(scene_path.read_text());scene['profile_sha256']=sha(profile_path);scene['favorites_revision_sha256']=sha(Path(__file__))
    scene_path.write_text(json.dumps(scene,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    launcher=(ROOT/'scripts/launch-is6-principal-moons-candidate.py').read_text()
    launcher=launcher.replace('product0.25.0','product0.25.1').replace("manifest['candidate']=='0.25.0'","manifest['candidate']=='0.25.1'")
    launcher=launcher.replace('staging/cosmos2.cfg','staging-v2/cosmos2.cfg').replace('0.25.0-unpromoted','0.25.1-unpromoted')
    (ROOT/'scripts/launch-is6-principal-moons-candidate-v2.py').write_text(launcher,encoding='utf8')
    print('Favorites UTF8 revision and legacy reader prepared')


if __name__=='__main__':main()
