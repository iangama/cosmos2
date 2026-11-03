"""Download the bounded, versioned OpenSpace galaxy proof data using HTTPS."""
from pathlib import Path
import hashlib
import json
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
FILES={
 'volume.raw':('milkyway/milkyway/volume/1/MilkyWayRGBAVolume1024x1024x128.raw',536870912),
 'points.off':('milkyway/milkyway/volume/1/MilkyWayPoints.off',211550222),
 'halo.png':('milkyway/milkyway/volume/1/halo.png',9325),
 'stars.speck':('digitaluniverse/stars/DU/7/stars.speck',29946294),
 'license_stars.lua':('digitaluniverse/stars/DU/6/license_stars.lua',1877),
 'colorbv.cmap':('digitaluniverse/stars/colormap/1/colorbv.cmap',9793),
 'viridis.cmap':('digitaluniverse/stars/colormap/2/viridis.cmap',9498),
 'glare.png':('digitaluniverse/stars/textures/1/glare.png',86262),
}
def main():
    directory=ROOT/'data'/'galaxy';directory.mkdir(parents=True,exist_ok=True)
    receipts=[]
    for name,(remote,size) in FILES.items():
        path=directory/name;url='https://liu-se.cdn.openspaceproject.com/files/'+remote
        if not path.exists():
            print('Downloading',name,flush=True)
            temp=path.with_suffix('.partial')
            with urllib.request.urlopen(url,timeout=90) as response,temp.open('wb') as output:
                count=0
                while block:=response.read(1024*1024):
                    output.write(block);count+=len(block)
                    if count>size:raise ValueError('Unexpected download size')
                if count!=size:raise ValueError('Incomplete download')
            temp.replace(path)
        if path.stat().st_size!=size:raise ValueError('Local dataset size mismatch: '+name)
        with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
        receipts.append({'file':str(path.relative_to(ROOT)),'url':url,'bytes':size,'sha256':digest})
    (ROOT/'evidence'/'galaxy-acquisition.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print('Galaxy data ready',flush=True)
if __name__=='__main__':main()
