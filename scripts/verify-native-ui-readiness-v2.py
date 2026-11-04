"""Exercise delayed listening, wrong services, incomplete pages and dead children."""
from pathlib import Path
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import threading
import time
from native_ui_readiness import wait_for_ui, ReadinessTimeout, ServerExited

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'evidence/local-ui-readiness-check-20261104.json'
if out.exists():
    raise FileExistsError('Preserve readiness tests')


class Handler(BaseHTTPRequestHandler):
    mode = 'ready'
    def do_GET(self):
        if self.path == '/health':
            body = json.dumps(dict(application='other' if self.mode == 'wrong' else 'cosmos2', protocol=True if self.mode == 'bool' else 1)).encode()
        else:
            body = b'<html><title>Loading</title></html>' if self.mode == 'page' else b'<html><title>Cosmos2 - Atlas</title></html>'
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass


checks = []
with socket.socket() as reservation:
    reservation.bind(('127.0.0.1', 0))
    port = reservation.getsockname()[1]
holder = []
started = threading.Event()
def delayed_server():
    time.sleep(.35)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    holder.append(server)
    started.set()
    server.serve_forever(poll_interval=.01)
worker = threading.Thread(target=delayed_server)
worker.start()
try:
    result = wait_for_ui(port=port, timeout_s=4, interval_s=.025)
    assert started.is_set() and result['elapsed_s'] >= .3 
    checks.append(dict(case='Delayed HTTP listener', result=result))
    for mode, label in [('wrong', 'Wrong service'), ('bool', 'Boolean protocol'), ('page', 'Root page still loading')]:
        Handler.mode = mode
        try:
            wait_for_ui(port=port, timeout_s=.15, interval_s=.02)
            raise AssertionError('Unready service accepted')
        except ReadinessTimeout as error:
            checks.append(dict(case=label, refused=True, error=str(error)))
    Handler.mode = 'ready'
    began = time.monotonic()
    try:
        wait_for_ui(port=port, timeout_s=10, child_alive=lambda: False)
        raise AssertionError('Dead child accepted')
    except ServerExited as error:
        assert time.monotonic()-began < .25
        checks.append(dict(case='Server exited', refused=True, elapsed_s=time.monotonic()-began, error=str(error)))
    alive_calls = []
    def dies_during_check():
        alive_calls.append(True)
        return len(alive_calls) == 1
    try:
        wait_for_ui(port=port, timeout_s=10, child_alive=dies_during_check)
        raise AssertionError('Child dying during health accepted')
    except ServerExited as error:
        checks.append(dict(case='Server exits after health', refused=True, error=str(error)))
    result = wait_for_ui(port=port, timeout_s=1)
    checks.append(dict(case='Immediate ready UI', result=result))
finally:
    assert started.wait(timeout=4)
    holder[0].shutdown()
    holder[0].server_close()
    worker.join(timeout=4)
    assert not worker.is_alive()
sources = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in [Path(__file__), ROOT / 'scripts/native_ui_readiness.py', ROOT / 'scripts/wait-local-ui.py']}
r = dict(accepted=True, completed=True, source_sha256=sources, checks=checks,
         scope='Local HTTP readiness and owned-child guard only; separate native launch verification remains required.')
out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(accepted=True, cases=len(checks))))
