"""Archive the two native files before the opt-in normalized trajectory receiver."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'.upstream/openspace'
DEST=ROOT/'output/is4-stream-runtime-staging'
NAMES=['modules/space/rendering/renderableconstellationlines.h','modules/space/rendering/renderableconstellationlines.cpp']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if DEST.exists():raise FileExistsError('Preserve stream receiver preparation.')
    DEST.mkdir()
    preserved={name:sha(ROOT/name) for name in ['.runtime-node-lifecycle-v2/bin/OpenSpace.exe','evidence/built-runtime-node-lifecycle-v2.json','user/sessions/latest.json']}
    before={name:sha(UP/name) for name in NAMES}
    with zipfile.ZipFile(DEST/'before-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in NAMES:
            path=DEST/'before'/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(UP/name,path);archive.write(path,name)
    (DEST/'preparation.json').write_text(json.dumps({'schema':1,'before_sha256':before,'preserved_sha256':preserved,'contract_sha256':sha(ROOT/'IS-4-TRANSPORTE-NATIVO-CONTRATO.md')},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'archived':True,'preserved':True}))


if __name__=='__main__':main()
