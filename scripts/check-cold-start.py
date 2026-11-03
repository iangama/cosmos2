"""Launch own offline native build with a new app cache and time useful capture.

The OS disk cache is not flushed. External HTTP is unavailable to engine/CEF
through the application's offline profile; Windows networking is unchanged.
The PNG completion time is an upper bound, not a GPU presentation timestamp.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import socket
import subprocess
import time
import urllib.request
from websockets.sync.client import connect
from websockets.exceptions import WebSocketException
from cef_page import Page

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--label', default='current')
args = parser.parse_args()
if not re.fullmatch(r'[a-z0-9_-]{1,48}', args.label):
    raise ValueError('Identificador de coleta inválido.')
destination=ROOT/f'evidence/cold-start-{args.label}.json'
if destination.exists():
    raise RuntimeError('Use outro identificador para preservar a coleta anterior.')
for port in (4682, 4700, 8088, 9):
    with socket.socket() as probe:
        probe.settimeout(.2)
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'Porta {port} ocupada. Encerre somente a sessão Cosmos2 antes deste ensaio.')
start = time.perf_counter()
utc = datetime.now(timezone.utc).isoformat()
log = (ROOT/'output/cold-launcher.log').open('wb')
launcher = subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                             '-File', str(ROOT/'scripts/start-cosmos2.ps1'), '-Built',
                             '-Benchmark1080', '-Offline', '-ColdCache', '-InspectCEF'], cwd=ROOT,
                            stdout=log, stderr=subprocess.STDOUT)
ready = None
session = None
loading_captured = False
attempts=[]
health_ready=None
process_seen=None
scene_connection=None
scene_topic=1
class SceneInitializing(Exception):
    pass
while time.perf_counter()-start < 180:
    attempt_start=time.perf_counter()-start
    if launcher.poll() is not None:
        raise RuntimeError('O lançador terminou antes da cena: veja output/cold-launcher.log.')
    try:
        session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        session_started=datetime.fromisoformat(session['started'].replace('Z','+00:00'))
        if session_started < datetime.fromisoformat(utc):
            session=None
            raise ValueError('Recibo anterior à coleta.')
        if process_seen is None:
            process_seen=time.perf_counter()-start
        if health_ready is None:
            try:
                with urllib.request.urlopen('http://127.0.0.1:4700/health',timeout=.2) as health:
                    if json.load(health).get('application')=='cosmos2':
                        health_ready=time.perf_counter()-start
            except (OSError, ValueError):
                pass
        if scene_connection is None:
            with (ROOT/'output/engine.log').open('rb') as engine_log:
                engine_log.seek(0,2)
                engine_log.seek(max(0,engine_log.tell()-65536))
                if b'Running Global initialization scripts' not in engine_log.read():
                    raise SceneInitializing()
            scene_connection=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.1,ping_interval=None)
            scene_connection.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
            scene_connection.send(json.dumps({'topic':scene_topic,'type':'luascript','payload':{'return':True,'script':
                               'return {camera=openspace.navigation.getNavigationState(), metrics=openspace.cosmos2MemoryMetrics(), earth=openspace.propertyValue("Scene.Earth.Renderable.Enabled")}'}}))
        reply=json.loads(scene_connection.recv(timeout=.5))
        if reply.get('topic') != scene_topic:
            continue
        payload = reply.get('payload', {})
        if '1' in payload:
            payload = payload['1']
        if payload.get('camera', {}).get('Anchor') == 'Earth' and payload.get('earth') is True:
            ready = time.perf_counter()-start
            attempts.append({'began_s':attempt_start,'ended_s':ready,'outcome':'scene_ready'})
            break
        attempts.append({'began_s':attempt_start,'ended_s':time.perf_counter()-start,'outcome':'scene_not_ready','payload':payload})
        scene_topic+=1
        scene_connection.send(json.dumps({'topic':scene_topic,'type':'luascript','payload':{'return':True,'script':
            'return {camera=openspace.navigation.getNavigationState(),metrics=openspace.cosmos2MemoryMetrics(),earth=openspace.propertyValue("Scene.Earth.Renderable.Enabled")}'}}))
    except SceneInitializing:
        attempts.append({'began_s':attempt_start,'ended_s':time.perf_counter()-start,'outcome':'engine_initialization_in_progress'})
    except TimeoutError:
        attempts.append({'began_s':attempt_start,'ended_s':time.perf_counter()-start,'outcome':'waiting_for_existing_scene_request'})
    except (OSError, ValueError, KeyError, WebSocketException):
        if scene_connection is not None:
            scene_connection.close()
            scene_connection=None
        attempts.append({'began_s':locals().get('attempt_start',0),'ended_s':time.perf_counter()-start,'outcome':'connection_or_scene_unavailable'})
    if not loading_captured and time.perf_counter()-start > 5 and session and session.get('offline'):
        loading = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                                  str(ROOT/'scripts/capture-window.ps1'),'-Name',f'cosmos2-cold-{args.label}-loading.png'],
                                 capture_output=True, timeout=10)
        loading_captured = loading.returncode == 0
    time.sleep(.1)
if scene_connection is not None:
    scene_connection.close()
if ready is None:
    raise RuntimeError('Cena não ficou pronta em180s; preservar logs para diagnóstico.')
ui_ready = None
deadline = time.monotonic()+30
while time.monotonic() < deadline:
    try:
        with Page() as page:
            page.wait_for_function('document.querySelector("#connection")?.textContent==="Motor conectado"', timeout=2000)
        ui_ready = time.perf_counter()-start
        break
    except (OSError, TimeoutError, StopIteration, RuntimeError):
        time.sleep(.1)
if ui_ready is None:
    raise RuntimeError('A cena abriu, mas a interface nativa não ficou pronta: preservar logs.')
capture = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                          str(ROOT/'scripts/capture-window.ps1'),'-Name',f'cosmos2-cold-{args.label}-ready.png'],
                         capture_output=True, timeout=15)
if capture.returncode:
    raise RuntimeError(capture.stderr.decode(errors='replace'))
report = {'started_utc':utc, 'launcher_pid':launcher.pid, 'session':session,
          'label':args.label,'process_receipt_seen_elapsed_s':process_seen,
          'local_server_ready_elapsed_s':health_ready,'scene_probe_attempts':attempts,
          'scene_api_ready_elapsed_s':ready, 'native_ui_ready_elapsed_s':ui_ready,
          'useful_capture_completed_elapsed_s':time.perf_counter()-start,
          'capture':f'evidence/cosmos2-cold-{args.label}-ready.png', 'loading_capture':loading_captured,
          'cache_mode':'New application cache directory; OS disk cache remains warm/unknown',
          'offline_mode':'Engine external HTTP denied; CEF fixed closed loopback proxy; local UI/WebSocket retained',
          'first_frame_timing_scope':'API readiness and screenshot upper bound; no presentation timestamp',
          'probe_method':'Wait for scene initialization log marker before HTTP upgrade; one persistent accepted WebSocket, no repeated queued requests; loading screenshot is synchronous and included in elapsed time',
          'startup_target_15s_met': time.perf_counter()-start <= 15,
          'runtime_receipt':json.loads((ROOT/'evidence/built-runtime.json').read_text()),
          'ready_response':reply}
report['configuration_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [ROOT/'config/cosmos2.cfg',ROOT/'user/data/profiles/cosmos2.profile',
              ROOT/'scripts/start-cosmos2.ps1',ROOT/'scripts/bootstrap-native-ui.py']}
destination.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key not in ('ready_response','runtime_receipt','scene_probe_attempts')}, indent=2))
