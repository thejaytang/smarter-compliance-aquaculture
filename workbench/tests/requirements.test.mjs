import test from 'node:test';
import assert from 'node:assert/strict';
import {RequirementsEditor,codepointOffset,quantityLabel,groupIds,quantityPreset,quantityMode,quantityPreview,quantityRange} from '../ui/requirements.js';
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
 assert.equal((host.innerHTML.match(/data-rq="extract"/g)||[]).length,4);
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
test('condition cards only expose recursive conditions; relation fields have fixed colours',()=>{
 const {editor}=fixture();editor.doc=documentFixture();editor.doc.roles.v='condition';
 const child=editor.unitMarkup(editor.doc.units.v,'',false);
 assert.doesNotMatch(child,/data-rq="assign"|data-field="exceptions"|data-field="subrequirement"/);
 assert.match(child,/rq-relation-field semantic semantic-4/);
 const root=editor.unitMarkup(editor.doc.units.u,'',false);
 for(const [i,field] of ['conditions','exceptions','subrequirement'].entries())assert.match(root,new RegExp(`semantic-${i+4}" data-field="${field}"`));
});
test('all three relation counts remain visible with nested ownership and no disclosure',()=>{
 const {editor}=fixture();editor.doc=documentFixture();
 for(const field of ['conditions','exceptions','subrequirement']){
  const html=editor.groupMarkup([[1,2],'u',[1,'v']],field,'owner',[2],false);
  assert.match(html,/data-rq-preview[^>]*>\[1, 2\]/);assert.match(html,/>QC<\/strong>/);assert.match(html,/data-owner="owner" data-path="2"/);assert.match(html,/data-path="2.2"/);
  assert.doesNotMatch(html,/<details/);assert.match(html,/data-rq="quantity-preset"/);
 }
});
test('material-wide labels match headers and complete Requirement reference choices',()=>{
 const {editor}=fixture();const a=documentFixture(),b={...documentFixture(),id:'s2',units:{x:{id:'x',text:'Other full requirement'}},roots:[1,'x'],roles:{x:'requirement'},done:['x'],spans:{x:[0,22]}};
 editor.doc=a;a.done=['u','v'];editor.sessions=[a,b];
 const labels=editor.displayLabels();assert.equal(new Set(Object.values(labels)).size,3);assert.equal(editor.entryLabel(b),editor.label('x'));
 const html=editor.relationMarkup(a.units.u,'exceptions','',false);assert.match(html,new RegExp(`${labels.x} · Other full requirement`));assert.match(html,/value="x"/);assert.doesNotMatch(html,/value="u"/);
});
test('right-pane selection reveals the matching left card and deselection clears the active interpretation',async()=>{
 const {editor,m,host}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc];editor.selected=null;editor.closedUnits=new Set(['u','v']);editor.render=()=>{};host.querySelector=()=>null;
 let opened,empty=0;m.interpretations={open:async id=>opened=id,render:()=>empty++,active:'old'};
 await editor.selectFromInterpretation('v');assert.equal(editor.selected,'v');assert.equal(opened,'v');assert.equal(editor.closedUnits.has('v'),false);
 await editor.selectFromInterpretation('v');assert.equal(editor.selected,null);assert.equal(m.interpretations.active,null);assert.equal(empty,1);
});
test('linking another complete Requirement submits its immutable ID and relationship',async()=>{
 const {editor}=fixture();editor.doc=documentFixture();let sent;
 const card={dataset:{unit:'u'},querySelector:()=>({value:'other-root-id'})};editor.step=async(a,b)=>sent={a,b};
 await editor.action('link-existing',{dataset:{field:'exceptions'},closest:()=>card});
 assert.deepEqual(sent,{a:'link',b:{unit_id:'u',field:'exceptions',target_id:'other-root-id'}});
});

test('quantity shortcuts distinguish inclusive OR, exactly one and direct-child All',()=>{
 assert.equal(quantityPreset('all',3),3);assert.deepEqual(quantityPreset('any',3),[1,3]);assert.equal(quantityPreset('one',3),1);
 assert.equal(quantityMode([2,3],4),'custom');assert.equal(quantityMode([1,3],3),'any');assert.equal(quantityMode(1,3),'one');
});
test('condition editor is nested between its siblings with no duplicate flat card',()=>{
 const {editor}=fixture();editor.doc=documentFixture();editor.doc.roots=[1,'u'];editor.doc.units.u.conditions=[2,'v','w'];editor.doc.units.v.conditions=[1,'z'];
 editor.doc.units.w={id:'w',text:'C2 wording'};editor.doc.units.z={id:'z',text:'Nested wording'};editor.doc.roles={u:'requirement',v:'condition',w:'condition',z:'condition'};
 const html=editor.documentMarkup();
 assert.equal((html.match(/data-unit="v"/g)||[]).length,1);assert.equal((html.match(/data-unit="z"/g)||[]).length,1);
 assert.ok(html.indexOf('rq-quantity-presets')<html.indexOf('data-unit="v"'));assert.ok(html.indexOf('data-unit="v"')<html.indexOf('data-unit="z"'));assert.ok(html.indexOf('data-unit="z"')<html.indexOf('data-unit="w"'));
 assert.match(html,/rq-inline-condition/);
});
test('nested quantity preset acts on its own owner and path, counting a nested group once',async()=>{
 const {editor}=fixture();editor.doc=documentFixture();editor.doc.units.u.conditions=[2,[2,'v',[1,'x']],'y'];let sent;
 const group={dataset:{owner:'u',field:'conditions',path:'1'}},card={dataset:{unit:'v'}};
 editor.step=async(a,b)=>sent={a,b};
 await editor.action('quantity-preset',{dataset:{preset:'any'},closest:s=>s==='[data-rq-group]'?group:card});
 assert.deepEqual(sent,{a:'quantity',b:{unit_id:'u',field:'conditions',path:[1],quantity:[1,2]}});
});
test('editing a nested child keeps its already-finished ancestor open',async()=>{
 const {editor,m}=fixture();editor.doc=documentFixture();editor.doc.done=['u'];editor.selected='v';editor.closedUnits=new Set();editor.render=()=>{};
 m.api=async()=>({document:{...editor.doc,revision:3}});await editor.step('extract',{unit_id:'v',field:'conditions',start:0,end:4});
 assert.equal(editor.closedUnits.has('u'),false);
});
test('custom range applies inclusive bounds to the selected group only',async()=>{
 const {editor}=fixture();editor.doc=documentFixture();editor.doc.units.u.exceptions=[2,'v','u'];let sent;
 const controls={querySelector:s=>({value:s==='[data-rq-min]'?'0':'2'})};
 const group={dataset:{owner:'u',field:'exceptions',path:''},querySelector:()=>controls};
 editor.step=async(a,b)=>sent={a,b};await editor.action('quantity',{dataset:{},closest:s=>s==='[data-rq-group]'?group:null});
 assert.deepEqual(sent,{a:'quantity',b:{unit_id:'u',field:'exceptions',path:[],quantity:[0,2]}});
});

test('compact QC preserves scalar and range representations with bounded shortcuts',()=>{
 assert.deepEqual(quantityPreset('not-all',4),[1,3]);assert.throws(()=>quantityPreset('not-all',1));
 assert.equal(quantityMode([1,1],2),'not-all');assert.equal(quantityMode(1,2),'one');
 assert.equal(quantityPreview(2),'2');assert.equal(quantityPreview([0,2]),'[0, 2]');
 assert.deepEqual(quantityRange('0','2',2),[0,2]);assert.deepEqual(quantityRange('1','1',2),[1,1]);
 for(const pair of [['','2'],['-1','2'],['1.5','2'],['1','3'],['2','1'],['1e0','2']])assert.throws(()=>quantityRange(...pair,2));
 const {editor}=fixture();editor.doc=documentFixture();const html=editor.groupMarkup([1,'u'],'conditions','u');
 assert.match(html,/data-preset="not-all"[^>]*disabled/);assert.match(html,/MIN-MAX:/);assert.doesNotMatch(html,/Apply range|quantity-custom/);
});
function quantityFixture(){
 const {editor,m}=fixture();editor.doc=documentFixture();editor.render=()=>{};
 const group={dataset:{owner:'u',field:'conditions',path:''}};
 const inputs=['2','2'].map(value=>({value,dataset:{},setAttribute(){},removeAttribute(){}}));
 const output={},error={hidden:true};
 const row={dataset:{count:'2',current:'2'},closest:()=>group,parentElement:{querySelector:()=>error},querySelectorAll:s=>s==='input'?inputs:[],querySelector:()=>output,contains:node=>inputs.includes(node)};
 editor.bindQuantity(row);return {editor,m,row,inputs,output,error};
}
test('range input previews immediately, rejects non-digits, clamps, and warns before leaving',async()=>{
 const {editor,row,inputs,output,error}=quantityFixture();let sent=0;editor.action=async()=>{sent++;return true;};
 inputs[0].value='0';inputs[0].oninput();assert.equal(output.textContent,'[0, 2]');assert.equal(editor.dirty,true);
 inputs[1].value='99';inputs[1].oninput();assert.equal(inputs[1].value,'2');
 inputs[1].value='-1';inputs[1].oninput();assert.equal(inputs[1].value,'2');
 let prevented=false;inputs[0].onbeforeinput({data:'e',preventDefault(){prevented=true;}});assert.ok(prevented);
 row.onfocusout({relatedTarget:inputs[1]});assert.equal(sent,0);
 inputs[1].value='';inputs[1].oninput();assert.equal(await row.commitQuantity(),false);assert.equal(sent,0);assert.equal(error.hidden,false);
 inputs[1].value='1';inputs[1].oninput();assert.equal(await row.commitQuantity(),true);assert.equal(sent,1);assert.equal(editor.quantityDrafts.size,0);
 await row.commitQuantity();assert.equal(sent,1);
});
test('Escape restores quantity without clearing pre-existing unsaved work; failed preview retains input',async()=>{
 const {editor,row,inputs,output}=quantityFixture();editor.dirty=true;
 inputs[0].value='0';inputs[0].oninput();editor.action=async()=>false;
 assert.equal(await row.commitQuantity(),false);assert.equal(editor.quantityDrafts.size,1);
 inputs[0].onkeydown({key:'Escape',preventDefault(){}});assert.equal(output.textContent,'2');assert.equal(editor.quantityDrafts.size,0);assert.equal(editor.dirty,true);
});

test('uncommitted bounds survive a render and block saving when invalid',async()=>{
 const {editor,row,inputs,output}=quantityFixture();inputs[0].value='';inputs[0].oninput();
 inputs[0].value='2';editor.bindQuantity(row);assert.equal(inputs[0].value,'');assert.equal(output.textContent,'[…, 2]');
 let saves=0;editor.host.querySelectorAll=()=>[row];editor.step=async()=>saves++;
 await editor.saveDraft();assert.equal(saves,0);assert.equal(editor.dirty,true);
});
test('manual Save flushes the current range before submitting its step list',async()=>{
 const {editor,row,inputs}=quantityFixture();inputs[0].value='0';inputs[0].oninput();
 const calls=[];editor.action=async()=>{calls.push('quantity');editor._dirty=true;return true;};
 editor.host.querySelectorAll=()=>[row];editor.step=async action=>calls.push(action);
 await editor.saveDraft();assert.deepEqual(calls,['quantity','save-draft']);
});
