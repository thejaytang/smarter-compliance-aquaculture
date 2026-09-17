"""Reentrant operation serialization with foreground preference and bounded aging."""
from contextlib import contextmanager
import threading
import time
from backend.shared.timing import measured


class OperationGate:
    def __init__(self, maximum_background_wait=10):
        self.condition = threading.Condition()
        self.local = threading.local()
        self.owner = None
        self.depth = 0
        self.waiters = []
        self.maximum_background_wait = maximum_background_wait

    @contextmanager
    def background(self):
        previous = getattr(self.local, 'background', False)
        self.local.background = True
        try:
            yield
        finally:
            self.local.background = previous

    def run_background(self, function):
        with self.background():
            function()

    @measured('operation_gate.wait')
    def acquire(self, blocking=True, timeout=-1):
        identity = threading.get_ident()
        with self.condition:
            if self.owner == identity:
                self.depth += 1
                return True
            started = time.monotonic()
            ticket = (object(), getattr(self.local, 'background', False), started)
            self.waiters.append(ticket)
            try:
                while True:
                    oldest = self.waiters[0]
                    aged = time.monotonic() - oldest[2] >= self.maximum_background_wait
                    first = oldest if aged else next((w for w in self.waiters if not w[1]), oldest)
                    if self.owner is None and first is ticket:
                        self.owner, self.depth = identity, 1
                        return True
                    remaining = None if timeout < 0 else timeout - (time.monotonic() - started)
                    if not blocking or remaining is not None and remaining <= 0:
                        return False
                    self.condition.wait(remaining)
            finally:
                self.waiters.remove(ticket)
                self.condition.notify_all()

    def release(self):
        with self.condition:
            if self.owner != threading.get_ident():
                raise RuntimeError('Cannot release another operation owner.')
            self.depth -= 1
            if not self.depth:
                self.owner = None
                self.condition.notify_all()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()
