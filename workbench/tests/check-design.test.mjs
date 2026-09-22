import test from 'node:test';
import assert from 'node:assert/strict';
import {emptyDesign,setDesign,setHandoff,filterPreview,designMarkup,ruleMarkup,conceptIssues,designNode,ruleValue,bindDesign,setDefinitionMarkup,revealDesign} from '../frontend/components/check-design.js';
test('unmapped groups remain explicit rather than invented filters',()=>{const d=emptyDesign();assert.equal(d.groups.scope,null);assert.match(designMarkup(d),/Empty groups remain unmapped/);assert.doesNotMatch(designMarkup(d),/Satisfied/);});
test('typed comparison inputs reject coercion and preserve lists',()=>{assert.equal(ruleValue('4','integer','greater_or_equal'),4);assert.throws(()=>ruleValue('','integer','equal'));assert.throws(()=>ruleValue('yes','boolean','equal'));assert.deepEqual(ruleValue('north\nsouth','string','in'),['north','south']);assert.equal(ruleValue('','string','is_null'),null);});
test('nested groups retain path ownership and escape source text',()=>{const d=emptyDesign();d.groups.scope={id:'g',condition:'OR',rules:[{id:'a',field:'table.kind',operator:'equal',type:'string',value:'<script>',interpretation_field:'scope'}]};assert.equal(designNode(d,'scope.0').id,'a');const markup=ruleMarkup(d,'scope');assert.match(markup,/any \(OR\)/);assert.match(markup,/&lt;script&gt;/);assert.doesNotMatch(markup,/<script>/);});

test('changing the value type clears obsolete validation errors on the value control',()=>{
 const d=emptyDesign();d.groups.scope={id:'g',condition:'AND',rules:[{id:'r',field:'staff.role',operator:'equal',type:'integer',value:'manager',interpretation_field:'scope'}]};
 const value={value:'manager',dataset:{rdProp:'value'},setCustomValidity(v){this.error=v;}};
 const type={value:'integer',dataset:{rdProp:'type'},setCustomValidity(v){this.error=v;}};
 const controls=[value,type],el={dataset:{rdPath:'scope.0'},querySelector:()=>value,querySelectorAll:()=>controls};controls.forEach(x=>x.closest=()=>el);
 const error={},preview={},host={querySelectorAll:s=>s==='[data-rd-prop]'?controls:[],querySelector:s=>s==='.rd-error'?error:preview};
 bindDesign(host,d,()=>{},()=>{});value.oninput();assert.match(value.error,/valid number/);
 type.value='string';type.oninput();assert.equal(value.error,'');assert.equal(d.groups.scope.rules[0].value,'manager');
});

test('unsupported OR and NOT predicates block the complete filter without dropping meaning',()=>{
 const d=setDesign(),comparison={id:'r',field:'component.kind',type:'string',operator:'equal',value:'chain',interpretation_field:'scope'};
 d.groups.scope={id:'g',condition:'OR',rules:[comparison,{id:'p',expression:'partOf some Anchor Line',interpretation_field:'scope'}]};
 assert.equal(filterPreview(d).scope,null);assert.match(JSON.stringify(d),/partOf some Anchor Line/);
 d.groups.scope.rules=[comparison];d.groups.scope.not=true;assert.equal(filterPreview(d).scope,null);
 d.groups.scope.not=false;assert.equal(filterPreview(d).scope.rules[0].value,'chain');
 d.groups.scope.rules=[];assert.equal(filterPreview(d).scope,null);
 const h=setHandoff({},d);assert.equal(h.sets.B.input,'A');assert.equal(h.sets.B.resolved,false);assert.equal(h.executable,false);
 assert.equal(h.mapping_status,'incomplete');assert.deepEqual(h.composition,{operator:'subset_of',left:'B',right:'C'});
});

test('reading preserves nested OR and group negation, shared concepts and escaped source text',()=>{
 const d=setDesign();d.concepts=[{id:'c',label:'Facility <one>',kind:'concept',status:'proposed',references:[]}];
 d.groups.scope={id:'all',condition:'AND',rules:[{id:'yes',expression:'Facility <one>',concept_ids:['c']},{id:'not',condition:'OR',not:true,rules:[{id:'storm',expression:'Storm',concept_ids:['c']},{id:'quake',expression:'Earthquake'}]}]};
 const before=structuredClone(d),html=setDefinitionMarkup(d,'scope');
 assert.match(html,/A = \{ x \|/);assert.match(html,/AND NOT \(.* OR /);assert.match(html,/Storm/);assert.match(html,/Earthquake/);assert.match(html,/Facility &lt;one&gt;/);assert.match(html,/Unconfirmed/);
 assert.match(html,/“Facility &lt;one&gt;”/);assert.doesNotMatch(html,/\[concepts:/);assert.doesNotMatch(html,/<textarea|<input|<select|<button/);assert.deepEqual(d,before);
});

test('set terms use longest exact labels, preserve quotes, escape HTML and never guess missing concepts',()=>{
 const d=setDesign();d.concepts=['Anchor','Anchor Line','partOf','<img onerror=bad>'].map((label,i)=>({id:String(i),label,kind:'concept',status:'proposed'}));
 d.groups.scope={expression:'"partOf" some “Anchor Line” AND Anchored <img onerror=bad>',concept_ids:['0','1','2','3']};
 const before=structuredClone(d),html=setDefinitionMarkup(d,'scope');
 assert.match(html,/“partOf”/);assert.match(html,/“Anchor Line”/);assert.doesNotMatch(html,/““|””|&quot;“|<img/);assert.match(html,/Anchored/);assert.match(html,/“&lt;img onerror=bad&gt;”/);
 assert.equal((html.match(/“Anchor”/g)||[]).length,0);assert.deepEqual(d,before);
 assert.match(setDefinitionMarkup(d,'condition'),/B = \{ x ∈ A \| Not yet defined/);
 assert.doesNotMatch(setDefinitionMarkup(d,'demand',{value:'Facility'}),/ip-concept-term/);
});

function conceptDesign(){return {schema:'requirement-check-design/2',groups:{scope:{id:'outer',condition:'AND',rules:[{id:'rule',expression:'Facility',interpretation_field:'scope',concept_ids:['old']}]},condition:null,demand:null},concepts:[{id:'old',label:'Facility',kind:'concept',status:'confirmed',references:[{id:'earlier',quote:'Exact old wording'}]},{id:'new',label:'Facility',kind:'property',status:'proposed',references:[]}]};}
function actionFixture(design=conceptDesign(),path='scope.0',fields={}){
 const ui={},choice={value:'new'},node={dataset:{rdPath:path}},concept={dataset:{concept:'old'}},button={dataset:{rd:'link-concept'},closest:s=>s==='[data-concept]'?concept:node,parentElement:{querySelector:()=>choice}},error={};let changes=0,destination;
 const host={querySelectorAll:s=>s==='[data-rd]'?[button]:[],querySelector:()=>error};bindDesign(host,design,()=>changes++,target=>destination=target,{fields:[]},fields,ui);
 return {design,ui,choice,button,error,act(action){button.dataset.rd=action;button.onclick({stopPropagation(){}});},changes:()=>changes,destination:()=>destination};
}
test('range operators enforce two ordered non-boolean endpoints with Python codepoint ordering',()=>{
 for(const [text,type] of [['1\n2\n3','integer'],['5\n1','double'],['true\nfalse','boolean'],['🐟\n\ue000','string']])assert.throws(()=>ruleValue(text,type,'between'),/two ordered/);
 assert.deepEqual(ruleValue('1\n5','integer','not_between'),[1,5]);assert.deepEqual(ruleValue('\ue000\n🐟','string','between'),['\ue000','🐟']);assert.deepEqual(ruleValue('3\n1\n2','integer','in'),[3,1,2]);
});
test('source absence is a status without fabricating a Set predicate',()=>{
 const d=emptyDesign(),f={state:'not_stated',value:'',absence_reason:'No condition is explicitly stated.'},before=structuredClone(f);const html=setDefinitionMarkup(d,'condition',f);
 assert.match(html,/B · Not stated in the source/);assert.doesNotMatch(html,/\{|No condition|B = A/);assert.deepEqual(f,before);assert.match(setDefinitionMarkup(d,'condition',{state:'unresolved'}),/Not yet defined/);
});
test('concept, comparison and link disclosures remain keyed to stable rule IDs after sibling deletion',()=>{
 const d=conceptDesign();d.groups.scope.rules.unshift({id:'before',expression:'Old preceding rule',concept_ids:[]});d.groups.scope.rules[1].expression=undefined;delete d.groups.scope.rules[1].expression;Object.assign(d.groups.scope.rules[1],{field:'x.count',type:'integer',operator:'between',value:[1,2]});
 const before=ruleMarkup(d,'scope');d.groups.scope.rules.shift();const after=ruleMarkup(d,'scope');
 for(const identity of ['concept:rule:old','comparison:rule','link:rule']){assert.ok(before.includes('data-disclosure="'+identity+'"'));assert.ok(after.includes('data-disclosure="'+identity+'"'));}assert.match(after,/data-rd-path="scope.0" data-rd-id="rule"/);
});
test('new rule, group and concept creation provide only the created stable editing destination',()=>{
 for(const action of ['start','add-predicate','add-group','add-concept']){
  const d=conceptDesign(),f=actionFixture(d,action==='add-concept'?'scope.0':'scope');f.act(action);const destination=f.destination();assert.ok(destination.ruleId);assert.equal(f.changes(),1);
  if(action==='add-concept'){assert.equal(destination.ruleId,'rule');assert.equal(d.concepts.at(-1).id,destination.conceptIds[0]);assert.equal(d.concepts.at(-1).label,'New concept');}
  else {const locate=n=>n.id===destination.ruleId?n:(n.rules||[]).map(locate).find(Boolean);assert.equal(locate(d.groups.scope).expression,action==='start'?'':'');}
 }
});
test('card citations merge exact pairs once, keep prior quotations and reject overflow without mutation',()=>{
 const f=actionFixture(conceptDesign(),'scope.0',{scope:{references:[{id:'earlier',quote:'Exact old wording'},{id:'new-source',quote:'New quotation'},{id:'new-source',quote:'New quotation'}]}});f.act('cite-concept');assert.deepEqual(f.design.concepts[0].references,[{id:'earlier',quote:'Exact old wording'},{id:'new-source',quote:'New quotation'}]);f.act('cite-concept');assert.equal(f.changes(),1);
 const full=conceptDesign();full.concepts[0].references=Array.from({length:100},(_,i)=>({id:String(i),quote:'Keep '+i}));const g=actionFixture(full,'scope.0',{scope:{references:[{id:'101',quote:'Extra'}]}});g.act('cite-concept');assert.equal(full.concepts[0].references.length,100);assert.equal(g.changes(),0);assert.match(g.ui.error,/at most 100/);
 const empty=actionFixture();empty.act('cite-concept');assert.equal(empty.design.concepts[0].references[0].quote,'Exact old wording');assert.equal(empty.changes(),0);
});
test('repeated, missing and unavailable concept picks never corrupt the linked ID list',()=>{
 const f=actionFixture();f.act('link-concept');f.act('link-concept');assert.deepEqual(f.design.groups.scope.rules[0].concept_ids,['old','new']);assert.equal(f.changes(),1);f.choice.value='missing';f.act('link-concept');f.choice.value='';f.act('link-concept');assert.equal(f.changes(),1);
});
test('shared concept inputs synchronize by ID while retaining the active caret and distinct same-label concept',()=>{
 const d=conceptDesign();const input=(prop,value)=>({dataset:{conceptProp:prop},value,checked:true,selectionStart:4});const instance=id=>{const controls={label:input('label','Facility'),kind:input('kind','concept'),status:input('status','')},chip={},summary={};const node={dataset:{concept:id},querySelector:s=>s==='.rd-chip'?chip:s==='summary small'?summary:controls[s.match(/"(\w+)"/)[1]]};Object.values(controls).forEach(c=>c.closest=()=>node);return {node,controls};};
 const a=instance('old'),b=instance('old'),other=instance('new'),inputs=[a.controls.label,a.controls.kind,a.controls.status],host={querySelectorAll:s=>s==='[data-concept-prop]'?inputs:s==='[data-concept]'?[a.node,b.node,other.node]:[],querySelector:()=>null};bindDesign(host,d,()=>{},()=>{});
 a.controls.label.value='Salmon facility';a.controls.label.oninput();assert.equal(b.controls.label.value,'Salmon facility');assert.equal(other.controls.label.value,'Facility');assert.equal(a.controls.label.selectionStart,4);assert.equal(b.controls.status.checked,false);a.controls.kind.value='property';a.controls.kind.oninput();assert.equal(b.controls.kind.value,'property');
});
test('invalid comparison text and invalidity are reconstructed on the next binding',()=>{
 const d=conceptDesign(),n=d.groups.scope.rules[0];delete n.expression;Object.assign(n,{field:'x.count',type:'integer',operator:'between',value:[1,2]});const ui={},value={value:'5\n1',dataset:{rdProp:'value'},setCustomValidity(error){this.error=error;}},el={dataset:{rdPath:'scope.0'},querySelector:()=>value,querySelectorAll:()=>[value]};value.closest=()=>el;const host={querySelectorAll:s=>s==='[data-rd-prop]'?[value]:[],querySelector:()=>null};bindDesign(host,d,()=>{},()=>{},{fields:[]},{},ui);value.oninput();assert.equal(ui.values.rule,'5\n1');assert.match(value.error,/two ordered/);assert.match(ruleMarkup(d,'scope','',{fields:[]},{},ui),/>5\n1<\/textarea>/);
 value.error='';bindDesign(host,d,()=>{},()=>{},{fields:[]},{},ui);assert.match(value.error,/two ordered/);value.value='1\n5';value.oninput();assert.equal(value.error,'');assert.deepEqual(n.value,[1,5]);
});
test('quoted navigation retains every associated same-label concept ID without choosing the first meaning',()=>{
 const d=conceptDesign();d.groups.scope.rules[0].concept_ids=['old','new'];const before=structuredClone(d),html=setDefinitionMarkup(d,'scope');assert.match(html,/role="button" tabindex="0"/);assert.match(html,/data-rule-id="rule"/);assert.match(html,/data-concept-nav="\[&quot;old&quot;,&quot;new&quot;\]"/);assert.match(html,/2 linked concepts/);assert.deepEqual(d,before);assert.doesNotMatch(setDefinitionMarkup(d,'scope',{},false),/data-concept-nav/);
});
test('one local removal Undo restores exact OR/NOT structure and pruned evidence, and expires on another edit',()=>{
 const d=conceptDesign();d.groups.scope.rules.push({id:'nested',condition:'OR',not:true,rules:[{id:'p',expression:'Exact extra wording',interpretation_field:'scope',concept_ids:['new']}]});const before=structuredClone(d),f=actionFixture(d,'scope.1');f.act('remove');assert.equal(d.groups.scope.rules.length,1);assert.deepEqual(d.concepts.map(c=>c.id),['old']);assert.equal(f.ui.undo.root,'scope');f.act('undo-remove');assert.deepEqual(d,before);assert.equal(f.ui.undo,null);
 f.act('remove');f.button.closest=()=>({dataset:{rdPath:'scope'}});f.act('add-predicate');assert.equal(f.ui.undo,null);const edited=structuredClone(d);f.act('undo-remove');assert.deepEqual(d,edited);
});

test('concept and rule focus preserves native keyboard tab stops, including read-only summaries',()=>{
 for(const tagName of ['INPUT','TEXTAREA','SUMMARY']){const control={tagName,setAttribute(){assert.fail('Do not remove a natural Tab stop');},scrollIntoView(){},focus(){}},rule={dataset:{rdId:'r'},parentElement:null,querySelectorAll:()=>[],querySelector:()=>control};assert.equal(revealDesign({querySelectorAll:()=>[rule]},'r'),true);}
 let focused=false;const summary={tagName:'SUMMARY',setAttribute(){assert.fail('Preserve native summary');},scrollIntoView(){},focus(){focused=true;}},concept={dataset:{concept:'c'},querySelector:s=>s==='summary'?summary:{disabled:true}},rule={dataset:{rdId:'r'},parentElement:null,querySelectorAll:()=>[concept]};assert.equal(revealDesign({querySelectorAll:()=>[rule]},'r',['c']),true);assert.equal(concept.open,true);assert.equal(focused,true);
});
