import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {materialSystems,systemCards,renderDashboard} from '../frontend/components/dashboard.js';
const code = await readFile(new URL('../frontend/components/materials.js', import.meta.url), 'utf8');
const {Materials,materialStatus,extractionScopeText,locationLabel} = await import('../frontend/components/materials.js');
const storage = new Map();
globalThis.localStorage = {getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,String(value)),removeItem:key=>storage.delete(key)};
const material = () => ({id:'one',title:'Isolated material',source:{source_id:'fixture',snapshot_id:'snapshot-1'},revision:4,content_revision:2,blocks:[{id:'text-1',type:'text',text:'Human correction',source_refs:[{scope_id:'page:1',page:1}]}],scope:[{id:'page:1',label:'Page 1'}],issues:[],checked_scope:[],association_review_required:true,content_status:'draft',candidates:[]});
function instance(){
  const x=new Materials();x.requirements={render(){}};x.state={actor:{id:'reviewer-1',name:'Isolated reviewer'}};x.material=material();x.id=x.material.id;x.localBase=4;x.draft=x.fromMaterial(x.material);x.dirty=true;x.token={};x.items=[x.material];x.nodes=new Map();x.q=s=>{if(!x.nodes.has(s))x.nodes.set(s,{innerHTML:'',textContent:'',scrollTop:0});return x.nodes.get(s);};x.root={querySelectorAll:()=>[]};x.renderMaterial=()=>{};x.renderContent=()=>{};x.message=(text,kind)=>x.lastMessage={text,kind};return x;
}
test('save sends one material snapshot and never confirms or extracts', async()=>{
  const x=instance(),calls=[];x.api=async(path,body)=>{calls.push({path,body});return {status:'applied',material:{...material(),revision:5}};};
  await x.save();assert.equal(calls.length,1);assert.equal(calls[0].path,'/api/material/save');assert.equal(calls[0].body.material_id,'one');assert.equal(calls[0].body.expected_revision,4);assert.equal(calls[0].body.blocks[0].text,'Human correction');assert.equal('actor' in calls[0].body,false);assert.equal(x.dirty,false);assert.equal(x.material.content_status,'draft');
});
test('in-flight save prevents navigation and makes editor inert',async()=>{
  const x=instance();let complete;x.api=()=>new Promise(resolve=>complete=resolve);const request=x.save();assert.equal(x.busy,true);assert.equal(x.canLeave(),false);assert.equal(x.q('#mw-content').inert,true);complete({status:'applied',material:{...material(),revision:5}});await request;assert.equal(x.q('#mw-content').inert,false);assert.equal(x.canLeave(),true);
});
test('a conflicting save preserves local changes and original revision guard',async()=>{
  const x=instance(),original=x.draft;x.api=async()=>({status:'conflict',conflict_id:'durable-1',material:{...material(),revision:6}});assert.equal(await x.save(),false);assert.equal(x.draft,original);assert.equal(x.localBase,4);assert.equal(x.dirty,true);assert.equal(x.localConflict,true);assert.match(x.lastMessage.text,/retained/);
});
test('retry after uncertain save reuses request identity',async()=>{
  const x=instance(),calls=[];let first=true;x.api=async(path,body)=>{calls.push(body);if(first){first=false;throw Error('Connection interrupted');}return {status:'applied',material:{...material(),revision:5}};};
  await x.save();assert.equal(x.dirty,true);await x.save();assert.equal(calls[0].request_id,calls[1].request_id);assert.equal(calls[0].expected_revision,calls[1].expected_revision);
});
test('editing content clears declarations so changed work must be reviewed again',()=>{
  const x=instance();x.draft.checked_scope=['page:1'];x.draft.association_reviewed=true;x.changed(true);assert.deepEqual(x.draft.checked_scope,[]);assert.equal(x.bodyChanged,true);assert.equal(x.draft.association_reviewed,false);assert.equal(x.dirty,true);
});
test('saved checklist survives readback only when association review is resolved',()=>{
  const x=instance();assert.equal(x.fromMaterial({...material(),association_review_required:false}).association_reviewed,false);assert.equal(x.fromMaterial({...material(),association_review_required:false,checked_scope:['page:1']}).association_reviewed,true);assert.equal(x.fromMaterial({...material(),association_review_required:true,checked_scope:['page:1']}).association_reviewed,false);
});
test('stale candidate permits explicit keep or merge but disables direct adoption',async()=>{
  const x=instance();x.material.candidates=[{id:'candidate-1',status:'ready',stale:true,complete:true,input_revision:1,blocks:[]}];x.api=async()=>x.material.candidates[0];x.dialog=html=>x.dialogHTML=html;await x.candidateDialog('candidate-1');assert.match(x.dialogHTML,/<button id="mw-adopt" disabled>/);assert.match(x.dialogHTML,/<button id="mw-keep">/);assert.match(x.dialogHTML,/<button id="mw-edit-merge">/);assert.match(x.dialogHTML,/older input/);
});
test('large material exposes explicit block pages instead of hidden content loss',()=>{
  const x=instance();x.draft.blocks=Array.from({length:95},(_,i)=>({id:String(i),type:'text',text:String(i)}));x.blockPage=1;assert.match(x.blockNavigation(),/Blocks 41–80 of 95/);assert.match(x.blockNavigation(),/Previous blocks/);assert.match(x.blockNavigation(),/Next blocks/);
});
test('overview counts material snapshots and current human reviews independently from blocks',()=>{
  const sourceCard={key:'system1',retained:'source authority'};
  const rows=[{content_status:'draft',blocks:Array(800).fill({})},{content_status:'content_review_complete'},{content_status:'content_review_complete',source_stale:true},{content_status:'content_review_complete',candidates:[{status:'ready'}]},{content_status:'content_review_complete',source_issues:[{reason:'Missing source page'}]}];
  const systems=materialSystems({systems:[sourceCard,{key:'system2',pending:{value:9999}}],material_workbench:{status:'ready',data:{materials:rows,sources:Array(8).fill({})}}});
  assert.deepEqual(systems[0],{...sourceCard,label:'Source governance',title:'Source Management System'});assert.deepEqual(sourceCard,{key:'system1',retained:'source authority'});assert.equal(systems[1].pending.value,3);assert.deepEqual(systems[1].metrics.map(m=>m.value),[5,1,8,1]);assert.deepEqual(systems.map(s=>s.key),['system1','system2']);assert.match(systems[1].note,/Requirement structuring remains unconnected/);assert.equal(systems[1].action.view,'system2');
});
test('overview fetch failure stays unavailable and displays the escaped underlying error',()=>{
  const systems=materialSystems({material_workbench:{status:'error',error:'Reader <unavailable> due to source lock'}}),card=systems[0];assert.equal(card.pending.value,null);assert.ok(card.metrics.every(m=>m.value===null));const html=systemCards(systems);assert.match(html,/Read failed/);assert.match(html,/Reader &lt;unavailable&gt; due to source lock/);assert.match(html,/Unavailable/);assert.doesNotMatch(html,/>0</);
});
test('overview loading does not present fabricated zero material counts',()=>{
  const card=materialSystems({})[0];assert.equal(card.pending.value,null);assert.equal(card.pending.display,'Loading…');assert.ok(card.metrics.every(m=>m.value===null));
});
test('overview renders new entry and retains explicit legacy navigation',()=>{
  const allButton={};const container={innerHTML:'',querySelector:s=>s==='#dashboard-all'?allButton:null,querySelectorAll:()=>[]};
  renderDashboard(container,{as_of:0,counts:{sources:0,pending:0,stored:0,included:0,missing:0},selection:[],issues:[],categories:[],priority:[],systems:[],material_workbench:{status:'ready',data:{materials:[],sources:[]}}},()=>{},()=>{});
  assert.match(container.innerHTML,/Sources → Material workbench/);assert.doesNotMatch(container.innerHTML,/data-open-system="system3"|Three-system/);assert.match(container.innerHTML,/third pane inside each material/);assert.match(container.innerHTML,/data-legacy-view="legacyHistory"/);assert.match(container.innerHTML,/Retained weekly inspection records/);assert.doesNotMatch(container.innerHTML,/complete requirement workflow|Open review demo|Requirements extracted/);
});
test('switching material clears source-specific action notices',async()=>{
  storage.clear();const x=instance();x.dirty=false;x.lastMessage={text:'Original problem sent; confirmation unavailable.'};x.api=async()=>({...material(),id:'two',source:{source_id:'other-source',snapshot_id:'snapshot-2'}});x.loadReader=async()=>{};await x.open('two');assert.equal(x.id,'two');assert.equal(x.lastMessage.text,'');
});
test('PDF reader presents a bound page image without requiring a native PDF plugin',()=>{
  const x=instance(),html=x.pdfMarkup({page:2,pages:6,image:'data:image/png;base64,fixture',native_text:'Original <text>',page_warning:'Native text is unverified.'});assert.match(html,/Saved original PDF page 2 of 6/);assert.match(html,/src="data:image\/png;base64,fixture"/);assert.doesNotMatch(html,/<iframe|<details|Original &lt;text&gt;/);const details=x.pdfInfoMarkup({page:2,pages:6,native_text:'Original <text>'});assert.match(details,/separate from the page image/);assert.match(details,/Original &lt;text&gt;/);assert.match(details,/Optional browser PDF viewer/);
});
test('scan-only PDF reader does not claim selectable original text or OCR completion',()=>{
  const x=instance(),html=x.pdfInfoMarkup({page:1,pages:1,image:'data:image/png;base64,scan',native_text:''});assert.match(html,/No native text on this page/);assert.match(html,/manually transcribe/);assert.match(html,/No OCR has run/);assert.doesNotMatch(html,/<pre/);
});
test('PDF previous and next navigation stay within complete original page bounds',async()=>{
  const x=instance(),pages=[];x.reader={kind:'pdf',page:1,pages:3};x.loadReader=async p=>pages.push(p.page);await x.readerAction('reader-pdf-prev');await x.readerAction('reader-pdf-next');x.reader.page=3;await x.readerAction('reader-pdf-next');await x.readerAction('reader-pdf-prev');assert.deepEqual(pages,[1,2,3,2]);
});
test('PDF zoom changes only page image width and preserves fit-width option',()=>{
  const x=instance();x.q('.mw-pdf-page-image').style={};x.pdfZoom='150';x.setPdfZoom({width:612});assert.equal(x.q('.mw-pdf-page-image').style.width,'1224px');x.pdfZoom='page-width';x.setPdfZoom({width:612});assert.equal(x.q('.mw-pdf-page-image').style.width,'100%');
});
test('HTTP 409 thrown by the real API helper opens conflict recovery without discarding draft',async()=>{
  storage.clear();const x=instance(),draft=x.draft,newer={...material(),revision:5};x.renderContent=()=>x.conflictControlsRendered=x.localConflict;
  x.api=async()=>{const error=Error('newer_material_revision_saved_draft_preserved');error.current=newer;error.status=409;error.definitive=true;error.conflict_id='durable-http-conflict';error.details={status:'conflict',material:newer,conflict_id:'durable-http-conflict'};throw error;};
  assert.equal(await x.save(),false);assert.equal(x.draft,draft);assert.equal(x.localBase,4);assert.equal(x.localConflict,true);assert.equal(x.conflictControlsRendered,true);assert.equal(x.conflictResult.conflict_id,'durable-http-conflict');assert.match(x.lastMessage.text,/Compare saved and local/);assert.doesNotMatch(x.lastMessage.text,/newer_material_revision/);assert.equal(storage.size,0);
});
test('legacy Error.current shape is also recoverable as a guarded conflict',async()=>{
  const x=instance();x.api=async()=>{const error=Error('newer_material_revision_saved_draft_preserved');error.current={...material(),revision:6};error.definitive=true;throw error;};await x.save();assert.equal(x.localConflict,true);assert.equal(x.draft.blocks[0].text,'Human correction');assert.equal(x.localBase,4);
});
test('conflict merge preserves newer unique blocks, local edits and unresolved issues',()=>{
  const x=instance();x.draft.issues=[{id:'issue',message:'Previously checked',resolved:true}];const newer={...material(),revision:5,blocks:[{id:'new-heading',type:'heading',text:'New heading',level:1},{id:'text-1',type:'text',text:'Other reviewer edit'},{id:'new-tail',type:'text',text:'New unseen paragraph'}],issues:[{id:'issue',message:'Reopened issue',resolved:false},{id:'new-issue',message:'New source issue',resolved:false}]};
  const merged=x.conflictDraft(newer);assert.deepEqual(merged.blocks.map(b=>b.id),['new-heading','text-1','new-tail']);assert.equal(merged.blocks[1].text,'Human correction');assert.equal(merged.issues.find(i=>i.id==='issue').resolved,false);assert.match(merged.issues.find(i=>i.id==='issue').message,/Reopened issue/);assert.match(merged.issues.find(i=>i.id==='issue').message,/Previously checked/);assert.equal(merged.issues.length,2);assert.deepEqual(merged.checked_scope,[]);assert.equal(merged.association_reviewed,false);assert.equal(x.draft.blocks.length,1);
  assert.equal(x.conflictDraft(newer,{'text-1':'saved'}).blocks[1].text,'Other reviewer edit');
});

test('ready extraction candidate has a processing label without pretending content is adopted',()=>{
  const status=materialStatus({content_status:'not_extracted',candidates:[{status:'ready',blocks:Array(120).fill({})}]});assert.equal(status.content,'No adopted content');assert.match(status.processing,/Candidate ready · 120 blocks · adoption pending/);assert.equal(status.group,'In progress');assert.equal(status.currentReviewed,false);
});
test('processing status distinguishes running, partial and failure without changing content review',()=>{
  const base={content_status:'draft'};assert.match(materialStatus({...base,candidates:[{status:'running'}]}).processing,/Extraction running/);assert.match(materialStatus({...base,candidates:[{status:'partial',blocks:[{}]}]}).processing,/Partial candidate/);assert.match(materialStatus({...base,candidates:[{status:'failed'}]}).processing,/Extraction failed/);assert.equal(materialStatus({...base,candidates:[{status:'failed'}]}).content,'Content draft');
});
test('old confirmations with source or candidate issues are not current reviewed materials',()=>{
  const complete={content_status:'content_review_complete'};assert.equal(materialStatus(complete).group,'Content reviewed');for(const flags of [{source_issues:[{reason:'Missing image'}]},{source_check_error:'Unavailable'},{candidates:[{status:'ready'}]}]){const state=materialStatus({...complete,...flags});assert.equal(state.currentReviewed,false);assert.equal(state.group,'Needs follow-up');assert.equal(state.content,'Previous content confirmation retained');}
  const old=materialStatus({...complete,source_stale:true});assert.equal(old.group,'Historical versions');assert.equal(old.content,'Historical content confirmation');assert.equal(old.currentReviewed,false);
});
test('list and right pane qualify preserved confirmations consistently',()=>{
  const x=instance();x.items=[{...material(),id:'ok',title:'Current reviewed',content_status:'content_review_complete'},{...material(),id:'old',title:'Old snapshot',content_status:'content_review_complete',source_stale:true},{...material(),id:'waiting',title:'Waiting candidate',content_status:'content_review_complete',candidates:[{status:'ready',blocks:[{}]}]}];x.renderList();const html=x.q('#mw-material-list').innerHTML;assert.match(html,/1–3 of 3 materials/);assert.match(html,/Historical content confirmation/);assert.match(html,/Previous content confirmation retained/);
  x.material=x.items[2];x.dirty=false;x.updateBar();assert.match(x.q('#mw-requirement-state').innerHTML,/Previous content confirmation retained/);assert.match(x.q('#mw-requirement-state').innerHTML,/Candidate reconciliation pending/);assert.doesNotMatch(x.q('#mw-requirement-state').innerHTML,/class="mw-state"/);assert.equal(x.q('[data-action="review"]').disabled,true);
});

test('old client upgrade response preserves local draft and gives recovery direction',async()=>{const x=instance(),before=x.draft;x.api=async()=>{const e=Error('material_api_version_required');e.status=426;e.definitive=true;throw e;};assert.equal(await x.save(),false);assert.equal(x.draft,before);assert.equal(x.dirty,true);assert.match(x.lastMessage.text,/Reload this browser page to recover/);});
test('pending source open cannot extract or save the previously active material',async()=>{const x=instance();x.dirty=false;x.q('#mw-source').value='other';x.loadReader=async()=>{};const calls=[];let finishOpen;x.api=async(path,body)=>{calls.push({path,body});if(path==='/api/material/open')return new Promise(resolve=>finishOpen=resolve);return {...material(),id:'two'};};const request=x.action('open-source',{dataset:{},closest:()=>null});assert.equal(x.opening,true);assert.equal(x.q('[data-action="extract"]').disabled,true);assert.equal(x.q('#mw-source').disabled,true);assert.equal(x.q('[data-action="open-source"]').disabled,true);assert.equal(x.canLeave(),false);assert.equal(await x.mutate('/api/material/extract',{},'should not run'),false);finishOpen({...material(),id:'two'});await request;assert.equal(x.id,'two');assert.equal(x.opening,false);assert.equal(calls.some(c=>c.path==='/api/material/extract'),false);});
test('pending saved material read locks old actions and errors restore previous context',async()=>{const x=instance();x.dirty=false;let reject;x.api=()=>new Promise((_,fail)=>reject=fail);const request=x.open('two');assert.equal(x.opening,true);assert.equal(x.q('#mw-content').inert,true);assert.equal(x.q('[data-action="save"]').disabled,true);assert.equal(await x.mutate('/api/material/extract',{},''),false);reject(Error('Unavailable fixture read'));await request;assert.equal(x.id,'one');assert.equal(x.opening,false);assert.equal(x.q('#mw-content').inert,false);assert.match(x.lastMessage.text,/Unavailable fixture read/);});
test('switching materials clears prior original before draft recovery completes',async()=>{const x=instance();x.dirty=false;x.q('#mw-original-toolbar').innerHTML='Old sheet controls';x.q('#mw-reader').innerHTML='Old source table';x.reader={kind:'xlsx',sheet:'Previous'};let recover;x.recoverDraft=()=>new Promise(resolve=>recover=resolve);x.api=async()=>({...material(),id:'two'});x.loadReader=async()=>{};const request=x.open('two');await Promise.resolve();await Promise.resolve();await Promise.resolve();assert.equal(x.id,'two');assert.equal(x.reader,null);assert.equal(x.q('#mw-original-toolbar').innerHTML,'');assert.doesNotMatch(x.q('#mw-reader').innerHTML,/Old source/);assert.match(x.q('#mw-reader').innerHTML,/Opening saved original/);recover(null);await request;});
test('reloading original removes stale controls and ignores old in-flight response',async()=>{const x=instance();x.q('#mw-original-toolbar').innerHTML='Old page controls';x.q('#mw-reader').innerHTML='Old original';const responses=[];x.api=()=>new Promise(resolve=>responses.push(resolve));const rendered=[];x.renderReader=r=>rendered.push(r.page);const first=x.loadReader({page:1});const second=x.loadReader({page:2});assert.equal(x.reader,null);assert.equal(x.q('#mw-original-toolbar').innerHTML,'');assert.doesNotMatch(x.q('#mw-reader').innerHTML,/Old original/);responses[0]({kind:'pdf',page:1});await first;assert.deepEqual(rendered,[]);responses[1]({kind:'pdf',page:2});await second;assert.deepEqual(rendered,[2]);});

async function candidateClock(run){
  const oldSet=globalThis.setTimeout,oldClear=globalThis.clearTimeout,timers=new Map();let serial=0;
  globalThis.setTimeout=(callback,delay)=>{timers.set(++serial,{callback,delay});return serial;};globalThis.clearTimeout=id=>timers.delete(id);
  const clock={get count(){return timers.size;},get delay(){return timers.values().next().value?.delay;},async next(){const [id,timer]=timers.entries().next().value;timers.delete(id);await timer.callback();}};
  try{await run(clock);}finally{globalThis.setTimeout=oldSet;globalThis.clearTimeout=oldClear;}
}
test('reopening a running extraction resumes status checks without another Extract',async()=>candidateClock(async clock=>{
  storage.clear();const x=instance();x.dirty=false;const calls=[];x.api=async path=>{calls.push(path);return {...material(),candidates:[{id:'candidate',status:'running'}]};};x.loadReader=async()=>{};
  await x.open('one');assert.equal(clock.count,1);await clock.next();assert.equal(clock.count,1);assert.ok(calls.every(p=>p.startsWith('/api/material?id=')));assert.equal(x.dirty,false);
}));
test('candidate status progresses while preserving dirty draft body checks and revision guard',async()=>candidateClock(async clock=>{
  const x=instance(),draft=x.draft;x.draft.blocks[0].text='Unsaved local correction';x.draft.checked_scope=['page:1'];x.material.candidates=[{id:'candidate',status:'running'}];let status='running';
  x.api=async()=>({...material(),revision:6,candidates:[{id:'candidate',status}]});x.watchCandidate();await clock.next();assert.equal(clock.count,1);status='ready';await clock.next();
  assert.equal(clock.count,0);assert.equal(x.material.candidates[0].status,'ready');assert.equal(x.draft,draft);assert.equal(x.draft.blocks[0].text,'Unsaved local correction');assert.deepEqual(x.draft.checked_scope,['page:1']);assert.equal(x.localBase,4);assert.equal(x.dirty,true);
}));
test('busy candidate polling waits and resumes without reading over an in-flight save',async()=>candidateClock(async clock=>{
  const x=instance();let reads=0;x.api=async()=>{reads++;return {...material(),candidates:[]};};x.busy=true;x.watchCandidate();await clock.next();assert.equal(reads,0);assert.equal(clock.count,1);x.busy=false;await clock.next();assert.equal(reads,1);assert.equal(clock.count,0);
}));
test('candidate status read failures retry with a finite failure limit and can be restarted',async()=>candidateClock(async clock=>{
  const x=instance();let reads=0;x.api=async()=>{reads++;throw Error('Service restarting');};x.watchCandidate();await clock.next();assert.equal(clock.delay,3600);await clock.next();assert.equal(clock.delay,7200);await clock.next();assert.equal(reads,3);assert.equal(clock.count,0);assert.match(x.lastMessage.text,/three attempts.*Refresh candidate status/);assert.equal(x.dirty,true);
  x.api=async()=>({...material(),candidates:[{id:'candidate',status:'ready'}]});await x.action('refresh-candidate',{dataset:{},closest:()=>null});assert.equal(clock.count,1);await clock.next();assert.equal(x.material.candidates[0].status,'ready');
}));
test('late candidate status cannot update another actor material original or master view',async()=>candidateClock(async clock=>{
  for(const change of [x=>x.state.actor.id='someone-else',x=>x.id='other',x=>x.material.source={...x.material.source,snapshot_id:'new'},x=>x.material.collaboration={view:'master'}]){
    const x=instance();let finish;x.api=()=>new Promise(resolve=>finish=resolve);x.watchCandidate();const pending=clock.next();change(x);finish({...material(),revision:8,candidates:[{status:'ready'}]});await pending;assert.deepEqual(x.material.candidates,[]);assert.equal(x.localBase,4);assert.equal(clock.count,0);
  }
}));
test('clean status polling cannot silently substitute another tabs saved body',async()=>candidateClock(async clock=>{
  const x=instance();x.dirty=false;const draft=x.draft;x.api=async()=>({...material(),revision:6,content_revision:3,blocks:[{id:'other',type:'text',text:'New server content'}],candidates:[{status:'ready'}]});x.watchCandidate();await clock.next();assert.equal(x.draft,draft);assert.equal(x.draft.blocks[0].text,'Human correction');assert.equal(x.localBase,4);assert.equal(x.material.revision,4);
}));

test('conflict comparison represents both one-sided blocks and allows explicit absence',()=>{
  const x=instance();x.draft.blocks=[{id:'local-only',type:'text',text:'Old local block'},{id:'shared',type:'text',text:'Shared'}];
  const newer={...material(),revision:8,blocks:[{id:'shared',type:'text',text:'Shared'},{id:'saved-only',type:'text',text:'New server block'}]};
  const summary=x.conflictDifferences(newer);assert.deepEqual(summary.differences.map(d=>d.id),['local-only','saved-only']);assert.equal(summary.orderChanged,false);
  const merged=x.conflictDraft(newer,{'local-only':'saved','saved-only':'local'});assert.deepEqual(merged.blocks.map(b=>b.id),['shared']);assert.deepEqual(x.draft.blocks.map(b=>b.id),['local-only','shared']);
  assert.deepEqual(x.conflictDraft(newer,{'local-only':'local','saved-only':'saved'}).blocks.map(b=>b.id),['local-only','shared','saved-only']);
});
test('order-only conflicts have an explicit order choice while retaining selected one-sided blocks',()=>{
  const x=instance();const a={id:'a',type:'heading',level:1,text:'A'},b={id:'b',type:'heading',level:1,text:'B'},extra={id:'extra',type:'text',text:'Keep this addition'};
  x.draft.blocks=[a,b];const newer={...material(),blocks:[b,extra,a]};assert.equal(x.conflictDifferences(newer).orderChanged,true);
  assert.deepEqual(x.conflictDraft(newer,{extra:'saved'},'saved').blocks.map(b=>b.id),['b','extra','a']);assert.deepEqual(x.conflictDraft(newer,{extra:'local'},'local').blocks.map(b=>b.id),['a','b']);assert.deepEqual(x.draft.blocks,[a,b]);
});
test('version choice saves a whole version against the compared revision and never mixes block order',async()=>{
 const x=instance();x.api=async()=>({...material(),revision:9,blocks:[]});let sent;
 x.mutate=async(path,body)=>{sent={path,body,revision:x.localBase};return true;};
 const choices=['saved','local'].map(v=>({dataset:{versionChoice:v}})),status={},d={querySelector:()=>status,querySelectorAll:()=>choices,close:()=>d.closed=true};
 x.dialog=(html,wire)=>{x.dialogHTML=html;wire(d);};await x.conflictDialog();await choices[1].onclick();
 assert.equal(sent.revision,9);assert.equal(sent.body.version_choice,'local');assert.deepEqual(sent.body.blocks,x.draft.blocks);assert.equal(d.closed,true);assert.match(x.dialogHTML,/Only changed passages/);
});
test('conflict comparison ignores a late response after switching reviewer',async()=>{
  const x=instance();let finish,opened=false;x.api=()=>new Promise(resolve=>finish=resolve);x.dialog=()=>opened=true;const pending=x.conflictDialog();x.state.actor.id='other';finish({...material(),revision:9});await pending;assert.equal(opened,false);assert.equal(x.localBase,4);
});

test('opening a material replaces only its matching unopened snapshot in the visible queue',()=>{
  const x=instance(),source={source_id:'PA001',snapshot_id:'v2',content_hash:'new'},opened={...material(),source},unopened={id:null,title:'PA001',source,queue:{unopened:true}},old={id:null,title:'PA001 old',source:{...source,snapshot_id:'v1',content_hash:'old'},queue:{unopened:true}},other={id:null,title:'Other source',source:{...source,source_id:'CS010'},queue:{unopened:true}};
  x.items=[unopened,old,other];x.rememberOpenedMaterial(opened);assert.deepEqual(x.items,[opened,old,other]);x.rememberOpenedMaterial(opened);assert.deepEqual(x.items,[opened,old,other]);
});
test('late status response cannot roll back revision after a concurrent same-body save',async()=>candidateClock(async clock=>{
  const x=instance();x.dirty=false;x.material.candidates=[{status:'running'}];let finish;x.api=()=>new Promise(resolve=>finish=resolve);x.watchCandidate();const pending=clock.next();x.material={...material(),revision:7,candidates:[{status:'running'}]};x.localBase=7;finish({...material(),revision:5,candidates:[{status:'running'}]});await pending;assert.equal(x.material.revision,7);assert.equal(x.localBase,7);assert.equal(clock.count,1);
}));

test('empty extraction with image blocks is distinct from ready and partial text candidates',()=>{
  const candidate={id:'scan',status:'partial',block_count:2,complete:false,extraction:{parser_status:'empty',processed_scope_count:2,usable_scope_count:0,unprocessed_scope_count:0,unresolved_count:2}};
  const x=instance();x.material.candidates=[candidate];assert.match(materialStatus(x.material).processing,/No usable extracted content/);const html=x.candidatesMarkup();assert.match(html,/No usable text or table content was extracted/);assert.match(html,/text\/table content in 0/);assert.match(html,/Processing details/);assert.match(html,/Compare \/ resolve/);assert.doesNotMatch(html,/Full candidate scope/);
  assert.equal(materialStatus({...material(),candidates:[{...candidate,extraction:{...candidate.extraction,parser_status:'partial',usable_scope_count:1}}]}).processing.startsWith('Partial candidate'),true);
});
test('older candidates and adopted content do not invent extraction scope or claim unstarted content',()=>{
  assert.match(extractionScopeText({status:'partial',metadata:{covered_scope:['page:1']}}),/not recorded/);
  assert.equal(materialStatus({...material(),candidates:[]}).processing,'Saved content · no current extraction');
  assert.equal(materialStatus({content_status:'draft',block_count:7,candidates:[]}).processing,'Saved content · no current extraction');
});
test('processing detail exposes retained unresolved locations without altering human draft',async()=>{
  const x=instance(),draft=x.draft;const candidate={id:'scan',status:'partial',blocks:[],metadata:{parser_status:'empty',processed_scope:['page:1'],usable_scope:[],unprocessed_scope:['page:2'],unresolved:[{scope_id:'page:1',message:'No native text <check>'}]},warnings:['No OCR was run']};
  x.api=async()=>candidate;x.dialog=html=>x.dialogHTML=html;await x.processingDetails('scan');assert.match(x.dialogHTML,/No native text &lt;check&gt;/);assert.match(x.dialogHTML,/page:2/);assert.match(x.dialogHTML,/data-processing-scope="page:1"/);assert.match(x.dialogHTML,/Requirement identification has not run/);assert.equal(x.draft,draft);assert.equal(x.localBase,4);
});

test('material open and save preserve inspection and submission routes from the queue',async()=>{
  storage.clear();const x=instance(),queue={bucket:'pending',inspection_only:false,incoming_submission:true,open_inspections:[{id:'check',assignee:'Weijie Tang',status:'pending'}]};
  x.items=[{...material(),queue}];x.dirty=false;x.loadReader=async()=>{};x.api=async()=>({...material(),revision:5});await x.open('one');assert.deepEqual(x.items[0].queue,queue);
  x.dirty=true;x.api=async()=>({material:{...material(),revision:6}});await x.save();assert.deepEqual(x.items[0].queue,queue);
  x.renderList();assert.match(x.q('#mw-material-list').innerHTML,/Submitted changes await review/);assert.match(x.q('#mw-material-list').innerHTML,/data-action="inspection-open" data-task="check"/);
  let opened;x.inspections.open=async id=>opened=id;await x.action('inspection-open',{dataset:{task:'check'}});assert.equal(opened,'check');
});
test('queue metadata cannot follow a detail response bound to a different source version',()=>{
  const x=instance();x.items=[{...material(),queue:{open_inspections:[{id:'old-check'}]}}];x.rememberMaterialDetail({...material(),source:{...material().source,snapshot_id:'new-original'}});assert.equal(x.items[0].queue,undefined);
});
test('empty reviewer queue explains work-package entry without inventing a coordinator cause',()=>{
  const x=instance();x.items=[];x.sources=[];x.collaboration.state={mode:'reviewer'};x.renderList();assert.match(x.q('#mw-material-list').innerHTML,/No work package has been imported/);assert.match(x.q('#mw-material-list').innerHTML,/Exchange work packages → Import package/);
  x.collaboration.state={mode:'coordinator'};x.renderList();assert.match(x.q('#mw-material-list').innerHTML,/No materials in this category/);assert.doesNotMatch(x.q('#mw-material-list').innerHTML,/No work package/);
});


test('original location labels use exact reader evidence and keep PDF and sheet locations',()=>{
  const reader={anchors:[{id:'original-known',locator:'/body/p[1]',label:'Section 2 · Scope <special>'}]};
  const ref={anchor:'original-known',locator:'/body/p[1]'},before=structuredClone(ref);
  assert.equal(locationLabel(ref,reader),'Section 2 · Scope <special>');
  assert.deepEqual(ref,before);
  assert.equal(locationLabel({locator:'/body/p[1]'},reader),'Section 2 · Scope <special>');
  assert.equal(locationLabel({anchor:'original-missing',locator:'/body/p[1]'},reader),'Linked HTML location');
  assert.equal(locationLabel(ref),'Linked HTML location');
  assert.equal(locationLabel({page:2},reader),'Page 2');
  assert.equal(locationLabel({page_index:0},reader),'Page 1');
  assert.equal(locationLabel({sheet:'Limits',cell_range:'B2:C4'},reader),'Limits · B2:C4');
});

test('readable original labels remain separate from exact source references in editing details',()=>{
  const x=instance(),b={id:'text-1',type:'text',text:'Human correction',source_refs:[{anchor:'original-known',locator:'/body/p[1]'}]};
  x.draft.blocks=[b];x.reader={anchors:[{id:'original-known',label:'Section <2>'}]};
  const read=x.blockMarkup(b,0);
  assert.doesNotMatch(read,/original-known|<textarea/);
  x.notebook.active=b.id;assert.match(x.blockMarkup(b,0),/Original/);
  assert.doesNotMatch(read,/>original-known</);
  const edit=x.editBlockMarkup(b,0);
  assert.match(edit,/<summary>Exact source references<\/summary><pre>.*original-known/s);
  assert.equal(b.source_refs[0].anchor,'original-known');
});

test('late reader labels update visible reading text without rerendering or touching the draft',()=>{
  const x=instance(),refs=[{anchor:'original-known'}],node={dataset:{locationRefs:JSON.stringify(refs)},textContent:'Linked HTML location'};
  x.root.querySelectorAll=selector=>selector==='[data-location-refs]'?[node]:[];
  const draft=x.draft,contents=JSON.stringify(draft);let renders=0;x.renderContent=()=>renders++;
  x.renderReader({kind:'html',anchors:[{id:'original-known',label:'Section 2 · Scope'}]});
  assert.equal(node.textContent,'Section 2 · Scope');
  assert.equal(x.draft,draft);assert.equal(JSON.stringify(draft),contents);assert.equal(renders,0);assert.equal(x.dirty,true);
});

test('personal confirmation and newer master draft are separately labelled without changing either version',()=>{
 const x=instance(),personal={...material(),content_status:'content_review_complete',collaboration_view:'personal',queue:{master_revision:3,master_content_status:'draft',master_review_current:false,archive_revision:2,needs_revision:true}};
 x.items=[personal];x.renderList();let html=x.q('#mw-material-list').innerHTML;
 assert.match(html,/Personal content · Content review complete/);assert.match(html,/Master revision 3 · Content draft/);assert.equal(x.items[0],personal);
 personal.queue.master_content_status='content_review_complete';x.renderList();html=x.q('#mw-material-list').innerHTML;
 assert.match(html,/Master revision 3 · Previous content confirmation retained/);
 x.history=true;x.renderList();html=x.q('#mw-material-list').innerHTML;assert.match(html,/Finalized revision 2/);assert.doesNotMatch(html,/Master revision 3/);
});

test('saved partial extraction retains its machine evidence entry without another apply action',()=>{
 const x=instance(),candidate={id:'saved-partial',status:'merged',complete:false,extraction:{parser_status:'partial',processed_scope_count:3,usable_scope_count:1,unprocessed_scope_count:0,unresolved_count:2}};
 x.material.candidates=[candidate];const before=JSON.stringify(x.material),html=x.candidatesMarkup();
 assert.match(html,/Retained extraction limitations/);assert.match(html,/human corrections are assessed separately/);assert.match(html,/unresolved 2/);
 assert.match(html,/data-action="processing-details" data-id="saved-partial"/);assert.doesNotMatch(html,/compare-candidate|Compare \/ resolve|refresh-candidate/);assert.equal(JSON.stringify(x.material),before);
});
test('resolved empty evidence stays available but successful or superseded extraction does not invent current limitations',()=>{
 const x=instance(),old={id:'old',status:'kept',extraction:{parser_status:'empty',unresolved_count:1}};x.material.candidates=[old];assert.match(x.candidatesMarkup(),/Retained extraction limitations/);
 x.material.candidates.push({id:'clean',status:'merged',complete:true,extraction:{parser_status:'candidate_available',unresolved_count:0,unprocessed_scope_count:0}});assert.equal(x.candidatesMarkup(),'');
 x.material.candidates=[];assert.equal(x.candidatesMarkup(),'');
});

test('unavailable original offers a reader-only retry at the same page without replacing a draft',async()=>{
 const x=instance(),draft=x.draft,calls=[];let fail=true,rendered;
 x.api=async(path,body)=>{calls.push({path,body});if(fail)throw Error("[Errno 2] No such file or directory: '/isolated/original.pdf'");return {kind:'pdf',page:3};};
 x.renderReader=r=>{rendered=r;};await x.loadReader({page:3});
 assert.match(x.q('#mw-reader').innerHTML,/The saved original is unavailable/);
 assert.match(x.q('#mw-reader').innerHTML,/reader-retry/);
 assert.match(x.q('#mw-reader').innerHTML,/<details><summary>Reading failure details/);
 assert.equal(x.draft,draft);assert.equal(x.dirty,true);assert.equal(x.reader,null);
 fail=false;await x.readerAction('reader-retry');
 assert.equal(rendered.page,3);assert.equal(x.draft,draft);assert.equal(x.dirty,true);
 assert.equal(calls.length,2);assert.equal(calls[0].path,calls[1].path);
 assert.ok(calls.every(c=>c.path.startsWith('/api/material/reader?')&&c.body===undefined));
});
test('failed extraction gives recovery advice and preserves raw error for processing details',async()=>{
 const x=instance(),error="[Errno 2] No such file or directory: '/isolated/original.pdf'";
 x.material.candidates=[{id:'failure',status:'failed',error}];
 const html=x.candidatesMarkup();assert.match(html,/extraction attempt could not access the saved original/);assert.doesNotMatch(html,/\[Errno 2\]/);assert.doesNotMatch(html,/Compare \/ resolve/);
 assert.match(html,/Processing details/);assert.equal(x.material.candidates[0].error,error);
 x.api=async()=>({error,metadata:{},warnings:[]});let dialog;
 x.dialog=s=>{dialog=s;};await x.processingDetails('failure');
 assert.match(dialog,/<details><summary>Recorded failure details/);assert.match(dialog,/\[Errno 2\]/);
});

test('empty panes contain only the content extraction entry, with no review declaration or Requirements result',()=>{
 const x=instance();x.draft.blocks=[];assert.match(x.emptyContentMarkup(),/>Auto-extract</);assert.equal(x.reviewDeclarationMarkup(),'');x.renderRequirements();assert.equal(x.q('#mw-requirement-content').innerHTML,'');assert.equal(x.reviewReady(),false);
 x.material.candidates=[{id:'c',status:'running'}];assert.match(x.emptyContentMarkup(),/aria-busy="true"/);assert.match(x.emptyContentMarkup(),/mw-extract-spinner/);assert.doesNotMatch(x.emptyContentMarkup(),/>Auto-extract</);
});
test('Archive requires all declarations but Save allows an unchecked dirty personal draft',()=>{
 const x=instance();x.updateBar();assert.equal(x.q('[data-action="save"]').disabled,false);assert.equal(x.q('[data-action="review"]').disabled,true);
 x.draft.checked_scope=['page:1'];x.updateBar();assert.equal(x.q('[data-action="review"]').disabled,true);
 x.draft.association_reviewed=true;x.updateBar();assert.equal(x.q('[data-action="review"]').disabled,false);
 x.draft.issues=[{id:'a',message:'Missing paragraph',resolved:false}];x.updateBar();assert.equal(x.q('[data-action="review"]').disabled,true);
});
test('ready first extraction can be declared and saved before archive, but other candidates still block',()=>{
 const x=instance();x.initialCandidate='c';x.material.candidates=[{id:'c',status:'ready'}];x.draft.checked_scope=['page:1'];x.draft.association_reviewed=true;x.updateBar();assert.equal(x.q('[data-action="review"]').disabled,false);
 x.material.candidates.push({id:'different',status:'ready'});x.updateBar();assert.equal(x.q('[data-action="review"]').disabled,true);
});
test('checked changed draft is persisted before checks are stamped on the identical returned body',async()=>{
 const x=instance(),calls=[];x.bodyChanged=true;x.draft.checked_scope=['page:1'];x.draft.association_reviewed=true;
 x.api=async(path,body)=>{calls.push({path,body});return {status:'applied',material:{...material(),revision:4+calls.length,checked_scope:calls.length===2?['page:1']:[],association_review_required:calls.length!==2}};};
 assert.equal(await x.save(),true);assert.equal(calls.length,2);assert.equal('checked_scope' in calls[0].body,false);assert.equal(calls[1].body.expected_revision,5);assert.deepEqual(calls[1].body.checked_scope,['page:1']);assert.ok(calls.every(c=>c.path==='/api/material/save'));assert.equal(x.dirty,false);assert.equal(x.reviewReady(),true);
});
test('changed save response cannot receive declarations for a different body',async()=>{
 const x=instance();x.bodyChanged=true;x.draft.checked_scope=['page:1'];x.draft.association_reviewed=true;let writes=0;
 x.api=async()=>{writes++;const m=material();m.blocks[0].text='Different saved body';return {status:'applied',material:m};};await x.save();assert.equal(writes,1);assert.equal(x.reviewReady(),false);
});
test('a failed second save retains explicit declarations as a recoverable personal draft',async()=>{
 const x=instance();x.bodyChanged=true;x.draft.checked_scope=['page:1'];x.draft.association_reviewed=true;let writes=0;x.api=async()=>{if(++writes===2)throw Error('Disconnected');return {status:'applied',material:{...material(),revision:5}};};
 assert.equal(await x.save(),false);assert.equal(x.dirty,true);assert.equal(x.localBase,5);assert.deepEqual(x.draft.checked_scope,['page:1']);assert.equal(x.draft.association_reviewed,true);
});
test('manual passage entry keeps source wording and does not invoke extraction',()=>{
 const x=instance();x.material.scope=[];const block={id:'p',type:'text',text:'The human shall act.',source_refs:[]};x.draft.blocks=[block];
 x.notebook.active='p';assert.match(x.blockMarkup(block,0),/To requirements/);assert.match(x.blockMarkup(block,0),/data-md-action="requirement"/);
 assert.equal(x.draft.blocks[0].text,'The human shall act.');
});
function cloneForTest(value){return structuredClone(value);}
test('notebook retains hierarchy data while rendering text, tables and image captions without forms',()=>{
 const x=instance();const h={id:'h',type:'heading',level:1,text:'Chapter',source_refs:[]},child={id:'p',type:'text',text:'Paragraph',parent_id:'h',source_refs:[]};x.draft.blocks=[h,child];assert.match(x.blockMarkup(child,1),/data-md-cell="p"/);assert.doesNotMatch(x.blockMarkup(child,1),/data-field="text"/);assert.equal(child.parent_id,'h');
 const table={id:'t',type:'table',table:{rows:[['A','B']],merges:[],notes:[]},source_refs:[]};x.draft.blocks.push(table);assert.match(x.blockMarkup(table,2),/<table>/);assert.doesNotMatch(x.blockMarkup(table,2),/<textarea/);
 const image={id:'i',type:'image',text:'Caption',source_refs:[]};x.draft.blocks.push(image);assert.match(x.blockMarkup(image,3),/Image: Caption/);assert.doesNotMatch(x.blockMarkup(image,3),/mw-input-image/);
});
test('editing an issue invalidates declarations even when its resolved flag stays true',()=>{
 const x=instance();x.draft.issues=[{id:'issue',message:'Old note',resolved:true}];x.draft.checked_scope=['page:1'];x.draft.association_reviewed=true;
 x.editInput({target:{dataset:{issueText:'0'},value:'Changed note',closest:()=>null}});assert.equal(x.draft.issues[0].message,'Changed note');assert.equal(x.reviewReady(),false);assert.deepEqual(x.draft.checked_scope,[]);
});
test('a changed original identity cannot inherit declarations through a save response',async()=>{
 const x=instance();x.bodyChanged=true;x.draft.checked_scope=['page:1'];x.draft.association_reviewed=true;let writes=0;x.api=async()=>{writes++;return {status:'applied',material:{...material(),source:{source_id:'fixture',snapshot_id:'snapshot-2'}}};};await x.save();assert.equal(writes,1);assert.equal(x.reviewReady(),false);
});
test('Archive refuses undeclared content before invoking save or preview',async()=>{
 const x=instance();let writes=0;x.save=async()=>{writes++;return true;};await x.archiveContent();assert.equal(writes,0);assert.match(x.lastMessage.text,/declaration/);
});

test('untouched preview can re-extract while preserving the old candidate server-side',async()=>{
  const x=instance();x.material.blocks=[];x.material.content_revision=0;x.initialCandidate='old';
  const candidate={id:'old',status:'ready',input_revision:0,source:x.material.source,blocks:structuredClone(x.draft.blocks)};
  x.api=async()=>candidate;let mutation;x.mutate=async(path,extra)=>{mutation={path,extra};return true;};let watched=false;x.watchCandidate=()=>watched=true;
  await x.extractContent();assert.deepEqual(mutation,{path:'/api/material/extract',extra:{replace_candidate_id:'old'}});assert.equal(watched,true);assert.equal(x.initialCandidate,null);
});
test('preview refresh protects edits, review checks, changed material, and imported human content',async()=>{
  for(const change of [x=>x.draft.blocks[0].text='Human edit',x=>x.draft.checked_scope=['page:1'],x=>x.draft.association_reviewed=true,x=>x.draft.issues.push({id:'new',message:'Finding'}),x=>x.material.blocks=[{text:'Saved work'}],(x,c)=>c.origin='legacy_effective_content']){
    const x=instance();x.material.blocks=[];x.material.content_revision=0;x.initialCandidate='old';
    const candidate={id:'old',status:'ready',input_revision:0,source:x.material.source,blocks:structuredClone(x.draft.blocks)};change(x,candidate);x.api=async()=>candidate;x.mutate=()=>assert.fail('Human work must not be replaced');
    await x.extractContent();assert.match(x.lastMessage.text,/Save them/);assert.equal(x.initialCandidate,'old');assert.equal(x.dirty,true);
  }
});
test('preview refresh abandons an old response after switching materials',async()=>{
  const x=instance();x.material.blocks=[];x.initialCandidate='old';let finish;x.api=()=>new Promise(r=>finish=r);x.mutate=()=>assert.fail('Changed context');
  const pending=x.extractContent();x.id='other';finish({});await pending;assert.equal(x.initialCandidate,'old');
});
test('empty material previews newest ready candidate instead of first old result',async()=>{
  const x=instance();x.dirty=false;x.draft.blocks=[];x.material.blocks=[];x.material.candidates=[{id:'old',status:'ready'},{id:'new',status:'ready'}];let url;
  x.api=async path=>{url=path;return {input_revision:x.material.content_revision,source:x.material.source,blocks:[{id:'body',type:'text',text:'Body'}]};};
  await x.previewEmptyCandidate();assert.match(url,/candidate_id=new/);assert.equal(x.initialCandidate,'new');assert.equal(x.draft.blocks[0].text,'Body');
});

test('closing to the list retains the open material draft and blocks unresolved requirement writes',()=>{
 const x=instance(),draft=x.draft;x.listVisible=false;
 x.requirements.pending=true;x.showList();assert.equal(x.listVisible,false);
 x.requirements.pending=false;x.requirements.retryRequest={};x.showList();assert.equal(x.listVisible,false);
 x.requirements.retryRequest=null;let warned=0;x.unsavedDialog=()=>warned++;x.showList();assert.equal(warned,1);assert.equal(x.listVisible,false);x.dirty=false;x.showList();assert.equal(x.listVisible,true);assert.equal(x.draft,draft);assert.equal(x.dirty,false);assert.equal(x.id,'one');
 x.showDetail();assert.equal(x.listVisible,false);assert.equal(x.draft,draft);
});

test('unsaved material changes never write browser storage and are not recovered after reload',async()=>{storage.clear();const x=instance();x.draftTouched=true;x.draft.blocks[0].text='Not saved';x.persistDraft();assert.equal(storage.size,0);assert.equal(await x.recoverDraft('one'),null);assert.equal(x.draft.blocks[0].text,'Not saved');});


test('return to material list warns for unsaved content before hiding the editor',()=>{
 const m=new Materials();let warned=0;m.material={};m.listVisible=false;m.dirty=true;m.unsavedDialog=()=>warned++;m.interpretations.canLeave=()=>true;m.inspections.canLeave=()=>true;m.collaboration.canLeave=()=>true;m.showList();assert.equal(warned,1);assert.equal(m.listVisible,false);
});
