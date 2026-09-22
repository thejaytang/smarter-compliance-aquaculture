import test from 'node:test';
import assert from 'node:assert/strict';
import {SubmissionDrawer,receiptMarkup} from '../frontend/components/submission-drawer.js';
const receipt=()=>({item_type:'adoption_receipt',receipt:{status:'adopted',actor:'Coordinator',contributor:'<Colleague>',at:'2026-09-13T10:00:00Z',material:{title:'Material A',revision:4,content_status:'draft',source:{source_id:'PA001'},blocks:[{text:'<script>PAYLOAD_SENTINEL</script>'}]}}});
test('received receipt summary separates adoption, content review and immutable folded payload',()=>{
 const input=receipt(),before=structuredClone(input),html=receiptMarkup(input),summary=html.split('<details>')[0];
 assert.match(summary,/Material A/);assert.match(summary,/PA001/);assert.match(summary,/&lt;Colleague&gt;/);assert.match(summary,/Master revision/);assert.match(summary,/>4</);assert.match(summary,/Adoption decision/);assert.match(summary,/Adopted/);assert.match(summary,/Content review at receipt/);assert.match(summary,/Draft/);
 assert.doesNotMatch(summary,/PAYLOAD_SENTINEL|<script>/);assert.match(html,/<details><summary>Original receipt details<\/summary>/);assert.doesNotMatch(html,/<details open|<script>/);assert.match(html,/&lt;script&gt;PAYLOAD_SENTINEL/);assert.deepEqual(input,before);
});
test('task receipt distinguishes kept-current decision, archive check and unknown master review',()=>{
 const html=receiptMarkup({item_id:'task-result',status:'adopted',choice:'current',actor:'Coordinator',contributor:'Reviewer',result:{inspection:{title:'Check A',archive_revision:9,status:'passed'}}},[{id:'task-result',base:{source_id:'PA002'}}]);
 const summary=html.split('<details>')[0];assert.match(summary,/Kept current/);assert.match(summary,/Checked archive revision/);assert.match(summary,/>9</);assert.match(summary,/Not recorded in this receipt/);assert.match(summary,/Master revision<\/dt><dd><span class="collab-value">Not recorded/);assert.match(summary,/Spot-check status/);assert.match(summary,/Passed/);assert.match(summary,/PA002/);
});
test('unknown receipt fields remain explicitly missing, without an inferred adoption or review',()=>{
 const html=receiptMarkup({receipt:{status:'pending'}}).split('<details>')[0];assert.match(html,/Pending/);assert.match(html,/Not recorded/);assert.doesNotMatch(html,/Content Review Complete|>Adopted</);
});
test('both drawer routes render receipt cards with only second-level details for raw payload',async()=>{
 const received=receipt(),data={items:[],received_receipts:[received],receipts:[received.receipt],inbox:[]},w={api:async()=>data,dialog:html=>w.html=html};
 const drawer=new SubmissionDrawer(w);await drawer.open();assert.match(w.html,/<summary>Received adoption receipts<\/summary><article/);assert.match(w.html,/<summary>Original receipt details<\/summary>/);
 await drawer.inbox();assert.match(w.html,/<summary>Per-item adoption receipts<\/summary><article/);assert.match(w.html,/Content review at receipt/);
});

function compareWorkspace(){
 const w={state:{actor:{id:'reviewer'}}},nodes=new Map();let html='';
 const root={set innerHTML(value){html=value;nodes.clear();nodes.set('#bundle-confirm',{checked:false,disabled:/id="bundle-confirm"[^>]*disabled/.test(value)});for(const choice of ['current','incoming'])nodes.set(choice,{dataset:{bundleChoice:choice},disabled:new RegExp('data-bundle-choice="'+choice+'"[^>]*disabled').test(value)});nodes.set('#bundle-adopt-status',{textContent:''});nodes.set('#bundle-refresh',{hidden:true,disabled:false});if(value.includes('id="bundle-adopt-retry"'))nodes.set('#bundle-adopt-retry',{disabled:/id="bundle-adopt-retry" disabled/.test(value)});},get innerHTML(){return html;}};
 const d={querySelector:s=>s==='#bundle-comparison'?root:nodes.get(s)||null,querySelectorAll:()=>['current','incoming'].map(x=>nodes.get(x)),close(){}};
 w.dialog=(_,bind)=>bind(d);return {w,d,nodes,root};
}
const taskPreview=()=>({item:{actor:'Author'},current:{note:'current'},proposed:{note:'submitted'},base:{note:'base'},current_digest:'digest-one',conflict:false});
test('task adoption serializes opposing choices and an uncertain retry retains the exact decision across drawers',async()=>{
 const {w,d,nodes}=compareWorkspace(),p=taskPreview(),requests=[];let finish;
 w.api=async(path,body)=>{if(path.endsWith('preview'))return p;requests.push(structuredClone(body));if(requests.length===1)return new Promise(resolve=>finish=resolve);return {status:'adopted'};};
 await new SubmissionDrawer(w).compare('item');d.querySelector('#bundle-confirm').checked=true;const opposing=nodes.get('incoming'),first=nodes.get('current').onclick();assert.equal(nodes.get('current').disabled,true);assert.equal(nodes.get('incoming').disabled,true);await opposing.onclick();assert.equal(requests.length,1);
 finish({status:'pending',result:{message:'Owner response pending'}});await first;assert.ok(d.querySelector('#bundle-adopt-retry'));assert.equal(nodes.get('incoming').disabled,true);
 await new SubmissionDrawer(w).compare('item');await d.querySelector('#bundle-adopt-retry').onclick();assert.deepEqual(requests[1],requests[0]);assert.equal(requests[1].choice,'current');assert.equal(nodes.get('incoming').disabled,true);assert.equal(d.querySelector('#bundle-adopt-retry'),null);await nodes.get('incoming').onclick();assert.equal(requests.length,2);
});
test('uncertain task failure retains decision identity while expired comparison refresh requires a new confirmation',async()=>{
 const {w,d,nodes,root}=compareWorkspace();let previews=0,decisions=0;const requests=[];w.api=async(path,body)=>{if(path.endsWith('preview'))return {...taskPreview(),current_digest:'digest-'+(++previews),current:{note:'version '+previews}};requests.push(structuredClone(body));decisions++;if(decisions===1)throw Error('Response lost');if(decisions===2)throw Object.assign(Error('Task changed after comparison. Reopen it.'),{definitive:true,status:400});return {status:'adopted'};};
 await new SubmissionDrawer(w).compare('item');d.querySelector('#bundle-confirm').checked=true;await nodes.get('incoming').onclick();assert.ok(d.querySelector('#bundle-adopt-retry'));await d.querySelector('#bundle-adopt-retry').onclick();assert.deepEqual(requests[0],requests[1]);assert.equal(d.querySelector('#bundle-refresh').hidden,false);assert.equal(nodes.get('incoming').disabled,true);
 await d.querySelector('#bundle-refresh').onclick();assert.match(root.innerHTML,/version 2/);assert.equal(d.querySelector('#bundle-confirm').checked,false);await nodes.get('incoming').onclick();assert.equal(decisions,2);d.querySelector('#bundle-confirm').checked=true;await nodes.get('incoming').onclick();assert.equal(requests[2].expected_current_digest,'digest-2');assert.notEqual(requests[2].request_id,requests[1].request_id);
});
test('failed task refresh keeps submitted evidence and cannot reset an uncertain adoption',async()=>{
 const {w,d,nodes,root}=compareWorkspace();let reads=0;w.api=async(path)=>{if(path.endsWith('preview')){if(reads++)throw Error('Offline');return taskPreview();}throw Object.assign(Error('Task changed after comparison. Reopen it.'),{definitive:true});};await new SubmissionDrawer(w).compare('item');d.querySelector('#bundle-confirm').checked=true;await nodes.get('current').onclick();const before=root.innerHTML;await d.querySelector('#bundle-refresh').onclick();assert.equal(root.innerHTML,before);assert.match(d.querySelector('#bundle-adopt-status').textContent,/previous comparison is retained/);assert.equal(nodes.get('incoming').disabled,true);
});
function freezeWorkspace(){
 const w={state:{actor:{id:'reviewer'}}},nodes=new Map(),items=[{type:'source',key:'one',title:'Source one'},{type:'task',key:'two',title:'Task two'}];let current;
 w.dialog=(_,bind)=>{const controls=items.map((_,i)=>({dataset:{itemIndex:String(i)},checked:false,disabled:false})),summary={dataset:{},value:'',disabled:false},b={disabled:false},status={textContent:'',children:[],ownerDocument:{createElement:tag=>({tag})},replaceChildren(){this.children=[];},appendChild(node){this.children.push(node);}},d={open:false,querySelector:s=>({'#bundle-summary':summary,'#bundle-download':b,'#bundle-status':status}[s]),querySelectorAll:s=>s==='[data-item-index]'?controls:s==='[data-item-index]:checked'?controls.filter(n=>n.checked):[]};current={controls,summary,b,status,d};bind(d);d.open=true;};
 return {w,items,get current(){return current;}};
}
test('freeze locks captured scope and summary and an uncertain retry survives close and reopen',async()=>{
 const fixture=freezeWorkspace(),{w,items}=fixture,requests=[];let reject;w.api=async()=>({items});w.api.download=async(path,body)=>{requests.push(structuredClone(body));if(requests.length===1)return new Promise((_,r)=>reject=r);return {downloadUrl:'/immutable',filename:'same.zip'};};
 await new SubmissionDrawer(w).open();const first=fixture.current;first.controls[1].checked=true;first.summary.value='Reviewed task scope';const pending=first.b.onclick();assert.ok(first.controls.every(n=>n.disabled));assert.equal(first.summary.disabled,true);reject(Error('Lost response'));await pending;assert.equal(first.summary.value,'Reviewed task scope');assert.ok(first.controls.every(n=>!n.disabled));
 await new SubmissionDrawer(w).open();const second=fixture.current;assert.equal(second.controls[1].checked,true);assert.equal(second.summary.value,'Reviewed task scope');assert.match(second.status.textContent,/Lost response.*Retry this selection/);await second.b.onclick();assert.deepEqual(requests[1],requests[0]);assert.ok(second.status.children.some(n=>n.textContent?.includes('Captured selection: Task two · Reviewed task scope')));assert.ok(second.status.children.some(n=>n.href==='/immutable'));
 await second.b.onclick();assert.deepEqual(requests[2].items,requests[1].items);assert.equal(requests[2].summary,requests[1].summary);assert.notEqual(requests[2].request_id,requests[1].request_id);second.controls[0].checked=true;await second.b.onclick();assert.notEqual(requests[3].request_id,requests[2].request_id);
});
test('reopening a freeze while pending follows its completion without enabling a second request',async()=>{
 const fixture=freezeWorkspace(),{w,items}=fixture;let finish,calls=0;w.api=async()=>({items});w.api.download=async()=>{calls++;return new Promise(r=>finish=r);};await new SubmissionDrawer(w).open();fixture.current.controls[0].checked=true;const first=fixture.current.b.onclick();await new SubmissionDrawer(w).open();const second=fixture.current;assert.equal(second.b.disabled,true);await second.b.onclick();assert.equal(calls,1);finish({downloadUrl:'/same',filename:'f.zip'});await first;assert.equal(second.b.disabled,false);assert.ok(second.status.children.some(n=>n.href==='/same'));
});

test('a task decision finishing after close and reopen updates only the latest matching comparison',async()=>{
 for(const status of ['pending','adopted']){
  const {w,d,nodes}=compareWorkspace();let finish;w.api=async path=>path.endsWith('preview')?taskPreview():new Promise(r=>finish=r);await new SubmissionDrawer(w).compare('item');d.querySelector('#bundle-confirm').checked=true;const pending=nodes.get('current').onclick();await new SubmissionDrawer(w).compare('item');assert.equal(d.querySelector('#bundle-adopt-retry').disabled,true);finish({status,result:{message:'Receipt pending'}});await pending;
  if(status==='pending'){assert.equal(d.querySelector('#bundle-adopt-retry').disabled,false);assert.match(d.querySelector('#bundle-adopt-status').textContent,/remains pending/);}else {assert.equal(d.querySelector('#bundle-adopt-retry'),null);assert.match(d.querySelector('#bundle-adopt-status').textContent,/recorded/);}assert.equal(nodes.get('incoming').disabled,true);
 }
});

test('a delayed task receipt cannot redraw an unrelated dialog sharing the same native element',async()=>{
 const {w,d,nodes}=compareWorkspace();let finish;w.api=async path=>path.endsWith('preview')?taskPreview():new Promise(r=>finish=r);await new SubmissionDrawer(w).compare('item');d.querySelector('#bundle-confirm').checked=true;const pending=nodes.get('current').onclick(),oldQuery=d.querySelector;d.querySelector=()=>null;finish({status:'adopted'});await pending;assert.equal(w.collectionPending.get('reviewer:adopt:item').result.status,'adopted');d.querySelector=oldQuery;await new SubmissionDrawer(w).compare('item');assert.equal(d.querySelector('#bundle-adopt-retry'),null);assert.equal(nodes.get('incoming').disabled,true);
});

test('task comparison initializes before a native dialog opens but subsequent close blocks actions',async()=>{
 const {w,d,nodes,root}=compareWorkspace();d.open=false;w.dialog=(_,bind)=>{bind(d);assert.match(root.innerHTML,/Review task result/);d.open=true;};let writes=0;w.api=async(path)=>{if(path.endsWith('preview'))return taskPreview();writes++;return {status:'adopted'};};await new SubmissionDrawer(w).compare('item');assert.match(root.innerHTML,/Submitted result/);d.querySelector('#bundle-confirm').checked=true;d.open=false;await nodes.get('incoming').onclick();assert.equal(writes,0);
});
