"""Bounded geometric JPL states and confirmed native Atlas epoch commands."""
from pathlib import Path
import datetime
import hashlib
import importlib.metadata
import json
import math
import re
import threading
import time

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
BODIES={'Sun':('10','Sol',None),'Earth':('399','Terra','IAU_EARTH'),'Moon':('301','Lua','IAU_MOON'),'Saturn':('699','Saturno','IAU_SATURN')}
KERNELS=['naif0012.tls','pck00011.tpc','de442s.bsp','saturn-center-sat441.bsp']
LOCK=threading.RLock();SPICE=None;COVERAGE={};PROVENANCE=None

def initialize():
    global SPICE,PROVENANCE
    if SPICE is not None:return
    import spiceypy as spice
    receipt=json.loads((ROOT/'evidence/atlas-kernels-acquisition.json').read_text())
    hashes={}
    for name in KERNELS:
        path=ROOT/'data/spice'/name;sha=hashlib.sha256(path.read_bytes()).hexdigest()
        expected=json.loads((ROOT/'evidence/saturn-subset.json').read_text())['sha256'] if name=='saturn-center-sat441.bsp' else receipt['files'][name]['sha256']
        if sha!=expected:raise ValueError('Kernel local difere do recibo: '+name)
        hashes['data/spice/'+name]=sha;spice.furnsh(str(path))
    start=spice.str2et('1950-01-01T00:00:00');end=spice.str2et('2050-12-31T23:59:59')
    for node,(target,_,_) in BODIES.items():
        intervals=spice.spkcov(str(ROOT/'data/spice'/('saturn-center-sat441.bsp' if node=='Saturn' else 'de442s.bsp')),int(target))
        segments=[list(spice.wnfetd(intervals,i)) for i in range(spice.wncard(intervals))]
        if not any(a<=start and b>=end for a,b in segments):raise ValueError('Cobertura insuficiente para '+node)
        COVERAGE[node]=segments
    PROVENANCE={'kernels_sha256':hashes,'code_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['app/atlas.py','app/atlas_properties.py','user/data/assets/cosmos2/atlas.asset','user/data/assets/cosmos2/atmosphere.asset']},
                'spiceypy':importlib.metadata.version('spiceypy'),'cspice':spice.tkvrsn('TOOLKIT'),
                'sources':['https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de442_tech-comments.txt',
                           'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de442s.mrg',
                           'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls',
                           'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc',
                           'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat459.bsp']}
    SPICE=spice

def normalize_epoch(utc):
    if not isinstance(utc,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z?',utc):
        raise ValueError('Informe uma época UTC no formato AAAA-MM-DDTHH:MM:SS.')
    utc=utc.removesuffix('Z')
    try:date=datetime.datetime.fromisoformat(utc)
    except ValueError:raise ValueError('Data/hora UTC inválida.') from None
    if not 1950<=date.year<=2050:raise ValueError('Atlas inicial disponível de 1950 a 2050.')
    return utc

def states(utc=None,et=None):
    with LOCK:
        initialize()
        if utc is not None:et=float(SPICE.str2et(normalize_epoch(utc)))
        elif isinstance(et,bool) or not isinstance(et,(int,float)) or not math.isfinite(et):
            raise ValueError('Época TDB inválida.')
        utc=SPICE.et2utc(et,'ISOC',3)
        normalize_epoch(utc)
        bodies=[]
        to_render=SPICE.pxform('J2000','GALACTIC',et)
        for node,(target,name,frame) in BODIES.items():
            state,_=SPICE.spkezr(target,et,'J2000','NONE','0')
            bodies.append({'id':'sol:naif:'+target,'naif_id':target,'scene_node':node,'name':name,
                           'position_m':(state[:3]*1000).tolist(),'velocity_m_s':(state[3:]*1000).tolist(),
                           'position_render_m':(to_render@state[:3]*1000).tolist(),
                           'coverage_et_s':COVERAGE[node],
                           'body_frame':frame,'body_to_j2000':SPICE.pxform(frame,'J2000',et).tolist() if frame else None,
                           'shape':{'origin':'adopted_reference_shape','radii_m':[6378137,6378137,6356752.314245],'model':'WGS84'} if node=='Earth' else
                                   {'origin':'adopted_reference_sphere','radius_m':1737400} if node=='Moon' else
                                   {'origin':'model_reference_ellipsoid','radii_m':(SPICE.bodvrd('699','RADII',3)[1]*1000).tolist(),'model':'PCK00011 BODY699_RADII'} if node=='Saturn' else None})
        epoch={'utc':utc+'Z','et_tdb_s':et,'origin':'explicit model epoch',
               'utc_conversion':'naif0012 fixed leap-second table; future leaps unknown; pre-1972 UTC follows SPICE convention'}
        from atlas_properties import records
        from packages import store
        for body in bodies:
            body['properties']=records(body,epoch,PROVENANCE)
        by_node={b['scene_node']:b for b in bodies}
        difference=[a-b for a,b in zip(by_node['Moon']['position_m'],by_node['Earth']['position_m'])]
        return {'schema':1,'model':'JPL DE442s + SAT441 geometric ephemerides','epoch':epoch,
                'frame':'J2000/ICRF','render_frame':'GALACTIC','j2000_to_render_frame':to_render.tolist(),
                'matrix_layout':'row-major, acts on column vectors',
                'center_naif_id':'0','aberration':'NONE','position_unit':'m','velocity_unit':'m/s',
                'observer':{'kind':'geometric_simultaneous_coordinate_state','coordinate_origin_naif_id':'0',
                            'origin_definition':'Solar System Barycenter; coordinate origin, not a camera or observing body',
                            'state_epoch_et_tdb_s':et,'aberration':'NONE','light_time_applied':False,
                            'emission_et_tdb_s':None,'reception_et_tdb_s':None,
                            'reason':'No apparent observation computed; all bodies evaluated at the same coordinate epoch.'},
                'packages_manifest_sha256':store().manifest_sha256,
                'application_coverage_utc':['1950-01-01T00:00:00Z','2050-12-31T23:59:59Z'],
                'bodies':bodies,'earth_moon_separation_m':math.sqrt(sum(v*v for v in difference)),
                'source_uncertainty':'not locally propagated; numerical agreement is not observational accuracy',
                'rotation_scope':'IAU_EARTH/IAU_MOON/IAU_SATURN general PCK models; not precise ITRF/lunar binary orientation',
                'cross_scenario_coupling':'none','provenance':PROVENANCE}

class Atlas:
    def __init__(self):
        self.lock=threading.Lock();self.connection=None;self.topic=0
    def close(self):
        with self.lock:
            if self.connection:self.connection.close();self.connection=None
    def _lua(self,code):
        from websockets.sync.client import connect
        try:
            if self.connection is None:
                log=ROOT/'output/engine.log'
                if not log.exists() or b'Running Global initialization scripts' not in log.read_bytes():
                    raise RuntimeError('O Atlas aguarda a inicialização da cena.')
                self.connection=connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None)
                self.connection.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            self.topic+=1
            self.connection.send(json.dumps({'topic':self.topic,'type':'luascript','payload':{'script':code,'return':True}}))
            response=json.loads(self.connection.recv(timeout=5))
            value=response.get('payload',{}).get('1')
            if response.get('topic')!=self.topic or not isinstance(value,dict):raise RuntimeError('O motor não confirmou o estado do Atlas.')
            return value
        except Exception:
            if self.connection:self.connection.close();self.connection=None
            raise
    def _read(self):
        return self._lua('return {et=openspace.time.currentTime(),utc=openspace.time.UTC(),paused=openspace.time.isPaused(),positions={Sun=openspace.worldPosition("Sun"),Earth=openspace.worldPosition("Earth"),Moon=openspace.worldPosition("Moon"),Saturn=openspace.worldPosition("Saturn")}}')
    def status(self):
        with self.lock:
            native=self._read();result=states(et=native['et']);result['renderer']=native;return result
    def apply_epoch(self,utc):
        # Validate and calculate before mutating the renderer. setTime applies next frame.
        result=states(utc=utc);et=result['epoch']['et_tdb_s']
        with self.lock:
            self._lua(f'openspace.time.setPause(true);openspace.time.setTime({et:.17g});return {{queued=true}}')
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                native=self._read()
                if native['paused'] and abs(native['et']-et)<1e-7:
                    expected={b['scene_node']:b['position_render_m'] for b in result['bodies']}
                    if all(max(abs(a-b) for a,b in zip(native['positions'][name],position))<=.001 for name,position in expected.items()):
                        result['renderer']=native;return result
                time.sleep(.02)
            raise TimeoutError('Época solicitada, mas o motor não confirmou as posições. Consulte o Atlas antes de repetir.')
