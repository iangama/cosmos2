"""Acquire and fully decode six upstream moon maps without editing their pixels."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import traceback
import urllib.parse
import urllib.request
import warnings
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'.upstream/openspace/data/assets/scene/solarsystem/planets'
SPECS=[('Io','jupiter','io',1,'io.jpg','io_texture.asset'),
       ('Europa','jupiter','europa',2,'europa_os.tif','europa_texture.asset'),
       ('Ganymede','jupiter','ganymede',1,'ganymede.jpg','ganymede_texture.asset'),
       ('Callisto','jupiter','callisto',2,'callisto_os.tif','callisto_texture.asset'),
       ('Enceladus','saturn','enceladus',1,'enceladus.jpg','enceladus_texture.asset'),
       ('Titan','saturn','titan',2,'Titan_ISS_P19658_Mosaic_Global_4km_os.tif','cassini_iss_global_mosaic_4km_local.asset')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    label=parser.parse_args().label
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):parser.error('Invalid label')
    folder=ROOT/f'output/is6-principal-moons-visuals-{label}'
    receipt=ROOT/f'evidence/is6-principal-moons-visuals-{label}.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve original maps and acquisition evidence')
    folder.mkdir()
    report=dict(completed=False,maps={},script_sha256=sha(Path(__file__)),started_utc=datetime.now(timezone.utc).isoformat())
    def persist():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    persist()
    try:
        for node,parent,moon,version,filename,asset_name in SPECS:
            asset=ASSETS/parent/moon/'layers/colorlayers'/asset_name;text=asset.read_text()
            assert 'Identifier = "'+moon+'_textures"' in text and 'Version = '+str(version) in text and filename in text
            url='https://liu-se.bigbang.openspaceproject.com/request?'+urllib.parse.urlencode(dict(identifier=moon+'_textures',file_version=version,application_version=1))
            with urllib.request.urlopen(url,timeout=30) as response:manifest=response.read()
            manifest_path=folder/(moon+'-manifest.txt');manifest_path.write_bytes(manifest)
            original=next(line.strip() for line in manifest.decode().splitlines() if urllib.parse.unquote(urllib.parse.urlsplit(line.strip()).path).endswith('/'+filename))
            download=original.replace('http://','https://',1);destination=folder/filename
            print('Acquiring '+node,flush=True)
            subprocess.run(['curl','--fail','--location','--silent','--show-error','--retry','2','--max-time','300','--max-filesize',str(100*1024*1024),'--output',str(destination),download],check=True)
            with warnings.catch_warnings(record=True) as recorded:
                warnings.simplefilter('always')
                with Image.open(destination) as image:
                    width,height=image.size;mode=image.mode;image.load()
                warning_text=[str(w.message) for w in recorded]
            assert abs(width-2*height)<=2,(node,width,height)
            report['maps'][node]=dict(path=destination.relative_to(ROOT).as_posix(),sha256=sha(destination),
                bytes=destination.stat().st_size,width=width,height=height,mode=mode,all_pixels_decoded=True,
                decode_warnings=warning_text,manifest_url=url,manifest_sha256=sha(manifest_path),
                original_url=original,download_url=download,upstream_asset=asset.relative_to(ROOT).as_posix(),
                upstream_asset_sha256=sha(asset),asset_license='NASA/PDS in upstream Lua metadata' if node=='Titan' else 'MIT in upstream Lua metadata; image license not inferred',
                image_origin='OpenSpace fixed visual map; observational origin and epoch unconfirmed',
                observational_epoch=None,parent=parent,resource_identifier=moon+'_textures',resource_version=version)
            if node=='Titan':
                report['maps'][node]['upstream_description']='Cassini ISS global mosaic produced June2015, using observations through2014-04-07, as described in the upstream USGS layer metadata; linked primary page returned403 during verification.'
            persist()
        report['completed']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps(dict(completed=report['completed'],maps=len(report['maps']),failure=report.get('failure'))),flush=True)
    return 0 if report['completed'] else 1


if __name__=='__main__':raise SystemExit(main())
