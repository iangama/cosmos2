"""Pure admission of C2-14 benchmark identity, animation and raw sample timing."""
import hashlib
import json
import math

import expanded_residency_contract_v4 as native
import expanded_residency_timing as timing

require = native.require
LIMITS = dict(median_ms=16.7, p95_ms=25., p99_ms=50., over_100ms=0,
              RAM_bytes=8*2**30, GPU_bytes=5.5*2**30)
PARAMETERS = dict(mass_solar=10., semi_latus_rectum_rs=1000., eccentricity=.6,
                  radial_cycles=8, orientation='positive')
WINDOWS = [dict(name=name, view=view, orbit=orbit, orbit_kind=kind)
           for name, view, orbit, kind in [
               ('eccentric-orbit', 'orbits', True, 'eccentric'),
               ('eccentric-clocks', 'clocks', True, 'eccentric'),
               ('straight-clocks', 'clocks', False, 'eccentric'),
               ('circular-orbit', 'orbits', True, 'circular')]]

UI_EXPRESSION = '''(() => ({url:location.href,pending,configuration:config,
physics_sha256:response?.physics_sha256,configuration_sha256:response?.configuration_sha256,
view:byId('timelike-view').value,zoom:Number(getComputedStyle(document.body).zoom),
width:innerWidth,height:innerHeight,hidden:document.hidden,playing:animating,
index:Number(byId('time-index').value),max:Number(byId('time-index').max),
reading:response?.result.timelike?.readings[Number(byId('time-index').value)],
time_s:response?.result.time_s[Number(byId('time-index').value)],
canvas:{width:canvas.width,height:canvas.height},
viewport:{top:byId('viewport').getBoundingClientRect().top,bottom:byId('viewport').getBoundingClientRect().bottom},
profile:window.__c214Profile?{...window.__c214Profile}:null,
error:byId('force-status').classList.contains('error')}))()'''

ANIMATION_EXPRESSION = '''(() => {
if(window.__c214Profile)throw Error('Animation observer already exists');
window.__c214Profile={enabled:true,ticks:0,advances:0,loops:0,last_index:null,started_ms:performance.now(),now_ms:performance.now()};
function observe(){const p=window.__c214Profile;if(!p.enabled)return;
p.ticks++;p.now_ms=performance.now();const index=Number(byId('time-index').value);
if(p.last_index!==null&&index!==p.last_index)p.advances++;
p.last_index=index;
if(!pending&&!animating&&index===lastTimeIndex()){p.loops++;byId('animate').click();}
requestAnimationFrame(observe);}
if(!animating)byId('animate').click();requestAnimationFrame(observe);return true;
})()'''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def service(value, body_sha256):
    require(value['schema'] == 1 and value['phase'] == 'complete' and value['busy'] is False and value['error'] is None,
            'Timelike worker is not complete and idle')
    require(value['job_id'] and value['published_job_id'] == value['job_id'], 'Published job differs')
    result = value['result']
    require(result['ok'] is True and result['configuration'] == value['configuration'], 'Published configuration differs')
    require(result['configuration_sha256'] == digest(result['configuration']), 'Configuration hash differs from content')
    physics = dict(model=result['scientific_contract'], parameters=result['configuration']['parameters'],
                   applied_effects=result['result']['applied_effects'])
    require(result['physics_sha256'] == digest(physics), 'Physics fingerprint differs from its scientific record')
    require(result['configuration']['scenario'] == 'timelike-orbits' and len(result['result']['time_s']) == 1025,
            'Unexpected scientific bench/result length')
    return dict(job_id=value['job_id'], edit_token=value['edit_token'], revision=value['revision'],
                body_sha256=body_sha256, configuration=value['configuration'],
                configuration_sha256=result['configuration_sha256'], physics_sha256=result['physics_sha256'],
                kernel_configuration=result['result']['timelike']['configuration'],
                orbit_effect_applied=result['result']['timelike']['orbit_effect_applied'],
                clock_effect_applied=result['result']['timelike']['clock_effect_applied'])


def admit_service(value, recipe, expected=None):
    parameters = PARAMETERS | dict(orbit_kind=recipe['orbit_kind'])
    require(value['configuration']['parameters'] == parameters, 'Benchmark parameters differ')
    control = value['configuration']['controls']['gravity']
    require(control['acting'] is True and control['visible'] is True and
            control['effects']['orbital_acceleration'] is recipe['orbit'] and control['effects']['proper_clock_rate'] is True,
            'Benchmark operators/visibility differ')
    kernel = dict(mu_m3_s2=10*1.3271244e20, semi_latus_rectum_rs=1000,
                  eccentricity=0 if recipe['orbit_kind'] == 'circular' else .6,
                  source_radius_rs=1, radial_cycles=8, output_samples=1025, orientation=1)
    require(value['kernel_configuration'] == kernel and value['orbit_effect_applied'] is recipe['orbit'] and
            value['clock_effect_applied'] is True, 'Scientific kernel/actual operators differ from the public controls')
    if expected is not None:
        require(value == expected, 'Published job/result changed within a window')


def admit_ui(value, expected, recipe, result=None):
    require(value['url'] == 'http://127.0.0.1:4700/forces.html#timelike-orbits' and
            value['pending'] is False and value['hidden'] is False and value['error'] is False,
            'Native CEF bench absent, pending, hidden or faulted')
    require(value['configuration'] == expected['configuration'] and value['physics_sha256'] == expected['physics_sha256'] and
            value['configuration_sha256'] == expected['configuration_sha256'], 'CEF shows another scientific result')
    require(value['view'] == recipe['view'] and value['zoom'] == 1 and value['width'] == 1920 and value['height'] == 1080,
            'Native CEF view/zoom/dimensions differ')
    require(value['playing'] is True and value['max'] == 1024 and type(value['index']) is int and 0 <= value['index'] <= 1024,
            'Native animation/timeline differs')
    require(value['canvas']['width'] > 0 and value['canvas']['height'] > 0 and
            0 <= value['viewport']['top'] < value['viewport']['bottom'] <= 1080, 'Viewport not fully presented')
    profile = value['profile']
    require(profile and profile['enabled'] is True and profile['ticks'] > 0 and profile['advances'] > 0,
            'Animation observer has no progress')
    for key in ['ticks', 'advances', 'loops']:
        require(type(profile[key]) is int and profile[key] >= 0, 'Invalid animation counter')
    require(math.isfinite(profile['now_ms']) and profile['now_ms'] >= profile['started_ms'], 'CEF clock reversed')
    if result is not None:
        require(value['reading'] == result['timelike']['readings'][value['index']] and
                value['time_s'] == result['time_s'][value['index']], 'Displayed instant/readings differ from published data')


def admit_row(row, previous, index):
    duration, gap = timing.admit_row(row, previous, index)
    if gap is not None:
        require(.85 <= gap <= 1.15, 'C2-14 raw cadence outside sealed bounds')
    return duration, gap


def animation(first, last, seconds):
    a, b = first['profile'], last['profile']
    require(0 <= b['now_ms']-a['now_ms'] and abs((b['now_ms']-a['now_ms'])/1000-seconds) < 1,
            'Animation/wall clocks disagree')
    require(b['ticks'] > a['ticks'] and b['advances']-a['advances'] >= 1000 and b['loops']-a['loops'] >= 4,
            'Animation did not advance continuously through repeated full paths')
    return dict(advances=b['advances']-a['advances'], loops=b['loops']-a['loops'], ticks=b['ticks']-a['ticks'])
