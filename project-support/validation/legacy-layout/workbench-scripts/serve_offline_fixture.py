"""Serve the last isolated three-workspace check without business schedulers."""
from pathlib import Path
import json, threading, time
from local_workbench.server import Application, bind_local_server
ROOT=Path(__file__).resolve().parents[2]
FIX=ROOT/'workbench/runtime/offline-collaboration-acceptance'
state=json.loads((FIX/'latest-check.json').read_text())
servers=[];out={}
for role in ('coordinator','reviewer_a','reviewer_b'):
    app=Application(state[role],ROOT/'system1',FIX/'config/config.json',start_workers=False,reviewer=role!='coordinator',code_root=ROOT)
    app.material_worker.start()
    server=bind_local_server(app.runtime);server.app=app
    threading.Thread(target=server.serve_forever,daemon=True).start();servers.append(server)
    out[role]={'url':f'http://127.0.0.1:{server.server_port}/','root':state[role]}
(FIX/'browser-services.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out),flush=True)
try:
    while True:time.sleep(1)
finally:
    for s in servers:s.shutdown();s.server_close();s.app.close()
