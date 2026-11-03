"""Real older archives migrate to passive orbital instruments, without mutation."""
from pathlib import Path
import copy,hashlib,json,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
import rebound
from session import Session
from gravity_harmonics import copied
from material_driver import phase
paths=[ROOT/'user/sessions/latest.json']
for folder in ('c211-tides-native-fixtures','c211-j2-native-fixtures'):
    paths+=sorted((ROOT/'output'/folder).glob('*/latest.json'))
cases=[]
for path in paths:
    m=json.loads(path.read_text());binary=path.parent/m['binary']
    originals={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (path,binary)}
    with tempfile.TemporaryDirectory(prefix='cosmos2-orbital-migration-') as folder:
        target=Path(folder);shutil.copy2(path,target/'latest.json');shutil.copy2(binary,target/binary.name)
        expected=copied(lambda:rebound.Simulation(str(binary)),allow_pointer_warning=bool(m.get('gravity_effects')))
        s=Session(target,2);s.load();assert phase(s.sim)==phase(expected)
        assert s.orbital_instruments['definition'] is None and not s.orbital_instruments['samples'] and not s.orbital_instruments['recording']
        before=phase(s.sim);history=copy.deepcopy(s.instrument_history);material=None if s._tides is None else s._tides.checkpoint()
        if m['schema']==3:assert history==m['instrument_history'] and s.conservation_reference==m['conservation_reference']
        s.save();t=Session(target,2);t.load()
        assert phase(t.sim)==before and t.instrument_history==history and t.gravity_effects==s.gravity_effects
        assert (None if t._tides is None else t._tides.checkpoint())==material
        # The same future target also exercises restoration of a material ODE.
        goal=s.sim.t+.01;s.integrate(goal);t.integrate(goal);assert phase(s.sim)==phase(t.sim)
        cases.append({'source':str(path.relative_to(ROOT)),'version':m.get('saved_generation',{}).get('model_version'),'schema':m['schema'],'bodies':s.sim.N,'material_active':material is not None,'old_phase_history_reference_preserved':True,'roundtrip_future_exact':True,'orbital_capture_disabled':True})
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in originals.items())
report={'status':'installed3_11_real_checkpoint_migration_verified','cases':cases,'original_files_unchanged':True,'owner_pointer_sha256':hashlib.sha256(paths[0].read_bytes()).hexdigest()}
(ROOT/'evidence/resonance-migration-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
