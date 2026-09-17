from pathlib import Path
from html.parser import HTMLParser
import json,sys,uuid,re
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path.insert(0,'/private/tmp');from example_http import call
receipt=json.loads((OUT/'source-receipt.json').read_text());material=receipt['material'].get('material',receipt['material']);mid=material['id']
p=OUT/'population.json';saved=json.loads(p.read_text()) if p.exists() else {}
def record(k,v):saved[k]=v;p.write_text(json.dumps(saved,ensure_ascii=False,indent=2));return v
def ident(key):return str(uuid.uuid5(uuid.NAMESPACE_URL,'adf10-example/'+mid+'/'+key))
def once(key,path,request):
 if key not in saved:record(key,call(path,request))
 return saved[key]
md=(ROOT/'workbench/examples/example.md').read_text().strip();parts=md.split('\n\n');assert len(parts)==2
paragraph=re.sub(r'\[([^]]+)\]\([^)]+\)',r'\1',parts[0]);bullets=[x.removeprefix('- ') for x in parts[1].splitlines()];assert len(bullets)==3
class Anchors(HTMLParser):
 def __init__(self):super().__init__();self.stack=[];self.values={}
 def handle_starttag(self,tag,attrs):
  if tag in ('p','li'):self.stack.append([tag,dict(attrs),[]])
 def handle_data(self,text):
  for n in self.stack:n[2].append(text)
 def handle_endtag(self,tag):
  if self.stack and self.stack[-1][0]==tag:
   _,attrs,data=self.stack.pop();text=' '.join(''.join(data).split());self.values[text]=attrs.get('id')
a=Anchors();reader=call('/api/material/reader?id='+mid);a.feed(reader['html']);scope=material['scope'][0]['id']
blocks=[]
for i,text in enumerate([paragraph,*bullets]):
 assert text in a.values,(text,a.values)
 block=dict(id=ident('block/'+str(i)),type='text',text=text,source_refs=[{'scope_id':scope,'anchor':a.values[text]}],parent_id=None,dependencies=[])
 # Keep the user's Markdown links and list appearance separately from the plain source spans.
 source=parts[0] if i==0 else '- '+text
 block['markdown']={'version':1,'source':source,'baseline':source}
 blocks.append(block)
if 'content' not in saved:
 current=call('/api/material?id='+mid);current=current.get('material',current)
 once('content','/api/material/save',dict(request_id=ident('save-content'),material_id=mid,expected_revision=current['revision'],blocks=blocks,issues=[],checked_scope=[],association_reviewed=False))
current=call('/api/material?id='+mid);current=current.get('material',current)
assert [b['text'] for b in current['blocks']]==[paragraph,*bullets]
cond=json.loads((ROOT/'workbench/examples/example.json').read_text())['conditions'][0]
specs=[
 dict(key='R1',ids=[0],fields={'Subject':'the operational journal','Modal Verb':'shall','Main Verb':'contain','Object':'updated information'},conditions=[cond]),
 dict(key='R2',ids=[0,1],fields={'Subject':'the operational journal','Modal Verb':'shall','Main Verb':'contain','Object':'aquaculture animals and aquaculture animal products brought into and removed from the aquaculture establishment'},conditions=[cond],details=['place of origin','place of destination']),
 dict(key='R3',ids=[0,2],fields={'Subject':'the operational journal','Modal Verb':'shall','Main Verb':'contain','Object':'mortality per production unit'},conditions=[cond,'relevant to the production method']),
 dict(key='R4',ids=[0,3],fields={'Subject':'the operational journal','Modal Verb':'shall','Main Verb':'contain','Object':'results of completed health inspections'},conditions=[cond],details=['number of completed health inspections','sampling','examinations performed','diagnoses','treatments carried out'])]
units={}
for spec in specs:
 key=spec['key'];text='\n\n'.join(blocks[i]['text'] for i in spec['ids']);steps=[]
 def add(action,key,**kw):
  r=dict(request_id=ident(spec['key']+'/'+key),action=action,**kw);steps.append(r);return r['request_id']
 start=add('start','start',material_id=mid,material_revision=current['revision'],block_ids=[blocks[i]['id'] for i in spec['ids']])
 uid=str(uuid.uuid5(uuid.UUID(start),'root'));root=uid+'/structure';units[key]=uid
 field_ids={};members={}
 def mark(role,value,key,node=root):
  at=text.index(value);step=add('structure',key,unit_id=uid,node_id=node,operation='add',field=role,start=at,end=at+len(value))
  if node==root:
   field_ids.setdefault(role,str(uuid.uuid5(uuid.UUID(step),'field')));members[role]=members.get(role,0)+1
  return str(uuid.uuid5(uuid.UUID(step),'fragment'))
 for role,value in spec['fields'].items():mark(role,value,'field/'+role)
 for i,value in enumerate(spec['conditions']):mark('conditions',value,'condition/'+str(i))
 if spec.get('details'):
  details=spec['details'];a0=text.index(details[0]);end=text.index(details[-1])+len(details[-1]);detail=text[a0:end]
  node=mark('Object',detail,'details')
  add('structure','details/decompose',unit_id=uid,node_id=node,operation='decompose')
  for j,value in enumerate(details):mark('Object',value,'details/'+str(j),node=node)
  add('structure','details/quantity',unit_id=uid,node_id=node,operation='quantity',quantity=[len(details),len(details)])
 for role,count in members.items():
  if count>1:add('structure','quantity/'+role,unit_id=uid,node_id=field_ids[role],operation='quantity',quantity=count)
 add('done','done',unit_id=uid);add('phase','complete',phase='complete')
 result=once(key,'/api/requirements/step',dict(request_id=ident(key+'/save'),action='save-draft',steps=steps));assert result['status']=='saved'
 print(key,'saved',flush=True)
# Link the three complete list-item requirements, then finish the parent again.
parent=saved['R1']['document'];steps=[dict(request_id=ident('links/reopen'),action='phase',phase='fields')]
for key in ['R2','R3','R4']:
 rid=ident('link/'+key);steps.append(dict(request_id=rid,action='structure',unit_id=units['R1'],node_id=units['R1']+'/structure',operation='link',field='subrequirement',target_id=units[key]))
first=str(uuid.uuid5(uuid.UUID(ident('link/R2')),'field'))
steps.extend([dict(request_id=ident('links/qty'),action='structure',unit_id=units['R1'],node_id=first,operation='quantity',quantity=3),dict(request_id=ident('links/done'),action='done',unit_id=units['R1']),dict(request_id=ident('links/complete'),action='phase',phase='complete')])
once('R1-links','/api/requirements/step',dict(request_id=ident('links/save'),action='save-draft',session_id=parent['id'],expected_revision=parent['revision'],steps=steps))
record('units',units)
# Explanatory rule names below are proposed data concepts, not agreed Site Model fields.
common_scope='Identify the operational journal and its owning aquaculture establishment. A = journals associated with aquaculture establishments. Bind establishment_id, journal_id and the assessment date; these are proposed data concepts, not an agreed Site Model schema.'
common_condition='Within A, determine which establishments are covered by specific record-keeping provisions in Chapters 4, 5 or 6. Proposed logical form: NOT (covered_by_chapter_4 OR covered_by_chapter_5 OR covered_by_chapter_6). B contains journals whose establishments are outside those specific provisions. The excerpt links to these chapters but does not supply their contents. Unknown applicability must remain unresolved, not default to false.'
gaps=['The linked Chapters 4, 5 and 6 have not been supplied here; their applicability cannot be resolved from this excerpt alone.','The excerpt requires updated information but supplies no fixed update interval. Agree the assessment date, relevant records and evidence of currency without inventing a deadline.','No Site Model records, accepted field mappings or real compliance assessment are included.']
logic={
 'R1':dict(scope_information=common_scope,condition_information=common_condition,verification='For each journal in B, require ALL three linked content requirements: R2 AND R3 AND R4. Check that the required information is present and updated in the same assessment context. The phrase at a minimum means at least the listed content; it does not prohibit additional journal information. C contains journals supported by sufficient evidence for all three requirements. Only with adequate coverage and evidence may B ⊆ C support a positive result. Missing evidence is unresolved; a verified missing mandatory item is a failure. This example defines the method and does not produce a verdict.'),
 'R2':dict(scope_information=common_scope+' R2 inherits the lead-in paragraph from R1 and concerns records of animals and animal products entering and leaving the same establishment.',condition_information=common_condition+' Preserve both inbound and outbound coverage from brought into and removed from; do not inspect just one direction.',verification='For each applicable journal, compare its movement records with the relevant known inbound/outbound movements. The required location group is ALL 2: place of origin AND place of destination. Confirm the journal records cover the relevant animals and animal products and that their information is updated. [2,2] counts the two listed information categories; it does not limit the number of movements or records. Evidence sources and record joins are proposed checks requiring an agreed Site Model mapping. Do not infer completeness from a single populated row.'),
 'R3':dict(scope_information=common_scope+' R3 inherits the lead-in from R1. Identify the establishment’s production units and production method so mortality information can be checked at the stated unit level.',condition_information=common_condition+' Additionally retain relevant to the production method as a qualification on the mortality-per-production-unit information. Decide the relevant units/representation using the production method. This qualification does not exempt the entire establishment from R1, R2 or R4. The excerpt does not define relevance; keep that decision unresolved when unsupported.',verification='For every relevant production unit, verify that the journal contains updated mortality information attributable to that unit. The excerpt provides no mortality threshold, mandatory reporting interval or unit of measurement. Do not invent a mortality limit or treat a missing value as zero. The check concerns record coverage and currency, not whether mortality is acceptably low.'),
 'R4':dict(scope_information=common_scope+' R4 inherits the lead-in from R1 and concerns completed health inspections and their recorded results for the same establishment.',condition_information=common_condition+' Restrict inspection-result checking to completed inspections. The excerpt does not specify a minimum inspection frequency or require all listed activities to have occurred in every inspection.',verification='Check the recorded results against the known completed health inspections. The required result group is ALL 5: number of completed inspections AND sampling AND examinations performed AND diagnoses AND treatments carried out. [5,5] counts information categories, not five inspections or five mandatory interventions. Where no sampling, diagnosis or treatment occurred, determine from evidence how that absence is recorded; do not invent an event and do not treat a blank field as proof that none occurred. Verify completeness and currency; inspection frequency and required update deadlines are not stated here.')}
for spec in specs:
 key=spec['key'];ctx=call('/api/interpretations?unit_id='+units[key]);citations=[dict(id=c['id'],quote=c['text'],start=0,end=len(c['text'])) for c in ctx['context']['citations'] if c.get('block_id') in {b['id'] for b in blocks}]
 values={'scope':spec['fields']['Subject'],'condition':'\n'.join(spec['conditions']),'demand':' '.join([spec['fields']['Modal Verb'],spec['fields']['Main Verb'],spec['fields']['Object']]),**logic[key]}
 fields={k:dict(value=v,basis='source' if k in ('scope','condition','demand') else 'interpretation',references=citations,gaps=gaps if k=='condition_information' else [],state='specified') for k,v in values.items()}
 once(key+'-interpretation','/api/interpretations/save',dict(request_id=ident(key+'/interpretation'),unit_id=units[key],expected_revision=ctx['revision'],context_fingerprint=ctx['context']['fingerprint'],linked_material_ids=[],fields=fields,action='save'))
 print(key,'interpretation saved',flush=True)
record('pin',call('/api/material-queue/pin',{'material_id':mid,'pinned':True}))
# Portable explanation keeps the provided English JSON intact and states normalization explicitly.
(ROOT/'workbench/examples/example-workbench.json').write_text(json.dumps(dict(schema='workbench-example/1',source_id='ADF-10',source_language='English',provided_schema='example.json',requirements=specs,interpretations=logic,gaps=gaps,normalization=['English demonstration translation based on the user-supplied English JSON; original Norwegian excerpt retained in source history.','Each child entry includes the original lead-in plus its own list item, making inherited scope and modality traceable without invented text.','Three child Requirements are linked from R1 with All 3. Nested lists of 2 and 5 information categories become source-bound Object groups with exact [2,2] and [5,5]; the provided JSON remains unchanged.','Exact group counts concern the listed mandatory categories; they do not prohibit additional journal content.']),ensure_ascii=False,indent=2))
print('DONE',mid)
