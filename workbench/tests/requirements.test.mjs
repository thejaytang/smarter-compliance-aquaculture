import test from 'node:test';
import assert from 'node:assert/strict';
import {RequirementsEditor,codepointOffset,quantityLabel,groupIds,quantityPreset,quantityMode,quantityPreview,quantityRange} from '../frontend/components/requirements.js';
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
 const {editor,m,host,auto}=fixture();editor.render();assert.match(host.innerHTML,/To requirement/);assert.doesNotMatch(host.innerHTML,/data-rq-block|data-rq-session|rq-steps/);assert.match(host.innerHTML,/Not connected/);assert.equal(auto.disabled,undefined);
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
  assert.match(html,/data-rq-preview[^>]*>\[1, 2\]/);assert.doesNotMatch(html,/>QC<\/strong>/);assert.match(html,/data-owner="owner" data-path="2"/);assert.match(html,/data-path="2.2"/);
  assert.doesNotMatch(html,/<details/);assert.match(html,/data-rq="quantity-preset"/);
 }
});
test('material-wide labels match headers and complete Requirement reference choices',()=>{
 const {editor}=fixture();const a=documentFixture(),b={...documentFixture(),id:'s2',text:'Other full requirement',units:{x:{id:'x',text:'Other full requirement'}},roots:[1,'x'],roles:{x:'requirement'},done:['x'],spans:{x:[0,22]}};
 editor.doc=a;a.done=['u','v'];editor.sessions=[a,b];
 const labels=editor.displayLabels();assert.equal(new Set(Object.values(labels)).size,3);assert.equal(editor.entryLabel(b),editor.label('x'));
 const html=editor.relationMarkup(a.units.u,'exceptions','',false);assert.match(html,new RegExp(`${labels.x} · Other full requirement`));assert.match(html,/value="x"/);assert.doesNotMatch(html,/value="u"/);
});
test('right-pane selection reveals the matching left card and deselection clears the active interpretation',async()=>{
 const {editor,m,host}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc];editor.selected=null;editor.closedUnits=new Set(['u','v']);editor.render=()=>{};host.querySelector=()=>null;
 let opened,empty=0;m.interpretations={owner:()=> 'actor:material',open:async id=>{opened=id;m.interpretations.active='actor:material:'+id;m.interpretations.draft={unit_id:id};},render:()=>empty++,active:'old'};
 await editor.selectFromInterpretation('v');assert.equal(editor.selected,'v');assert.equal(opened,'v');assert.equal(editor.closedUnits.has('v'),false);
 await editor.selectFromInterpretation('v');assert.equal(editor.selected,null);assert.equal(m.interpretations.active,null);assert.equal(empty,1);
});
test('right-pane selection opens an already selected left card when its interpretation is not displayed',async()=>{
 const {editor,m,host}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc];editor.selected='v';editor.render=()=>{};host.querySelector=()=>null;
 let opened;m.interpretations={owner:()=> 'actor:material',active:null,open:async id=>opened=id};
 await editor.selectFromInterpretation('v');assert.equal(editor.selected,'v');assert.equal(opened,'v');
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
 assert.match(html,/data-preset="not-all"[^>]*disabled/);assert.match(html,/data-rq="quantity-range"[^>]*aria-pressed="false"/);assert.match(html,/data-rq-min[^>]*disabled/);assert.doesNotMatch(html,/>QC</);assert.doesNotMatch(html,/Apply range|quantity-custom/);
});
function quantityFixture(){
 const {editor,m}=fixture();editor.doc=documentFixture();editor.render=()=>{};
 const group={dataset:{owner:'u',field:'conditions',path:''}};
 const inputs=['2','2'].map(value=>({value,dataset:{},setAttribute(){},removeAttribute(){}}));
 const output={},error={hidden:true};
 const row={dataset:{count:'2',current:'2'},closest:()=>group,parentElement:{querySelector:()=>error},querySelectorAll:s=>s==='input'?inputs:[],querySelector:()=>output,contains:node=>inputs.includes(node)};
 editor.bindQuantity(row);return {editor,m,row,inputs,output,error};
}
test('range input previews immediately, rejects non-digits, retains invalid values, and warns before leaving',async()=>{
 const {editor,row,inputs,output,error}=quantityFixture();let sent=0;editor.action=async()=>{sent++;return true;};
 inputs[0].value='0';inputs[0].oninput();assert.equal(output.textContent,'[0, 2]');assert.equal(editor.dirty,true);
 inputs[1].value='99';inputs[1].oninput();assert.equal(inputs[1].value,'99');
 assert.equal(await row.commitQuantity(),false);assert.equal(sent,0);assert.equal(error.hidden,false);
 inputs[1].value='-1';inputs[1].oninput();assert.equal(inputs[1].value,'99');
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

test('one R per source entry and local children never become reference choices',()=>{
 const {editor}=fixture();const d=documentFixture();d.structure_views={u:{id:'ur',kind:'clause',children:[{id:'r',kind:'reference',target_id:'v'}]},v:{id:'vr',kind:'clause',children:[]}};editor.doc=d;editor.sessions=[d];
 assert.equal(editor.entryLabel(d),'R1');assert.equal(editor.label('v'),'G2');assert.deepEqual(editor.completeRequirements('u'),[]);assert.deepEqual(editor.visibleUnitIds(),['u']);
});

test('entry header row toggles disclosure; coloured source is outside that row',()=>{
 const {editor,host}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc];editor.selected='u';editor.notice='';editor.loading=false;editor.m.interpretations=null;
 editor.render(true);assert.match(host.innerHTML,/<button[^>]+data-rq="open-session"[^>]+aria-expanded="true"/);
 assert.match(host.innerHTML,/<div class="rq-session-title" data-entry-source>/);assert.doesNotMatch(host.innerHTML,/<summary data-rq="open-session"/);
 const bar=host.innerHTML.split('<div class="rq-entry-bar"')[1].split('<div class="rq-session-title"')[0];
 assert.match(bar,/data-rq="open-session"/);assert.match(bar,/rq-entry-actions/);assert.doesNotMatch(bar,/rq-source-preview/);
 const dispatched=[];editor.action=async(a)=>dispatched.push(a);
 const click=(action,disabled=false)=>host.onclick({target:{closest:s=>s==='[data-rq]'?{dataset:{rq:action},disabled}:null},stopPropagation(){},preventDefault(){}});
 click('open-session');click('locate-session');click('delete');click('auto-extract',true);
 assert.deepEqual(dispatched,['open-session','locate-session','delete']);
 editor.sessionCollapsed=true;editor.render(true);assert.doesNotMatch(host.innerHTML,/data-entry-source|rq-session-body/);
});

test('entry header has Locate, unavailable Auto-extract, then Remove, no Complete badge or duplicate removal action',()=>{
 const {editor,host}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc];editor.doc.phase='complete';editor.render(true);
 const header=host.innerHTML.split('<span class="rq-entry-actions">')[1].split('</span>')[0];
 assert.ok(header.indexOf('>Locate</button>')<header.indexOf('>Auto-extract</button>'));assert.ok(header.indexOf('>Auto-extract</button>')<header.indexOf('>Remove</button>'));assert.match(header,/data-rq="auto-extract"[^>]*disabled/);assert.doesNotMatch(header,/>Complete</);assert.equal((host.innerHTML.match(/data-rq="delete"/g)||[]).length,1);
});
test('Remove confirms the clicked entry, cancellation writes nothing and unsaved work blocks removal',async()=>{
 const {editor,m}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc,{...documentFixture(),id:'other',revision:8}];let sent,closed=0,markup,bind;
 editor.step=async(action,body)=>{sent={action,body};};m.dialog=(html,callback)=>{markup=html;bind=callback;};
 await editor.action('delete',{dataset:{id:'other'}});assert.equal(sent,undefined);assert.match(markup,/Cancel/);
 const buttons={};bind({querySelector:s=>buttons[s]??=( {} ),close:()=>closed++});buttons['[data-cancel-remove]'].onclick();assert.equal(sent,undefined);assert.equal(closed,1);
 await buttons['[data-remove-entry]'].onclick();assert.deepEqual(sent,{action:'delete',body:{session_id:'other',expected_revision:8}});
 let warned=false;editor.dirty=true;m.unsavedDialog=()=>warned=true;m.dialog=()=>assert.fail('Must warn before confirmation');await editor.action('delete',{dataset:{id:'other'}});assert.equal(warned,true);
});

test('saved work stays quiet while errors and unsaved notices remain visible; history moves to help',()=>{
 const {editor,m,host}=fixture();editor.doc={...documentFixture(),phase:'complete',steps:[{revision:2,action:'save-draft'}]};editor.sessions=[editor.doc];
 editor.render();assert.doesNotMatch(host.innerHTML,/rq-status|Saved step|Splitting complete|History &amp; structured result|rq-history|Field colours/);
 editor.notice='Unsaved changes · save before leaving';editor.render();assert.match(host.innerHTML,/role="status"[^>]*>Unsaved changes/);
 editor.notice='Connection lost';editor.render();assert.match(host.innerHTML,/role="status"[^>]*>Connection lost/);
 let help;m.dialog=html=>{help=html;};editor.showHelp();assert.match(help,/Requirements help/);assert.match(help,/Field colours/);assert.match(help,/Saved history/);assert.match(help,/data-rq="restore"/);assert.doesNotMatch(help,/Earlier inline items retained in history|rq-legacy-relations/);
});

test('Save & close validates all unfinished units and commits exactly once',async()=>{
 const {editor,host,m}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc];editor.selected='u';editor.edits=[{request_id:'edit',action:'assign',unit_id:'u',field:'Subject',start:0,end:4}];editor.dirty=true;editor.baseSession='s';editor.baseRevision=2;editor.doc.done=['u'];
 host.querySelectorAll=()=>[];editor.render=()=>{};const calls=[];
 m.api=async(path,body)=>{calls.push(body);return {document:{...editor.doc,phase:'complete',revision:3,done:['u','v']}};};
 await editor.saveDraft(true);
 assert.equal(calls.length,1);assert.equal(calls[0].action,'save-draft');assert.equal(calls[0].expected_revision,2);
 assert.deepEqual(calls[0].steps.map(s=>s.action),['assign','done','phase']);assert.equal(calls[0].steps[1].unit_id,'v');
 assert.equal(editor.dirty,false);assert.equal(editor.sessionCollapsed,true);
});
test('completion failure leaves original draft, groups and disclosure available',async()=>{
 const {editor,host,m}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc];editor.edits=[{action:'assign',request_id:'edit'}];editor.dirty=true;editor.render=()=>{};host.querySelectorAll=()=>[];
 const before=JSON.stringify(editor.doc),edits=JSON.stringify(editor.edits);let writes=0;
 m.api=async()=>{writes++;throw Object.assign(Error('Choose unresolved quantities before finishing.'),{definitive:true});};
 assert.equal(await editor.saveDraft(true),false);assert.equal(writes,1);assert.equal(JSON.stringify(editor.doc),before);assert.equal(JSON.stringify(editor.edits),edits);assert.equal(editor.dirty,true);assert.equal(editor.sessionCollapsed,false);assert.equal(editor.retryRequest==null,true);
});
test('ordinary Save permits incomplete work and never adds completion steps',async()=>{
 const {editor,host}=fixture();editor.doc=documentFixture();editor.dirty=true;editor.edits=[{action:'structure'}];editor.baseSession='s';editor.baseRevision=2;host.querySelectorAll=()=>[];let sent;
 editor.step=async(a,b)=>{sent={a,b};return true;};await editor.saveDraft();assert.equal(sent.a,'save-draft');assert.deepEqual(sent.b.steps,[{action:'structure'}]);assert.equal(editor.sessionCollapsed,false);
});
test('new unsaved entry completion keeps null saved identity and retains start step',async()=>{
 const {editor,host}=fixture();editor.doc=documentFixture();editor.dirty=true;editor.edits=[{action:'start',request_id:'new'}];editor.baseSession=null;editor.baseRevision=undefined;host.querySelectorAll=()=>[];let sent;
 editor.step=async(a,b)=>sent=b;await editor.saveDraft(true);assert.equal(sent.session_id,null);assert.equal(sent.steps[0].action,'start');assert.equal(sent.steps.at(-1).phase,'complete');
});
test('closing unchanged completed work is display-only and does not create history',async()=>{
 const {editor,host}=fixture();editor.doc={...documentFixture(),phase:'complete',done:['u','v']};editor.render=()=>{};host.querySelectorAll=()=>[];editor.step=()=>assert.fail('No write');editor.selected='u';
 await editor.saveDraft(true);assert.equal(editor.sessionCollapsed,true);assert.equal(editor.selected,null);assert.equal(editor.dirty,false);
});
test('a collapsed entry restores pending range controls before manual saving',async()=>{
 const {editor,host}=fixture();editor.doc=documentFixture();editor.quantityDrafts.set('range',['0','1']);editor.sessionCollapsed=true;let expanded=false,flushed=false;
 editor.render=()=>expanded=!editor.sessionCollapsed;host.querySelectorAll=()=>expanded?[{commitQuantity:async()=>{flushed=true;editor.edits=[{action:'structure'}];editor.quantityDrafts.clear();return true;}}]:[];
 editor.step=async()=>{assert.equal(flushed,true);return true;};await editor.saveDraft();assert.equal(expanded,true);assert.equal(flushed,true);
});
test('discard confirmation affects only current Requirement and can be cancelled',()=>{
 const {editor,m}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc];editor.dirty=true;const handlers={};let closed=0,discarded=0;
 m.dialog=(html,bind)=>{assert.match(html,/Discard changes to R1/);bind({querySelector:s=>handlers[s]??={},close:()=>closed++});};editor.discard=()=>discarded++;
 editor.confirmDiscard();handlers['[data-keep-editing]'].onclick();assert.equal(discarded,0);assert.equal(closed,1);
 handlers['[data-discard-requirement]'].onclick();assert.equal(discarded,1);
});
test('header disclosure never flushes a pending range into a preview',()=>{
 const {editor,host}=fixture();editor.doc=documentFixture();editor.sessions=[editor.doc];editor.render(true);let actions=0;
 host.querySelectorAll=()=>[{commitQuantity:()=>assert.fail('Disclosure must not change data')}];editor.action=async()=>actions++;
 host.onclick({target:{closest:s=>s==='[data-rq]'?{dataset:{rq:'open-session'}}:null},stopPropagation(){},preventDefault(){}});assert.equal(actions,1);
});

test('finishing a newly opened clean entry uses its own saved version, not prior draft state',async()=>{
 const {editor,host}=fixture();editor.doc={...documentFixture(),id:'new-session',revision:8};editor.baseSession='previous-session';editor.baseRevision=3;editor.edits=[];host.querySelectorAll=()=>[];let sent;
 editor.step=async(a,b)=>sent=b;await editor.saveDraft(true);assert.equal(sent.session_id,'new-session');assert.equal(sent.expected_revision,8);
});
test('an uncertain completion save retries its exact atomic request and retains the draft',async()=>{
 const {editor,m,host}=fixture();editor.doc=documentFixture();editor.edits=[{request_id:'edit',action:'assign'}];editor.dirty=true;editor.baseSession='s';editor.baseRevision=2;editor.render=()=>{};host.querySelectorAll=()=>[];let attempted;
 m.api=async(p,b)=>{attempted=b;throw Error('Network interrupted');};await editor.saveDraft(true);assert.equal(editor.dirty,true);assert.equal(editor.sessionCollapsed,false);assert.deepEqual(editor.retryRequest,attempted);
 m.api=async(p,b)=>{assert.deepEqual(b,attempted);return {document:{...editor.doc,revision:3,phase:'complete',done:['u','v']}};};await editor.step('',{},editor.retryRequest);assert.equal(editor.dirty,false);assert.equal(editor.sessionCollapsed,true);assert.equal(editor.selected,null);
});

test('reopening a saved material selects its Requirement for the fourth pane',async()=>{
 const {editor,m}=fixture();m.api=async()=>({sessions:[{id:'saved',units:{u:{text:'Source'}}}],deleted:[]});let args;
 editor.open=async(...values)=>{args=values;};await editor.loadList();assert.deepEqual(args,['saved']);
});

test('annotation navigation preserves the current document and selection when dirty, pending or rejected',async()=>{
 for(const reason of ['dirty','pending','rejected','missing-unit']){
  const {editor,m}=fixture();editor.doc=documentFixture();editor.selected='u';editor.closedUnits.add('v');editor.render=()=>{};let reads=0,sync=0;
  m.unsavedDialog=()=>{};editor.syncInterpretation=()=>sync++;
  if(reason==='dirty')editor.dirty=true;if(reason==='pending')editor.pending=true;
  m.api=async()=>{reads++;if(reason==='rejected')throw Error('Read failed');return {...documentFixture(),id:'other'};};
  await editor.navigateAnnotation([{session_id:'other',unit_id:'missing',field:'Subject'}]);
  assert.equal(editor.doc.id,'s',reason);assert.equal(editor.selected,'u',reason);assert.equal(editor.closedUnits.has('v'),true);assert.equal(sync,0);assert.equal(reads,['dirty','pending'].includes(reason)?0:1);
 }
});
test('an out-of-order annotation read cannot overwrite the later accepted destination',async()=>{
 const {editor,m}=fixture();editor.doc=documentFixture();editor.selected='u';editor.render=()=>{};const resolves={};m.api=p=>new Promise(resolve=>resolves[new URL(p,'http://local').searchParams.get('id')]=resolve);editor.syncInterpretation=()=>{};
 const old=editor.navigateAnnotation([{session_id:'slow',unit_id:'v',field:'Subject'}]),later=editor.open('new','u');
 resolves.new({...documentFixture(),id:'new'});assert.equal(await later,true);resolves.slow({...documentFixture(),id:'slow'});assert.equal(await old,false);assert.equal(editor.doc.id,'new');assert.equal(editor.selected,'u');
});
test('a delayed failed read does not replace the newer destination feedback',async()=>{
 const {editor,m}=fixture();editor.doc=documentFixture();editor.render=()=>{};editor.syncInterpretation=()=>{};let reject;
 m.api=()=>new Promise((_,r)=>reject=r);const read=editor.open('slow');m.api=async()=>({...documentFixture(),id:'fast'});await editor.open('fast');editor.notice='Current message';reject(Error('Old read failure'));await read;assert.equal(editor.doc.id,'fast');assert.equal(editor.notice,'Current message');
});
test('matching candidate source status is read independently of an unrelated stale open entry',async()=>{
 for(const stale of [false,true]){
  const {editor,m}=fixture();editor.doc={...documentFixture(),id:'unrelated',stale:!stale};editor.sessions=[{id:'match',block_id:'b',text:m.draft.blocks[0].text}];editor.render=()=>{};editor.syncInterpretation=()=>{};let starts=0,reads=0;
  m.api=async()=>{reads++;return {...documentFixture(),id:'match',stale};};editor.step=async(action)=>{assert.equal(action,'start');starts++;return true;};
  await editor.start('b');assert.equal(reads,1);assert.equal(starts,stale?1:0);assert.equal(editor.doc.id,stale?'unrelated':'match');
 }
});
test('failed or superseded candidate reads cannot create a duplicate entry',async()=>{
 const {editor,m}=fixture();editor.doc={...documentFixture(),id:'old'};editor.sessions=[{id:'match',block_id:'b',text:m.draft.blocks[0].text}];editor.render=()=>{};editor.step=()=>assert.fail('No start');m.api=async()=>{throw Error('Read failed');};await editor.start('b');assert.equal(editor.doc.id,'old');
 let resolve;m.api=()=>new Promise(r=>resolve=r);const task=editor.start('b');editor.context='changed-material';resolve({...documentFixture(),id:'match',stale:true});assert.equal(await task,false);assert.equal(editor.doc.id,'old');
});
function combinedFixture(blocks){
 const f=fixture();f.m.draft.blocks=blocks;f.editor.render=()=>{};const checks=blocks.map(b=>({dataset:{sourceBlock:b.id},checked:false})),create={},count={},error={};let closed=0;
 const dialog={querySelectorAll:()=>checks,querySelector:s=>s==='[data-create-requirement]'?create:s==='[data-source-count]'?count:error,close:()=>closed++};
 f.m.dialog=(html,bind)=>{assert.match(html,/data-source-count/);bind(dialog);};return {...f,checks,create,count,error,closed:()=>closed};
}
test('combined passage picker retains zero, 101 and 100001-codepoint selections without a request',async()=>{
 for(const scenario of ['empty','count','unicode']){
  const blocks=scenario==='count'?Array.from({length:101},(_,i)=>({id:'b'+i,type:'text',text:'x'})):[{id:'b',type:'text',text:'🐟'.repeat(50000)},{id:'c',type:'text',text:'🐟'.repeat(49999)}];
  const f=combinedFixture(blocks);f.editor.step=()=>assert.fail('Invalid selection must not request preview');await f.editor.start(blocks[0].id,true);
  f.checks.forEach(n=>n.checked=scenario!=='empty');await f.create.onclick();assert.equal(f.error.hidden,false);assert.equal(f.closed(),0);assert.equal(f.checks.filter(n=>n.checked).length,scenario==='empty'?0:blocks.length);
  if(scenario==='unicode')assert.match(f.count.textContent,/100,001/);
 }
});
test('combined picker sends original source-ordered IDs, retains definitive failures and closes for exact Retry',async()=>{
 const f=combinedFixture([{id:'a',type:'text',text:'🐟 A'},{id:'b',type:'text',text:'B'}]);await f.editor.start('a',true);f.checks.reverse().forEach(n=>n.checked=true);let sent;
 f.editor.step=async(a,b)=>{sent=b;f.editor.notice='Rejected original range';return false;};await f.create.onclick();assert.deepEqual(sent.block_ids,['a','b']);assert.equal(f.closed(),0);assert.equal(f.checks.every(n=>n.checked&&!n.disabled),true);assert.match(f.error.textContent,/Rejected/);assert.match(f.count.textContent,/6 \/ 100,000/);
 f.editor.step=async()=>{f.editor.retryRequest={request_id:'exact'};return false;};await f.create.onclick();assert.equal(f.closed(),1);assert.equal(f.editor.retryRequest.request_id,'exact');
});
test('Save & close locates server-defined pending structures after rejection while ordinary Save stays available',async()=>{
 for(const kind of ['empty','quantity','relationship']){
  const {editor,host,m}=fixture();editor.doc=documentFixture();editor.doc.units={u:editor.doc.units.u};editor.doc.roots=[1,'u'];editor.doc.spans={u:[0,16]};editor.render=()=>{};host.querySelectorAll=()=>[];
  const fragment={kind:'fragment',id:'f',role:'Subject',text:'Fish',span:[0,4]};const node={kind:'group',id:'pending',role:'Subject',span:[0,16],quantity:kind==='quantity'?null:1,children:kind==='empty'?[]:[fragment]};if(kind==='relationship')node.relationship={span:[5,10],text:'shall'};
  editor.doc.structures={u:{id:'root',kind:'clause',span:[0,16],children:[node]}};editor.closedUnits.add('u');editor.groupEditor.closed.add('pending');let calls=0;
  m.api=async()=>{calls++;throw Object.assign(Error('The structure is incomplete.'),{definitive:true});};assert.equal(await editor.saveDraft(true),false);assert.equal(calls,1);assert.equal(editor.groupEditor.closed.has('pending'),false);assert.equal(editor.closedUnits.has('u'),false);assert.match(editor.notice,/G\d+:/);
  editor.dirty=true;editor.edits=[{action:'structure'}];let steps;editor.step=async(a,b)=>{steps=b.steps;return true;};await editor.saveDraft();assert.equal(steps.some(s=>s.action==='phase'||s.action==='done'),false);
 }
});
test('an already-open matching candidate still reads authoritative source status before reuse',async()=>{
 const {editor,m}=fixture();editor.doc={...documentFixture(),block_id:'b',text:m.draft.blocks[0].text,stale:false};editor.sessions=[editor.doc];editor.render=()=>{};let reads=0,starts=0;
 m.api=async()=>{reads++;return {...editor.doc,stale:true};};editor.step=async action=>{assert.equal(action,'start');starts++;return true;};
 await editor.start('b');assert.equal(reads,1);assert.equal(starts,1);
});
