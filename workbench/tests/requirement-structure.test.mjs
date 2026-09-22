import test from 'node:test';
import assert from 'node:assert/strict';
import {StructureEditor,treeNodes,treeText,treeSource,relationshipSides} from '../frontend/components/requirement-structure.js';
import {sourceSections} from '../frontend/components/interpretations.js';
import {sourcePreview} from '../frontend/components/requirement-source.js';
const fragment=(id,role,text,span)=>({id,kind:'fragment',role,text,span});
const group=(id,role,children,quantity=children.length,negated=false)=>({id,kind:'group',role,children,quantity,negated});
const clause=(id,children,span)=>({id,kind:'clause',children,span});
const text='甲 checks A; 乙 checks B after a storm.';
const sample=()=>clause('root',[
 group('shared','conditions',[fragment('storm','conditions','after a storm',[23,36])]),
 group('branches','requirements',[
  clause('a',[group('sa','Subject',[fragment('af','Subject','甲',[0,1])]),group('oa','Object',[fragment('ao','Object','A',[9,10])])],[0,10]),
  clause('b',[group('sb','Subject',[fragment('bf','Subject','乙',[12,13])]),group('ob','Object',[fragment('bo','Object','B',[21,22])])],[12,22])
 ])
],[0,text.length]);
function editorFixture(tree=sample()){
 const e={doc:{structures:{u:tree},units:{u:{id:'u',text}},done:[]},selected:'u',closedUnits:new Set(),locked:false,quantityDrafts:new Map(),label:id=>id==='u'?'R1':id,unitText:id=>id,completeRequirements:()=>[{id:'v',text:'Other requirement'}],m:{},render(){}};
 return {e,editor:new StructureEditor(e),tree};
}
test('clause containers keep bindings; QC belongs only to combinations',()=>{
 const {editor,e}=editorFixture();const html=editor.unitMarkup(e.doc.units.u,false,false);
 assert.match(html,/data-structure-node="a"/);assert.match(html,/data-structure-node="b"/);assert.doesNotMatch(html,/data-source-node="[ab]"/);
 assert.match(html,/Select the original text above/);assert.match(editor.toolsMarkup(),/data-straction="add-group"/);
 assert.equal((html.match(/data-structure-qc/g)||[]).length,1);assert.match(html,/Quantity of direct items/);assert.doesNotMatch(html,/data-straction="show-qc"/);
 assert.doesNotMatch(editor.toolsMarkup(),/data-field="exceptions"|data-field="subrequirement"/);assert.doesNotMatch(html,/data-straction="not"/);
 assert.doesNotMatch(editor.toolsMarkup(),/data-straction="degroup-range"|>Degroup</);assert.doesNotMatch(editor.toolsMarkup(),/data-straction="clear-range"/);
 assert.match(html,/<section class="rq-reference-picker semantic/);
});
test('condition and Subject decomposition expose only their role and Group',()=>{
 const {editor,e,tree}=editorFixture();for(const role of ['conditions','Subject','Object']){
  const n=group('nested',role,[],null);n.span=[0,10];
  const html=editor.sourceMarkup(n,e.doc.units.u,tree,false);
  assert.match(html,new RegExp(`data-field="${role}"`));assert.match(html,/data-straction="add-group"/);
  for(const other of ['conditions','Subject','Object'].filter(f=>f!==role))assert.doesNotMatch(html,new RegExp(`data-field="${other}"`));
 }
});
test('historical NOT survives read-only fourth-pane projection',()=>{
 const tree=sample();tree.children[0].negated=true;
 const sections=sourceSections({requirement:{id:'u',text},structure:tree,sessions:[{units:{u:{id:'u',text}},structures:{u:tree}}]});
 assert.match(sections.condition.value,/NOT \(1 of 1: after a storm\)/);
 assert.match(sections.demand.value,/2 of 2: \{ Subject:.*甲.*Object:.*A.*\| \{ Subject:.*乙.*Object:.*B/);
 const labels=editorFixture(tree).editor.labels(tree);for(const id of ['a','b'])assert.ok(sections.scope.value.includes(labels[id]+': Subject'));
 tree.children[1].quantity=null;assert.equal(sourceSections({requirement:{},structure:tree}).demand.state,'unresolved');
});
test('source colours use exact offsets, escape content and never rewrite original',()=>{
 const text='🐟 A A < B',tree=clause('r',[group('o','Object',[fragment('f','Object','A',[4,5])])],[0,9]);
 const html=treeSource(tree,text);assert.match(html,/🐟 A <span/);assert.match(html,/>A<\/span> &lt; B/);
 const doc={text,units:{u:{text}},spans:{u:[0,9]},structures:{u:tree},field_spans:{u:{Subject:[2,3]}}};
 const preview=sourcePreview(doc);assert.match(preview,/Object/);assert.doesNotMatch(preview,/Subject/);assert.equal(doc.text,text);assert.match(preview,/Object · F1/);assert.doesNotMatch(preview,/Object · f in/);
});
test('selection action sends owner-relative codepoint spans and no invented wording',async()=>{
 const {editor,e}=editorFixture();e.host={querySelectorAll:()=>[]};let sent;e.step=async(action,body)=>{sent={action,body};};
 editor.selection={unit_id:'u',node_id:'root',start:12,end:13};
 await editor.action({dataset:{straction:'add',field:'Subject'},closest:()=>({dataset:{owner:'u',structureNode:'root'}})});
 assert.deepEqual(sent,{action:'structure',body:{unit_id:'u',node_id:'root',operation:'add',field:'Subject',start:12,end:13}});
});
test('recursive reference rendering preserves nested conditions rather than only source text',()=>{
 const child=clause('c',[group('cg','conditions',[fragment('cf','conditions','unless A',[0,8])],1,true)],[0,8]);
 assert.match(treeText({kind:'reference',target_id:'child'},{child:{text:'unless A'}},{child}),/NOT \(1 of 1: unless A\)/);
});

test('one entry root has no second R heading and plain fields have no QC or NOT',()=>{
 const tree=clause('root',[group('subject','Subject',[fragment('sf','Subject','甲',[0,1])]),group('obj','Object',[fragment('of','Object','A',[9,10])])],[0,text.length]);
 const {editor,e}=editorFixture(tree);e.rootIds=()=>['u'];e.internalLabel=()=> 'G1';
 const html=editor.unitMarkup(e.doc.units.u,false,false);
 assert.match(html,/rq-entry-root/);assert.doesNotMatch(html,/>R1<|data-straction="not"|data-structure-qc|>QC /);
 const nested=group('nested','Object',[fragment('of','Object','A',[9,10])]);nested.span=[9,10];
 const explicit=editor.nodeMarkup(nested,e.doc.units.u,tree,editor.labels(tree),false);
 assert.match(explicit,/Group · Object/);assert.match(explicit,/>1<\/span>/);assert.doesNotMatch(explicit,/data-straction="not"/);
});
test('condition NOT and a separate exception clause retain separate scope',()=>{
 const tree=sample();tree.children[0].negated=true;
 tree.children.push(group('exceptions','exceptions',[clause('ex',[group('exs','Subject',[fragment('exf','Subject','乙',[12,13])])],[12,22])]));
 const sections=sourceSections({requirement:{id:'u',text},structure:tree});
 assert.match(sections.condition.value,/NOT.*after a storm/);assert.match(sections.condition.value,/Exception structure \(separate scope\): .*exceptions/);
 assert.match(sections.condition.value,/Subject:.*乙/);
 assert.doesNotMatch(sections.scope.value,/Exception|exceptions/);
});

test('a Group outline keeps the inner field colour when both share the same source span',()=>{
 const tree=clause('root',[group('branch','requirements',[clause('nested',[group('subject','Subject',[fragment('field','Subject','甲',[0,1])])],[0,1])])],[0,1]);
 const html=sourcePreview({text:'甲',units:{u:{text:'甲'}},spans:{u:[0,1]},structures:{u:tree},labels:{u:'R1'}});
 assert.match(html,/Group · G/);assert.match(html,/annotation-outer/);assert.doesNotMatch(html,/semantic-overlap/);
});

test('plain and nested Conditions have no NOT authoring; source negation stays literal',()=>{
 const wording='not installed in the North of Norway';
 const plain=group('c','conditions',[fragment('f','conditions',wording,[0,wording.length])]);
 const nested=group('outer','conditions',[plain]);nested.span=[0,wording.length];
 for(const condition of [plain,nested]){
  const tree=clause('root',[condition],[0,wording.length]);
  const {editor,e}=editorFixture(tree);e.doc.units.u.text=wording;
  const html=editor.unitMarkup(e.doc.units.u,false,false);
  assert.doesNotMatch(html,/data-straction="not"|>NOT</);assert.match(html,/not installed in the North of Norway/);
  const value=sourceSections({requirement:{id:'u',text:wording},structure:tree}).condition.value;
  assert.match(value,/not installed in the North of Norway/);assert.doesNotMatch(value,/NOT \(/);
 }
});
test('retired NOT action cannot modify a draft or reopen a completed entry',async()=>{
 const {editor,e}=editorFixture();e.step=()=>assert.fail('No draft operation expected');
 await assert.rejects(editor.action({dataset:{straction:'not'}}),/Explicit NOT editing is unavailable/);
});

test('range is an explicit exclusive option; selecting it enables bounds without a saved operation',async()=>{
 const {editor,e,tree}=editorFixture();const node=tree.children[1];e.host={querySelector:()=>null,querySelectorAll:()=>[]};e.step=()=>assert.fail('Mode choice must not save');
 let html=editor.qcMarkup(node,false);
 assert.match(html,/data-straction="range-mode" aria-pressed="false"/);assert.match(html,/data-rq-min[^>]*disabled/);assert.doesNotMatch(html,/>QC</);
 await editor.action({dataset:{straction:'range-mode'},closest:()=>({dataset:{owner:'u',structureNode:node.id}})});
 html=editor.qcMarkup(node,false);assert.match(html,/data-straction="range-mode" aria-pressed="true"/);assert.doesNotMatch(html,/data-rq-(min|max)[^>]*disabled/);assert.match(html,/data-preset="all"[^>]*aria-pressed="false"/);
 let sent;e.step=async(a,b)=>{sent=b;};
 await editor.action({dataset:{straction:'preset',preset:'any'},closest:()=>({dataset:{owner:'u',structureNode:node.id}})});
 node.quantity=sent.quantity;html=editor.qcMarkup(node,false);assert.deepEqual(node.quantity,[1,2]);assert.match(html,/data-preset="any"[^>]*aria-pressed="true"/);assert.match(html,/data-rq-max[^>]*disabled/);
 node.quantity=[0,2];editor.rangeModes.clear();assert.match(editor.qcMarkup(node,false),/data-straction="range-mode" aria-pressed="true"/);
 assert.match(editor.qcMarkup(node,true),/data-rq-min[^>]*disabled/);
});
test('reference boundaries and repeated same-field marks keep verb and object source colours',()=>{
 const words='be checked for integrity or replaced';
 const doc={text:words,units:{child:{text:'be checked for integrity'},replacement:{text:'replaced'},parent:{text:words,subrequirement:[1,'child','replacement']}},spans:{parent:[0,36],child:[0,24],replacement:[28,36]},field_spans:{parent:{'Main Verb':[0,10],Object:[11,24]},child:{'Main Verb':[0,10],Object:[11,24]},replacement:{'Main Verb':[0,8]}}};
 const before=JSON.stringify(doc),html=sourcePreview(doc);assert.doesNotMatch(html,/semantic-overlap/);assert.match(html,/semantic-2[^>]*>be checked/);assert.match(html,/semantic-3[^>]*>for integrity/);assert.match(html,/semantic-2[^>]*>replaced/);assert.equal(JSON.stringify(doc),before);
 doc.field_spans.parent.Subject=[0,10];assert.match(sourcePreview(doc),/semantic-overlap/);
});

test('Exception and Subrequirement expose separate other-Requirement link selectors',async()=>{
 const {editor,e,tree}=editorFixture();e.host={querySelectorAll:()=>[]};
 const html=editor.linkMarkup(e.doc.units.u,tree,false);assert.match(html,/aria-label="Exception Requirement"/);assert.match(html,/aria-label="Subrequirement Requirement"/);assert.doesNotMatch(html,/<details|data-straction="add-exception"|data-field="exceptions"/);
 let sent;e.step=async(action,body)=>{sent=body;};
 const link={dataset:{referenceRole:'exceptions'},querySelector:()=>({value:'v'})},node={dataset:{owner:'u',structureNode:'root'}};
 await editor.action({dataset:{straction:'link'},closest:s=>s==='.rq-tree-link'?link:node});assert.equal(sent.field,'exceptions');assert.equal(sent.target_id,'v');
 const ref={kind:'reference',id:'ref',role:'exceptions',target_id:'v'};
 assert.match(editor.nodeMarkup(ref,e.doc.units.u,tree,{},false),/data-rq="select-unit" data-id="v"/);assert.match(editor.nodeMarkup(ref,e.doc.units.u,tree,{},false),/aria-label="Remove link to v"/);
});

test('relation picker has one heading and moves inline decomposition and its quantity to history',()=>{
 const oldRef={kind:'reference',id:'old-ref',role:'subrequirement',target_id:'old'};
 const external={kind:'reference',id:'external-ref',role:'subrequirement',target_id:'v'};
 const relation=group('sub','subrequirement',[oldRef,external],[1,2]);
 const tree=clause('root',[relation],[0,text.length]);
 const {editor,e}=editorFixture(tree);e.doc.units.old={id:'old',text:'Old inline wording'};
 const before=JSON.stringify(e.doc),html=editor.nodeMarkup(relation,e.doc.units.u,tree,editor.labels(tree),false);
 assert.equal((html.match(/<strong>Subrequirement<\/strong>/g)||[]).length,1);
 assert.equal((html.match(/<section class="rq-reference-picker/g)||[]).length,1);
 assert.equal((html.match(/data-structure-reference/g)||[]).length,1);
 assert.doesNotMatch(html,/Old inline wording|Saved decomposition|Earlier inline item ·|data-structure-qc/);
 assert.match(html,/data-id="v"/);assert.match(html,/aria-label="Remove link to v"/);
 const history=editor.historyMarkup();assert.match(history,/Old inline wording/);assert.match(history,/\[1, 2\] of 2/);
 assert.doesNotMatch(history,/data-straction|data-structure-reference/);assert.equal(JSON.stringify(e.doc),before);
 relation.children=[external,{...external,id:'ref2',target_id:'w'}];
 assert.match(editor.nodeMarkup(relation,e.doc.units.u,tree,editor.labels(tree),false),/data-structure-qc/);
});

test('card crosses remain available on completed entries and plain fields have only one',()=>{
 const tree=clause('root',[group('subject','Subject',[fragment('sf','Subject','甲',[0,1])])],[0,text.length]);
 const {editor,e}=editorFixture(tree);e.doc.done=['u'];e.doc.phase='complete';e.rootIds=()=>['u'];
 const html=editor.unitMarkup(e.doc.units.u,true,false);
 assert.equal((html.match(/class="rq-node-remove"/g)||[]).length,1);assert.match(html,/data-structure-node="subject"/);
 e.locked=true;assert.doesNotMatch(editor.unitMarkup(e.doc.units.u,true,false),/rq-node-remove/);
});
test('removing a completed Group reopens only the draft then removes the whole node',async()=>{
 const {editor,e}=editorFixture();e.doc.phase='complete';e.host={querySelectorAll:()=>[]};const calls=[];e.step=async(a,b)=>{calls.push({a,b});return true;};
 await editor.action({dataset:{straction:'remove'},closest:()=>({dataset:{owner:'u',structureNode:'a'}})});
 assert.deepEqual(calls,[{a:'phase',b:{phase:'fields'}},{a:'structure',b:{unit_id:'u',node_id:'a',operation:'remove'}}]);
});

test('nested Subrequirement links keep separate quantities and per-link removal cards',()=>{
 const ref=(id,target)=>({id,kind:'reference',role:'subrequirement',target_id:target});
 const tree=clause('root',[group('subs','subrequirement',[group('choices','subrequirement',[ref('a','v'),ref('b','w')],[1,2]),ref('c','x')],2)],[0,text.length]);
 const {editor,e}=editorFixture(tree);e.label=id=>({v:'R2',w:'R3',x:'R4'}[id]||id);e.completeRequirements=()=>[{id:'v',text:'First source'},{id:'w',text:'Second source'},{id:'x',text:'Third source'}];
 const html=editor.nodeMarkup(tree.children[0],e.doc.units.u,tree,editor.labels(tree),true);
 assert.equal((html.match(/data-structure-qc/g)||[]).length,2);assert.equal((html.match(/rq-tree-children rq-linked-list/g)||[]).length,2);
 for(const label of ['R2','R3','R4'])assert.match(html,new RegExp('aria-label="Remove link to '+label+'"'));
 assert.match(html,/>First source</);assert.match(html,/data-straction="group"/);assert.doesNotMatch(html,/data-straction="ungroup"/);assert.doesNotMatch(html,/>Unlink</);
 e.locked=true;const locked=editor.nodeMarkup(tree.children[0],e.doc.units.u,tree,editor.labels(tree),true);assert.doesNotMatch(locked,/Remove link to|data-structure-pick|data-straction="group"/);
});
test('a link-card cross removes only its reference node and stays an unsaved structure action',async()=>{
 const ref={id:'link',kind:'reference',role:'subrequirement',target_id:'v'},tree=clause('root',[group('subs','subrequirement',[ref],1)],[0,text.length]);
 const {editor,e}=editorFixture(tree);e.doc.phase='complete';e.host={querySelectorAll:()=>[]};const calls=[];e.step=async(a,b)=>{calls.push({a,b});return true;};
 await editor.action({dataset:{straction:'remove'},closest:()=>({dataset:{owner:'u',structureNode:'link'}})});
 assert.deepEqual(calls,[{a:'phase',b:{phase:'fields'}},{a:'structure',b:{unit_id:'u',node_id:'link',operation:'remove'}}]);assert.equal(ref.target_id,'v');
});

function relationshipFixture(){
 const wording='A including B and C';
 const before=clause('before',[group('subject','Subject',[fragment('a','Subject','A',[0,1])])],[0,1]);
 const after=group('objects','Object',[fragment('b','Object','B',[12,13]),fragment('c','Object','C',[18,19])],2);
 const owner=clause('owner',[after,group('binding','requirements',[before],1)],[0,19]);
 owner.relationship={text:'including',span:[2,11]};
 const tree=clause('root',[group('outer','requirements',[owner],1)],[0,19]);
 const fixture=editorFixture(tree);fixture.e.doc.units.u.text=wording;fixture.e.doc.text=wording;fixture.e.doc.spans={u:[0,19]};fixture.e.rootIds=()=>['u'];
 return {...fixture,wording,owner,after};
}
test('relationship is between its source-ordered operands, outside quantity children',()=>{
 const {editor,e,owner,after}=relationshipFixture();const before=JSON.stringify(e.doc);
 const sides=relationshipSides(owner);assert.equal(sides.before[0].id,'binding');assert.equal(sides.after[0].id,'objects');
 const html=editor.unitMarkup(e.doc.units.u,false,false);
 assert.equal((html.match(/data-structure-qc/g)||[]).length,1);
 assert.equal(after.children.length,2);assert.equal(after.quantity,2);
 assert.ok(html.indexOf('data-structure-node="before"')<html.indexOf('class="rq-relationship-row"'));
 assert.ok(html.indexOf('class="rq-relationship-row"')<html.indexOf('data-structure-node="objects"'));
 assert.doesNotMatch(html,/data-structure-node="outer"|data-structure-node="binding"/);
 assert.match(html,/aria-label="Remove relationship"/);assert.equal(JSON.stringify(e.doc),before);
});
test('relationship has exact source colour, including in collapsed text and fourth-pane source structure',()=>{
 const {tree,e,wording,owner,editor}=relationshipFixture();
 const preview=sourcePreview(e.doc);assert.match(preview,/semantic-7[^>]*>including</);assert.match(preview,/relationship · G/);
 assert.match(treeSource(tree,wording),/semantic-7[^>]*>including</);
 const sections=sourceSections({requirement:e.doc.units.u,structure:tree});assert.match(sections.demand.value,/relationship: including/);assert.match(sections.demand.value,/2 of 2: B \| C/);
 assert.ok(sections.scope.value.startsWith(editor.labels(tree).before+': '));assert.match(sections.demand.value,/Source Groups:/);
 const historical=group('saved','conditions',[fragment('a','conditions','A',[0,1]),fragment('b','conditions','B',[12,13])],2,true);
 historical.span=[0,13];historical.relationship={text:'including',span:[2,11]};assert.match(treeText(historical),/^NOT \{.*quantity: 2 of 2/);
 owner.children=owner.children.filter(n=>n.id!=='objects');
 assert.equal(sourceSections({requirement:e.doc.units.u,structure:tree}).demand.state,'unresolved');
});
test('relationship annotation and removal remain explicit unsaved source operations',async()=>{
 const {editor,e,owner}=relationshipFixture();e.host={querySelectorAll:()=>[]};const calls=[];e.step=async(a,b)=>{calls.push({a,b});return true;};
 editor.selection={unit_id:'u',node_id:owner.id,start:2,end:11};
 await editor.action({dataset:{straction:'relationship'},closest:()=>null});
 assert.equal(calls[0].b.operation,'relationship');assert.equal(calls[0].b.start,2);assert.equal(calls[0].b.end,11);assert.equal(calls[0].b.text,undefined);
 await editor.action({dataset:{straction:'remove-relationship'},closest:()=>({dataset:{owner:'u',structureNode:owner.id}})});
 assert.deepEqual(calls[1],{a:'structure',b:{unit_id:'u',node_id:owner.id,operation:'remove-relationship'}});
});

test('completed and unfinished entries share enabled editing controls without phase buttons',()=>{
 const {editor,e}=editorFixture();e.rootIds=()=>['u'];const normal=editor.unitMarkup(e.doc.units.u,false,false);
 e.doc.phase='complete';e.doc.done=['u'];const saved=editor.unitMarkup(e.doc.units.u,true,false);
 assert.equal(saved,normal);assert.match(saved,/>Split<\/button>/);assert.doesNotMatch(saved,/Resume editing|Finish|Continue decomposing/);
 assert.doesNotMatch(saved,/data-source-node=/);assert.match(saved,/data-straction="group" disabled/);
});
test('quantity editing reopens a completed draft through the same path as all structure actions',async()=>{
 const {editor,e}=editorFixture();e.doc.phase='complete';const calls=[];e.step=async(action,body)=>{calls.push({action,body});return true;};
 await editor.apply({unit_id:'u',node_id:'branches',operation:'quantity',quantity:[1,2]});
 assert.deepEqual(calls.map(c=>c.action),['phase','structure']);assert.deepEqual(calls[1].body.quantity,[1,2]);
 calls.length=0;e.step=async()=>false;assert.equal(await editor.apply({unit_id:'u'}),false);
});
test('Ungroup appears only where it can preserve both quantities and any connector',()=>{
 const {editor}=editorFixture();const child=group('child','Object',[fragment('a','Object','A',[0,1]),fragment('b','Object','B',[2,3])],2),parent=group('parent','Object',[child],1),tree=clause('root',[parent]);
 assert.equal(editor.canUngroup(child,tree),true);child.quantity=[1,2];assert.equal(editor.canUngroup(child,tree),false);
 child.quantity=2;parent.relationship={text:'including',span:[1,2]};assert.equal(editor.canUngroup(child,tree),false);delete parent.relationship;parent.negated=true;assert.equal(editor.canUngroup(child,tree),false);
});
test('toolbar honours same-field nesting and root versus Group relationship eligibility',()=>{
 const {editor,tree}=editorFixture();const buttons=['Subject','Object','conditions'].map(field=>({dataset:{field},hidden:false})),relation={};const bar={querySelectorAll:()=>buttons,querySelector:()=>relation};
 editor.updateSelectionTools(bar,'u',{kind:'group',role:'conditions',id:'c',span:[0,10]});assert.deepEqual(buttons.map(b=>b.hidden),[true,true,false]);assert.equal(relation.disabled,false);
 editor.updateSelectionTools(bar,'u',tree);assert.deepEqual(buttons.map(b=>b.hidden),[false,false,false]);assert.equal(relation.disabled,true);
});
test('nested link disclosure is local presentation and does not reopen saved work',async()=>{
 const {editor,e}=editorFixture();e.doc.phase='complete';e.step=()=>assert.fail('No data step for disclosure');let renders=0;e.render=()=>renders++;
 const button={dataset:{straction:'show-link'},closest:()=>({dataset:{owner:'u',structureNode:'a'}})};
 await editor.action(button);assert.equal(editor.linkOpen.has('a'),true);await editor.action(button);assert.equal(editor.linkOpen.has('a'),false);assert.equal(renders,2);
});

test('Split keeps one visible same-field Group without rewriting its implicit wrapper',()=>{
 const child=group('split','Object',[],null);child.span=[0,10];const wrapper=group('holder','Object',[child],1),tree=clause('root',[wrapper],[0,text.length]);
 const {editor,e}=editorFixture(tree);const before=JSON.stringify(tree),html=editor.nodeMarkup(tree,e.doc.units.u,tree,editor.labels(tree),false,true);
 assert.doesNotMatch(html,/data-structure-node="holder"/);assert.match(html,/data-structure-node="split"/);assert.doesNotMatch(html,/data-straction="group"/);assert.equal(JSON.stringify(tree),before);
 wrapper.quantity=[0,1];assert.match(editor.nodeMarkup(tree,e.doc.units.u,tree,editor.labels(tree),false,true),/data-structure-node="holder"/);
});

test('Group MIN–MAX keeps invalid and two-digit human input until explicitly corrected',async()=>{
 const {editor,e,tree}=editorFixture();const model=tree.children[1];const inputs=['1','2'].map(value=>({value,dataset:{},setAttribute(k,v){this[k]=v;},removeAttribute(k){delete this[k];}})),error={hidden:true},output={},node={dataset:{owner:'u',structureNode:model.id}};
 const row={closest:()=>node,querySelector:s=>s==='[data-rq-min]'?inputs[0]:s==='[data-rq-max]'?inputs[1]:output,parentElement:{querySelector:()=>error}};let calls=0;editor.apply=async()=>{calls++;return true;};editor.bindQC(row);
 inputs[1].value='99';inputs[1].oninput();assert.equal(inputs[1].value,'99');assert.equal(inputs[1]['aria-invalid'],'true');assert.equal(await row.commitQuantity(),false);assert.equal(calls,0);assert.deepEqual(e.quantityDrafts.get('tree:u:branches'),['1','99']);
 inputs[1].value='2';inputs[1].oninput();assert.equal(await row.commitQuantity(),true);assert.equal(calls,1);assert.equal(error.hidden,true);
 model.children=Array.from({length:10},(_,i)=>fragment('f'+i,'Object','x',[i,i+1]));editor.bindQC(row);inputs[1].value='1';inputs[1].oninput();inputs[1].value='10';inputs[1].oninput();assert.equal(inputs[1].value,'10');assert.equal(error.hidden,true);
});
test('checked siblings survive presentation redraw and grouping uses original direct-child order',async()=>{
 const {editor,e,tree}=editorFixture();const node=tree.children[1];node.children.push(clause('c',[],[25,30]));e.host={querySelectorAll:()=>[],querySelector:()=>null};editor.picks.set(editor.pickKey('u',node.id),new Set(['c','a']));let sent;e.step=async(a,b)=>{sent=b;return true;};
 const button=action=>({dataset:{straction:action},closest:()=>({dataset:{owner:'u',structureNode:node.id}})});
 await editor.action(button('range-mode'));await editor.action(button('show-link'));const html=editor.nodeMarkup(node,e.doc.units.u,tree,editor.labels(tree),false);
 assert.match(html,/data-structure-pick="a"[^>]*checked/);assert.match(html,/data-structure-pick="c"[^>]*checked/);assert.doesNotMatch(html,/data-structure-pick="b"[^>]*checked/);assert.match(html,/Group selected \(2\)/);assert.equal(sent,undefined);
 await editor.action(button('group'));assert.deepEqual(sent.selected,['a','c']);node.children=node.children.filter(n=>n.id!=='a');editor.prunePicks();assert.deepEqual(editor.picked('u',node),['c']);editor.reset();assert.deepEqual(editor.picked('u',node),[]);
});
test('failed removal retains target quantity drafts; successful removal clears only removed descendants',async()=>{
 for(const outcome of ['invalid-other','rejected','uncertain','success']){
  const {editor,e}=editorFixture();e.quantityDrafts.set('tree:u:a',['0','1']);e.quantityDrafts.set('tree:u:sa',['0','1']);e.quantityDrafts.set('tree:u:branches',['0','99']);let sent=0;
  e.host={querySelectorAll:()=>[{commitQuantity:async()=>outcome!=='invalid-other'}]};editor.apply=async()=>{sent++;if(outcome==='uncertain')e.retryRequest={};return outcome==='success';};
  await editor.action({dataset:{straction:'remove'},closest:()=>({dataset:{owner:'u',structureNode:'a'},contains:()=>false})});
  assert.equal(e.quantityDrafts.has('tree:u:a'),outcome!=='success',outcome);assert.equal(e.quantityDrafts.has('tree:u:sa'),outcome!=='success',outcome);assert.deepEqual(e.quantityDrafts.get('tree:u:branches'),['0','99']);assert.equal(sent,outcome==='invalid-other'?0:1);
 }
});
test('annotation reveal focuses exact stable nested node and connector, leaving unrelated Groups closed',()=>{
 const {editor,e}=relationshipFixture();let focused,scrolled;const target=id=>({dataset:{owner:'u',structureNode:id},setAttribute(){},scrollIntoView(){scrolled=id;},focus(){focused=id;},querySelector:()=>target('relationship-row')});
 e.host={querySelectorAll:()=>[target('owner'),target('c')]};editor.closed=new Set(['owner','objects','unrelated']);e.closedUnits.add('u');e.showError=err=>e.notice=err.message;
 assert.equal(editor.reveal('u','c'),true);assert.equal(focused,'c');assert.equal(scrolled,'c');assert.equal(editor.closed.has('unrelated'),true);assert.equal(editor.closed.has('objects'),false);
 assert.equal(editor.reveal('u','owner','relationship'),true);assert.equal(focused,'relationship-row');assert.equal(editor.reveal('u','stale'),false);assert.match(e.notice,/no longer be located/);
});
test('link picker shows full literal source wording and clears it before any Link action',()=>{
 const {editor,e}=editorFixture();const prefix='Identical '.repeat(15),targets=[{id:'v',text:prefix+'first <script>alert(1)</script>'},{id:'w',text:prefix+'second exact source'}];e.completeRequirements=()=>targets;const preview={},linkButton={},link={querySelector:s=>s==='[data-reference-preview]'?preview:linkButton};const select={value:'v',closest:s=>s==='.rq-tree-link'?link:{dataset:{owner:'u'}}};const host={querySelectorAll:s=>s==='[data-structure-reference]'?[select]:[]};editor.bind(host);
 select.onchange();assert.equal(preview.textContent,'v · v\n'+targets[0].text);assert.equal(preview.hidden,false);assert.equal(linkButton.disabled,false);select.value='w';select.onchange();assert.match(preview.textContent,/second exact source$/);select.value='';select.onchange();assert.equal(preview.textContent,'');assert.equal(preview.hidden,true);assert.equal(linkButton.disabled,true);
 const html=editor.linkMarkup(e.doc.units.u,editor.tree('u'));assert.match(html,/aria-describedby="rq-link-u-root/);assert.doesNotMatch(html,/<script>/);
});
test('definitively rejected source annotation retains exact range; source change invalidates it and uncertain results stay locked',async()=>{
 for(const outcome of ['rejected','changed','uncertain','success']){
  const {editor,e}=editorFixture();e.doc.units.u.text='🐟 exact words';e.host={querySelectorAll:()=>[]};editor.selection={unit_id:'u',node_id:'root',start:2,end:7};
  editor.apply=async()=>{if(outcome==='changed')e.doc.units.u.text='Changed source';if(outcome==='uncertain'){e.retryRequest={request_id:'exact'};e.locked=true;}return outcome==='success';};
  await editor.action({dataset:{straction:'add',field:'Object'},closest:()=>null});
  if(['changed','success'].includes(outcome))assert.equal(editor.selection,null);else{assert.deepEqual(editor.selection,{unit_id:'u',node_id:'root',start:2,end:7});assert.equal(editor.selectionValid(),true);}
  if(outcome==='uncertain')assert.equal(e.locked,true);
 }
});
test('ordinary binding does not restore an earlier rejected range or steal quantity focus',()=>{
 const {editor}=editorFixture();editor.selection={unit_id:'u',node_id:'root',start:0,end:1};editor.selectionContext=editor.selectionStamp();editor.restoreSelection=()=>assert.fail('Only a rejected action may restore the range');editor.bind({querySelectorAll:()=>[]});
});

test('source toolbar follows viewport changes and disappears when its original selection leaves view',()=>{const {editor,e}=editorFixture(),prior=globalThis.window,listeners=new Map();globalThis.window={innerWidth:1200,innerHeight:800,addEventListener:(key,fn)=>listeners.set(key,fn),removeEventListener:key=>listeners.delete(key)};const bar={isConnected:true,hidden:false,style:{},offsetWidth:320,offsetHeight:90},source={isConnected:true,closest:()=>({getBoundingClientRect:()=>({left:0,right:1200,top:0,bottom:700})})};let rect={left:880,right:990,top:300,bottom:320};const range={cloneRange(){return this;},getBoundingClientRect:()=>rect};const before=JSON.stringify(e.doc);editor.selectionValid=()=>true;try{editor.trackSelection({},source,bar,range);assert.equal(bar.style.left,'872px');window.innerWidth=500;rect={left:350,right:420,top:300,bottom:320};listeners.get('resize')();assert.equal(bar.style.left,'172px');assert.equal(bar.hidden,false);rect={left:40,right:90,top:300,bottom:320};editor.trackSelection({},source,bar,range);rect={left:40,right:90,top:-200,bottom:-50};listeners.get('scroll')();assert.equal(bar.hidden,true);assert.equal(listeners.size,0);assert.equal(JSON.stringify(e.doc),before);}finally{editor.stopSelectionTracking();globalThis.window=prior;}});
test('source toolbar Escape restores source focus and removes placement listeners without an edit',()=>{const {editor,e}=editorFixture(),bar={hidden:false},host={querySelectorAll:()=>[]};editor.bind(host);host.querySelectorAll=()=>[bar];const source={focus(){this.focused=true;}};editor.selectionSource=source;let removed=false;editor.selectionTracking=()=>removed=true;host.onkeydown({key:'Escape',target:{closest:()=>bar},preventDefault(){}});assert.equal(source.focused,true);assert.equal(bar.hidden,true);assert.equal(removed,true);assert.equal(editor.selectionSource,null);});
