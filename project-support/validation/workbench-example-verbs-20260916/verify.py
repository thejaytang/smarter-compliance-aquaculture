from pathlib import Path
import json,sys
sys.path.insert(0,'/private/tmp');from example_http import call
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
prior=json.loads((ROOT/'project-support/workbench-example-separate-20260916/verification.json').read_text());entries={x['entry']:x for x in prior['entries']};mid='3069f79e2481e4c18f1e268c8344de9f'
def walk(n):
 yield n
 for c in n.get('children',[]):yield from walk(c)
active=call('/api/requirements?material_id='+mid);assert len(active['sessions'])==4 and {s['id'] for s in active['sessions']}=={e['session'] for e in entries.values()}
report=[];docs={};checks={}
for key,e in entries.items():
 d=call('/api/requirements/session?id='+e['session']);u=e['id'];docs[key]=d;tree=d['structure_views'][u];assert d['text']==e['text'] and len(d['source_segments'])==1
 verbs=[]
 for n in walk(tree):
  if n['kind']=='fragment':
   assert d['text'][slice(*n['span'])]==n['text']
   if n['role']=='Main Verb':verbs.append(n['text'])
 if key=='R1':assert verbs==['contain']
 if key=='R2':assert verbs==['brought into','removed from'] and any(n.get('quantity')==[2,2] for n in walk(tree))
 if key=='R3':assert not verbs
 if key=='R4':assert verbs==['performed','carried out'] and any(n.get('quantity')==[5,5] and len(n['children'])==5 for n in walk(tree))
 x=call('/api/interpretations?unit_id='+u);assert not x['stale'];checks[key]=x
 report.append(dict(entry=key,id=u,session=d['id'],revision=d['revision'],verbs=verbs,interpretation_revision=x['revision']))
links=next(n for n in docs['R1']['structure_views'][entries['R1']['id']]['children'] if n.get('role')=='subrequirement');assert links['quantity']==3 and {n['target_id'] for n in links['children']}=={entries[k]['id'] for k in ['R2','R3','R4']}
# Keep portable normalization synchronized with the actual saved structure, not a lossy flat field list.
p=ROOT/'workbench/examples/example-workbench.json';data=json.loads(p.read_text())
for spec in data['requirements']:
 key=spec['key'];uid=entries[key]['id'];spec['structure']=docs[key]['structure_views'][uid]
 if key in ('R2','R4'):
  spec.pop('fields',None);spec.pop('details',None)
  spec['semantic_notes']='Main Verb marks include source-stated passive participles inside descriptive phrases. They are not independent obligations; the journal-keeping obligation remains in R1.'
 data['interpretations'][key]={k:checks[key]['fields'][k]['value'] for k in ['scope_information','condition_information','verification']}
data['normalization']=[x.replace('Nested lists of 2 and 5 information categories become source-bound Object groups with exact [2,2] and [5,5]','The 2 location categories and 5 inspection-result categories remain source-bound groups with exact [2,2] and [5,5]') for x in data['normalization']]
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
