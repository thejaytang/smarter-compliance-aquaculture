from pathlib import Path
import json
import sys
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workbench/src'))
from local_workbench.server import Application, bind_local_server
base=Path(__file__).resolve().parent/'fixture'
app=Application(base/'workbench', ROOT/'system1',base/'config/config.json',start_workers=False,code_root=ROOT)
actor='Weijie Tang'
opened=app.collaboration.material_action(actor,'open',dict(request_id=str(uuid.uuid4()),source_id='TS005'))
m=opened.get('material',opened)
if not m.get('blocks'):
    print('SCOPE',json.dumps(m.get('scope')),flush=True)
    scope=m['scope'][0]
    texts=[('heading','Chapter 2'),('text','The human shall remove the fish if the water is hot or the pump is off. Small fish are exempt when the water is cold.'),('heading','Chapter 3'),('text','The human shall use a net.')]
    blocks=[]
    for kind,text in texts:
        blocks.append(dict(id=str(uuid.uuid4()),type=kind,text=text,level=1 if kind=='heading' else None,source_refs=[dict(scope_id=scope['id'],**scope.get('location',{}))]))
    blocks.insert(2,dict(id=str(uuid.uuid4()),type='text',text='- Inspect the net.\n- Record the result.',source_refs=[dict(scope_id=scope['id'],**scope.get('location',{}))]))
    blocks.insert(3,dict(id=str(uuid.uuid4()),type='table',text='',table={'rows':[['Check','Limit'],['Temperature','20']], 'merges':[], 'notes':[]},source_refs=[dict(scope_id=scope['id'],**scope.get('location',{}))]))
    result=app.collaboration.material_action(actor,'save',dict(request_id=str(uuid.uuid4()),material_id=m['id'],expected_revision=m['revision'],blocks=blocks,issues=[],checked_scope=[],association_reviewed=False))
    m=result['material']
server=bind_local_server(app.runtime);server.app=app
meta=dict(url=f'http://127.0.0.1:{server.server_port}/',port=server.server_port,material_id=m['id'],scope='isolated engineering only; workers disabled')
(Path(__file__).resolve().parent/'browser-fixture.json').write_text(json.dumps(meta,indent=2))
print(json.dumps(meta),flush=True)
try: server.serve_forever(poll_interval=.3)
finally:server.server_close();app.close()
