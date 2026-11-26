"""Load a copied pre-vector checkpoint with the vector candidate; preserve exact phase."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-body-vector-product/app'
sys.path.insert(0,str(APP))
from session import Session
import rebound

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is3-vector-migration-20261024'
    receipt=ROOT/'evidence/is3-vector-migration-20261024.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve migration evidence.')
    folder.mkdir()
    source=ROOT/'output/is3-tides-product/gravity-sessions'
    manifest=json.loads((source/'latest.json').read_text(encoding='utf-8'))
    original={name:sha(source/name) for name in ['latest.json',manifest['binary']]}
    owner=sha(ROOT/'user/sessions/latest.json')
    for name in original:shutil.copy2(source/name,folder/name)
    paths=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[Path(__file__).resolve()]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    raw=rebound.Simulation(str(folder/manifest['binary']))
    phase=lambda sim:[(p.m,p.x,p.y,p.z,p.vx,p.vy,p.vz) for p in sim.particles]
    session=Session(folder);session.load();state=session.state()
    assert state['restoration']['status']=='changed_generation'
    assert state['scientific_generation']['candidate_extension']['version']=='0.4.0'
    assert state['atlas_initial']==manifest['atlas_initial']
    assert session.sim.t==raw.t and phase(session.sim)==phase(raw)
    guard={k:state[k] for k in ['system_id','edit_token','revision']}|{'expected_time':state['time'],'frame':state['contract']['frame']}
    earth=next(b for b in state['bodies'] if b['reference_id']=='sol:naif:399')
    jupiter=next(b for b in state['bodies'] if b['reference_id']=='sol:naif:599')
    earth_reading=session.earth_field({**guard,'body_id':earth['id'],'latitude_deg':0.,'longitude_deg':0.,'altitude_m':0.})
    jupiter_reading=session.jupiter_field({**guard,'body_id':jupiter['id'],'radius_m':71492000.,'latitude_deg':0.,'east_longitude_deg':0.,'degree':13})
    assert earth_reading['field_norm_T']>0 and jupiter_reading['field_norm_T']>0
    assert phase(session.sim)==phase(raw) and session.sim.t==raw.t
    assert all(sha(source/name)==digest and sha(folder/name)==digest for name,digest in original.items())
    assert sha(ROOT/'user/sessions/latest.json')==owner
    assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
    receipt.write_text(json.dumps({'schema':1,'accepted':True,'source_sha256':hashes,
        'original_checkpoint_sha256':original,'old_generation':manifest['saved_generation']['candidate_extension'],
        'restoration':state['restoration'],'exact_binary_phase_time_and_initial_source_preserved':True,
        'IGRF_JRM_readings_available_without_orbital_mutation':True,'old_copy_and_owner_not_rewritten':True,
        'scope':'Copied old scientific checkpoint under0.4; no visual layer persistence or integrator revalidation claim.'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':True,'exact_phase_preserved':True,'restoration':state['restoration']['status']}))


if __name__=='__main__':main()
