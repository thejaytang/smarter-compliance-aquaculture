from pathlib import Path
import json, os, signal, sys
area=Path(__file__).resolve().parent
candidate=area/'candidate'
sys.path.insert(0,str(candidate/'workbench/src'))
from local_workbench.server import Application, bind_local_server
fixture=area/'fixture'
app=Application(fixture/'workbench',candidate/'system1',fixture/'config/config.json',start_workers=False,code_root=candidate)
app.material_worker.start()
server=bind_local_server(app.runtime);server.app=app
state={'pid':os.getpid(),'url':f'http://127.0.0.1:{server.server_port}/','port':server.server_port,'scope':'isolated UI redesign fixture','code_root':str(candidate)}
(area/'candidate-server.json').write_text(json.dumps(state,indent=2));print(state,flush=True)
def stop(*args):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
try:server.serve_forever(poll_interval=.3)
except KeyboardInterrupt:pass
finally:server.server_close();app.close()
