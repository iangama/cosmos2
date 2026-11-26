"""Exercise C2-14 profile refusals without opening native windows or collecting gauges."""
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path

import c214_profile_contract as c

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out = ROOT/'evidence/c214-profile-admission-20261114a.json'
    assert not out.exists()
    source = ROOT/'output/c214-profile-admission-fixture-20261114a/export.json'
    published = json.loads(source.read_text())
    status = dict(schema=1, phase='complete', busy=False, error=None, job_id='offline-fixture',
                  published_job_id='offline-fixture', edit_token='offline-token', revision=4,
                  configuration=published['configuration'], result=published)
    recipe = c.WINDOWS[-1]
    expected = c.service(status, 'offline-body-sha')
    c.admit_service(expected, recipe)
    ui = dict(url='http://127.0.0.1:4700/forces.html#timelike-orbits', pending=False,
              configuration=published['configuration'], physics_sha256=published['physics_sha256'],
              configuration_sha256=published['configuration_sha256'], view='orbits', zoom=1,
              width=1920, height=1080, hidden=False, playing=True, index=512, max=1024,
              reading=published['result']['timelike']['readings'][512], time_s=published['result']['time_s'][512],
              canvas=dict(width=1480,height=540), viewport=dict(top=261,bottom=801), error=False,
              profile=dict(enabled=True,ticks=400,advances=150,loops=1,last_index=512,started_ms=0,now_ms=6000))
    c.admit_ui(ui, expected, recipe, published['result'])
    refused = []

    def refusal(name, action):
        try:
            action()
        except (ValueError, KeyError, TypeError) as error:
            refused.append(dict(name=name,error=str(error)))
        else:
            raise AssertionError('Unexpected admission: '+name)

    for name, path, value in [('busy',['busy'],True),('failed',['phase'],'failed'),
                              ('foreign_job',['published_job_id'],'another'),('worker_error',['error'],'failure'),
                              ('unpublished',['job_id'],None),('different_configuration',['configuration'],{})]:
        changed=copy.deepcopy(status)
        changed[path[0]]=value
        refusal(name,lambda changed=changed:c.service(changed,'offline-body-sha'))
    for name,path,value in [('mass',['configuration','parameters','mass_solar'],11),
                            ('orbit_kind',['configuration','parameters','orbit_kind'],'eccentric'),
                            ('hidden_reference',['configuration','controls','gravity','visible'],False),
                            ('clock_off',['configuration','controls','gravity','effects','proper_clock_rate'],False),
                            ('orbit_off',['configuration','controls','gravity','effects','orbital_acceleration'],False)]:
        changed=copy.deepcopy(expected);target=changed
        for key in path[:-1]:target=target[key]
        target[path[-1]]=value
        refusal(name,lambda changed=changed:c.admit_service(changed,recipe,expected))
    for key,value in [('url','http://127.0.0.1:4700/'),('pending',True),('hidden',True),('error',True),
                      ('playing',False),('view','clocks'),('zoom',1.5),('width',1280),('height',720),
                      ('index',1025),('max',240),('profile',None),('physics_sha256','foreign')]:
        changed=copy.deepcopy(ui);changed[key]=value
        refusal('ui_'+key,lambda changed=changed:c.admit_ui(changed,expected,recipe,published['result']))
    changed=copy.deepcopy(ui);changed['reading']['applied_lag_s']+=1
    refusal('wrong_reading',lambda:c.admit_ui(changed,expected,recipe,published['result']))
    changed=copy.deepcopy(ui);changed['viewport']['bottom']=1100
    refusal('clipped_viewport',lambda:c.admit_ui(changed,expected,recipe,published['result']))
    start=dt.datetime(2026,11,14,tzinfo=dt.timezone.utc)
    def sample(index,offset):
        a=start+dt.timedelta(seconds=offset)
        return dict(index=index,monotonic_offset_s=offset,started_utc=a.isoformat(),
                    utc=(a+dt.timedelta(seconds=.02)).isoformat(),finished_utc=(a+dt.timedelta(seconds=.05)).isoformat(),
                    phase_before=dict(id='same'),phase_after=dict(id='same'),boundary=False)
    first=sample(0,0);c.admit_row(first,None,0);c.admit_row(sample(1,1),first,1)
    for gap in [.84,1.16,.1,2]:
        refusal('cadence_'+str(gap),lambda gap=gap:c.admit_row(sample(1,gap),first,1))
    changed=copy.deepcopy(first);changed['finished_utc']=(start+dt.timedelta(seconds=1.01)).isoformat()
    refusal('overlong_raw_sample',lambda:c.admit_row(changed,None,0))
    frame=dict(width=1920,height=1080,invalid_samples=0,capacity_reached=False,samples_s=[1/75]*4501)
    c.native.frames(frame,60,steady=True)
    for name,key,value in [('truncated','capacity_reached',True),('invalid','invalid_samples',1),('wrong_size','width',1280)]:
        changed=copy.deepcopy(frame);changed[key]=value
        refusal(name,lambda changed=changed:c.native.frames(changed,60,steady=True))
    changed=copy.deepcopy(frame);changed['samples_s'][2000]=.101
    refusal('single_stall',lambda:c.native.frames(changed,60,steady=True))
    changed=copy.deepcopy(frame);changed['samples_s'][100]=float('nan')
    refusal('nan_frame',lambda:c.native.frames(changed,60,steady=True))
    end=copy.deepcopy(ui);end['profile'].update(now_ms=66000,ticks=5000,advances=1650,loops=6)
    c.animation(ui,end,60)
    frozen=copy.deepcopy(ui);frozen['profile']['now_ms']=66000
    refusal('stopped_animation',lambda:c.animation(ui,frozen,60))
    proof=dict(accepted=True,completed=True,refusals=refused,groups=5,
               source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),ROOT/'scripts/c214_profile_contract.py',source]},
               scope='Offline profile identity/timing/playback/frame admission only; no new native performance acceptance')
    out.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=True,refusals=len(refused),groups=5)))


if __name__=='__main__':main()
