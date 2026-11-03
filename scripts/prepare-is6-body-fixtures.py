"""Archive two actual paused orbital phases for spherical-reference binding."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is5-compression-product0.17.2/app'
sys.path.insert(0,str(APP))
from session import Session
from physics import PHYSICAL_SCALE


def main():
    folder=ROOT/'output/is6-body-fixtures-20261101a'
    if folder.exists():raise FileExistsError('Preserve body fixtures')
    folder.mkdir()
    original=ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json'
    initial=json.loads(original.read_text())['phase']['atlas_initial']
    session=Session(folder/'isolated-session');session.import_atlas(initial)
    phases=[{**session.state(),'paused':True}]
    session.sim.integrate(86400/PHYSICAL_SCALE['time_unit_s'])
    phases.append({**session.state(),'paused':True})
    result=dict(schema=1,accepted=False,phases=phases,elapsed_between_phases_s=86400.,
                origin=dict(path=original.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(original.read_bytes()).hexdigest()),
                independent_radii_m={'sol:naif:10':[695700000.,695700000.,695700000.],
                    'sol:naif:399':[6378136.6,6378136.6,6356751.9],
                    'sol:naif:301':[1737400.,1737400.,1737400.],
                    'sol:naif:599':[71492000.,71492000.,66854000.]})
    (folder/'fixtures-before-execution.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(prepared=True,accepted=False,phases=len(phases),folder=str(folder))))


if __name__=='__main__':main()
