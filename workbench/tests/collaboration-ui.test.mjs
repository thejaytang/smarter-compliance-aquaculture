import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {Collaboration,pointerParts,differenceBlock,differenceLabel,differenceMarkup,provenanceMarkup,valueEditor,collectEditedValue,importResultMessage} from '../frontend/components/collaboration.js';
import {Materials} from '../frontend/components/materials.js';
function workspace(){const nodes=new Map();return {token:{},tabIdentity:'tab-one',id:'material-1',busy:false,opening:false,state:{actor:{id:'reviewer',name:'Reviewer'}},material:{id:'material-1',revision:2,source:{source_id:'SOURCE'},blocks:[],collaboration:{view:'personal'}},draft:{blocks:[],issues:[],checked_scope:[]},q(s){if(!nodes.has(s))nodes.set(s,{innerHTML:'',value:'',textContent:'',querySelectorAll:()=>[]});return nodes.get(s);},root:{querySelectorAll:()=>[]},message(text){this.lastMessage=text;},updateBar(){},clearReader(){},renderMaterial(){},fromMaterial(m){return {blocks:m.blocks||[],issues:[],checked_scope:[]};},loadReader:async()=>{},canLeave:()=>true};}
test('generic difference renderer resolves escaped block paths and remains schema-independent',()=>{const diff={id:'d',path:'/blocks/a~1b/table/cells/41/12',label:'Table cell M42',kind:'changed',base:'old',current:'<master>',incoming:'reviewed',conflict:true};assert.deepEqual(pointerParts(diff.path),['blocks','a/b','table','cells','41','12']);assert.equal(differenceBlock(diff),'a/b');const html=differenceMarkup(diff);assert.match(html,/Table cell M42/);assert.match(html,/Conflict/);assert.match(html,/&lt;master&gt;/);assert.match(html,/Keep current/);assert.match(html,/Adopt submitted/);assert.match(html,/Edit result/);const future=differenceMarkup({...diff,path:'/opaque/nested/value'},{title:'Reserved adapter test',editable:false});assert.match(future,/Reserved adapter test/);assert.doesNotMatch(future,/data-action=/);});
test('missing values and provenance do not invent human review or machine adoption',()=>{const html=differenceMarkup({id:'x',path:'/source_review/fields/version',current_present:false,incoming:'v2'});assert.match(html,/Not present/);const p=provenanceMarkup([{path:'/blocks/b/text',origin:'machine',status:'machine_unreviewed'},{path:'/blocks/b/text',origin:'human',actor:'<Reviewer>',status:'pending_adoption'}]);assert.match(p,/Machine Unreviewed/);assert.match(p,/Pending Adoption/);assert.match(p,/&lt;Reviewer&gt;/);assert.doesNotMatch(p,/human_reviewed/);});
test('nested value editor preserves numbers, booleans, nulls and untouched object shape',()=>{const initial={label:'before',nested:{count:2,enabled:false,empty:null},list:['a']};const values=[{dataset:{valuePath:'["label"]',valueType:'string'},value:'after'},{dataset:{valuePath:'["nested","count"]',valueType:'number'},value:'4'},{dataset:{valuePath:'["nested","enabled"]',valueType:'boolean'},checked:true}];const result=collectEditedValue({querySelectorAll:()=>values},initial);assert.deepEqual(result,{label:'after',nested:{count:4,enabled:true,empty:null},list:['a']});assert.equal(initial.label,'before');assert.match(valueEditor(initial),/data-value-type="boolean"/);});
test('master and merge views reject ordinary material mutations before any API call',async()=>{const x=new Materials();let calls=0;x.api=async()=>calls++;x.message=()=>{};x.material={collaboration:{view:'master'}};assert.equal(await x.mutate('/api/material/save',{},''),false);x.material.collaboration.view='merge';assert.equal(await x.mutate('/api/material/extract',{},''),false);assert.equal(calls,0);});
test('merge conflicts attach to their recorded block and source differences stay global',()=>{const w=workspace(),c=new Collaboration(w);c.state={mode:'coordinator'};w.material.collaboration.provenance=[{path:'/blocks/one/text',origin:'human',actor:'A',status:'pending_adoption'}];w.draft.blocks=[{id:'one'}];c.merge={merge_id:'merge',unresolved:['b'],differences:[{id:'b',path:'/blocks/one/text',current:'a',incoming:'b',conflict:true},{id:'s',path:'/source_review/selection',current:'INCLUDE',incoming:'EXCLUDE'},{id:'gone',path:'/blocks/deleted',current:{text:'removed'},incoming_present:false}]};assert.match(c.blockMarkup({id:'one'}),/data-difference="b"/);assert.doesNotMatch(c.blockMarkup({id:'one'}),/data-difference="s"/);assert.match(c.globalDifferences(),/data-difference="s"/);assert.match(c.globalDifferences(),/data-difference="gone"/);assert.match(c.mergeSummary(),/data-action="collab-adopt" disabled/);});
test('resolving a difference creates only a merge decision and ignores duplicate in-flight clicks',async()=>{const w=workspace(),c=new Collaboration(w);c.state={mode:'coordinator'};c.merge={merge_id:'one',differences:[]};let finish;const calls=[];w.api=async(path,body)=>{calls.push({path,body});return new Promise(resolve=>finish=resolve);};c.showPreview=async r=>c.merge=r;const pending=c.resolve('diff','incoming');await c.resolve('diff','current');assert.equal(calls.length,1);assert.deepEqual(calls[0],{path:'/api/collaboration/resolve',body:{merge_id:'one',decisions:{diff:{action:'incoming'}}}});finish({merge_id:'one',differences:[],unresolved:0});await pending;assert.equal(w.busy,false);});
test('reviewer cannot resolve or adopt master previews',async()=>{const w=workspace(),c=new Collaboration(w);c.state={mode:'reviewer'};c.merge={merge_id:'one'};w.api=async()=>{throw Error('Unexpected mutation');};w.dialog=()=>{throw Error('Coordinator action exposed');};await c.resolve('d','incoming');c.adoptDialog();c.confirmMaster();});
test('source-only preview clears the former material instead of showing unrelated source body',async()=>{const w=workspace(),c=new Collaboration(w);c.state={mode:'coordinator'};await c.showPreview({merge_id:'source-only',material:null,differences:[{id:'s',path:'/source_review/note',current:'a',incoming:'b'}],unresolved:0});assert.equal(w.material,null);assert.equal(w.id,null);assert.match(w.q('#mw-reader').innerHTML,/source-only package/);assert.match(w.q('#mw-content').innerHTML,/data-difference="s"/);assert.equal(c.readonly,true);});
test('source form recovery keys bind actor and source and dirty forms block navigation',()=>{const w=workspace(),c=new Collaboration(w);assert.equal(c.sourceKey('one'),'collaboration-source-v1:reviewer:one:tab-one');assert.notEqual(c.sourceKey('one'),c.sourceKey('two'));c.sourceDirty=true;assert.equal(c.canLeave(),false);assert.match(w.lastMessage,/personal source review/);});
test('new collaboration client refuses old mutation protocol and keeps binary transfer explicit',async()=>{const code=await readFile(new URL('../frontend/components/app.js',import.meta.url),'utf8');assert.match(code,/'X-Material-API-Version':'3'/);assert.match(code,/api\.importPackage=async file/);assert.match(code,/Content-Type':'application\/zip'/);assert.match(code,/api\.download=async/);assert.match(code,/state\.collaboration\?\.mode==='reviewer'/);});

test('source journals bind live tab ownership and keep another tab record intact',()=>{const oldLocal=globalThis.localStorage,oldSession=globalThis.sessionStorage,records=new Map(),session=new Map();globalThis.localStorage={getItem:k=>records.get(k)||null,setItem:(k,v)=>records.set(k,v),removeItem:k=>records.delete(k)};globalThis.sessionStorage={getItem:k=>session.get(k)||null,setItem:(k,v)=>session.set(k,v)};try{const a=new Collaboration(workspace()),wb=workspace();wb.tabIdentity='tab-two';const b=new Collaboration(wb);a.sourceDirty=b.sourceDirty=true;a.sourceDraft={source_id:'source',expected_revision:1,source_review:{note:'A'}};b.sourceDraft={source_id:'source',expected_revision:1,source_review:{note:'B'}};a.saveSourceJournal();b.saveSourceJournal();assert.equal(JSON.parse(records.get(a.sourceKey('source'))).source_review.note,'A');assert.equal(JSON.parse(records.get(b.sourceKey('source'))).source_review.note,'B');assert.notEqual(a.sourceKey('source'),b.sourceKey('source'));}finally{globalThis.localStorage=oldLocal;globalThis.sessionStorage=oldSession;}});
test('coordinator preview request is guarded against duplicate actions and lost view responses',async()=>{const w=workspace(),c=new Collaboration(w);let finish,calls=0,shown=0;w.api=()=>{calls++;return new Promise(resolve=>finish=resolve);};c.showPreview=async()=>shown++;const request=c.runPreview('/api/collaboration/prepare-own',{source_id:'s'});await c.runPreview('/api/collaboration/prepare-own',{source_id:'s'});assert.equal(calls,1);w.token={};finish({merge_id:'late'});await request;assert.equal(shown,0);assert.equal(w.busy,false);});
test('viewing an existing merge decision does not reload its unchanged original',async()=>{const w=workspace(),c=new Collaboration(w);c.state={mode:'coordinator'};w.reader={kind:'pdf',page:7};let reads=0;w.loadReader=async()=>reads++;await c.showPreview({merge_id:'m',material:{...w.material,blocks:[]},differences:[],unresolved:0});assert.equal(reads,0);assert.equal(w.reader.page,7);});

test('nested presence flags distinguish deleted cells and machine comparison labels',()=>{const html=differenceMarkup({id:'cell',path:'/blocks/t/table/rows/41/12',label:'/blocks/t/table/rows/41/12',presence:{current:false,incoming:true,base:false},incoming:'new'},{machine:true});assert.match(html,/row 42, column 13/);assert.match(html,/Not present/);assert.match(html,/Current personal content/);assert.match(html,/Machine candidate/);assert.doesNotMatch(html,/Current master/);});
test('coordinator host does not grant coordinator actions to another named reviewer',async()=>{const w=workspace(),c=new Collaboration(w);c.state={mode:'coordinator',can_adopt:false};assert.equal(c.coordinator,false);await assert.rejects(c.action('collab-adopt',{}),/coordinator/);});
test('reviewer machine resolution uses personal endpoint and preserves merged input binding',async()=>{const w=workspace(),c=new Collaboration(w);c.state={mode:'reviewer',can_adopt:false};c.merge={merge_id:'machine',kind:'machine'};let captured;w.api=async(path,body)=>{captured={path,body};return {...c.merge,differences:[]};};c.showPreview=async()=>{};await c.resolve('cell','edit','reviewed');assert.equal(captured.path,'/api/collaboration/machine-resolve');assert.deepEqual(captured.body,{merge_id:'machine',decisions:{cell:{action:'edit',value:'reviewed'}}});});
test('reader routes personal machine previews separately from coordinator master merges',()=>{const w=new Materials();w.material={collaboration:{view:'merge'}};w.collaboration.merge={kind:'machine'};assert.equal(w.readerView(),'personal');w.collaboration.merge={kind:'submission'};assert.equal(w.readerView(),'master');w.material.collaboration.view='personal';assert.equal(w.readerView(),'personal');});
test('restored inspection disables collaboration before any action or personal recovery write',async()=>{const c=new Collaboration(workspace());c.state={mode:'inspection',read_only:true};assert.equal(c.readonly,true);await assert.rejects(c.action('collab-source',{}),/read-only/);});
test('dialog mutations lock material navigation until server response and reject repeated requests',async()=>{const w=workspace(),c=new Collaboration(w);let finish,calls=0;w.api=()=>{calls++;return new Promise(resolve=>finish=resolve);};const request=c.mutationRequest('/api/collaboration/adopt',{merge_id:'bound'});assert.equal(w.busy,true);await assert.rejects(c.mutationRequest('/api/collaboration/adopt',{merge_id:'bound'}),/Wait/);assert.equal(calls,1);finish({status:'adopted'});assert.equal((await request).status,'adopted');assert.equal(w.busy,false);});
test('HTML original-anchor navigation retains the selected master branch',async()=>{const w=new Materials(),frame={},anchor={value:'table-anchor'};w.id='material';w.material={collaboration:{view:'master'}};w.reader={kind:'html'};w.q=s=>s==='.mw-html'?frame:s==='#mw-html-anchor'?anchor:null;await w.readerAction('reader-anchor');assert.match(frame.src,/view=master#table-anchor$/);});
test('reopened adoption resumes the server request identity after browser restart',()=>{const c=new Collaboration(workspace()),merge={merge_id:'mid',resume_request_id:'server-receipt-id'};assert.equal(c.mergeRequestId('adopt:mid',merge),'server-receipt-id');assert.equal(c.mergeRequestId('adopt:mid',{resume_request_id:'unexpected-other-id'}),'server-receipt-id');assert.equal(c.pending.get('adopt:mid'),'server-receipt-id');});

test('unit provenance separately exposes author reviewer adopter and exact extraction evidence',()=>{
  const html=provenanceMarkup([{path:'/blocks/table/table/rows/1/1',origin:'human',actor:'Ana Jokic',
    reviewer:'Daniel Restad',adopter:'Weijie Tang',content_revision:7,adopted_revision:9,
    candidate_id:'batch-12',submission_id:'submission-34',source_refs:[{scope_id:'page:2'}],status:'human_reviewed'}]);
  for(const value of ['Modified by','Ana Jokic','Reviewed by','Daniel Restad','Adopted by','Weijie Tang',
    'Extraction batch','batch-12','Content version','Adopted version','page:2','row 2, column 2'])assert.ok(html.includes(value),value);
  assert.ok(html.includes('<details>'));
});

// Whole-block differences must be findable by document content, including deletions.
test('added and removed blocks use source text in difference navigation',()=>{
 const added={path:'/blocks/opaque-id',incoming:{type:'text',numbering:'2.1',text:'Keep oxygen above 5 mg/L.'}};
 assert.equal(differenceLabel(added),'2.1 · Keep oxygen above 5 mg/L.');
 assert.equal(differenceLabel({...added,incoming:null,current:added.incoming}),differenceLabel(added));
 assert.match(differenceMarkup({...added,id:'addition',incoming:{text:'<script>',type:'text'}}),/&lt;script&gt;/);
});

test('material adoption reopens master then refreshes personal queue and exposes refresh failure',async()=>{
 for(const queueResult of [true,false]){
  const w=workspace(),c=new Collaboration(w),events=[],personal={id:'material-1',revision:2,blocks:[{text:'Personal saved work'}]};
  w.items=[personal];c.state={mode:'coordinator'};c.merge={merge_id:'merge',resume_request_id:'saved-request'};
  const controls=new Map(),dialog={querySelector(s){if(!controls.has(s))controls.set(s,{checked:true,textContent:''});return controls.get(s);},close(){events.push('close');}};
  w.dialog=(_,init)=>init(dialog);w.api=async()=>({status:'adopted',material:{id:'material-1',revision:3}});
  w.open=async(id,fromSource,view)=>{assert.equal(view,'master');events.push('open-master');};
  c.load=async()=>events.push('collaboration-refresh');w.loadList=async()=>{events.push('queue-refresh');return queueResult;};
  c.adoptDialog();await controls.get('#collab-adopt-submit').onclick();
  assert.deepEqual(events,['close','open-master','collaboration-refresh','queue-refresh']);assert.equal(w.items[0],personal);
  if(queueResult)assert.match(w.lastMessage,/Master content confirmation remains separate/);
  else assert.match(w.lastMessage,/material list could not refresh/);
 }
});


test('receipt import wording follows returned item kinds, including duplicate imports',()=>{
 for(const status of ['imported','already_imported']){
  const message=importResultMessage({status,items:[{kind:'adoption_receipt',status:'imported_for_review'}],message:'Each item requires its own comparison and adoption.'});
  assert.match(message,/Adoption receipt recorded/);assert.match(message,/No further adoption is needed/);assert.doesNotMatch(message,/requires.*adoption/);
 }
 assert.match(importResultMessage({status:'imported',kind:'work'}),/Compare each work or submission item/);
 assert.match(importResultMessage({status:'imported',kind:'submission'}),/Compare each work or submission item/);
 assert.doesNotMatch(importResultMessage({status:'imported',items:[]}),/Adoption receipt recorded/);
 assert.equal(importResultMessage({status:'failed',items:[{kind:'adoption_receipt'}],message:'Validation failed'}),'Validation failed');
 const mixed=importResultMessage({status:'imported',items:[{kind:'adoption_receipt'},{kind:'submission'}]});
 assert.match(mixed,/Compare each work or submission item/);assert.match(mixed,/Recorded adoption receipts need no further adoption/);
});

test('recorded keep-current distinguishes a proposed omission from the chosen result',()=>{
 const html=differenceMarkup({id:'deletion',path:'/blocks/b',kind:'deletion',resolution:'current',current:{id:'b',type:'text',text:'Retained human text'},presence:{current:true,incoming:false}},{machine:true});
 assert.match(html,/Candidate omits content · Selected: Keep current/);
 assert.match(html,/data-choice="current" aria-pressed="true"/);
 assert.match(html,/data-choice="incoming" aria-pressed="false"/);
 assert.doesNotMatch(html,/Deletion · choice recorded/);
});
test('automatic comparison suggestions never claim a recorded human selection',()=>{
 for(const resolution of ['auto_current','auto_incoming']){
  const html=differenceMarkup({id:'value',path:'/source_review/fields/title',resolution,current:'Current',incoming:'Submitted'});
  assert.match(html,/Suggested:/);assert.doesNotMatch(html,/Selected:/);assert.doesNotMatch(html,/aria-pressed="true"/);
 }
 const edited=differenceMarkup({id:'edit',path:'/blocks/b/text',resolution:'edit',current:'A',incoming:'B'});
 assert.match(edited,/Selected: Edited result/);
});
