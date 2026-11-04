"""Wait for the owned local Cosmos2 HTTP process before opening its CEF URL."""
import json
import time
import urllib.error
import urllib.request


class ReadinessTimeout(TimeoutError):
    pass


class ServerExited(RuntimeError):
    pass


def wait_for_ui(*, port=4700, timeout_s=240, child_alive=lambda: True, interval_s=.1):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Invalid local port')
    if timeout_s <= 0 or interval_s <= 0:
        raise ValueError('A positive readiness budget is required')
    base = 'http://127.0.0.1:' + str(port)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    began = time.monotonic()
    deadline = began + timeout_s
    attempts = 0
    last_error = 'No HTTP response'
    while True:
        if not child_alive():
            raise ServerExited('O servidor local encerrou antes de a interface ficar pronta.')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ReadinessTimeout('O servidor local não ficou pronto: ' + last_error)
        attempts += 1
        try:
            with opener.open(base + '/health', timeout=min(1., remaining)) as response:
                if response.geturl() != base + '/health' or response.status != 200:
                    raise ValueError('Unexpected local health response')
                data = response.read(4097)
                if len(data) > 4096:
                    raise ValueError('Local health response is oversized')
                health = json.loads(data)
                if not isinstance(health, dict) or health.get('application') != 'cosmos2' or type(health.get('protocol')) is not int or health['protocol'] != 1:
                    raise ValueError('The local service is not the expected Cosmos2 UI')
            if not child_alive():
                raise ServerExited('O servidor local encerrou durante a abertura.')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ReadinessTimeout('O prazo terminou antes de confirmar a página da interface.')
            with opener.open(base + '/', timeout=min(1., remaining)) as response:
                html = response.read(65536)
                if response.geturl() != base + '/' or response.status != 200 or b'<title>Cosmos2' not in html:
                    raise ValueError('The local Cosmos2 page is not ready')
            if not child_alive():
                raise ServerExited('O servidor local encerrou durante a abertura.')
            return dict(ready=True, health_url=base + '/health', ui_url=base + '/',
                        health=health, checked_root_page=True, attempts=attempts,
                        elapsed_s=time.monotonic() - began)
        except (OSError, urllib.error.URLError, ValueError) as error:
            last_error = type(error).__name__ + ': ' + str(error)
        time.sleep(min(interval_s, max(0., deadline-time.monotonic())))
