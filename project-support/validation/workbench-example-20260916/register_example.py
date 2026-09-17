"""Explicitly create the user-requested demonstration through owning HTTP APIs."""
from pathlib import Path
import sys,json,html
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,'/private/tmp')
from example_http import call,rid
OUT=Path(__file__).parent
receipt_path=OUT/'registration.json'
r=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
def record(k,v):
 r[k]=v;receipt_path.write_text(json.dumps(r,ensure_ascii=False,indent=2));return v
spec=json.loads((ROOT/'workbench/examples/example.json').read_text())
body=['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>example</title></head><body><main id="documentBody"><h1>example</h1><p>'+html.escape(spec['notice'])+'</p>']
for case in spec['cases']:
 body.append('<section><h2 id="'+case['id']+'">'+html.escape(case['title'])+'</h2>')
 for i,p in enumerate(case['paragraphs']):body.append('<p id="'+case['id']+'-'+str(i)+'">'+html.escape(p)+'</p>')
 body.append('</section>')
body.append('</main></body></html>')
original='\n'.join(body)
(ROOT/'workbench/examples/example.html').write_text(original)
if 'upload' not in r:record('upload',call('/api/upload',raw=original.encode()))
if 'inspection' not in r:record('inspection',call('/api/sources/inspect',{'upload_id':r['upload']['upload_id'],'filename':'example.html'}))
fields=dict(source_title='example',folder_code='E_Project_Engineering',file_format='html',issuer='Workbench demonstration',jurisdiction='Other',document_type='Other',requirement_role='Draft working material',authoritative_language='English',source_family='Workshop demonstration',version='2026-09-16',inclusion_rationale='User-requested training example for demonstrating the Workbench; no normative authority.',source_notes=spec['notice'],official_url='',retrieval_url='')
if 'intake_request' not in r:record('intake_request',dict(request_id=rid(),upload_id=r['upload']['upload_id'],inspection_id=r['inspection']['inspection_id'],**fields))
if 'intake' not in r:record('intake',call('/api/sources/intake',r['intake_request']))
if 'accept_request' not in r:
 data=call('/api/source-workspace');task=next(t for t in data['tasks'] if t['operation_id']==r['intake']['operation_id'])
 allowed={k:v for k,v in fields.items() if k in task['candidate_fields']}
 allowed['operator_selection_decision']='INCLUDE'
 record('accept_request',dict(request_id=rid(),task_id=task['operation_id'],revision=task['revision'],source_revision=task.get('source_revision',''),action='candidate_accept',candidate_fields=allowed,note='Create the example requested by the user for Workbench training only; not a legal source or compliance approval.',explicit_confirmation=True))
if 'accepted' not in r:record('accepted',call('/api/source-workspace/task-apply',r['accept_request']))
data=call('/api/source-workspace');sources=[s for s in data['sources'] if s.get('source_title')=='example'];assert len(sources)==1,sources
record('source_id',sources[0]['source_id'])
if 'open_request' not in r:record('open_request',dict(request_id=rid(),source_id=r['source_id']))
if 'material' not in r:record('material',call('/api/material/open',r['open_request']))
print(json.dumps({'source_id':r['source_id'],'material':r['material']},ensure_ascii=False)[:3000])
