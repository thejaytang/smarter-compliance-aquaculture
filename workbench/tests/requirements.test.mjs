import test from 'node:test';
import assert from 'node:assert/strict';
import {RequirementsEditor,codepointOffset,quantityLabel,groupIds} from '../ui/requirements.js';
function fixture(){
 const host={innerHTML:'',classList:{add(){}},setAttribute(){},removeAttribute(){}};
 const auto={},m={id:'m',state:{actor:{id:'a'}},material:{revision:3,collaboration:{view:'personal'}},draft:{blocks:[{id:'b',type:'text',text:'Original whole passage'}]},collaboration:{readonly:false},q:s=>s==='#mw-requirement-content'?host:auto};
 const editor=new RequirementsEditor(m);editor.context=editor.key();return {editor,m,host,auto};
}
test('count labels mean exact k and inclusive range; nested group is one direct item',()=>{
 assert.equal(quantityLabel(1),'Exactly 1');assert.equal(quantityLabel([1,3]),'1 to 3');assert.deepEqual(groupIds([1,'a',[2,'b','c']]),['a','b','c']);
});
test('source selection offsets preserve Unicode outside the BMP',()=>{
 assert.equal(codepointOffset('Fish 🐟 shall',7),6);assert.equal(codepointOffset('Fish 🐟 shall',12),11);
});
test('manual intake has honest empty and dirty states without automatic processing',()=>{
 const {editor,m,host,auto}=fixture();editor.render();assert.match(host.innerHTML,/To requirements/);assert.doesNotMatch(host.innerHTML,/data-rq-block|data-rq-session|rq-steps/);assert.match(host.innerHTML,/Not connected/);assert.equal(auto.disabled,true);
 m.dirty=true;editor.render();assert.match(host.innerHTML,/Save the source content before splitting/);assert.equal(editor.locked,true);
});
test('whole passage start sends a block ID and saved version, never rewritten text',async()=>{
 const {editor,m}=fixture();let request;m.api=async(path,body)=>{request={path,body};return {document:{id:'s',revision:1,units:{u:{id:'u',text:'Whole'}},done:[]}};};editor.render=()=>{};
 await editor.start('b');assert.equal(request.body.action,'preview');assert.equal(request.body.steps[0].action,'start');assert.equal(request.body.steps[0].block_id,'b');assert.equal(request.body.steps[0].material_revision,3);assert.equal('text' in request.body,false);
});
test('uncertain write retains the exact idempotent request and retry identity',async()=>{
 const {editor,m}=fixture();let first;m.api=async(path,body)=>{first??=body;throw Error('Connection lost');};editor.render=()=>{};await editor.start('b');assert.equal(editor.retryRequest,first.steps[0]);
 m.api=async(path,body)=>{assert.deepEqual(body.steps,first.steps);return {document:{id:'s',revision:1,units:{u:{id:'u',text:'Whole'}},done:[]}};};await editor.step('',{},editor.retryRequest);assert.equal(editor.retryRequest,null);assert.equal(editor.doc.revision,1);
});
test('source-stale session allows a new whole-passage start but protects old steps',async()=>{
 const {editor,m}=fixture();editor.doc={id:'old',revision:1,stale:true};editor.render=()=>{};let action;m.api=async(p,b)=>{action=b.action;return {document:{id:'new',revision:1,units:{u:{id:'u',text:'Whole'}},done:[]}};};await editor.start('b');assert.equal(action,'preview');
});
test('loading another saved passage locks all mutation steps until it is bound',async()=>{
 const {editor,m}=fixture();editor.loading=true;let calls=0;m.api=async()=>calls++;await editor.step('phase',{phase:'fields'});assert.equal(calls,0);assert.equal(editor.locked,true);
});

function documentFixture(){return {id:'s',revision:2,phase:'relationships',text:'Fish shall swim. Nets shall hold.',chapter:'Chapter 2',material_revision:3,block_id:'b',units:{u:{id:'u',text:'Fish shall swim.'},v:{id:'v',text:'Nets shall hold.'}},done:[],roots:[2,'u','v'],spans:{u:[0,16],v:[16,33]},roles:{u:'requirement',v:'requirement'},reference_evidence:{},source_refs:[]};}
test('all units expose inline fields without phase navigation; finished units collapse',()=>{
 const {editor,host}=fixture();editor.doc=documentFixture();editor.doc.done=['u'];editor.closedUnits.add('u');editor.sessions=[editor.doc];editor.render();
 assert.doesNotMatch(host.innerHTML,/Current unit|rq-steps|Whole source passage|Saved passages|Continue to unit fields/);
 assert.equal((host.innerHTML.match(/data-rq-text/g)||[]).length,2);
 assert.equal((host.innerHTML.match(/data-rq="assign"/g)||[]).length,8);
 assert.match(host.innerHTML,/data-unit="u"[^>]* >/);assert.match(host.innerHTML,/data-unit="v"[^>]* open/);
});
test('session order follows source blocks and stays fixed after saving a step',async()=>{
 const {editor,m}=fixture();m.draft.blocks.push({id:'last'});
 editor.doc=documentFixture();editor.sessions=[{...editor.doc,id:'later',block_id:'last'},editor.doc];editor.render=()=>{};
 m.api=async()=>({document:{...editor.doc,revision:3}});
 await editor.step('assign',{unit_id:'u',field:'Subject',start:0,end:4});
 assert.deepEqual(editor.orderedSessions().map(s=>s.id),['s','later']);assert.equal(editor.sessions.length,2);
});
test('a field action uses its own card selection, not the first source textarea',async()=>{
 const {editor}=fixture();editor.doc=documentFixture();editor.selected='u';let sent;
 const area={value:'Nets shall hold.',selectionStart:0,selectionEnd:4};
 const card={dataset:{unit:'v'},querySelector:s=>{assert.equal(s,'[data-rq-text]');return area;}};
 editor.step=async(a,b)=>{sent={a,b};};
 await editor.action('assign',{dataset:{field:'Subject'},closest:()=>card});
 assert.deepEqual(sent,{a:'assign',b:{unit_id:'v',start:0,end:4,field:'Subject'}});
});
test('source-header locate and direct relation actions replace redundant controls',()=>{
 const {editor,host}=fixture();editor.doc=documentFixture();editor.doc.units.u.conditions=[1,'v'];editor.doc.roles.v='condition';editor.sessions=[editor.doc];editor.render();
 assert.doesNotMatch(host.innerHTML,/Interpret requirement|Split at cursor|<details class="rq-add-relations"/);
 const header=host.innerHTML.slice(host.innerHTML.indexOf('data-rq="open-session"'),host.innerHTML.indexOf('</summary>',host.innerHTML.indexOf('data-rq="open-session"')));
 assert.match(header,/rq-source-preview/);assert.match(header,/data-rq="locate-session"/);
 assert.equal((host.innerHTML.match(/data-rq="extract"/g)||[]).length,6);
 assert.match(host.innerHTML,/data-rq="decompose" data-id="v"/);
});
test('decompose reopens only the chosen finished child and exposes its exact text',async()=>{
 const {editor,host}=fixture();editor.doc=documentFixture();editor.doc.phase='complete';editor.doc.done=['u','v'];editor.doc.roles.v='condition';editor.selected='u';editor.closedUnits=new Set(['u','v']);let sent,focused=false;
 editor.render=()=>{};host.querySelector=()=>({scrollIntoView(){},querySelector:()=>({focus(){focused=true;}})});
 editor.step=async(a,b)=>{sent={a,b};editor.doc.phase='fields';editor.doc.done=['u'];editor.dirty=true;};
 await editor.action('decompose',{dataset:{id:'v'},closest:()=>null});
 assert.deepEqual(sent,{a:'reopen',b:{unit_id:'v'}});assert.equal(editor.selected,'v');assert.ok(editor.closedUnits.has('u'));assert.ok(!editor.closedUnits.has('v'));assert.equal(focused,true);
 let extracted;editor.step=async(a,b)=>extracted={a,b};
 const card={dataset:{unit:'v'},querySelector:()=>({value:'Nets shall hold.',selectionStart:0,selectionEnd:4})};
 await editor.action('extract',{dataset:{field:'conditions'},closest:()=>card});
 assert.deepEqual(extracted,{a:'extract',b:{unit_id:'v',start:0,end:4,field:'conditions'}});
});
test('selection loads saved interpretation without a dedicated button and skips unsaved splitting',async()=>{
 const {editor,m,host}=fixture();editor.doc=documentFixture();editor.selected='u';editor.render=()=>{};host.querySelector=()=>null;const opened=[];m.interpretations={open:async id=>opened.push(id)};
 await editor.action('select-unit',{dataset:{id:'v'},closest:()=>null});assert.deepEqual(opened,['v']);
 editor.dirty=true;await editor.syncInterpretation();assert.deepEqual(opened,['v']);
 editor.dirty=false;editor.doc.roles.v='condition';await editor.syncInterpretation();assert.deepEqual(opened,['v']);
});
test('header location uses that whole entry even when another unit is selected',async()=>{
 const {editor,m}=fixture();editor.doc=documentFixture();editor.selected='v';editor.sessions=[{id:'other',text:'Original whole passage',block_id:'b'}];let jumped,located;
 m.jumpToBlock=i=>jumped=i;m.locateBlock=async b=>located=b.id;
 await editor.action('locate-session',{dataset:{id:'other'},closest:()=>null});
 assert.equal(jumped,0);assert.equal(located,'b');assert.equal(editor.selected,'v');
});
