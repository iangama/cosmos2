"""One cancellable, versioned force-bench computation; only completed results can be published."""
import copy
import threading
import time
import uuid


class Laboratory:
    def __init__(self, evaluate=None):
        self._evaluate = evaluate
        self.lock = threading.RLock()
        self.thread = None
        self.event = None
        self.revision = 0
        self.job_id = None
        self.token = uuid.uuid4().hex
        self.phase = 'idle'
        self.result = None
        self.result_job_id = None
        self.error = None
        self.configuration = None

    def status(self):
        with self.lock:
            return dict(schema=1, revision=self.revision, job_id=self.job_id, edit_token=self.token,
                        busy=self.thread is not None and self.thread.is_alive(), phase=self.phase,
                        configuration=copy.deepcopy(self.configuration), result=copy.deepcopy(self.result),
                        published_job_id=self.result_job_id, error=self.error)

    def _guard(self, request):
        if request.get('edit_token') != self.token or type(request.get('revision')) is not int or request['revision'] != self.revision:
            raise ValueError('Pedido obsoleto: consulte o estado atual da bancada.')

    def command(self, request):
        if type(request) is not dict or request.get('command') not in ['compute', 'cancel']:
            raise ValueError('Comando de órbitas inválido.')
        with self.lock:
            self._guard(request)
            busy = self.thread is not None and self.thread.is_alive()
            if request['command'] == 'cancel':
                if set(request) != {'command','edit_token','revision','job_id'} or not busy or self.phase not in ['computing','cancelling'] or request['job_id'] != self.job_id:
                    raise ValueError('Não há esse cálculo ativo para cancelar.')
                self.event.set()
                self.phase = 'cancelling'
                return self.status()
            if set(request) != {'command','edit_token','revision','configuration'} or busy:
                raise ValueError('Aguarde o término do cálculo ativo.')
            from forces import normalize
            cfg = normalize(request['configuration'])
            if cfg['scenario'] != 'timelike-orbits':
                raise ValueError('Use a bancada de órbitas e relógios.')
            # Validate the effective kernel before starting a worker or changing identities.
            from timelike_force_adapter import kernel_configuration
            kernel_configuration(cfg['parameters'])
            self.revision += 1
            self.job_id, self.token = uuid.uuid4().hex, uuid.uuid4().hex
            identity = (self.revision, self.job_id, self.token)
            self.configuration = copy.deepcopy(cfg)
            self.phase, self.error = 'computing', None
            self.event = event = threading.Event()

            def run():
                try:
                    if self._evaluate is None:
                        from forces import evaluate_c214
                        result = evaluate_c214(copy.deepcopy(cfg), cancelled=event.is_set)
                    else:
                        result = self._evaluate(copy.deepcopy(cfg), event.is_set)
                    with self.lock:
                        if identity != (self.revision, self.job_id, self.token):
                            return
                        if event.is_set():
                            self.phase = 'cancelled'
                        else:
                            self.result = result
                            self.result_job_id = self.job_id
                            self.phase = 'complete'
                except Exception as error:
                    with self.lock:
                        if identity == (self.revision, self.job_id, self.token):
                            self.phase = 'cancelled' if event.is_set() else 'failed'
                            self.error = None if event.is_set() else str(error)

            self.thread = threading.Thread(target=run, name='c214-orbits-worker', daemon=True)
            self.thread.start()
            return self.status()

    def close(self):
        with self.lock:
            event, thread = self.event, self.thread
            if event:
                event.set()
        if thread:
            thread.join(timeout=16)
            if thread.is_alive():
                raise RuntimeError('O cálculo não confirmou encerramento no orçamento.')
