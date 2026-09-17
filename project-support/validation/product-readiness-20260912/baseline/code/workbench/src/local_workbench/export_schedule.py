"""Bounded coalescing and retry state for an already-running local exporter."""


class ExportSchedule:
    def __init__(self, now, settle=2, maximum_wait=5, retry=5, periodic=60):
        self.settle, self.maximum_wait = settle, maximum_wait
        self.retry, self.periodic = retry, periodic
        self.next_periodic = now + periodic
        self.next_attempt = now
        self.version = None
        self.dirty_since = self.last_change = None
        self.failures = 0

    def due(self, version, pending, now):
        if not pending:
            self.dirty_since = self.last_change = None
            self.version = version
            return now >= max(self.next_periodic, self.next_attempt)
        if self.dirty_since is None:
            self.dirty_since = self.last_change = now
        if self.version != version:
            self.last_change = now
            self.version = version
        due = min(self.last_change + self.settle, self.dirty_since + self.maximum_wait)
        return now >= max(due, self.next_attempt)

    def finished(self, success, now):
        self.next_periodic = now + self.periodic
        if success:
            self.failures = 0
            self.next_attempt = now
            self.dirty_since = self.last_change = None
        else:
            self.failures += 1
            self.next_periodic = now
            self.next_attempt = now + min(30, self.retry * 2**min(3, self.failures-1))
