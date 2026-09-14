"""Actual local HTTP checks for the workspace's JavaScript import graph."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
import threading
from types import SimpleNamespace
import unittest
from urllib.parse import urljoin

from local_workbench.server import Handler


class FrontendModuleRouteTests(unittest.TestCase):
    def test_app_import_graph_is_served_as_javascript_with_exact_source_bytes(self):
        ui = Path(__file__).resolve().parents[1] / 'ui'
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.app = SimpleNamespace(ui_root=ui, reviewer=False, read_only_restored=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        visited = set(); pending = ['/app.js']
        # Literal local static and dynamic imports are the project's current convention.
        imports = re.compile(r'''(?:from\s*|import\s*\(\s*|import\s*)['"](\.[^'"]+\.js)['"]''')
        try:
            while pending:
                path = pending.pop()
                if path in visited: continue
                connection = HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                try:
                    connection.request('GET', path)
                    response = connection.getresponse(); data = response.read()
                    self.assertEqual(response.status, 200, f'{path}: {data[:160]!r}')
                    self.assertIn(response.getheader('Content-Type').split(';')[0],
                                  ('text/javascript', 'application/javascript'), path)
                    self.assertEqual(data, (ui / path.lstrip('/')).read_bytes(), path)
                finally:
                    connection.close()
                visited.add(path)
                pending.extend(urljoin(path, target) for target in imports.findall(data.decode('utf-8')))
            self.assertIn('/collaboration.js', visited)
            self.assertNotIn('/collaboration-relationships.js', visited,
                             'Startup must also work with an already-running pre-route-update parent.')
            self.assertIn('/submission-drawer.js', visited)
            self.assertIn('/package-download.js', visited)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__': unittest.main()
