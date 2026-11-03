"""Loopback-only static host for the in-application Cosmos2 interface."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import threading
import argparse
from laboratory import Laboratory
from atlas import Atlas

LAB = Laboratory()
ATLAS = Atlas()
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
            if self.path == '/api/shutdown':
                self.json_response({'ok':True})
                threading.Thread(target=self.server.shutdown,daemon=True).start()
            elif self.path == '/api/command':
                if request.get('command') == 'import_atlas':
                    raise ValueError('A cópia do Atlas exige o comando dedicado de época/procedência.')
                self.json_response(LAB.command(request))
            elif self.path == '/api/atlas/epoch':
                if LAB.status()['mode']!='atlas':raise ValueError('Volte ao Atlas para alterar sua época.')
                self.json_response({'ok':True,'atlas':ATLAS.apply_epoch(request.get('utc'))})
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
        if self.path not in ('/api/state','/health'):
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
        LAB.close()
        ATLAS.close()
        server.server_close()
