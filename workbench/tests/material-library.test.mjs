import test from 'node:test';
import assert from 'node:assert/strict';
import {Materials} from '../frontend/components/materials.js';
const record=(id='m1')=>({id,title:'Synthetic material '+id,source:{source_id:'S'+id},block_count:1,revision:3,content_status:'draft',queue:{task_type:'review'},candidates:[]});
function fixture(){const v=new Materials(),nodes=new Map();v.state={actor:{id:'fixture-reviewer'},collaboration:{peer_sync:true}};v.sources=[];v.items=[record()];v.token={};v.q=s=>{if(!nodes.has(s))nodes.set(s,{value:'',textContent:'',innerHTML:'',scrollTop:0,disabled:false,focusCount:0,focus(){this.focusCount++;}});return nodes.get(s);};v.root={innerHTML:'',querySelectorAll:()=>[]};v.wireResize=()=>{};v.collaboration.load=async()=>{};v.message=()=>{};return v;}
const tick=()=>new Promise(resolve=>setTimeout(resolve,300));
const stateStorage=new Map();globalThis.sessionStorage={getItem:k=>stateStorage.get(k)||null,setItem:(k,v)=>stateStorage.set(k,v),removeItem:k=>stateStorage.delete(k)};globalThis.window={addEventListener(){},removeEventListener(){}};

test('library range describes zero, first, second and last pages truthfully',()=>{
 const v=fixture();for(const [total,offset,count,expected] of [[0,0,0,'0 of 0'],[1,0,1,'1–1 of 1'],[50,0,50,'1–50 of 50'],[51,50,1,'51–51 of 51'],[124,50,50,'51–100 of 124'],[124,100,24,'101–124 of 124']]){v.items=Array.from({length:count},(_,i)=>record(String(i)));v.listPage={total,offset};v.renderList();assert.ok(v.q('#mw-material-list').innerHTML.includes(expected),expected);assert.match(v.q('#mw-material-list').innerHTML,/aria-label="Material result pages"/);}
 v.history=true;v.renderList();assert.match(v.q('#mw-material-list').innerHTML,/archived materials/);
});

test('accepted page offset survives module remount and stays isolated by reviewer and Archive',async()=>{
 stateStorage.clear();const v=fixture(),requests=[],api=async path=>{const q=new URL(path,'http://fixture').searchParams;requests.push(q);return {materials:[record()],sources:[],total:124,offset:Number(q.get('offset')||0)};};
 await v.mount(v.root,{api,state:v.state});await v.loadList(50);v.q('.mw-library').scrollTop=91;v.leave();await v.mount(v.root,{api,state:v.state});assert.equal(requests.at(-1).get('offset'),'50');assert.equal(v.q('.mw-library').scrollTop,91);
 await v.mount(v.root,{api,state:{...v.state,actor:{id:'other-reviewer'}}});assert.equal(requests.at(-1).get('offset'),'0');
 await v.mount(v.root,{api,state:{...v.state,actor:{id:'fixture-reviewer'}},history:true});assert.equal(requests.at(-1).get('offset'),'0');assert.equal(requests.at(-1).get('bucket'),'archive');
 await v.mount(v.root,{api,state:{...v.state,actor:{id:'fixture-reviewer'}}});assert.equal(requests.at(-1).get('offset'),'50');
});

test('IME composition never sends intermediate queries and completed text remains intact',async()=>{
 const v=fixture(),calls=[];v.loadList=async offset=>calls.push({offset,query:v.listQuery});v.shell();const search=v.q('#mw-find');search.oncompositionstart();search.value='海';search.oninput({isComposing:true});await tick();assert.equal(calls.length,0);search.value='海水温度';search.oncompositionend();search.oninput({isComposing:false});await tick();assert.deepEqual(calls,[{offset:0,query:'海水温度'}]);
 search.value='water';search.oninput({});await tick();assert.equal(calls.at(-1).query,'water');
});

test('leaving during IME composition does not block ordinary search or paging after remount',async()=>{
 stateStorage.clear();const v=fixture(),calls=[],api=async path=>{const params=new URL(path,'http://fixture').searchParams;calls.push(Object.fromEntries(params));return {materials:[record()],sources:[],total:124,offset:Number(params.get('offset')||0),has_more:true};};
 await v.mount(v.root,{api,state:v.state});const oldSearch=v.q('#mw-find');oldSearch.oncompositionstart();oldSearch.value='海';oldSearch.oninput({isComposing:true});v.leave();assert.equal(v.listComposing,false);
 await v.mount(v.root,{api,state:v.state});const search=v.q('#mw-find');search.value='water';search.oninput({isComposing:false});await tick();assert.equal(calls.at(-1).query,'water');const before=calls.length;await v.action('list-next',{dataset:{}});assert.equal(calls.length,before+1);assert.equal(calls.at(-1).offset,'50');
});

test('typing then immediately paging binds the new query to offset zero and cancels the old debounce',async()=>{
 const v=fixture(),calls=[];v.shell();v.listPage={offset:50,total:124,has_more:true};v.loadedListContext=v.listContext();v.api=async path=>{const q=new URL(path,'http://fixture').searchParams;calls.push(Object.fromEntries(q));return {materials:[],total:0,offset:Number(q.get('offset'))};};const search=v.q('#mw-find');search.value='new query';search.oninput({});await v.action('list-next',{dataset:{}});await tick();assert.equal(calls.length,1);assert.equal(calls[0].offset,'0');assert.equal(calls[0].query,'new query');assert.equal(v.q('#mw-list-range').focusCount,1);
});

test('a changed filter cancels debounce and a late old result cannot replace the current query',async()=>{
 const v=fixture();v.shell();let finishOld;const calls=[];v.api=path=>{const q=new URL(path,'http://fixture').searchParams;calls.push(q);if(q.get('query')==='old')return new Promise(resolve=>finishOld=resolve);return Promise.resolve({materials:[record('current')],total:1,offset:0});};v.listQuery='old';const pending=v.loadList(50);const search=v.q('#mw-find');search.value='current';search.oninput({});v.q('#mw-task-filter').onchange({target:{value:'review'}});await tick();finishOld({materials:[record('old')],total:1,offset:50});await pending;assert.equal(v.items[0].id,'current');assert.equal(calls.length,2);assert.equal(calls[1].get('offset'),'0');assert.equal(calls[1].get('task_type'),'review');
});

test('explicit paging starts at the range while ordinary reload and Back preserve their list position',async()=>{
 const v=fixture();v.api=async()=>({materials:[record()],total:124,offset:50});v.q('.mw-library').scrollTop=850;await v.loadList(50,{pageChange:true});assert.equal(v.q('.mw-library').scrollTop,0);assert.equal(v.q('#mw-list-range').focusCount,1);
 v.q('.mw-library').scrollTop=73;await v.loadList(50);assert.equal(v.q('.mw-library').scrollTop,73);assert.equal(v.q('#mw-list-range').focusCount,1);v.listScroll=73;v.q('.mw-library').scrollTop=0;v.canLeave=()=>true;v.showList();assert.equal(v.q('.mw-library').scrollTop,73);
});

test('saved-source opener requires a valid selection through lock/unlock and same titles retain exact IDs',()=>{
 const v=fixture();v.sources=[{source_id:'S1',source_title:'Same <title> 中文',version:'v1'},{source_id:'S2',source_title:'Same <title> 中文',version:'v2'}];v.shell();assert.match(v.root.innerHTML,/value="S1">S1 · Same &lt;title&gt; 中文 · v1/);assert.match(v.root.innerHTML,/value="S2">S2 · Same &lt;title&gt; 中文 · v2/);const select=v.q('#mw-source'),opener=v.q('#mw-source-opener');assert.equal(opener.disabled,true);select.value='S2';select.onchange();assert.equal(opener.disabled,false);v.busy=true;v.updateNavigationLock();assert.equal(opener.disabled,true);v.busy=false;v.updateNavigationLock();assert.equal(opener.disabled,false);select.value='';v.updateNavigationLock();v.busy=true;v.updateNavigationLock();v.busy=false;v.updateNavigationLock();assert.equal(opener.disabled,true);
});

test('library surfaces actual extraction attention without routine processing noise or invented requirement status',()=>{
 const v=fixture();v.items=['running','partial','ready','failed'].map(status=>({...record(status),candidates:[{status,block_count:4}]}));v.items.push(record('normal'));v.renderList();const html=v.q('#mw-material-list').innerHTML;for(const state of ['Extraction running','Partial candidate','Candidate ready','Extraction failed · saved content retained'])assert.ok(html.includes(state));assert.match(html,/adoption pending/);assert.doesNotMatch(html,/Saved content · no current extraction/);
 v.history=true;v.renderList();assert.match(v.q('#mw-material-list').innerHTML,/Finalized revision 3/);assert.doesNotMatch(v.q('#mw-material-list').innerHTML,/Requirements unfinished/);
});

test('inspection links expose archive revision and creation time while preserving exact task identities',async()=>{
 const v=fixture();v.items=[{...record(),queue:{open_inspections:[{id:'first-task',assignee:'Reviewer',status:'pending',archive_revision:2,at:'2026-09-20T10:00:00Z'},{id:'second-task',assignee:'Reviewer',status:'pending',archive_revision:3,at:'invalid'}]}}];v.renderList();const html=v.q('#mw-material-list').innerHTML;assert.match(html,/data-task="first-task"/);assert.match(html,/archive revision 2/);assert.match(html,/data-task="second-task"/);assert.match(html,/archive revision 3 · Date not recorded/);let opened;v.inspections.action=async(op,node)=>opened=node.dataset.task;await v.action('inspection-open',{dataset:{task:'second-task'}});assert.equal(opened,'second-task');for(const invalid of ['0','2026-02-30T10:00:00Z',null]){v.items[0].queue.open_inspections[1].at=invalid;v.renderList();assert.match(v.q('#mw-material-list').innerHTML,/archive revision 3 · Date not recorded/);}
});
