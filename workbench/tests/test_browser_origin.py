import json
import tempfile
import unittest
from pathlib import Path
from local_workbench.server import bind_local_server


class BrowserOriginTests(unittest.TestCase):
    def test_restarts_retain_origin_and_occupied_port_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = bind_local_server(root)
            port = first.server_port
            first.server_close()
            second = bind_local_server(root)
            try:
                self.assertEqual(second.server_port, port)
                third = bind_local_server(root)
                try:
                    self.assertNotEqual(third.server_port, port)
                    self.assertEqual(third.server_address[0], '127.0.0.1')
                    self.assertEqual(json.loads((root / 'listen-port.json').read_text())['port'], third.server_port)
                finally:
                    third.server_close()
            finally:
                second.server_close()
