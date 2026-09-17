"""Actual Workbench Application/Handler with isolated stores and only requested material jobs."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workbench/src'))
from local_workbench.server import Application,bind_local_server

fixture=ROOT/'workbench/runtime/human-led-acceptance'
app=Application(fixture/'workbench',ROOT/'system1',fixture/'config/config.json',start_workers=False)
app.material_worker.start()
server=bind_local_server(app.runtime);server.app=app
url=f'http://127.0.0.1:{server.server_port}/'
(fixture/'server.json').write_text(json.dumps({'url':url,'port':server.server_port,'scope':'isolated_engineering_only'}))
print(url,flush=True)
try:server.serve_forever(poll_interval=.3)
finally:server.server_close();app.close()
