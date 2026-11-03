"""Confirmed camera commands, bounded Atlas clock and sealed local viewpoints."""
from pathlib import Path
import copy
import hashlib
import json
import math
import os
import threading
import time
import uuid
import numpy as np
from atlas import ROOT, states, normalize_epoch

DESTINATIONS={
    'Earth':('Earth',[17674090.653605793,-1566585.5066504919,18170644.716643292]),
    'Moon':('Moon',[-4500000,-5000000,3000000]),
    'Saturn':('Saturn',[2e8,-1.5e8,1.6e8]),
    'System':('Earth',[190000000,-600000000,320000000]),
    'Galaxy':('MilkyWayVolume',[0,-8e20,9e20])}
ANCHORS={'Sun','Earth','Moon','Saturn','MilkyWayVolume','CosmosFreeAnchor'}
MODES={'orbit','follow','free'}

def vec(value):
    if not isinstance(value,list) or len(value)!=3 or any(type(v) not in (float,int) or not math.isfinite(v) or abs(v)>1e23 for v in value):
        raise ValueError('Vetor de câmera inválido.')
    return np.array(value,dtype=float)

def unit(v):
    n=float(np.linalg.norm(v))
    if n<1e-15:raise ValueError('Direção de câmera degenerada.')
    return v/n

def pose(nav,anchor):
    p=vec(nav['Position']);f=unit(-p);up=unit(vec(nav.get('Up',[0,0,1])))
    r=unit(np.cross(f,up));u=unit(np.cross(r,f))
    yaw,pitch=nav.get('Yaw',0),nav.get('Pitch',0)
    forward=r*math.sin(yaw)*math.cos(pitch)+u*math.sin(pitch)+f*math.cos(yaw)*math.cos(pitch)
    up=-r*math.sin(yaw)*math.sin(pitch)+u*math.cos(pitch)-f*math.cos(yaw)*math.sin(pitch)
    return {'position_render_m':(vec(anchor)+p).tolist(),'forward':unit(forward).tolist(),'up':unit(up).tolist()}

def lua(value):
    if isinstance(value,str):return json.dumps(value)
    if isinstance(value,bool):return str(value).lower()
    if isinstance(value,(int,float)) and math.isfinite(value):return format(value,'.17g')
    if isinstance(value,list):return '{'+','.join(lua(v) for v in value)+'}'
    if isinstance(value,dict):return '{'+','.join(k+'='+lua(v) for k,v in value.items())+'}'
    raise ValueError('Valor Lua inválido.')

def valid_state(nav):
    if not isinstance(nav,dict) or nav.get('Anchor') not in ANCHORS or nav.get('ReferenceFrame')!='Root':raise ValueError('Referencial de câmera inválido.')
    result={'Anchor':nav['Anchor'],'ReferenceFrame':'Root','Position':vec(nav.get('Position')).tolist(),'Up':unit(vec(nav.get('Up'))).tolist()}
    if not 1<=np.linalg.norm(result['Position'])<=1e22:raise ValueError('Distância de câmera fora do domínio.')
    for key in ['Yaw','Pitch']:
        v=nav.get(key,0)
        if type(v) not in (int,float) or not math.isfinite(v) or abs(v)>2*math.pi:raise ValueError('Ângulo de câmera inválido.')
        result[key]=v
    pose(result,[0,0,0])
    return result

def occluded(camera,positions,rotations):
    """Opaque reference ellipsoids occlude a marker's center ray; rings stay transparent."""
    radii={'Earth':[6378137,6378137,6356752.314245],'Moon':[1737400]*3,'Saturn':[60268000,60268000,54364000]}
    hidden=[];camera=vec(camera)
    for target in radii:
        ray=vec(positions[target])-camera;distance=float(np.linalg.norm(ray));direction=ray/max(distance,1)
        for blocker,axes in radii.items():
            if blocker==target:continue
            raw=rotations[blocker]
            rotation=np.array([raw[str(i)] for i in range(1,10)] if isinstance(raw,dict) else raw,dtype=float).reshape(3,3,order='F')
            origin=(rotation.T@(camera-vec(positions[blocker])))/axes;v=(rotation.T@direction)/axes
            a=float(np.dot(v,v));b=2*float(np.dot(origin,v));c=float(np.dot(origin,origin))-1;disc=b*b-4*a*c
            if disc<0:continue
            # The q-form avoids cancellation for nearby and distant blockers.
            q=-.5*(b+math.copysign(math.sqrt(disc),b));roots=[q/a,c/q] if q else [-b/(2*a)]
            if any(0<t<distance for t in roots):hidden.append(target);break
    return hidden

class Navigation:
    def __init__(self,atlas,folder=None):
        self.atlas=atlas;self.lock=threading.RLock();self.mode='orbit';self.target='Earth'
        self.path=Path(folder or ROOT/'user/navigation')/'favorites.json';self.return_view=None;self.boundary=None;self.requested_rate=1
    def _read(self):
        with self.atlas.lock:
            value=self.atlas._lua('local n=openspace.navigation.getNavigationState("Root"); return {navigation=n,anchor_position=openspace.worldPosition(n.Anchor),et=openspace.time.currentTime(),utc=openspace.time.UTC(),paused=openspace.time.isPaused(),rate=openspace.time.deltaTime(),flying=openspace.navigation.isFlying(),positions={Sun=openspace.worldPosition("Sun"),Earth=openspace.worldPosition("Earth"),Moon=openspace.worldPosition("Moon"),Saturn=openspace.worldPosition("Saturn")},rotations={Earth=openspace.worldRotation("Earth"),Moon=openspace.worldRotation("Moon"),Saturn=openspace.worldRotation("Saturn")}}')
        # Some native dictionaries serialize vector entries as keyed arrays.
        for key in ['Position','Up']:
            if isinstance(value['navigation'].get(key),dict):value['navigation'][key]=[value['navigation'][key][str(i)] for i in range(1,4)]
        value['camera']=pose(value['navigation'],value['anchor_position'])
        if self.mode=='free' and value['navigation']['Anchor']!='CosmosFreeAnchor':self.mode='orbit'
        value['occluded_targets']=occluded(value['camera']['position_render_m'],value['positions'],value['rotations'])
        value['effective_rate']=value['rate']
        if not value['paused'] and value['rate']!=0:self.requested_rate=value['rate']
        value['rate']=self.requested_rate
        value.update(mode=self.mode,target=self.target,boundary=self.boundary,return_available=self.return_view is not None)
        return value
    def _script(self,code):
        with self.atlas.lock:return self.atlas._lua(code+';return {queued=true}')
    def status(self):
        with self.lock:
            s=self._read()
            # Keep renderer inside the declared data window, even while UI is closed.
            if not s['paused']:
                from atlas import LOCK, initialize
                import atlas
                with LOCK:
                    initialize();lo=atlas.SPICE.str2et('1950-01-01T00:00:00');hi=atlas.SPICE.str2et('2050-12-31T23:59:59')
                if s['et']<lo or s['et']>hi:
                    endpoint=lo if s['et']<lo else hi
                    self._script(f'openspace.time.setPause(true);openspace.time.setTime({endpoint:.17g})')
                    self.boundary='Limite de cobertura atingido; Atlas pausado.';time.sleep(.04);s=self._read()
            return s
    def _capture(self):
        s=self._read()
        anchor=s['navigation']['Anchor'];target=self.target
        if anchor!='CosmosFreeAnchor' and DESTINATIONS[target][0]!=anchor:
            target=next((name for name,(node,_) in DESTINATIONS.items() if node==anchor),None)
        if target is None:raise ValueError('A vista atual não pertence aos destinos do Atlas.')
        return {'schema':1,'target':target,'mode':'free' if anchor=='CosmosFreeAnchor' else 'follow' if self.mode=='follow' else 'orbit','utc':s['utc'],
                'et':s['et'],'paused':s['paused'],'rate':s['rate'],'navigation':valid_state(s['navigation']),
                'free_anchor_render_m':s['anchor_position'] if s['navigation']['Anchor']=='CosmosFreeAnchor' else None}
    def _confirm(self,nav):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            s=self._read();n=s['navigation']
            if n['Anchor']==nav['Anchor'] and np.linalg.norm(vec(n['Position'])-vec(nav['Position']))<=max(.01,np.linalg.norm(nav['Position'])*1e-12):return s
            time.sleep(.02)
        raise TimeoutError('O motor não confirmou a pose solicitada.')
    def visit(self,target,smooth=False,sunlit=False):
        if target not in DESTINATIONS or type(smooth)!=bool or type(sunlit)!=bool:raise ValueError('Destino/comando inválido.')
        with self.lock:
            self.return_view=self._capture();anchor,position=DESTINATIONS[target]
            if sunlit:
                if target not in {'Earth','Moon','Saturn'}:raise ValueError('Escolha um planeta ou a Lua.')
                s=self._read();d=unit(vec(s['positions']['Sun'])-vec(s['positions'][target]));side=np.cross(d,[0,0,1])
                if np.linalg.norm(side)<1e-8:side=np.array([1.,0,0])
                position=(np.linalg.norm(position)*(math.cos(math.pi/6)*d+math.sin(math.pi/6)*unit(side))).tolist()
            nav={'Anchor':anchor,'ReferenceFrame':'Root','Position':position,'Up':[0,0,1]}
            self._script('openspace.pathnavigation.stopPath();openspace.setPropertyValueSingle("NavigationHandler.OrbitalNavigator.FollowAnchorNodeRotation",false);openspace.navigation.'+('flyToNavigationState' if smooth else 'setNavigationState')+'('+lua(nav)+(',4)' if smooth else ')'))
            self.mode='orbit';self.target=target
            if smooth:
                time.sleep(.08);return self._read()
            return self._confirm(nav)
    def cancel(self):
        with self.lock:self._script('openspace.pathnavigation.stopPath()');return self._read()
    def set_mode(self,mode):
        if mode not in MODES:raise ValueError('Modo de câmera inválido.')
        with self.lock:
            before=self._read();self._script('openspace.pathnavigation.stopPath()')
            if mode=='free':
                p=vec(before['camera']['position_render_m']);f=vec(before['camera']['forward']);up=before['camera']['up'];d=max(1e7,np.linalg.norm(before['navigation']['Position'])*.5)
                self._script('openspace.setPropertyValueSingle("Scene.CosmosFreeAnchor.Translation.Position",'+lua((p+f*d).tolist())+');openspace.navigation.setNavigationState('+lua({'Anchor':'CosmosFreeAnchor','ReferenceFrame':'Root','Position':(-f*d).tolist(),'Up':up})+')')
            elif before['navigation']['Anchor']=='CosmosFreeAnchor':
                anchor=DESTINATIONS[self.target][0];offset=vec(before['camera']['position_render_m'])-vec(before['positions'].get(anchor,[0,0,0]))
                # Restoring the saved navigation basis preserves free-flight heading.
                f=vec(before['camera']['forward']);u=vec(before['camera']['up']);neutral=unit(-offset);r=unit(np.cross(neutral,u));nup=np.cross(r,neutral)
                pitch=math.asin(float(np.clip(np.dot(f,nup),-1,1)));yaw=math.atan2(float(np.dot(f,r)),float(np.dot(f,neutral)))
                self._script('openspace.navigation.setNavigationState('+lua({'Anchor':anchor,'ReferenceFrame':'Root','Position':offset.tolist(),'Up':u.tolist(),'Yaw':yaw,'Pitch':pitch})+')')
            self._script('openspace.setPropertyValueSingle("NavigationHandler.OrbitalNavigator.FollowAnchorNodeRotation",'+lua(mode=='follow')+');openspace.setPropertyValueSingle("NavigationHandler.OrbitalNavigator.FollowAnchorNodeRotationDistance",20)')
            self.mode=mode;time.sleep(.04);return self._read()
    def move(self,request):
        translation=vec(request.get('translation'));look=vec(request.get('look',[0,0,0]));speed=request.get('speed');dt=request.get('dt')
        if type(speed) not in (int,float) or not 1<=speed<=1e18 or type(dt) not in (int,float) or not 0<dt<=.15 or np.linalg.norm(translation)>1.733 or max(abs(look))>.3:raise ValueError('Passo de câmera livre inválido.')
        with self.lock:
            if self.mode!='free':raise ValueError('Ative o voo livre.')
            s=self._read();p=vec(s['camera']['position_render_m']);f=vec(s['camera']['forward']);u=vec(s['camera']['up']);r=unit(np.cross(f,u))
            f=unit(f+look[0]*r+look[1]*u);r=unit(np.cross(f,u));u=unit(np.cross(r,f));norm=np.linalg.norm(translation)
            if norm>1:translation/=norm
            p+=speed*dt*(translation[0]*r+translation[1]*u+translation[2]*f);d=np.linalg.norm(s['navigation']['Position'])
            nav={'Anchor':'CosmosFreeAnchor','ReferenceFrame':'Root','Position':(-f*d).tolist(),'Up':u.tolist()}
            self._script('openspace.setPropertyValueSingle("Scene.CosmosFreeAnchor.Translation.Position",'+lua((p+f*d).tolist())+');openspace.navigation.setNavigationState('+lua(nav)+')')
            return {'queued':True}
    def clock(self,request):
        rate=request.get('rate',1);paused=request.get('paused',True)
        if type(rate) not in (int,float) or not math.isfinite(rate) or not 0<abs(rate)<=86400 or type(paused)!=bool:raise ValueError('Ritmo de Atlas inválido.')
        with self.lock:
            self.boundary=None;self.requested_rate=rate;self._script('openspace.time.setDeltaTime('+lua(rate)+');openspace.time.setPause('+lua(paused)+')');time.sleep(.04);return self.status()
    def viewpoint(self,target,preset):
        if target not in {'Earth','Moon','Saturn'} or preset not in {'overview','terminator','polar','detail'}:raise ValueError('Vista de corpo inválida.')
        with self.lock:
            s=self._read();model=states(et=s['et']);body=next(b for b in model['bodies'] if b['scene_node']==target)
            pole=unit(np.array(model['j2000_to_render_frame'])@np.array(body['body_to_j2000'])@np.array([0.,0,1.]));d=unit(vec(s['positions']['Sun'])-vec(s['positions'][target]));side=unit(np.cross(pole,d));radius={'Earth':6378137,'Moon':1737400,'Saturn':60268000}[target]
            distance=radius*(7 if target=='Saturn' else 4)
            if preset=='terminator':direction=unit(d*math.cos(math.radians(75))+side*math.sin(math.radians(75)))
            elif preset=='polar':direction=unit(pole*.96+d*.28)
            elif target=='Saturn':direction=unit(unit(d-pole*np.dot(d,pole))*math.cos(math.radians(25))+pole*(1 if np.dot(d,pole)>=0 else -1)*math.sin(math.radians(25)))
            else:direction=unit(d*math.cos(math.radians(30))+side*math.sin(math.radians(30)))
            if preset=='detail':distance=radius*(2.8 if target=='Saturn' else 3.1)
            nav={'Anchor':target,'ReferenceFrame':'Root','Position':(direction*distance).tolist(),'Up':pole.tolist()}
            self.return_view=self._capture();self._script('openspace.pathnavigation.stopPath();openspace.setPropertyValueSingle("NavigationHandler.OrbitalNavigator.FollowAnchorNodeRotation",false);openspace.navigation.setNavigationState('+lua(nav)+')');self.mode='orbit';self.target=target
            return self._confirm(nav)
    def display(self,request):
        exposure=request.get('exposure');stars=request.get('stars')
        if type(exposure) not in (float,int) or not math.isfinite(exposure) or not .5<=exposure<=5 or type(stars)!=bool:raise ValueError('Exposição/camada de céu inválida.')
        with self.lock:
            code='openspace.setPropertyValueSingle("RenderEngine.HDRExposure",'+lua(exposure)+');'
            for node in ['CatalogStars','MilkyWaySky','MilkyWayVolume']:code+='openspace.setPropertyValueSingle("Scene.'+node+'.Renderable.Enabled",'+lua(stars)+');'
            self._script(code);time.sleep(.04)
            return self.display_status()
    def display_status(self):
        with self.atlas.lock:return self.atlas._lua('return {exposure=openspace.propertyValue("RenderEngine.HDRExposure"),stars=openspace.propertyValue("Scene.CatalogStars.Renderable.Enabled")}')
    def favorites(self):
        if not self.path.exists():return []
        envelope=json.loads(self.path.read_text());payload=envelope['payload']
        if hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()!=envelope['sha256']:raise ValueError('Integridade dos favoritos inválida.')
        if payload.get('schema')!=1 or not isinstance(payload.get('views'),list) or len(payload['views'])>64:raise ValueError('Arquivo de favoritos inválido.')
        return payload['views']
    def save(self,name):
        if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ValueError('Nome do favorito deve ter 1–80 caracteres.')
        with self.lock:
            rows=self.favorites()
            if len(rows)>=64:raise ValueError('Limite local de 64 favoritos atingido.')
            if self._read()['flying']:raise ValueError('Conclua ou cancele a viagem antes de salvar a vista.')
            row={'id':uuid.uuid4().hex,'name':name.strip(),'view':self._capture()};rows.append(row);self._write(rows);return rows
    def _write(self,rows):
        payload={'schema':1,'views':rows};sealed={'payload':payload,'sha256':hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()}
        self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(sealed,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,self.path)
    def restore(self,identifier):
        with self.lock:
            if identifier=='return':view=copy.deepcopy(self.return_view)
            else:view=next((r['view'] for r in self.favorites() if r['id']==identifier),None)
            if not isinstance(view,dict) or view.get('schema')!=1 or view.get('target') not in DESTINATIONS or view.get('mode') not in MODES:raise ValueError('Favorito/vista de retorno inválido.')
            nav=valid_state(view.get('navigation'));et=view.get('et')
            if (view['mode']=='free')!=(nav['Anchor']=='CosmosFreeAnchor') or (view['mode']!='free' and nav['Anchor']!=DESTINATIONS[view['target']][0]):raise ValueError('Alvo/modo do favorito incompatível com sua âncora.')
            states(et=et) # Validate complete epoch/model before touching renderer.
            rate=view.get('rate');paused=view.get('paused')
            if type(rate) not in (int,float) or not math.isfinite(rate) or abs(rate)>86400 or type(paused)!=bool:raise ValueError('Relógio salvo inválido.')
            anchor=vec(view.get('free_anchor_render_m')).tolist() if nav['Anchor']=='CosmosFreeAnchor' else None
            previous=self._capture();code='openspace.pathnavigation.stopPath();openspace.time.setPause(true);openspace.time.setTime('+lua(et)+');'
            if anchor is not None:code+='openspace.setPropertyValueSingle("Scene.CosmosFreeAnchor.Translation.Position",'+lua(anchor)+');'
            code+='openspace.setPropertyValueSingle("NavigationHandler.OrbitalNavigator.FollowAnchorNodeRotation",'+lua(view['mode']=='follow')+');openspace.navigation.setNavigationState('+lua(nav)+');openspace.time.setDeltaTime('+lua(rate)+')'
            self._script(code);self.target=view['target'];self.mode=view['mode'];self.requested_rate=rate;self.return_view=previous
            confirmed=self._confirm(nav)
            if abs(confirmed['et']-et)>1e-6:raise TimeoutError('O motor não confirmou a época do favorito.')
            if not paused:self._script('openspace.time.setPause(false)')
            return self._read()
    def delete(self,identifier):
        with self.lock:
            rows=self.favorites();found=[r for r in rows if r['id']!=identifier]
            if len(rows)==len(found):raise ValueError('Favorito não encontrado.')
            self._write(found);return found
