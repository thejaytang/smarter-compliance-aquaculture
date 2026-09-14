import threading
import unittest
from local_workbench.server import Application


class ShutdownTests(unittest.TestCase):
    def test_shutdown_waits_for_running_export_before_releasing_service(self):
        app=Application.__new__(Application);app.stop=threading.Event()
        entered=threading.Event();release=threading.Event();closed=threading.Event()
        def exporting():entered.set();release.wait(3)
        def idle():app.stop.wait(3)
        app.worker=threading.Thread(target=idle)
        app.parser_worker=threading.Thread(target=idle)
        app.workbook_worker=threading.Thread(target=exporting)
        app.confidence_worker=threading.Thread(target=idle)
        for worker in (app.worker,app.parser_worker,app.workbook_worker,app.confidence_worker):worker.start()
        self.assertTrue(entered.wait(1))
        closer=threading.Thread(target=lambda:(app.close(),closed.set()));closer.start()
        try:
            self.assertTrue(app.stop.wait(1))
            self.assertFalse(closed.wait(.05))
        finally:release.set();closer.join(3)
        self.assertTrue(closed.is_set())
        self.assertFalse(app.workbook_worker.is_alive())
