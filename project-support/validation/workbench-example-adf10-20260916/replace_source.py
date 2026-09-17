from pathlib import Path
import json,sys,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path.insert(0,'/private/tmp');from example_http import call,rid
p=OUT/'source-receipt.json';saved=json.loads(p.read_text()) if p.exists() else {}
def record(k,v):saved[k]=v;p.write_text(json.dumps(saved,ensure_ascii=False,indent=2));return v
def once(k,path,body):
 if k not in saved:record(k,call(path,body))
 return saved[k]
inputs=OUT/'inputs';inputs.mkdir(exist_ok=True)
for name in ['example 1.html','example 1.md','example 1 2.json']:
 src=Path('/Users/tang/Desktop')/name;target=inputs/name
 if not target.exists():shutil.copy2(src,target)
 assert target.read_bytes()==src.read_bytes()
html=(inputs/'example 1.html').read_text().split('```html\n',1)[1].rsplit('```',1)[0].strip()
original='<!doctype html>\n<html lang="nb"><head><meta charset="utf-8"><title>example</title></head><body><main>\n'+html+'\n</main></body></html>\n'
examples=ROOT/'workbench/examples';(examples/'example.html').write_text(original)
(examples/'example.md').write_text((inputs/'example 1.md').read_text().removeprefix('# Markdown\n\n'))
(examples/'example.json').write_bytes((inputs/'example 1 2.json').read_bytes())
record('input_hashes',{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs.iterdir()})
if 'upload' not in saved:record('upload',call('/api/upload',raw=original.encode()))
if 'manual' not in saved:
 data=call('/api/source-workspace');task=next(t for t in data['tasks'] if t.get('source_id')=='PE001' and t['operation_type'] in ('SOURCE_REVIEW','SELECTION_REVIEW'))
 req=dict(request_id=rid(),task_id=task['operation_id'],revision=task['revision'],source_revision=task.get('source_revision',''),action='manual',note='User explicitly replaces the Workbench example with the supplied ADF-10 excerpt. This is a training excerpt, not a complete legal document or a legal review. Only file-format wrappers were removed; Norwegian text and chapter links are unchanged.',upload_id=saved['upload']['upload_id'],identity_verified=True,permission_verified=True,explicit_confirmation=True)
 record('manual_request',req);record('manual',call('/api/source-workspace/task-apply',req))
source=next(s for s in call('/api/source-workspace')['sources'] if s['source_id']=='PE001')
record('source',{k:source.get(k) for k in ['source_id','source_title','snapshot_id','content_hash','effective_selection']})
assert source['content_hash']==hashlib.sha256(original.encode()).hexdigest(),saved['manual']
if 'open_request' not in saved:record('open_request',dict(request_id=rid(),source_id='PE001'))
if 'material' not in saved:record('material',call('/api/material/open',saved['open_request']))
print(json.dumps(saved['source']));print('material',saved['material'].get('material',saved['material'])['id'])
