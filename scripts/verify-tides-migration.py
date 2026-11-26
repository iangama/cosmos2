"""Real pre-material archives migrate without mutation or automatic material."""
from pathlib import Path
import hashlib,json,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
import rebound
from session import Session
from gravity_harmonics import copied
from material_driver import phase

paths=[ROOT/'user/sessions/latest.json']
paths+=sorted((ROOT/'output/c211-j2-native-fixtures').glob('*/latest.json'))
older=next(p for p in sorted((ROOT/'output/c211-branches-native-fixtures').glob('*/latest.json')) if json.loads(p.read_text()).get('body_count')==3)
paths.append(older);cases=[]
for path in paths:
    manifest=json.loads(path.read_text());binary=path.parent/manifest['binary']
    originals={path:hashlib.sha256(path.read_bytes()).hexdigest(),binary:hashlib.sha256(binary.read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory(prefix='cosmos2-tides-migration-') as folder:
        target=Path(folder);shutil.copy2(path,target/'latest.json');shutil.copy2(binary,target/binary.name)
        expected=copied(lambda:rebound.Simulation(str(binary)),allow_pointer_warning=bool(manifest.get('gravity_effects')))
        s=Session(target,2);s.load();state=s.state()
        assert s._tides is None and state['material_tides'] is None
        assert phase(s.sim)==phase(expected) and s.sim.t==expected.t
        if manifest.get('schema')==3:
            assert s.instrument_history==manifest['instrument_history'] and s.gravity_effects==manifest.get('gravity_effects',{})
            assert s.conservation_reference==manifest['conservation_reference']
        # Re-saving/reading a migrated archive must preserve physical phase,
        # history and the known J2 callback, with material still disabled.
        before=phase(s.sim);history=s.instrument_history
        s.save();t=Session(target,2);t.load()
        assert phase(t.sim)==before and t.instrument_history==history and t._tides is None
        cases.append({'source':str(path.relative_to(ROOT)),'saved_version':manifest.get('saved_generation',{}).get('model_version'),'saved_schema':manifest['schema'],'bodies':s.sim.N,'J2_active':bool(s.gravity_effects),'phase_history_reference_exact':True,'material_disabled':True,'roundtrip_exact':True})
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in originals.items())
report={'status':'installed3_10_real_checkpoint_migration_verified','cases':cases,'original_files_unchanged':True,'owner_pointer_sha256':hashlib.sha256(paths[0].read_bytes()).hexdigest()}
(ROOT/'evidence/tides-migration-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
