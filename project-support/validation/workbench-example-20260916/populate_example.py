"""Populate only the registered example via versioned material/splitting APIs."""
from pathlib import Path
from html.parser import HTMLParser
import json,sys,uuid
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path.insert(0,'/private/tmp')
from example_http import call
r=json.loads((OUT/'registration.json').read_text());m=r['material'].get('material',r['material']);mid=m['id']
spec=json.loads((ROOT/'workbench/examples/example.json').read_text())
path=OUT/'population.json';saved=json.loads(path.read_text()) if path.exists() else {}
def record(k,v):saved[k]=v;path.write_text(json.dumps(saved,ensure_ascii=False,indent=2));return v
def ident(key):return str(uuid.uuid5(uuid.NAMESPACE_URL,'workbench-example/20260916/'+mid+'/'+key))
class Anchors(HTMLParser):
 def __init__(self):super().__init__();self.values={};self.active=None
 def handle_starttag(self,tag,attrs):
  if tag in ('p','h1','h2'):self.active=(tag,dict(attrs).get('id'),[])
 def handle_data(self,data):
  if self.active:self.active[2].append(data)
 def handle_endtag(self,tag):
  if self.active and self.active[0]==tag:
   key=''.join(self.active[2]);assert key not in self.values;self.values[key]=self.active[1];self.active=None
reader=call('/api/material/reader?id='+mid);anchors=Anchors();anchors.feed(reader['html'])
def refs(text):return [{'scope_id':m['scope'][0]['id'],'anchor':anchors.values[text]}]
blocks=[dict(id=ident('notice'),type='text',role='document_information',text=spec['notice'],source_refs=refs(spec['notice']),parent_id=None,dependencies=[])]
for c in spec['cases']:
 hid=ident(c['id']+'/heading');blocks.append(dict(id=hid,type='heading',level=1,text=c['title'],source_refs=refs(c['title']),parent_id=None,dependencies=[]))
 for i,text in enumerate(c['paragraphs']):blocks.append(dict(id=ident(c['id']+'/p'+str(i)),type='text',text=text,source_refs=refs(text),parent_id=hid,dependencies=[]))
if 'content_request' not in saved:record('content_request',dict(request_id=ident('content-save'),material_id=mid,expected_revision=m['revision'],blocks=blocks,issues=[],checked_scope=[],association_reviewed=False))
if 'content' not in saved:record('content',call('/api/material/save',saved['content_request']))
material=call('/api/material?id='+mid);material=material.get('material',material)
assert material['title']=='example' and [b['text'] for b in material['blocks']]==[b['text'] for b in blocks]
for c in spec['cases']:
 name=c['id'];steps=[];unit_text={};roots=[]
 def add(action,key,**args):
  request={'request_id':ident(name+'/'+key),'action':action,**args};steps.append(request);return request['request_id']
 start=add('start','start',material_id=mid,material_revision=material['revision'],block_ids=[ident(name+'/p'+str(i)) for i in range(len(c['paragraphs']))])
 root=str(uuid.uuid5(uuid.UUID(start),'root'));unit_text[root]='\n\n'.join(c['paragraphs'])
 roots=[root]
 if c.get('second'):
  split=add('split','split',unit_id=root,at=len(c['paragraphs'][0])+2)
  left,right=(str(uuid.uuid5(uuid.UUID(split),key)) for key in ('left','right'))
  unit_text[left]=c['paragraphs'][0]+'\n\n';unit_text[right]=c['paragraphs'][1];del unit_text[root];roots=[left,right]
 def build(uid,details,key):
  text=unit_text[uid]
  for field,value in details.get('fields',{}).items():
   start=text.index(value);add('assign',key+'/field/'+field,unit_id=uid,field=field,start=start,end=start+len(value))
  for child in details.get('children',[]):
   fragment=child['text'];start=text.index(fragment)
   if text.find(fragment,start+1)>=0 and child.get('occurrence')!=0:raise ValueError('Ambiguous example child: '+child['key'])
   step=add('extract',key+'/'+child['key'],unit_id=uid,field=child['relation'],start=start,end=start+len(fragment))
   childid=str(uuid.uuid5(uuid.UUID(step),'child'));unit_text[childid]=fragment;build(childid,child,key+'/'+child['key'])
  if details.get('group'):add('group',key+'/group',unit_id=uid,**details['group'])
  for field,quantity in details.get('quantities',{}).items():add('quantity',key+'/quantity/'+field,unit_id=uid,field=field,quantity=quantity)
  add('done',key+'/done',unit_id=uid)
 build(roots[0],c,name+'/root')
 if c.get('second'):build(roots[1],c['second'],name+'/second')
 add('phase','complete',phase='complete')
 if name+'/request' not in saved:record(name+'/request',dict(request_id=ident(name+'/save'),action='save-draft',steps=steps))
 if name+'/document' not in saved:record(name+'/document',call('/api/requirements/step',saved[name+'/request'])['document'])
 doc=saved[name+'/document'];assert doc['phase']=='complete';print(name,len(doc['units']),'units',flush=True)
 for i,uid in enumerate(roots):
  key=name+'/interpretation'+str(i);values=c['interpretation'] if i==0 else c['second_interpretation']
  context=call('/api/interpretations?unit_id='+uid)
  relevant=c['paragraphs'] if not c.get('second') else [c['paragraphs'][i]]
  citations=[{'id':x['id'],'quote':x['text'],'start':0,'end':len(x['text'])} for x in context['context']['citations'] if x['text'] in relevant]
  assert len(citations)==len(relevant)
  fields={}
  for field,value in values.items():
   exact=next((ref for ref in citations if value in ref['quote']),None)
   fields[field]={'value':value,'basis':'source' if field in ('scope','condition','demand') and exact else 'interpretation','references':citations,'gaps':c['gaps'] if field=='verification' else [],'state':'specified'}
  if key+'/request' not in saved:record(key+'/request',dict(request_id=ident(key+'/save'),unit_id=uid,expected_revision=context['revision'],context_fingerprint=context['context']['fingerprint'],linked_material_ids=[],fields=fields,action='save'))
  if key not in saved:record(key,call('/api/interpretations/save',saved[key+'/request']))
record('pin',call('/api/material-queue/pin',{'material_id':mid,'pinned':True}))
first=call('/api/material-queue?bucket=pending&limit=1')['materials'][0];assert first['id']==mid and first['title']=='example' and first['queue']['pinned']
record('verified_first',{'id':mid,'title':first['title'],'source_id':first['source']['source_id']})
print(json.dumps(saved['verified_first']))
