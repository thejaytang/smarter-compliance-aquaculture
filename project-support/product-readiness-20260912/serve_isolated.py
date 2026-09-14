"""Resume this goal's owned engineering services; never starts business schedules."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workbench/src'))
from local_workbench.server import Application, bind_local_server

parser = argparse.ArgumentParser()
parser.add_argument('role', choices=('coordinator', 'reviewer', 'faults'))
args = parser.parse_args()
base = ROOT / 'workbench/runtime/product-readiness-20260912'
fixture = base / ('ui-fault-fixture' if args.role == 'faults' else 'fixture')
if not (fixture / 'config/config.json').is_file():
    raise SystemExit('The preserved isolated fixture must exist; this script does not rebuild it.')
reviewer = args.role == 'reviewer'
root = base / 'reviewer' if reviewer else fixture / 'workbench'
app = Application(root, ROOT / 'system1', fixture / 'config/config.json',
                  start_workers=False, reviewer=reviewer, code_root=ROOT)
for component in ('source', 'excel', 'source_excel', 'legacy'):
    app.monitor.disable(component, 'Engineering fixture: coordinator schedules are disabled.')
app.material_worker.start()
server = bind_local_server(app.runtime)
server.app = app
url = f'http://127.0.0.1:{server.server_port}/'
metadata = {'url': url, 'port': server.server_port, 'scope': 'isolated_engineering_only',
            'role': args.role, 'code_root': str(ROOT)}
(base / 'reviewer' / 'server.json' if reviewer else fixture / 'server.json').write_text(
    json.dumps(metadata, indent=2))
print(url, flush=True)
try:
    server.serve_forever(poll_interval=.3)
finally:
    server.server_close()
    app.close()
