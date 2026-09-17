"""Actual HTTP application, isolated business stores, explicit material worker only."""
import fcntl
import json
import os
from pathlib import Path
import sys
import signal
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workbench/src'))
from local_workbench.server import Application,bind_local_server

fixture=ROOT/'workbench/runtime/round2-acceptance'
if os.environ.get('ROUNDTWO_TRACE_ALLOCATIONS') == '1':
    import tracemalloc
    tracemalloc.start(1)
    def allocation_snapshot(_signal, _frame):
        snapshot=tracemalloc.take_snapshot()
        data={'at':time.time(),'pid':os.getpid(),'traced_bytes':tracemalloc.get_traced_memory(),
              'largest_live_allocations':[str(item) for item in snapshot.statistics('lineno')[:30]]}
        with (fixture/'parent-allocation-snapshots.jsonl').open('a') as target:
            target.write(json.dumps(data)+'\n')
    signal.signal(signal.SIGUSR1,allocation_snapshot)
guard=(fixture/'workbench/runtime/service.lock').open('a')
fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
app=Application(fixture/'workbench',ROOT/'system1',fixture/'config/config.json',start_workers=False)
app.material_worker.start()
server=bind_local_server(app.runtime);server.app=app
state={'url':f'http://127.0.0.1:{server.server_port}/','port':server.server_port,'pid':os.getpid(),
       'root':str(app.root),'instance':app.instance,'scope':'isolated_engineering_only'}
(fixture/'server.json').write_text(json.dumps(state))
(app.runtime/'server.json').write_text(json.dumps(state))
print(json.dumps(state),flush=True)
try:server.serve_forever(poll_interval=.3)
finally:server.server_close();app.close();guard.close()
