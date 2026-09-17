"""Serve workflow correction fixtures; only explicit material extraction workers."""
import json
import threading
import time
from pathlib import Path
from local_workbench.server import Application,bind_local_server
ROOT=Path(__file__).resolve().parents[2]
report=ROOT/'docs/reports/offline-collaboration-20260912'
state=json.loads((report/'workflow-correction.json').read_text());servers=[];out={}
for role,root in [('coordinator',state['coordinator_root']),('reviewer',state['reviewer_roots'][0])]:
 app=Application(root,ROOT/'system1',ROOT/'workbench/runtime/offline-collaboration-acceptance/config/config.json',start_workers=False,reviewer=role!='coordinator',code_root=ROOT)
 app.material_worker.start();server=bind_local_server(app.runtime);server.app=app
 threading.Thread(target=server.serve_forever,daemon=True).start();servers.append(server);out[role]={'url':f'http://127.0.0.1:{server.server_port}/','root':root}
(report/'workflow-browser-services.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
try:
 while True:time.sleep(1)
finally:
 for server in servers:server.shutdown();server.server_close();server.app.close()
