"""Foreground preference must retain mutual exclusion, reentrancy and recovery."""
import threading
import time
import unittest

from local_workbench.operation_gate import OperationGate


class OperationGateTests(unittest.TestCase):
    def test_reentrant_exception_release_and_nonblocking_acquire(self):
        gate = OperationGate()
        blocked = []
        with self.assertRaisesRegex(ValueError, 'fixture'):
            with gate, gate:
                worker = threading.Thread(target=lambda: blocked.append(gate.acquire(False)))
                worker.start(); worker.join(2)
                self.assertFalse(worker.is_alive())
                raise ValueError('fixture')
        self.assertEqual(blocked, [False])
        self.assertTrue(gate.acquire(timeout=.1))
        gate.release()

    def run_waiters(self, aging):
        gate = OperationGate(maximum_background_wait=aging)
        order = []
        gate.acquire()
        def enter(label, background):
            def operation():
                with gate: order.append(label)
            if background: gate.run_background(operation)
            else: operation()
        workers = []
        try:
            for count, (label, background) in enumerate([('background', True), ('foreground', False)], 1):
                worker = threading.Thread(target=enter, args=(label, background))
                workers.append(worker); worker.start()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    with gate.condition:
                        if len(gate.waiters) == count: break
                    time.sleep(.005)
                else: self.fail('Waiter was not queued')
        finally:
            gate.release()
            for worker in workers: worker.join(2)
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        return order

    def test_foreground_precedes_waiting_background(self):
        self.assertEqual(self.run_waiters(10), ['foreground', 'background'])

    def test_aged_background_is_not_starved(self):
        self.assertEqual(self.run_waiters(0), ['background', 'foreground'])
