import test from 'node:test';
import assert from 'node:assert/strict';
import {StructureEditor,treeNodes,treeText,treeSource} from '../ui/requirement-structure.js';
import {sourceSections} from '../ui/interpretations.js';
import {sourcePreview} from '../ui/requirement-source.js';
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
 assert.match(html,/data-source-node="a"/);assert.match(html,/data-source-node="b"/);
 assert.match(html,/Shared conditions stay in the enclosing Group/);assert.match(html,/data-straction="add-group"/);
 assert.equal((html.match(/data-structure-qc/g)||[]).length,1);assert.match(html,/Show quantity controls/);
 assert.doesNotMatch(editor.toolsMarkup(),/data-field="exceptions"|data-field="subrequirement"/);assert.doesNotMatch(html,/data-straction="not"/);
 assert.match(html,/data-straction="degroup-range"/);assert.match(html,/data-straction="clear-range"/);
 assert.match(html,/<details class="rq-reference-picker">/);
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
 assert.match(sections.scope.value,/G4: Subject/);assert.match(sections.scope.value,/G7: Subject/);
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
 assert.match(explicit,/Group · Object/);assert.match(explicit,/>QC 1/);assert.doesNotMatch(explicit,/data-straction="not"/);
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
