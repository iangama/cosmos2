"""Acquire the six upstream visual maps with pinned source and image metadata."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / '.upstream/openspace/data/assets/scene/solarsystem/planets'
SPECS = [
    ('Mercury', 'mercury', 2, 'Mercury_MESSENGER_MDIS_Basemap_BDR_Mosaic_Global_32ppd.jpg'),
    ('Venus', 'venus', 2, 'venus_clouds.jpg'),
    ('Mars', 'mars', 3, 'mars.png'),
    ('Jupiter', 'jupiter', 2, 'jupiter_os.tif'),
    ('Uranus', 'uranus', 1, 'uranus.jpg'),
    ('Neptune', 'neptune', 1, 'neptune.jpg'),
]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    label = parser.parse_args().label
    if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        parser.error('Invalid label')
    folder = ROOT / 'output' / f'is6-planet-visuals-{label}'
    receipt = ROOT / 'evidence' / f'is6-planet-visuals-{label}.json'
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve visual acquisition')
    folder.mkdir()
    report = dict(completed=False, maps={}, script_sha256=sha(Path(__file__)),
                  started_utc=datetime.now(timezone.utc).isoformat())
    try:
        for node, planet, version, filename in SPECS:
            asset = ASSETS / planet / 'layers/colorlayers' / (planet + '_texture.asset')
            text = asset.read_text()
            assert 'Identifier = "' + planet + '_textures"' in text
            assert 'Version = ' + str(version) in text and filename in text
            url = 'https://liu-se.bigbang.openspaceproject.com/request?' + urllib.parse.urlencode(
                dict(identifier=planet+'_textures', file_version=version, application_version=1))
            with urllib.request.urlopen(url, timeout=30) as response:
                manifest = response.read()
            manifest_path = folder / (planet + '-manifest.txt')
            manifest_path.write_bytes(manifest)
            original = next(line.strip() for line in manifest.decode().splitlines()
                            if urllib.parse.unquote(urllib.parse.urlsplit(line.strip()).path).endswith('/' + filename))
            download = original.replace('http://', 'https://', 1)
            destination = folder / filename
            print('Acquiring ' + node, flush=True)
            subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                            '--retry', '2', '--max-time', '300', '--max-filesize', str(100*1024*1024),
                            '--output', str(destination), download], check=True)
            with Image.open(destination) as image:
                width, height = image.size
                image.verify()
            report['maps'][node] = dict(
                path=destination.relative_to(ROOT).as_posix(), sha256=sha(destination),
                bytes=destination.stat().st_size, width=width, height=height,
                manifest_url=url, manifest_sha256=sha(manifest_path),
                original_url=original, download_url=download,
                upstream_asset=asset.relative_to(ROOT).as_posix(), upstream_asset_sha256=sha(asset),
                asset_license='MIT in upstream Lua metadata',
                image_origin='OpenSpace fixed visual map; observational origin and epoch unconfirmed',
                observational_epoch=None, planet=planet, resource_version=version
            )
            receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
        report['completed'] = True
    finally:
        receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(completed=report['completed'], maps=len(report['maps']))), flush=True)


if __name__ == '__main__':
    main()
