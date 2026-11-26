"""Loopback-only static host for the in-application Cosmos2 interface."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import threading
import argparse
import os
from laboratory import Laboratory
from atlas import Atlas

# This unpromoted server always defaults to its own checkpoint namespace.
os.environ.setdefault('COSMOS2_STORAGE', str(Path(__file__).resolve().parents[1] / 'gravity-sessions'))
LAB = Laboratory()
from is4_laboratory import ParticleLaboratory
PARTICLES = ParticleLaboratory(LAB)
from is5_laboratory import SolarLaboratory
SOLAR_ZONE = SolarLaboratory(LAB)
from is6_laboratory import SpatialLaboratory
SPATIAL = SpatialLaboratory(LAB)
from is6_layers_laboratory import LayerLaboratory
LAYERS = LayerLaboratory(LAB)
SOURCE_COMMANDS = threading.RLock()
ATLAS = Atlas()
from urllib.parse import urlsplit
from is5_reference_browser import Library
SOLAR_REFERENCES = Library()
from navigation import Navigation
NAVIGATION = Navigation(ATLAS)
FORCE_JOBS = threading.BoundedSemaphore(2)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / "ui"), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def json_response(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path.startswith('/api/stellar-reference/'):
            try:
                result=SOLAR_REFERENCES.query(parsed.path.removeprefix('/api/stellar-reference/'),parsed.query)
                return self.json_response(result)
            except ValueError as error:
                return self.json_response({'ok':False,'error':str(error)},400)
        if self.path=='/api/layers/state':
            return self.json_response(LAYERS.status())
        if self.path=='/api/spatial/state':
            return self.json_response(SPATIAL.status())
        if self.path=='/api/solar-zone/state':
            return self.json_response(SOLAR_ZONE.status())
        if self.path=='/api/particles/state':
            return self.json_response(PARTICLES.status())
        if self.path=='/api/orbital/curves':
            try:
                state=LAB.status()['physics']
                if state is None:raise ValueError('Abra o laboratório primeiro.')
                result=LAB.command({'command':'orbital_curves','system_id':state['system_id'],'edit_token':state['edit_token']})
                return self.json_response(result['ack']['result'])
            except Exception as error:return self.json_response({'ok':False,'error':str(error)},400)
        if self.path=='/api/instruments/history':
            try:
                state=LAB.status()['physics']
                if state is None:raise ValueError('Abra o laboratório primeiro.')
                result=LAB.command({'command':'history_curves','system_id':state['system_id'],'edit_token':state['edit_token']})
                return self.json_response(result['ack']['result'])
            except Exception as error:return self.json_response({'ok':False,'error':str(error)},400)
        if self.path=='/api/laboratory/experiments':
            try:
                from gravity_experiments import catalog
                return self.json_response(catalog())
            except Exception as error:return self.json_response({'ok':False,'error':str(error)},503)
        if self.path=='/api/navigation/display':
            try:return self.json_response(NAVIGATION.display_status())
            except Exception as error:return self.json_response({'ok':False,'error':str(error)},503)
        if self.path in ('/api/navigation/state','/api/navigation/favorites'):
            try:return self.json_response(NAVIGATION.status() if self.path.endswith('/state') else {'views':NAVIGATION.favorites()})
            except Exception as error:return self.json_response({'ok':False,'error':str(error)},503)
        if self.path == '/api/nuclear-energies/catalog':
            try:
                from nuclear_energies import catalog
                return self.json_response(catalog())
            except Exception as error:
                return self.json_response({'ok': False, 'error': str(error)}, 503)
        if self.path == '/api/packages/catalog':
            try:
                from packages import store
                return self.json_response(store().catalog())
            except Exception as error:
                return self.json_response({'ok': False, 'error': str(error)}, 503)
        if self.path == '/api/nuclei/catalog':
            try:
                from nuclei import catalog
                return self.json_response(catalog())
            except Exception as error:
                return self.json_response({'ok': False, 'error': str(error)}, 503)
        if self.path == '/api/atlas/state':
            try:return self.json_response(ATLAS.status())
            except Exception as error:return self.json_response({'ok':False,'error':str(error)},503)
        if self.path=='/api/geomagnetism/texture':
            texture=Path(__file__).resolve().parents[1]/'data/textures/earth.jpg'
            content=texture.read_bytes()
            self.send_response(200);self.send_header('Content-Type','image/jpeg')
            self.send_header('Content-Length',str(len(content)));self.end_headers()
            self.wfile.write(content);return
        if self.path == '/api/forces/catalog':
            from forces import SCENARIOS, EFFECTS
            return self.json_response({'schema': 2, 'scenarios': SCENARIOS, 'effects': EFFECTS})
        if self.path == '/api/state':
            return self.json_response(LAB.status())
        if self.path == '/health':
            return self.json_response({'application':'cosmos2','protocol':1})
        super().do_GET()

    def do_POST(self):
        # Keep source transactions serial, and reject queued late zone commands.
        if self.path in ('/api/shutdown','/api/solar-zone/cancel','/api/spatial/cancel','/api/layers/cancel'):
            return self._post()
        if self.path in ('/api/solar-zone/command','/api/spatial/command','/api/layers/command'):
            if not SOURCE_COMMANDS.acquire(blocking=False):
                return self.json_response({'ok':False,'error':'Aguarde a alteração da cena em andamento.'},400)
            try:
                return self._post()
            finally:
                SOURCE_COMMANDS.release()
        if LAYERS.status().get('busy'):
            return self.json_response({'ok':False,'error':'Aguarde a confirmação das camadas.'},400)
        if SPATIAL.status().get('busy'):
            return self.json_response({'ok':False,'error':'Aguarde a confirmação da malha.'},400)
        if SOLAR_ZONE.status().get('busy'):
            return self.json_response({'ok':False,'error':'Aguarde a confirmação da zona solar.'},400)
        with SOURCE_COMMANDS:
            return self._post()

    def _post(self):
        port = self.server.server_port
        if self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):
            return self.json_response({'error':'Host inválido'},403)
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{port}',f'http://localhost:{port}'):
            return self.json_response({'error':'Origem inválida'},403)
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 8192:
                raise ValueError('Tamanho de comando inválido')
            request = json.loads(self.rfile.read(length))
            if not isinstance(request,dict):
                raise ValueError('Comando deve ser um objeto')
            layer_state = LAYERS.status()
            if layer_state['active'] or layer_state['recovery_required']:
                if self.path in ('/api/command','/api/particles/command','/api/solar-zone/command','/api/spatial/command') or self.path.startswith(('/api/solar/','/api/atlas/','/api/navigation/')):
                    raise ValueError('Feche as camadas coordenadas antes de alterar a cena ou abrir outro instrumento.')
            if SOLAR_ZONE.status()['active'] and (self.path in ('/api/command','/api/particles/command') or self.path.startswith(('/api/solar/','/api/atlas/','/api/navigation/'))):
                raise ValueError('Feche a zona solar antes de alterar a cena orbital ou abrir uma partícula.')
            if SPATIAL.status()['active'] or SPATIAL.status().get('recovery_required'):
                if self.path in ('/api/command','/api/particles/command','/api/solar-zone/command') or self.path.startswith(('/api/solar/','/api/atlas/','/api/navigation/')):
                    raise ValueError('Feche a malha antes de alterar a cena orbital ou abrir outro instrumento.')
            if self.path == '/api/layers/command':
                components = [PARTICLES.status(), SOLAR_ZONE.status(), SPATIAL.status()]
                if any(s['active'] or s.get('busy') or s.get('recovery_required') for s in components):
                    raise ValueError('Feche os outros instrumentos antes de abrir as camadas coordenadas.')
                self.json_response(LAYERS.command(request))
            elif self.path == '/api/layers/cancel':
                self.json_response(LAYERS.cancel(request))
            elif self.path == '/api/spatial/command':
                if PARTICLES.status()['active'] or SOLAR_ZONE.status()['active']:
                    raise ValueError('Feche a partícula ou a zona solar antes de abrir a malha.')
                self.json_response(SPATIAL.command(request))
            elif self.path == '/api/spatial/cancel':
                self.json_response(SPATIAL.cancel(request))
            elif self.path == '/api/solar-zone/command':
                if PARTICLES.status()['active']:
                    raise ValueError('Feche a partícula antes de abrir a zona solar.')
                self.json_response(SOLAR_ZONE.command(request))
            elif self.path == '/api/solar-zone/cancel':
                self.json_response(SOLAR_ZONE.cancel(request))
            elif self.path == '/api/particles/command':
                self.json_response(PARTICLES.command(request))
            elif self.path == '/api/shutdown':
                self.json_response({'ok':True})
                threading.Thread(target=self.server.shutdown,daemon=True).start()
            elif self.path == '/api/solar/jupiter-field':
                required = {'system_id', 'edit_token', 'revision', 'expected_time', 'frame',
                            'body_id', 'radius_m', 'latitude_deg', 'east_longitude_deg', 'degree'}
                if set(request) != required:
                    raise ValueError('O campo joviano exige identidade, fase, corpo, coordenadas e grau.')
                self.json_response(LAB.command({**request, 'command': 'jupiter_field'}))
            elif self.path == '/api/solar/earth-field':
                required = {'system_id', 'edit_token', 'revision', 'expected_time', 'frame',
                            'body_id', 'latitude_deg', 'longitude_deg', 'altitude_m'}
                if set(request) != required:
                    raise ValueError('O campo terrestre exige identidade, fase, corpo e posição geodética.')
                self.json_response(LAB.command({**request, 'command': 'earth_field'}))
            elif self.path == '/api/solar/tide':
                required = {'system_id', 'edit_token', 'revision', 'expected_time', 'frame', 'body_id', 'offset_m'}
                if set(request) != required:
                    raise ValueError('A maré exige identidade, fase, corpo e deslocamento em SI.')
                self.json_response(LAB.command({**request, 'command': 'solar_tide'}))
            elif self.path == '/api/command':
                if PARTICLES.status()['active']:
                    raise ValueError('Feche o experimento de partícula antes de alterar a cena solar.')
                if request.get('command') == 'import_atlas':
                    raise ValueError('A cópia do Atlas exige o comando dedicado de época/procedência.')
                self.json_response(LAB.command(request))
            elif self.path == '/api/atlas/epoch':
                if LAB.status()['mode']!='atlas':raise ValueError('Volte ao Atlas para alterar sua época.')
                self.json_response({'ok':True,'atlas':ATLAS.apply_epoch(request.get('utc'))})
            elif self.path in ('/api/solar/reference', '/api/solar/experiment'):
                if set(request) != {'utc'}:
                    raise ValueError('A cópia solar aceita apenas a época; estados e fontes vêm do cadastro fixado.')
                if self.path.endswith('/experiment') and LAB.status()['mode'] != 'atlas':
                    raise ValueError('Volte ao Atlas para criar uma cópia dos quatro centros.')
                from solar_catalog import states as solar_states
                catalog = solar_states(request['utc'])
                if self.path.endswith('/reference'):
                    self.json_response({'ok': True, 'reference': catalog})
                else:
                    from solar_import import prepare as solar_prepare
                    initial = solar_prepare(catalog)
                    ATLAS.apply_epoch(request['utc'])
                    self.json_response(LAB.command({'command': 'import_atlas', 'initial_state': initial}))
            elif self.path.startswith('/api/navigation/'):
                if LAB.status()['mode']!='atlas':raise ValueError('Volte ao Atlas para navegar.')
                action=self.path.removeprefix('/api/navigation/')
                if action=='visit':result=NAVIGATION.visit(request.get('target'),request.get('smooth',False),request.get('sunlit',False))
                elif action=='mode':result=NAVIGATION.set_mode(request.get('mode'))
                elif action=='cancel':result=NAVIGATION.cancel()
                elif action=='move':result=NAVIGATION.move(request)
                elif action=='clock':result=NAVIGATION.clock(request)
                elif action=='viewpoint':result=NAVIGATION.viewpoint(request.get('target'),request.get('preset'))
                elif action=='display':result=NAVIGATION.display(request)
                elif action=='save':result={'views':NAVIGATION.save(request.get('name'))}
                elif action=='restore':result=NAVIGATION.restore(request.get('id'))
                elif action=='delete':result={'views':NAVIGATION.delete(request.get('id'))}
                else:raise ValueError('Comando de navegação desconhecido.')
                self.json_response({'ok':True,'navigation':result})
            elif self.path == '/api/atlas/experiment':
                if LAB.status()['mode'] != 'atlas':
                    raise ValueError('Volte ao Atlas para criar uma nova cópia.')
                from atlas import states
                from atlas_import import prepare, experiment_subset
                initial = prepare(experiment_subset(states(utc=request.get('utc'))))
                ATLAS.apply_epoch(request.get('utc'))
                self.json_response(LAB.command({'command': 'import_atlas', 'initial_state': initial}))
            elif self.path == '/api/packages/verify':
                from packages import store
                self.json_response({'ok': True, 'verification': store().verify(request.get('package_id'))})
            elif self.path == '/api/packages/export':
                from packages import store
                from artifacts import export_json
                self.json_response(export_json('packages', {'schema': 1, 'catalog': store().catalog()}))
            elif self.path == '/api/atlas/export':
                from artifacts import export_json
                self.json_response(export_json('atlas', {'schema': 1, 'atlas': ATLAS.status()}))
            elif self.path.startswith('/api/nuclear-energies/'):
                from nuclear_energies import evaluate, save, load
                if self.path == '/api/nuclear-energies/evaluate':
                    self.json_response({'ok': True, **evaluate(request)})
                elif self.path == '/api/nuclear-energies/save':
                    self.json_response({'ok': True, 'saved': save(request)})
                elif self.path == '/api/nuclear-energies/load':
                    self.json_response({'ok': True, **load()})
                elif self.path == '/api/nuclear-energies/export':
                    from artifacts import export_json
                    self.json_response(export_json('nuclear-energies', evaluate(request)))
                else:
                    self.json_response({'error': 'Comando não encontrado'}, 404)
            elif self.path.startswith('/api/nuclei/'):
                from nuclei import export_file, save, load
                if self.path == '/api/nuclei/export':
                    self.json_response(export_file(request))
                elif self.path == '/api/nuclei/save':
                    self.json_response({'ok': True, 'saved': save(request)})
                elif self.path == '/api/nuclei/load':
                    self.json_response({'ok': True, **load()})
                else:
                    self.json_response({'error': 'Comando não encontrado'}, 404)
            elif self.path.startswith('/api/forces/'):
                from forces import evaluate, save_configuration, load_configuration_record
                if not FORCE_JOBS.acquire(blocking=False):
                    return self.json_response({'ok': False, 'error': 'Aguarde o cálculo em andamento.'}, 429)
                try:
                    if self.path == '/api/forces/evaluate':
                        self.json_response(evaluate(request))
                    elif self.path == '/api/forces/export':
                        from artifacts import export_json
                        result = evaluate(request)
                        self.json_response(export_json('forces-' + result['configuration']['scenario'], result))
                    elif self.path == '/api/forces/save':
                        self.json_response({'ok': True, 'saved': save_configuration(request)})
                    elif self.path == '/api/forces/load':
                        self.json_response({'ok': True, **load_configuration_record()})
                    else:
                        self.json_response({'error': 'Comando não encontrado'}, 404)
                finally:
                    FORCE_JOBS.release()
            else:
                self.json_response({'error':'Comando não encontrado'},404)
        except Exception as error:
            self.json_response({'ok':False,'error':str(error)},400)

    def log_message(self, format, *args):
        if self.path not in ('/api/state','/api/particles/state','/api/solar-zone/state','/api/spatial/state','/api/layers/state','/health'):
            super().log_message(format,*args)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4700)
    args = parser.parse_args()
    print(f"Cosmos2 UI http://127.0.0.1:{args.port}", flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    def guard_clock():
        while True:
            time.sleep(.25)
            if ATLAS.connection is not None:
                try:NAVIGATION.status()
                except Exception:pass # Renderer may be starting or shutting down.
    import time
    threading.Thread(target=guard_clock,daemon=True).start()
    try:
        server.serve_forever()
    finally:
        cleanup_errors = []
        for name, component in [('layers',LAYERS),('spatial',SPATIAL),('solar_zone',SOLAR_ZONE),('particles',PARTICLES),('laboratory',LAB),('atlas',ATLAS)]:
            try:
                component.close()
            except Exception as error:
                cleanup_errors.append(name+': '+str(error))
        server.server_close()
        if cleanup_errors:
            raise RuntimeError('Falhas no encerramento: '+'; '.join(cleanup_errors))
