"""SI consistency and legacy/explicit-binding checkpoint compatibility."""
from pathlib import Path
import json
import math
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from physics import PHYSICAL_SCALE,fixture
from session import Session
u=PHYSICAL_SCALE
assert math.isclose(u['G_m3_kg_s2']*u['mass_unit_kg']*u['time_unit_s']**2/u['length_unit_m']**3,1,rel_tol=1e-14)
assert math.isclose(u['nominal_GM_unit_m3_s2']*u['time_unit_s']**2/u['length_unit_m']**3,1,rel_tol=1e-14)
assert math.isclose(u['velocity_unit_m_s']*u['time_unit_s'],u['length_unit_m'],rel_tol=1e-14)
period=2*math.pi*u['time_unit_s']/math.sqrt(1+1e-8)
assert math.isclose(period,2*math.pi*math.sqrt(u['length_unit_m']**3/(u['nominal_GM_unit_m3_s2']*(1+1e-8))),rel_tol=1e-14)
with tempfile.TemporaryDirectory(prefix='cosmos2-units-') as directory:
    session=Session(directory);session.sim.integrate(.5);session.save()
    state=session.state();p=Path(directory)/'latest.json';manifest=json.loads(p.read_text())
    assert manifest['physical_scale']==u
    session.load();assert session.state()==state
    bad={**manifest,'physical_scale':{**u,'length_unit_m':u['length_unit_m']*2}}
    p.write_text(json.dumps(bad))
    try:session.load()
    except ValueError as error:assert 'SI binding' in str(error)
    else:raise AssertionError('Accepted incompatible SI binding')
    assert session.state()==state
    del manifest['physical_scale'];p.write_text(json.dumps(manifest))
    session.load();assert session.state()==state
report={'si_binding':u,'G_canonical_consistent':True,'two_body_period_s':period,
        'explicit_binding_round_trip':True,'incompatible_binding_rejected_without_mutation':True,
        'legacy_canonical_checkpoint_preserved':True,
        'scope':'fixed point-mass experiment unit binding; no observed Solar System epoch'}
(ROOT/'evidence/canonical-units-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
