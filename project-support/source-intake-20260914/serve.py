from pathlib import Path
import json,sys,signal,os
area=Path(__file__).resolve().parent;root=area.parents[1]
sys.path.insert(0,str(root/'workbench/src'))
from local_workbench.server import Application,bind_local_server
app=Application(area/'fixture/workbench',root/'system1',area/'fixture/config/config.json',start_workers=False,code_root=root)
server=bind_local_server(app.runtime);server.app=app
state={'port':server.server_port,'pid':os.getpid()};(area/'server.json').write_text(json.dumps(state));print(state,flush=True)
def stop(*a):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
try:server.serve_forever(.2)
except KeyboardInterrupt:pass
finally:server.server_close();app.close()
