"""Serialized local JSON workers in owning environments, with no automatic replay."""
import atexit
import json
import os
import signal
import subprocess
import threading
import uuid

from backend.shared.timing import span


class ComponentProcess:
    def __init__(self, python, module, cwd, env):
        self.python, self.module, self.cwd, self.env = python, module, cwd, env
        self.lock = threading.Lock()
        self.process = None

    def _start(self, timeout=180):
        env = dict(self.env, WORKBENCH_COMPONENT_CHILD='1', WORKBENCH_COMPONENT_READY_PROTOCOL='1')
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {
            'start_new_session': not bool(os.environ.get('WORKBENCH_COMPONENT_CHILD'))}
        with span('component.start'):
            self.process = subprocess.Popen(
                [str(self.python), '-m', 'backend.shared.component_worker', self.module],
                cwd=self.cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding='utf-8', **options)
        process = self.process
        result, done = [], threading.Event()
        def ready():
            try:result.append(json.loads(process.stdout.readline()))
            except (OSError, ValueError):pass
            finally:done.set()
        thread = threading.Thread(target=ready, daemon=True)
        thread.start()
        with span('component.ready'):
            completed = done.wait(timeout)
        if not completed or result != [{'ready': self.module}]:
            self._close(force=True)
            thread.join(timeout=5)
            raise RuntimeError('Component could not initialize. No business request was sent.')
        thread.join()

    def prepare(self):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self._close()
                self._start()

    def request(self, payload, timeout):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self._close()
                self._start(timeout)
            process = self.process
            identity = uuid.uuid4().hex
            result, errors, done = [], [], threading.Event()

            def exchange():
                try:
                    process.stdin.write(json.dumps({'id': identity, 'payload': payload}) + '\n')
                    process.stdin.flush()
                    line = process.stdout.readline()
                    reply = json.loads(line)
                    if reply.get('id') != identity or not isinstance(reply.get('reply'), dict):
                        raise ValueError('Invalid component receipt.')
                    result.append(reply['reply'])
                except Exception as exc:
                    errors.append(exc)
                finally:
                    done.set()

            thread = threading.Thread(target=exchange, daemon=True)
            thread.start()
            with span('component.roundtrip'):
                completed = done.wait(timeout)
            if not completed or errors:
                self._close(force=True)
                thread.join(timeout=5)
                # The write may have committed. Only the caller can retry its same
                # durable request ID; never submit a fresh operation here.
                raise RuntimeError('Component receipt unavailable. Retry the same request after checking saved state.')
            thread.join()
            return result[0]

    def _close(self, force=False):
        process, self.process = self.process, None
        if process is None:
            return
        if not force:
            try:
                process.stdin.close()
                process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                force = True
        if force and process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
            elif not os.environ.get('WORKBENCH_COMPONENT_CHILD'):
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=10)
        for stream in (process.stdin, process.stdout):
            if stream and not stream.closed:
                stream.close()

    def close(self):
        with self.lock:
            self._close()


class ComponentPool:
    def __init__(self):
        self.lock = threading.Lock()
        self.workers = {}
        atexit.register(self.close)

    def _worker(self, python, module, cwd, env):
        key = (str(python), module, str(cwd), tuple(sorted(env.items())))
        with self.lock:
            worker = self.workers.get(key)
            if worker is None:
                worker = self.workers[key] = ComponentProcess(python, module, cwd, env)
        return worker

    def prepare(self, python, module, cwd, env):
        self._worker(python, module, cwd, env).prepare()

    def request(self, python, module, cwd, env, payload, timeout=180):
        return self._worker(python, module, cwd, env).request(payload, timeout)

    def close(self):
        with self.lock:
            workers, self.workers = list(self.workers.values()), {}
        for worker in workers:
            worker.close()
