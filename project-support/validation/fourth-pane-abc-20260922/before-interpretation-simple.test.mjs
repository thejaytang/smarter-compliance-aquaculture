import test from 'node:test';
import assert from 'node:assert/strict';
import {setDesign} from '../frontend/components/check-design.js';
import {InterpretationEditor,sourceSections,interpretationKeys,cardApproved} from '../frontend/components/interpretations.js';
const field=value=>({value,basis:'interpretation',references:[],gaps:[]});
function fixture(){const m={id:'m',state:{actor:{id:'a'}},collaboration:{readonly:false},requirements:{selected:'u',label:()=> 'R1'},q:()=>null};const e=new InterpretationEditor(m);e.active=e.key('u');e.drafts.set(e.active,{unit_id:'u',revision:1,fields:Object.fromEntries(interpretationKeys.map(k=>[k,field('manual '+k)])),context:{fingerprint:'fp',requirement:{id:'u',Subject:'Fish'},sessions:[],materials:[]},provider:{available:true},linked_material_ids:[]});e.render=()=>{};return {e,m,d:e.draft};}
test('source projection preserves exact ranges, branches and exceptions without a verdict',()=>{
 const sections=sourceSections({requirement:{id:'r',Subject:'The human','Modal Verb':'shall','Main Verb':'remove',Object:'fish',conditions:[[1,2],'a',[2,'b','c']],exceptions:[1,'e'],subrequirement:[[2,3],'a','b','c','e']},sessions:[{units:{a:{text:'red'},b:{text:'hot'},c:{text:'sick'},e:{text:'small fish'}}}]});
 assert.equal(sections.scope.value,'The human');assert.match(sections.condition.value,/1–2 of 2/);assert.match(sections.condition.value,/Exactly 2 of 2/);assert.match(sections.condition.value,/Exceptions: Exactly 1 of 1/);assert.match(sections.demand.value,/2–3 of 4/);assert.doesNotMatch(JSON.stringify(sections),/Satisfied|within.*day/);
});
test('logic candidate stays separate until Accept, which uses edited candidate text',async()=>{
 const {e,m,d}=fixture();d.logicCandidates={verification:{status:'ready',context_fingerprint:'fp',value:'edited candidate',suggestion:field('AI original')}};
 await e.action('accept-logic',{closest:()=>({dataset:{ipField:'verification'}})});
 assert.equal(d.fields.verification.value,'edited candidate');assert.equal(d.logicCandidates.verification,undefined);assert.equal(d.dirty,true);
});
test('generation response does not overwrite edits made while waiting',async()=>{
 const {e,m,d}=fixture();const c={status:'generating',value:'human typed while waiting',edited:true};d.logicCandidates={verification:c};m.api=async()=>({status:'ready',context_fingerprint:'fp',suggestions:{verification:field('AI result')}});
 await e.watchLogic('run',e.active,'verification',c);assert.equal(c.value,'human typed while waiting');assert.equal(c.suggestion.value,'AI result');assert.equal(d.fields.verification.value,'manual verification');assert.equal(c.status,'ready');
});
test('save excludes unaccepted candidates and preserves edits during a save',async()=>{
 const {e,m,d}=fixture();d.logicCandidates={verification:{status:'ready',value:'candidate'}};
 await assert.rejects(e.save('save',{}),/Accept/);d.logicCandidates={};
 m.api=async(path,body)=>{if(body){d.fields.verification.value='newer edit';d.changeNumber=1;return {draft_revision:0};}return {...d,revision:2,fields:{...d.fields,verification:field('saved old edit')}};};
 await e.save('save',{});assert.equal(e.draft.fields.verification.value,'newer edit');assert.equal(e.draft.revision,2);assert.equal(e.draft.dirty,true);
});
test('save uses the committed response without requesting a second document',async()=>{
 const {e,m,d}=fixture();let calls=0;
 m.api=async(path,body)=>{calls++;assert.ok(body);assert.equal(path,'/api/interpretations/save');return {status:'saved',revision:2,document:{...d,revision:2}};};
 await e.save('save',{});assert.equal(calls,1);assert.equal(e.draft.revision,2);assert.equal(e.draft.dirty,false);
});
test('interpreted facility and measurement constraints survive save without replacing third-pane wording',async()=>{
 const {e,m,d}=fixture();d.context.requirement.Subject='Seawater temperature';
 d.fields.scope=field('The facility identified by the surrounding source context');
 d.fields.demand=field('Measure seawater temperature at a depth of three metres at least once every week');
 d.logicCandidates={scope:{status:'ready',value:'Unaccepted alternate scope'}};
 assert.match(e.editorMarkup(d),/Seawater temperature/);assert.match(e.editorMarkup(d),/The facility identified/);
 delete d.logicCandidates.scope;
 m.api=async(path,body)=>{assert.equal(body.fields.scope.value,d.fields.scope.value);assert.equal(body.fields.demand.value,d.fields.demand.value);assert.equal(body.check_design.schema,'requirement-check-design/2');return {status:'saved',document:{...d,revision:2}};};
 await e.save('save',{});assert.equal(e.draft.fields.scope.value,'The facility identified by the surrounding source context');
 assert.equal(e.draft.context.requirement.Subject,'Seawater temperature');
});
test('committed response retains newer edits made while saving',async()=>{
 const {e,m,d}=fixture();let calls=0;
 m.api=async()=>{calls++;const saved=structuredClone(d);d.fields.verification.value='typed during save';d.changeNumber=1;return {status:'saved',revision:2,document:{...saved,revision:2}};};
 await e.save('save',{});assert.equal(calls,1);assert.equal(e.draft.fields.verification.value,'typed during save');assert.equal(e.draft.revision,2);assert.equal(e.draft.dirty,true);
});
test('logic text areas remain editable in pending and generating states',()=>{
 const {e,d}=fixture();e.editing=e.active;e.pending=true;d.generation={status:'running'};
 const html=e.editorMarkup(d);assert.match(html,/Generating/);assert.doesNotMatch(html,/<textarea[^>]*(disabled|readonly)/);assert.doesNotMatch(html,/Source status|Not explicitly stated|Generate six suggestions/);
});

test('stale AI candidates cannot be accepted into a changed source context',async()=>{
 const {e,d}=fixture();d.logicCandidates={verification:{status:'ready',context_fingerprint:'old',value:'old candidate',suggestion:field('old')}};
 await assert.rejects(e.action('accept-logic',{closest:()=>({dataset:{ipField:'verification'}})}),/older source/);assert.equal(d.fields.verification.value,'manual verification');
});
test('generation failure preserves manual text and restores an earlier candidate on regeneration failure',async()=>{
 const {e,m,d}=fixture();const previous={status:'ready',value:'edited prior candidate',suggestion:field('prior')};d.logicCandidates={verification:previous};m.api=async()=>{throw Error('timeout');};
 await e.suggestLogic('verification');assert.equal(d.logicCandidates.verification,previous);assert.equal(d.fields.verification.value,'manual verification');
});
test('retry of an uncertain save preserves edits made after its original snapshot',async()=>{
 const {e,m,d}=fixture();m.api=async()=>{throw Error('Connection lost');};await e.save('save',{});assert.ok(d.retry);
 d.fields.verification.value='typed after uncertain save';d.changeNumber=1;d.dirty=true;
 m.api=async(path,body)=>body?{}:{...d,revision:2,fields:{...d.fields,verification:field('old saved value')}};
 await e.save('retry',{});assert.equal(e.draft.fields.verification.value,'typed after uncertain save');assert.equal(e.draft.dirty,true);assert.equal(e.draft.revision,2);
});

 test('missing current context on an older source retains saved text without breaking material navigation',()=>{
 const {e,m,d}=fixture();delete d.context;d.stale=true;d.context_error='Source content changed; saved session is read-only.';
 const projected=sourceSections(undefined);assert.ok(Object.values(projected).every(x=>x.state==='unresolved'&&x.value===''));
 const host={innerHTML:'',querySelectorAll:()=>[]};m.q=()=>host;m.requirements.orderedSessions=()=>[{id:'s',text:'Original',units:{u:{id:'u',text:'Original'}}}];
 InterpretationEditor.prototype.render.call(e);assert.match(host.innerHTML,/Source content changed/);assert.match(host.innerHTML,/manual verification/);assert.doesNotMatch(host.innerHTML,/reading .structure/);
 // Opening another material must be able to render even while the old draft is retained.
 m.id='new-material';assert.doesNotThrow(()=>InterpretationEditor.prototype.render.call(e));assert.doesNotMatch(host.innerHTML,/manual verification/);
 });
test('three cards accept structured candidates independently, preserve explanations and reject stale adoption',async()=>{
 const {e,d}=fixture();d.check_design=setDesign();d.check_design.groups.demand={id:'human',condition:'AND',rules:[{id:'human-rule',expression:'Human demand',interpretation_field:'demand'}]};
 const untouched=structuredClone(d.fields.demand),group=structuredClone(d.check_design.groups.demand);
 d.candidate={context_fingerprint:d.context.fingerprint,suggestions:{scope:field('Candidate scope'),scope_information:field('Candidate information')},check_design:{...setDesign(),concepts:[{id:'facility',label:'Facility',kind:'concept',status:'proposed',references:[]}],groups:{scope:{id:'ai-s',condition:'AND',rules:[{id:'ai-r',expression:'Facility with salmonids',interpretation_field:'scope',concept_ids:['facility']}]},condition:null,demand:null}}};
 await e.action('accept-card',{dataset:{field:'scope'},closest:()=>null});assert.deepEqual(d.fields.demand,untouched);assert.deepEqual(d.check_design.groups.demand,group);assert.equal(d.fields.scope.value,'Candidate scope');assert.equal(d.check_design.concepts.length,1);assert.equal(d.check_design.concepts[0].id,d.check_design.groups.scope.rules[0].concept_ids[0]);assert.equal(d.reviewed,false);
 const html=e.editorMarkup(d);assert.equal((html.match(/data-ip="generate"/g)||[]).length,1);assert.doesNotMatch(html,/data-ip="suggest-logic"|Generated set definitions/);assert.equal((html.match(/data-card=/g)||[]).length,3);assert.match(html,/Earlier explanation/);
 d.sourceChanged=true;await assert.rejects(e.action('accept-card',{dataset:{field:'scope'},closest:()=>null}),/older source/);
});

test('reading follows only the selected Requirement and toggling editing does not change its draft',async()=>{
 const {e,m,d}=fixture(),host={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null};m.q=()=>host;
 m.requirements.orderedSessions=()=>[{id:'s',text:'Selected requirement',units:{u:{id:'u',text:'Selected requirement'}}},{id:'other',text:'Other requirement must not be repeated',units:{v:{id:'v',text:'Other requirement must not be repeated'}}}];
 const before=structuredClone(d.fields);InterpretationEditor.prototype.render.call(e);
 assert.equal((host.innerHTML.match(/class="ip-requirement/g)||[]).length,1);assert.doesNotMatch(host.innerHTML,/Other requirement must not be repeated|data-rd="add-predicate"/);
 assert.match(host.innerHTML,/data-ip="edit"/);assert.equal(d.dirty,undefined);
 await e.action('edit',{closest:()=>null});const editing=e.editorMarkup(d);assert.match(editing,/data-logic-value="scope"/);assert.match(editing,/Done editing/);
 await e.action('edit',{closest:()=>null});assert.deepEqual(d.fields,before);assert.equal(d.dirty,undefined);
 m.requirements.selected='v';InterpretationEditor.prototype.render.call(e);assert.doesNotMatch(host.innerHTML,/manual scope/);
});

test('editing enables Save immediately without allowing confirmation of unsaved changes',()=>{
 const {e,m,d}=fixture();const save={disabled:true},review={disabled:false};m.q=()=>({querySelector:s=>s==='[data-ip="save"]'?save:s==='[data-ip="review"]'?review:null});
 e.changed();assert.equal(save.disabled,false);assert.equal(review.disabled,true);assert.equal(d.dirty,true);assert.equal(d.reviewed,false);
 e.pending=true;e.changed();assert.equal(save.disabled,true);
});

test('one generation returns all three separate candidates without filling or approving any field',async()=>{
 const {e,m,d}=fixture(),before=structuredClone(d.fields);
 const run={id:'run',status:'ready',context_fingerprint:'fp',suggestions:Object.fromEntries(interpretationKeys.map(k=>[k,field('AI '+k)]))};
 m.api=async()=>run;await e.watch('run',e.active);
 assert.deepEqual(d.fields,before);assert.equal(d.dirty,undefined);assert.ok(['scope','condition','demand'].every(k=>!cardApproved(d,k)));
 const html=e.editorMarkup(d);assert.equal((html.match(/data-ip="generate"/g)||[]).length,1);assert.equal((html.match(/Approve (scope|condition|demand) candidate/g)||[]).length,3);
 await e.action('accept-card',{dataset:{field:'scope'},closest:()=>null});
 assert.equal(d.fields.scope.value,'AI scope');assert.equal(d.fields.scope_information.value,'AI scope_information');assert.equal(d.fields.condition.value,before.condition.value);assert.equal(d.fields.demand.value,before.demand.value);
 assert.equal(cardApproved(d,'scope'),true);assert.equal(d.pendingApprovals.scope,'run');assert.equal(cardApproved(d,'condition'),false);
});

test('individual human approvals invalidate only affected cards and are sent only after Save',async()=>{
 const {e,m,d}=fixture();d.check_design=setDesign();let calls=0;m.api=async()=>{calls++;};
 for(const key of ['scope','condition','demand'])await e.action('approve-card',{dataset:{field:key},closest:()=>null});
 assert.equal(calls,0);assert.ok(['scope','condition','demand'].every(k=>cardApproved(d,k)));
 d.fields.condition.value='Changed condition';e.changed();assert.equal(cardApproved(d,'scope'),true);assert.equal(cardApproved(d,'condition'),false);assert.equal(cardApproved(d,'demand'),true);
 await assert.rejects(e.save('review',{}),/individually/);
 m.api=async(path,body)=>{assert.deepEqual(body.approve_cards,{scope:null,demand:null});return {document:{...d,revision:2,card_review_status:{scope:true,condition:false,demand:true}}};};
 await e.save('save',{});assert.equal(cardApproved(e.draft,'scope'),true);assert.deepEqual(e.draft.pendingApprovals,{});
 e.draft.sourceChanged=true;assert.equal(cardApproved(e.draft,'scope'),false);
});

test('program-combined wording never fills interpreted fields until explicitly copied, and cannot approve them',async()=>{
 const {e,d}=fixture();d.context.requirement.Subject='Seawater temperature';const original=d.fields.scope.value;
 const html=e.editorMarkup(d);assert.match(html,/program-combined/);assert.match(html,/Seawater temperature/);assert.equal(d.fields.scope.value,original);assert.equal(cardApproved(d,'scope'),false);
 d.fields.scope.value='';await e.action('use-mapped',{dataset:{field:'scope'},closest:()=>null});assert.equal(d.fields.scope.value,'Seawater temperature');assert.equal(cardApproved(d,'scope'),false);
});

test('previously adopted candidates stay retired after later human corrections',()=>{
 const {e,d}=fixture();d.candidate={id:'prior-run',suggestions:{scope:field('Earlier AI text')}};d.adopted_candidates={scope:['prior-run']};
 assert.equal(e.cardCandidate(d,'scope',0,''),'');
 d.candidate.id='new-run';assert.match(e.cardCandidate(d,'scope',0,''),/Approve scope candidate/);
});
