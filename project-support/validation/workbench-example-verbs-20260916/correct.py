from pathlib import Path
import json,sys,uuid,sqlite3
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path.insert(0,'/private/tmp');from example_http import call
old=json.loads((ROOT/'project-support/workbench-example-separate-20260916/verification.json').read_text());entries={v['entry']:v for v in old['entries']};mid='3069f79e2481e4c18f1e268c8344de9f'
p=OUT/'correction.json';saved=json.loads(p.read_text()) if p.exists() else {}
if not (OUT/'before.sqlite').exists():
 with sqlite3.connect(ROOT/'workbench/runtime/workbench.sqlite') as src,sqlite3.connect(OUT/'before.sqlite') as dst:src.backup(dst)
def ident(key):return str(uuid.uuid5(uuid.NAMESPACE_URL,'adf10-verbs/'+key))
def record(k,v):saved[k]=v;p.write_text(json.dumps(saved,ensure_ascii=False,indent=2));return v
def once(key,path,body):
 if key not in saved:record(key,call(path,body))
 return saved[key]
for key in ['R2','R4']:
 if key in saved:continue
 doc=call('/api/requirements/session?id='+entries[key]['session']);uid=entries[key]['id'];root=uid+'/structure';text=doc['text'];steps=[];holders={};counts={}
 def step(action,label,**kw):
  rid=ident(key+'/'+label);steps.append(dict(request_id=rid,action=action,**kw));return rid
 def edit(op,label,node=root,**kw):return step('structure',label,unit_id=uid,node_id=node,operation=op,**kw)
 def mark(role,value,label,node=root,start=None):
  at=text.index(value) if start is None else text.index(value,start)
  rid=edit('add',label,node,field=role,start=at,end=at+len(value));holders.setdefault((node,role),str(uuid.uuid5(uuid.UUID(rid),'field')));counts[(node,role)]=counts.get((node,role),0)+1
  return str(uuid.uuid5(uuid.UUID(rid),'fragment'))
 def clause(value,label):
  at=text.index(value);rid=edit('add-group',label,start=at,end=at+len(value));holders.setdefault((root,'requirements'),str(uuid.uuid5(uuid.UUID(rid),'field')));counts[(root,'requirements')]=counts.get((root,'requirements'),0)+1
  return str(uuid.uuid5(uuid.UUID(rid),'clause'))
 step('phase','reopen',phase='fields')
 for n in doc['structure_views'][uid]['children']:edit('remove','clear/'+n['id'],n['id'])
 if key=='R2':
  core=text.split(', including')[0];g=clause(core,'movement-group')
  mark('Subject','aquaculture animals','animal',g);mark('Subject','aquaculture animal products','product',g)
  mark('Main Verb','brought into','inbound',g);mark('Main Verb','removed from','outbound',g)
  mark('Object','the aquaculture establishment','establishment',g)
  mark('Object','place of origin','origin');mark('Object','place of destination','destination')
 else:
  mark('Object','results of completed health inspections','result')
  items=[('number of completed health inspections',None),('sampling',None),('examinations performed',('examinations','performed')),('diagnoses',None),('treatments carried out',('treatments','carried out'))]
  for i,(value,pair) in enumerate(items):
   g=clause(value,'category/'+str(i))
   if pair:
    mark('Subject',pair[0],'category/'+str(i)+'/subject',g);mark('Main Verb',pair[1],'category/'+str(i)+'/verb',g)
   else:mark('Object',value,'category/'+str(i)+'/object',g)
 for (owner,role),n in counts.items():
  if n>1:edit('quantity','quantity/'+owner+'/'+role,holders[(owner,role)],quantity=[n,n] if (key=='R2' and owner==root and role=='Object') or (key=='R4' and role=='requirements') else n)
 step('done','done',unit_id=uid);step('phase','complete',phase='complete')
 req=dict(request_id=ident(key+'/save'),action='save-draft',session_id=doc['id'],expected_revision=doc['revision'],steps=steps)
 preview=call('/api/requirements/step',dict(req,request_id=ident(key+'/preview'),action='preview'));assert preview['document']['text']==text
 record(key+'-before',doc);once(key,'/api/requirements/step',req);print(key,'verbs saved',flush=True)
# Refresh R1's explicit links to the revised child versions, preserving all IDs.
if 'R1' not in saved:
 doc=call('/api/requirements/session?id='+entries['R1']['session']);uid=entries['R1']['id'];root=uid+'/structure';group=next(n for n in doc['structure_views'][uid]['children'] if n.get('role')=='subrequirement');steps=[dict(request_id=ident('R1/reopen'),action='phase',phase='fields'),dict(request_id=ident('R1/remove-links'),action='structure',unit_id=uid,node_id=group['id'],operation='remove')]
 for key in ['R2','R3','R4']:steps.append(dict(request_id=ident('R1/link/'+key),action='structure',unit_id=uid,node_id=root,operation='link',field='subrequirement',target_id=entries[key]['id']))
 field=str(uuid.uuid5(uuid.UUID(ident('R1/link/R2')),'field'));steps.extend([dict(request_id=ident('R1/all'),action='structure',unit_id=uid,node_id=field,operation='quantity',quantity=3),dict(request_id=ident('R1/done'),action='done',unit_id=uid),dict(request_id=ident('R1/complete'),action='phase',phase='complete')])
 once('R1','/api/requirements/step',dict(request_id=ident('R1/save'),action='save-draft',session_id=doc['id'],expected_revision=doc['revision'],steps=steps))
# Review the existing explanatory fields against the revised source structures.
for key in ['R1','R2','R4']:
 if key+'-interpretation' in saved:continue
 uid=entries[key]['id'];x=call('/api/interpretations?unit_id='+uid);fields=x['fields']
 if key=='R2':
  fields['scope']['value']='Operational journals under R1, covering records of aquaculture animals and aquaculture animal products.';fields['scope']['basis']='interpretation'
  fields['scope_information']['value']='R1 supplies the journal-keeping obligation and its establishment scope. Within R2, aquaculture animals and aquaculture animal products are the grammatical subjects of the reduced passive phrase: they undergo the movement, and no actor performing the movement is named. The two Subject entries list covered categories; a single record need not be both an animal and a product.'
  fields['condition_information']['value']='Use R1’s shared chapter-applicability condition through the Subrequirement link. The phrases brought into and removed from describe the inbound and outbound records that must be covered. They do not require each animal or product to undergo both movements. Preserve the reference to the same aquaculture establishment. No independent modal verb appears in R2.'
  fields['verification']['value']='For each journal to which R1 applies, check the relevant animal and animal-product movement records. Cover both source-stated directions: brought into AND removed from. The establishment is the shared location complement. Check both required location categories: place of origin AND place of destination, [2,2]. Group counts describe coverage of the listed categories and directions, not simultaneous properties of every record. Verify updated and complete records. The verbs qualify the movements to be recorded; they do not create an obligation to bring in or remove animals. Missing records do not prove that no movement occurred.'
 elif key=='R4':
  fields['condition_information']['value']='Apply R1’s shared applicability condition. In R4, completed qualifies health inspections; performed qualifies examinations and carried out qualifies treatments. These words restrict the records to activities that occurred. They do not require every activity to take place. Sampling is a noun naming an information category here, not an imperative verb.'
  fields['verification']['value']='Compare the recorded results with completed health inspections. Check ALL five information categories, [5,5]: number of completed health inspections; sampling; examinations performed; diagnoses; treatments carried out. The examinations/performed and treatments/carried out groups preserve their passive verbal relations. Their grammatical subjects are activities being described, not named personnel. Do not convert these participles into new duties to perform examinations or carry out treatments. Verify coverage and currency, including supported records of none where appropriate. No inspection frequency or update deadline is stated in this excerpt.'
 once(key+'-interpretation','/api/interpretations/save',dict(request_id=ident(key+'/interpretation'),unit_id=uid,expected_revision=x['revision'],context_fingerprint=x['context']['fingerprint'],linked_material_ids=[],fields=fields,action='save'));print(key,'interpretation saved',flush=True)
print('DONE')
