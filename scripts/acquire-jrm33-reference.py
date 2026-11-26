"""Preserve pinned PSH community reference sources for JRM33 research only."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'output/is3-jrm33-staging'
COMMIT='cf7e712e39a45a14905d13d21978043026089a4e'
BASE='https://raw.githubusercontent.com/rjwilson-LASP/PSH/'+COMMIT+'/'
FILES=['LICENSE','CITATION.cff','README.md','Mother_Source/MOP_spherical.py','Mother_Source/reordergh.py',
    'Jupiter/Python/jovian_jrm33_order13_internal_rtp.py','Jupiter/Python/jovian_jrm33_order13_internal_xyz.py',
    'Jupiter/Python/jovian_jrm33_order18_internal_rtp.py','Jupiter/Python/jovian_jrm33_order18_internal_xyz.py']


def main():
    receipt=ROOT/'evidence/is3-jrm33-reference-acquisition-20261023.json'
    if DEST.exists() or receipt.exists():raise FileExistsError('Preserve previous reference acquisition.')
    DEST.mkdir();records={}
    report={'schema':1,'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'PSH_commit':COMMIT,
        'primary_community_link':'https://lasp.colorado.edu/mop/missions/juno/community-code/',
        'files':records,'completed':False,'scope':'Pinned external reference in staging, not product code or scene-model adoption.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    persist()
    for name in FILES:
        target=DEST/'upstream-PSH'/name;target.parent.mkdir(parents=True,exist_ok=True)
        url=BASE+name
        with urllib.request.urlopen(url,timeout=30) as response:raw=response.read()
        assert 0<len(raw)<2*1024*1024
        target.write_bytes(raw)
        records[name]={'url':url,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};persist()
    report['completed']=True;report['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'files':len(records),'bytes':sum(v['bytes'] for v in records.values())}))

if __name__=='__main__':main()
