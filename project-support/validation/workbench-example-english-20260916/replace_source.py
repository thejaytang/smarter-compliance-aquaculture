from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path.insert(0,'/private/tmp');from example_http import call,rid
p=OUT/'source-receipt.json';saved=json.loads(p.read_text()) if p.exists() else {}
def record(k,v):saved[k]=v;p.write_text(json.dumps(saved,ensure_ascii=False,indent=2));return v
original=(ROOT/'workbench/examples/example.html').read_bytes()
if 'upload' not in saved:record('upload',call('/api/upload',raw=original))
if 'manual' not in saved:
 data=call('/api/source-workspace')
 if not any(t.get('source_id')=='PE001' and t['operation_type'] in ('SOURCE_REVIEW','SELECTION_REVIEW') for t in data['tasks']):
  source=next(s for s in data['sources'] if s['source_id']=='PE001')
  if 'reopen_request' not in saved:record('reopen_request',dict(request_id=rid(),source_id='PE001',expected_source_revision=source['source_revision'],note='User requested replacing the current demonstration with its complete English version.'))
  record('reopen',call('/api/source-workspace/reopen',saved['reopen_request']))
  data=call('/api/source-workspace')
 task=next(t for t in data['tasks'] if t.get('source_id')=='PE001' and t['operation_type'] in ('SOURCE_REVIEW','SELECTION_REVIEW'))
 req=dict(request_id=rid(),task_id=task['operation_id'],revision=task['revision'],source_revision=task.get('source_revision',''),action='manual',note='User requested an entirely English example. English demonstration translation based on the user-supplied ADF-10 English JSON, with chapter links and all listed categories retained. This is a training excerpt, not an official English legal publication. The prior Norwegian source remains in history.',upload_id=saved['upload']['upload_id'],identity_verified=True,permission_verified=True,explicit_confirmation=True)
 record('manual_request',req);record('manual',call('/api/source-workspace/task-apply',req))
source=next(s for s in call('/api/source-workspace')['sources'] if s['source_id']=='PE001');record('source',{k:source.get(k) for k in ['source_id','source_title','snapshot_id','content_hash','effective_selection']})
assert source['content_hash']==hashlib.sha256(original).hexdigest()
if 'open_request' not in saved:record('open_request',dict(request_id=rid(),source_id='PE001'))
if 'material' not in saved:record('material',call('/api/material/open',saved['open_request']))
print(json.dumps(saved['source']));print('material',saved['material'].get('material',saved['material'])['id'])
