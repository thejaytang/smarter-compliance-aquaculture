import test from 'node:test';
import assert from 'node:assert/strict';
import {Collaboration,differenceMarkup,differenceLabel} from '../ui/collaboration.js';
import {relationshipValueMarkup,relationshipEditor,collectRelationshipValue,relationshipOptions} from '../ui/collaboration-relationships.js';

const blocks=()=>[{id:'heading-id',type:'heading',level:1,text:'Measurements'}, {id:'child-id',type:'text',text:'Temperature'}, {id:'later-id',type:'heading',level:1,text:'Later heading'}];
const diff=(kind='parent_id')=>({id:'difference-id',path:`/blocks/child-id/${kind}`,base:null,current:null,incoming:kind==='parent_id'?'heading-id':['heading-id'],conflict:true});

test('each comparison side uses its own exact heading label and retains raw references folded',()=>{
 const d={...diff(),base:'heading-id',current:'heading-id'},before=structuredClone(d),referenceContext={base:{'heading-id':{type:'heading',text:'Old heading'}},current:{'heading-id':{type:'heading',text:'Current heading'}},incoming:{'heading-id':{type:'heading',text:'<Candidate heading>'}}};
 const html=differenceMarkup(d,{referenceContext});
 assert.equal(differenceLabel(d),'Under heading');assert.equal(differenceLabel(diff('dependencies')),'Related content');
 assert.match(html,/Current master<\/small><p>Current heading<\/p>/);
 assert.match(html,/Submitted change<\/small><p>&lt;Candidate heading&gt;<\/p>/);
 assert.match(html,/Shared starting version<\/summary><p>Old heading<\/p>/);
 assert.doesNotMatch(html,/<Candidate heading>|<details open/);assert.match(html,/<summary>Reference details<\/summary>/);assert.match(html,/heading-id/);assert.deepEqual(d,before);
});

test('null missing empty and unavailable references retain different meanings',()=>{
 assert.match(relationshipValueMarkup(null,{kind:'parent_id'}),/Top level/);
 assert.equal(relationshipValueMarkup(null,{kind:'parent_id',present:false}),'<em>Not present</em>');
 assert.match(relationshipValueMarkup([],{kind:'dependencies'}),/No related content/);
 const context={'other':{type:'heading',text:'Do not borrow'}};
 const unknown=relationshipValueMarkup('missing',{kind:'parent_id',context});assert.match(unknown,/heading not found in this version/);assert.doesNotMatch(unknown,/Do not borrow/);
 assert.match(relationshipValueMarkup('__proto__',{kind:'parent_id'}),/not found/);
});

test('whole-block difference relationship values use the supplied side context',()=>{
 const d={...diff(),path:'/blocks/child-id',current:{id:'child-id',parent_id:'heading-id',dependencies:['heading-id']},incoming:null,presence:{incoming:false}};
 const html=differenceMarkup(d,{referenceContext:{current:{'heading-id':{type:'heading',text:'Current heading'}}}});
 assert.match(html,/Under heading/);assert.match(html,/Related content/);assert.match(html,/<p>Current heading<\/p>/);assert.match(html,/Not present/);
});

test('relationship choices use actual preceding headings and write the original IDs',()=>{
 const data=blocks();data[0].text='<Measurements>';const before=structuredClone(data),html=relationshipEditor(diff(),null,data);
 assert.match(html,/<select id="collab-relationship-value"/);assert.match(html,/value="heading-id"/);assert.match(html,/&lt;Measurements&gt;/);assert.doesNotMatch(html,/value="later-id"|<textarea|>heading-id</);
 const input={value:'heading-id'},root={querySelector:()=>input};
 assert.equal(collectRelationshipValue(root,diff(),data),'heading-id');input.value='';assert.equal(collectRelationshipValue(root,diff(),data),null);assert.deepEqual(data,before);
 const headings=[{id:'higher',type:'heading',level:1,text:'Higher'},{id:'same',type:'heading',level:2,text:'Peer'},{id:'child-id',type:'heading',level:2,text:'Child'}];
 assert.deepEqual(relationshipOptions(diff(),headings).map(o=>o.block.id),['higher']);
});

test('dependency multi-selection retains IDs, permits empty, and rejects removed targets',()=>{
 const d=diff('dependencies'),data=blocks(),input={selectedOptions:[{value:'heading-id'},{value:'later-id'}]},root={querySelector:()=>input};
 assert.deepEqual(collectRelationshipValue(root,d,data),['heading-id','later-id']);input.selectedOptions=[];assert.deepEqual(collectRelationshipValue(root,d,data),[]);
 input.selectedOptions=[{value:'gone'}];assert.throws(()=>collectRelationshipValue(root,d,data),/no longer available/);
 assert.match(relationshipEditor(d,['gone'],data),/role="alert"/);assert.match(relationshipEditor(d,['gone'],data),/Referenced content unavailable/);assert.match(relationshipEditor(d,[],data),/Clear related content/);
});

function editFixture(){
 const input={value:'heading-id'},save={disabled:false},error={textContent:''};let closed=0;const calls=[];
 const nodes={'#collab-value-save':save,'#collab-relationship-error':error,'#collab-relationship-value':input};
 const dialog={querySelector:s=>nodes[s]||null,close:()=>closed++};
 const w={busy:false,opening:false,token:{},updateBar(){},dialog(html,wire){this.html=html;wire(dialog);}};
 const c=new Collaboration(w);c.state={mode:'coordinator'};c.merge={merge_id:'merge-id',material:{blocks:blocks()},differences:[diff()]};
 c.showPreview=async r=>{c.merge=r;};w.api=async(path,payload)=>{calls.push({path,payload});return {...c.merge};};
 return {w,c,input,save,error,calls,closed:()=>closed};
}

test('relationship edit sends the selected ID to existing resolve without changing its identity',async()=>{
 const f=editFixture();f.c.editDifference('difference-id');assert.match(f.w.html,/Edit under heading/);await f.save.onclick();
 assert.deepEqual(f.calls,[{path:'/api/collaboration/resolve',payload:{merge_id:'merge-id',decisions:{'difference-id':{action:'edit',value:'heading-id'}}}}]);assert.equal(f.closed(),1);
});

test('missing target, server rejection and busy operation preserve dialog selection',async()=>{
 const missing=editFixture();missing.c.editDifference('difference-id');missing.c.merge.material.blocks.shift();await missing.save.onclick();assert.equal(missing.calls.length,0);assert.equal(missing.closed(),0);assert.equal(missing.input.value,'heading-id');assert.match(missing.error.textContent,/no longer available/);
 const rejected=editFixture();rejected.c.editDifference('difference-id');rejected.w.api=async()=>{throw Error('The selected heading is not in the combined content.');};await rejected.save.onclick();assert.equal(rejected.closed(),0);assert.equal(rejected.input.value,'heading-id');assert.match(rejected.error.textContent,/not in the combined/);assert.equal(rejected.save.disabled,false);
 const busy=editFixture();busy.c.editDifference('difference-id');busy.w.busy=true;await busy.save.onclick();assert.equal(busy.closed(),0);assert.equal(busy.calls.length,0);assert.match(busy.error.textContent,/Wait for/);
});
