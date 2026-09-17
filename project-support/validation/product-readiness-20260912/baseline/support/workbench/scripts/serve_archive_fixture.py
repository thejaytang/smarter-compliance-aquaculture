"""Serve the synthetic archive/inspection acceptance root without schedulers."""
import json
from pathlib import Path
from local_workbench.server import Application, bind_local_server
ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'docs/reports/offline-collaboration-20260912'
state=json.loads((REPORT/'archive-inspection.json').read_text())
app=Application(state['root'],ROOT/'system1',ROOT/'workbench/runtime/offline-collaboration-acceptance/config/config.json',start_workers=False,code_root=ROOT)
server=bind_local_server(app.runtime);server.app=app
result={'url':f'http://127.0.0.1:{server.server_port}/','root':state['root']}
(REPORT/'archive-browser-service.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
try:server.serve_forever()
finally:server.server_close();app.close()
