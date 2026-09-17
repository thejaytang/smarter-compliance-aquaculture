import test from 'node:test';
import assert from 'node:assert/strict';
import {Collaboration,differenceMarkup,differenceLabel,orderMarkup,validateOrder,moveOrder,orderEditorMarkup} from '../frontend/components/collaboration.js';

const blocks=()=>[{id:'h-id',type:'heading',text:'Measurements',numbering:'1',source_refs:[{page:2}]},{id:'t-id',type:'table',text:'Water quality',table:{rows:[['Temperature','14'],['Added row','2']]},source_refs:[{page:3}]},{id:'n-id',type:'text',text:'My retained note'}];
const difference=()=>({id:'order-diff',path:'/blocks',kind:'order',base:['h-id','t-id','n-id'],current:['h-id','n-id','t-id'],incoming:['h-id','t-id','n-id'],conflict:true});
const visible=html=>html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/g,'');

test('order comparison uses exact side labels and folded IDs, without replacing content',()=>{
 const d=difference(),before=structuredClone(d),referenceContext={base:{'h-id':{text:'Old title'}},current:Object.fromEntries(blocks().map(b=>[b.id,b])),incoming:Object.fromEntries(blocks().map(b=>[b.id,{...b,text:b.id==='h-id'?'<Renamed candidate>':b.text}]))};
 const html=differenceMarkup(d,{machine:true,referenceContext});
 assert.equal(differenceLabel(d),'Content order');assert.match(html,/Keep current order/);assert.match(html,/Use candidate order/);assert.match(html,/Arrange order/);assert.match(html,/data-choice="incoming"/);assert.match(html,/changes content order only/);
 assert.match(html,/Current personal content<\/small><ol><li>1 · Measurements/);assert.match(html,/Machine candidate<\/small><ol><li>1 · &lt;Renamed candidate&gt;/);assert.match(html,/Old title/);assert.match(html,/Original: Page 2/);assert.doesNotMatch(html,/<Renamed candidate>|<details open/);assert.doesNotMatch(visible(html),/h-id|t-id|n-id/);assert.deepEqual(d,before);
 assert.match(orderMarkup(['absent']),/not found in this version/);assert.match(orderMarkup(['__proto__']),/not found in this version/);
 assert.match(differenceMarkup(d),/Use submitted order/);
});

test('historical whole-list and machine table fallback display readable content with entire-item consequences',()=>{
 const data=blocks(),d={...difference(),kind:'structure',base:data,current:data,incoming:data};
 const html=differenceMarkup(d,{machine:true}),shown=visible(html);
 assert.match(shown,/Content and order/);assert.match(shown,/Measurements/);assert.match(shown,/<td>14<\/td>/);assert.match(shown,/<td>Added row<\/td>/);assert.match(shown,/My retained note/);assert.match(shown,/Keep entire current content and order/);assert.match(shown,/Replace with entire candidate content/);assert.doesNotMatch(shown,/Edit result|Arrange order|h-id|source_refs|No selective merge/);
 const table={id:'table-diff',path:'/blocks/t-id/table',kind:'machine_difference',current:data[1].table,incoming:{rows:[['<Value>','15']]},base:data[1].table};
 const t=differenceMarkup(table,{machine:true,referenceContext:{current:{'t-id':data[1]}}});
 assert.match(t,/Table content and structure/);assert.match(t,/Water quality/);assert.match(t,/Original: Page 3/);assert.match(t,/Use entire candidate table/);assert.match(t,/To change individual cells, keep your table/);assert.match(t,/&lt;Value&gt;/);assert.doesNotMatch(t,/<Value>|Edit result|Arrange order/);
});

test('order is a strict complete permutation and moves never mutate contents or input',()=>{
 const data=blocks(),before=structuredClone(data),ids=data.map(b=>b.id),copy=validateOrder(ids,data);
 assert.notEqual(ids,copy);for(const invalid of [[],['h-id','t-id'],['h-id','t-id','t-id'],['h-id','t-id','gone'],null])assert.throws(()=>validateOrder(invalid,data),/Reopen the comparison/);
 assert.throws(()=>validateOrder(ids,[...data,data[0]]),/Reopen/);
 assert.deepEqual(moveOrder(ids,1,'up'),['t-id','h-id','n-id']);assert.deepEqual(moveOrder(ids,1,'down'),['h-id','n-id','t-id']);assert.deepEqual(moveOrder(ids,0,'up'),ids);assert.deepEqual(moveOrder(ids,2,'down'),ids);assert.deepEqual(ids,['h-id','t-id','n-id']);assert.deepEqual(data,before);
 data[0].text='<Title "unsafe">';const html=orderEditorMarkup(ids,data);assert.match(html,/&lt;Title &quot;unsafe&quot;&gt;/);assert.doesNotMatch(html,/<Title|>h-id</);assert.match(html,/data-order-index="0" data-order-move="up"[^>]*disabled/);assert.match(html,/data-order-index="2" data-order-move="down"[^>]*disabled/);
});

function fixture(){
 const save={disabled:false},error={textContent:''},calls=[],messages=[];let buttons=[],html='',closed=0,focused=null;
 const editor={set innerHTML(value){html=value;buttons=[...value.matchAll(/<button([^>]*)>/g)].map(([,attrs])=>{const b={dataset:{orderIndex:attrs.match(/data-order-index="(\d+)"/)[1],orderMove:attrs.match(/data-order-move="(\w+)"/)[1]},disabled:/\bdisabled\b/.test(attrs),focus(){focused=this.dataset;}};return b;});},get innerHTML(){return html;}};
 const dialog={querySelector(s){return {'#collab-order-save':save,'#collab-order-error':error,'#collab-order-editor':editor}[s]||buttons.find(b=>s===`[data-order-index="${b.dataset.orderIndex}"][data-order-move="${b.dataset.orderMove}"]`);},querySelectorAll:()=>buttons,close(){closed++;}};
 const w={busy:false,opening:false,token:{},updateBar(){},message(text){messages.push(text);},dialog(content,wire){this.dialogContent=content;wire(dialog);}};
 const c=new Collaboration(w);c.state={mode:'coordinator'};c.merge={merge_version:2,merge_id:'merge-id',kind:'machine',material:{blocks:blocks(),revision:13},differences:[difference()],input_revision:6};
 c.showPreview=async r=>{c.merge=r;};w.api=async(path,payload)=>{calls.push({path,payload});return {...c.merge};};
 return {w,c,save,error,calls,messages,editor,button:(index,direction)=>buttons.find(b=>b.dataset.orderIndex===String(index)&&b.dataset.orderMove===direction),closed:()=>closed,focused:()=>focused};
}

test('order editor writes only the chosen ID permutation through the existing machine resolve identity',async()=>{
 const f=fixture(),before=structuredClone(f.c.merge.material.blocks);f.c.editDifference('order-diff');f.button(1,'down').onclick();assert.deepEqual(f.focused(),{orderIndex:'2',orderMove:'up'});await f.save.onclick();
 assert.deepEqual(f.calls,[{path:'/api/collaboration/machine-resolve',payload:{merge_id:'merge-id',decisions:{'order-diff':{action:'edit',value:['h-id','n-id','t-id']}}}}]);assert.deepEqual(f.c.merge.material.blocks,before);assert.equal(f.closed(),1);
});

test('unversioned previews and incomplete side orders cannot open an independent order editor',()=>{
 const old=fixture();delete old.c.merge.merge_version;old.c.editDifference('order-diff');assert.equal(old.w.dialogContent,undefined);assert.match(old.messages[0],/new comparison/);
 const missing=fixture();missing.c.merge.differences[0].incoming.pop();missing.c.editDifference('order-diff');assert.equal(missing.w.dialogContent,undefined);assert.match(missing.messages[0],/Reopen/);assert.equal(missing.calls.length,0);
});

test('rejected, stale, missing-content and busy saves retain the order draft and allow recovery',async()=>{
 const rejected=fixture();rejected.c.editDifference('order-diff');rejected.button(1,'down').onclick();const html=rejected.editor.innerHTML;rejected.w.api=async()=>{throw Error('Place the heading before its child.');};await rejected.save.onclick();assert.equal(rejected.closed(),0);assert.equal(rejected.editor.innerHTML,html);assert.match(rejected.error.textContent,/heading before/);assert.equal(rejected.save.disabled,false);
 const missing=fixture();missing.c.editDifference('order-diff');missing.c.merge.material.blocks.pop();await missing.save.onclick();assert.equal(missing.calls.length,0);assert.equal(missing.closed(),0);assert.match(missing.error.textContent,/Reopen/);
 const stale=fixture();stale.c.editDifference('order-diff');stale.c.merge.merge_id='different';await stale.save.onclick();assert.equal(stale.calls.length,0);assert.match(stale.error.textContent,/comparison changed/);
 const busy=fixture();busy.c.editDifference('order-diff');busy.w.busy=true;const original=busy.editor.innerHTML;busy.button(1,'down').onclick();await busy.save.onclick();assert.equal(busy.editor.innerHTML,original);assert.equal(busy.calls.length,0);assert.match(busy.error.textContent,/Wait for/);
});

test('double-clicking an order save sends one request while the first is pending',async()=>{
 const f=fixture();let release;f.w.api=async(path,payload)=>{f.calls.push({path,payload});return await new Promise(resolve=>{release=()=>resolve({...f.c.merge});});};f.c.editDifference('order-diff');const pending=f.save.onclick();await f.save.onclick();assert.equal(f.calls.length,1);release();await pending;assert.equal(f.closed(),1);
});

test('candidate input content version and present saved record have distinct labels',()=>{
 const f=fixture(),html=f.c.mergeSummary();assert.match(html,/Input content revision 6/);assert.match(html,/Current saved record: revision 13/);assert.match(html,/separate from content revisions/);assert.doesNotMatch(html,/Input saved record|Input revision 13/);
});

test('textless tables are identified by exact sheet and cell range across order, editor and table comparison',()=>{
 const data=[{id:'near',type:'table',numbering:'TEST1.1',text:'',source_refs:[{sheet:'Measurements',cell_range:'A1:C3'}]},{id:'far',type:'table',text:'',source_refs:[{sheet:'Measurements',cell_range:'Z105:Z105'}]}],context=Object.fromEntries(data.map(b=>[b.id,b])),before=structuredClone(data);
 for(const html of [orderMarkup(['near','far'],context),orderEditorMarkup(['near','far'],data)]){
  assert.match(html,/TEST1\.1 · Table · Measurements · A1:C3/);assert.match(html,/Table · Measurements · Z105:Z105/);assert.doesNotMatch(html,/text not recorded|>near<|>far</);
 }
 const table=differenceMarkup({id:'diff',kind:'machine_difference',path:'/blocks/far/table',current:{rows:[['Value','14']]},incoming:{rows:[['Value','15']]}},{referenceContext:{current:context,incoming:{far:{...data[1],source_refs:[{sheet:'<Candidate sheet>',cell_range:'A1:B2'}]}}}});
 assert.match(table,/Table · Measurements · Z105:Z105/);assert.match(table,/Table · &lt;Candidate sheet&gt; · A1:B2/);assert.doesNotMatch(table,/<Candidate sheet>/);assert.deepEqual(data,before);
 const html=orderMarkup(['html','unknown'],{html:{type:'table',source_refs:[{anchor:'opaque-original-123'}]},unknown:{type:'private_internal_type',source_refs:[]}});
 assert.match(html,/Table · Linked original location/);assert.doesNotMatch(visible(html),/opaque-original|private_internal_type|text not recorded/);assert.match(html,/<li>Content<\/li>/);
});
