"""Checkpoint and intervention acceptance checks, using native REBOUND state."""
from pathlib import Path
import json
import math
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from session import Session

with tempfile.TemporaryDirectory(prefix='cosmos2-check-') as temporary:
    session=Session(temporary)
    session.sim.integrate(1)
    old_mass=session.sim.particles[0].m
    old_vectors=[(p.x,p.y,p.z,p.vx,p.vy,p.vz) for p in session.sim.particles]
    old_energy=session.sim.energy()
    event=session.set_mass('p0',2.0)
    assert old_vectors==[(p.x,p.y,p.z,p.vx,p.vy,p.vz) for p in session.sim.particles]
    assert event['external_energy_delta']==session.sim.energy()-old_energy
    assert event['external_momentum_delta']==[(2-old_mass)*v for v in old_vectors[0][3:]]
    unchanged=session.state()
    for invalid in (True,False,float('nan'),float('inf'),-1,0,101,'2'):
        try:session.set_mass('p0',invalid)
        except ValueError:pass
        else:raise AssertionError(f'Accepted invalid mass: {invalid}')
        assert session.state()==unchanged
    session.save()
    session.sim.integrate(2)
    expected=session.state()
    session.load()
    assert session.sim.t==1 and session.revision==1
    session.sim.integrate(2)
    actual=session.state()
    maximum=max(abs(a-b) for p,q in zip(expected['bodies'],actual['bodies'])
        for key in ('position','velocity') for a,b in zip(p[key],q[key]))
    assert maximum < 1e-12, maximum
    manifest=json.loads((Path(temporary)/'latest.json').read_text())
    binary=Path(temporary)/manifest['binary']
    content=bytearray(binary.read_bytes());content[len(content)//2]^=1;binary.write_bytes(content)
    unchanged=session.state()
    try:session.load()
    except ValueError as error:assert 'checksum' in str(error)
    else:raise AssertionError('Corrupted checkpoint was accepted')
    assert unchanged==session.state()
    result={'native_platform':sys.platform,'external_intervention_accounted':True,
            'invalid_masses_rejected':8,'checkpoint_continuation_max_error':maximum,
            'corrupt_checkpoint_rejected_without_state_change':True}
(ROOT/'evidence'/'session-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
