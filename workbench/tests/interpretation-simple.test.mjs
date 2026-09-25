import test from 'node:test';
import assert from 'node:assert/strict';
import {setDesign,bindDesign} from '../frontend/components/check-design.js';
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
 const {e,d}=fixture();e.pending=true;d.generation={status:'running'};
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

test('ABC reading follows selection and keeps each editor inside its closed Set disclosure',()=>{
 const {e,m,d}=fixture(),host={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null};m.q=()=>host;
 m.requirements.orderedSessions=()=>[{id:'s',text:'Selected requirement',units:{u:{id:'u',text:'Selected requirement'}}},{id:'other',text:'Other requirement must not be repeated',units:{v:{id:'v',text:'Other requirement must not be repeated'}}}];
 const before=structuredClone(d.fields);InterpretationEditor.prototype.render.call(e);
 assert.equal((host.innerHTML.match(/class="ip-requirement/g)||[]).length,1);
 assert.equal((host.innerHTML.match(/class="ip-set-editor"/g)||[]).length,3);
 assert.equal((host.innerHTML.match(/class="ip-source-wording"/g)||[]).length,3);
 assert.doesNotMatch(host.innerHTML,/Other requirement must not be repeated|data-ip="edit"|class="ip-more"|class="ip-evidence-panel"|data-disclosure="integration"|data-disclosure="set-[^"]+" open/);
 assert.match(host.innerHTML,/B ⊆ A/);assert.match(host.innerHTML,/B ⊆ C/);assert.deepEqual(d.fields,before);assert.equal(d.dirty,undefined);
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

test('pane completion stays separate from individual card approvals',()=>{
 const {e,d}=fixture();assert.doesNotMatch(e.editorMarkup(d),/data-ip="review"/);
 for(const key of ['scope','condition','demand'])e.approveCard(key);
 assert.doesNotMatch(e.editorMarkup(d),/data-ip="review"/);
 d.dirty=false;d.pendingApprovals={};assert.doesNotMatch(e.editorMarkup(d),/data-ip="review"/);assert.match(e.editorMarkup(d),/confirm completion below/);
 d.fields.verification.gaps=['Need a criterion'];assert.doesNotMatch(e.editorMarkup(d),/data-ip="review"/);
});

test('unadded exact quotations stay on the page draft across field edits and formal Save',async()=>{
 const {e,m,d}=fixture();d.context.citations=[{id:'source-a',text:'Exact 🐟 supporting quotation'},{id:'source-b',text:'Other quotation'}];d.citationDrafts={scope:{id:'source-a',quote:'🐟 supporting'}};
 assert.equal(e.hasUnsaved(),true);assert.match(e.fieldMarkup(d,'scope','Scope'),/>🐟 supporting<\/textarea>/);assert.match(e.fieldMarkup(d,'scope','Scope'),/value="source-a" selected/);
 d.fields.verification.value='Updated method';e.changed();let request;m.api=async(path,body)=>{request=body;return {document:{...d,revision:2,citationDrafts:undefined}};};await e.save('save',{});
 assert.deepEqual(e.draft.citationDrafts.scope,{id:'source-a',quote:'🐟 supporting'});assert.deepEqual(request.fields.scope.references,[]);assert.equal('citationDrafts' in request,false);assert.equal(e.draft.dirty,false);assert.equal(e.hasUnsaved(),true);assert.match(e.notice,/unadded quotation remains unsaved/);
 let calls=0;m.api=async()=>calls++;await e.save('save',{});assert.equal(calls,0);assert.match(e.notice,/has not been added/);
});
test('Add citation keeps invalid staging and clears only the explicitly added exact pair',async()=>{
 const {e,d}=fixture();d.context.citations=[{id:'source',text:'Original exact words'}];d.citationDrafts={scope:{id:'source',quote:'Wrong quote'},condition:{id:'source',quote:'exact'}};
 const quote={value:'Wrong quote'},el={dataset:{ipField:'scope'},querySelector:s=>s==='[data-ip-citation]'?{value:'source'}:quote},button={closest:()=>el};await assert.rejects(e.action('add-ref',button),/exact nonempty/);assert.equal(d.citationDrafts.scope.quote,'Wrong quote');assert.deepEqual(d.fields.scope.references,[]);
 quote.value='exact words';await e.action('add-ref',button);assert.deepEqual(d.fields.scope.references,[{id:'source',quote:'exact words'}]);assert.equal(d.citationDrafts.scope,undefined);assert.equal(d.citationDrafts.condition.quote,'exact');await e.action('add-ref',button);assert.equal(d.fields.scope.references.length,1);
});
test('quotation-only drafts survive reopening their unit and remain isolated from another reviewer',async()=>{
 const {e,m,d}=fixture();d.citationDrafts={scope:{id:'source',quote:'Original quotation'}};m.api=async()=>({...d,citationDrafts:undefined});await e.open('u');assert.equal(e.draft,d);assert.equal(e.draft.citationDrafts.scope.quote,'Original quotation');
 m.state.actor.id='other';assert.equal(e.hasUnsaved(),false);await e.open('u');assert.equal(e.draft.citationDrafts,undefined);assert.equal(e.drafts.get('a:m:u').citationDrafts.scope.quote,'Original quotation');
});
test('disclosure identity is retained for the current unit and is not copied to another unit',()=>{
 const {e,m,d}=fixture();const open=[{dataset:{disclosure:'review-scope'},open:true},{dataset:{disclosure:'concept:stable-rule:c'},open:true}],fresh=[{dataset:{disclosure:'review-scope'},open:false},{dataset:{disclosure:'concept:stable-rule:c'},open:false}];let current=open;
 const host={set innerHTML(value){this.html=value;current=fresh.map(n=>({...n}));},querySelectorAll:s=>s==='details[open][data-disclosure]'?current.filter(n=>n.open):s==='details[data-disclosure]'?current:[],querySelector:()=>null};m.q=()=>host;e.renderedKey=e.active;InterpretationEditor.prototype.render.call(e);assert.equal(current.every(n=>n.open),true);assert.deepEqual(d.disclosures,['review-scope','concept:stable-rule:c']);
 const second={...d,unit_id:'v',disclosures:undefined};e.drafts.set(e.key('v'),second);e.active=e.key('v');m.requirements.selected='v';InterpretationEditor.prototype.render.call(e);assert.equal(current.every(n=>!n.open),true);assert.equal(second.disclosures,undefined);
});
test('removal Undo restores human draft content and concept IDs without restoring prior card approval',()=>{
 const {e,m,d}=fixture();d.check_design={...setDesign(),concepts:[{id:'concept',label:'Facility',kind:'concept',status:'confirmed',references:[{id:'source',quote:'Facility'}]}],groups:{scope:{id:'group',condition:'OR',not:true,rules:[{id:'rule',expression:'Facility',interpretation_field:'scope',concept_ids:['concept']}]},condition:null,demand:null}};d.designUI={};e.approveCard('scope');assert.equal(cardApproved(d,'scope'),true);const before=structuredClone(d.check_design.groups.scope);
 const element={dataset:{rdPath:'scope'}},button={dataset:{rd:'remove'},closest:()=>element},host={querySelectorAll:s=>s==='[data-rd]'?[button]:[],querySelector:()=>null};bindDesign(host,d.check_design,()=>e.changed(),()=>{},undefined,d.fields,d.designUI);
 button.onclick({stopPropagation(){}});assert.equal(cardApproved(d,'scope'),false);assert.doesNotMatch(e.notice,/Scope approved/);assert.equal(d.check_design.groups.scope,null);button.dataset.rd='undo-remove';button.onclick({stopPropagation(){}});assert.deepEqual(d.check_design.groups.scope,before);assert.equal(cardApproved(d,'scope'),false);assert.equal(d.pendingApprovals.scope,undefined);assert.equal(d.dirty,true);
 button.dataset.rd='remove';button.onclick({stopPropagation(){}});assert.ok(d.designUI.undo);d.fields.verification.value='Next edit';e.notice='Generation status unavailable.';e.changed();assert.equal(d.designUI.undo,null);assert.equal(e.notice,'Generation status unavailable.');
});
test('quoted concept navigation is a read-only delegated action and prevents summary toggling twice',()=>{
 const {e,m,d}=fixture();let opened=false,focused=false,prevented=0,stopped=0;const details={tagName:'DETAILS',parentElement:null,set open(value){opened=value;}},input={setAttribute(){},scrollIntoView(){},focus(){focused=true;}},concept={dataset:{concept:'c'},querySelector:()=>input},rule={dataset:{rdId:'rule'},parentElement:details,querySelectorAll:()=>[concept]};const host={innerHTML:'',querySelectorAll:s=>s==='[data-rd-id]'?[rule]:[],querySelector:()=>null};m.q=()=>host;InterpretationEditor.prototype.render.call(e);
 const term={dataset:{ruleId:'rule',conceptNav:'["c"]'}},event={target:{closest:s=>s==='[data-concept-nav]'?term:null},preventDefault(){prevented++;},stopPropagation(){stopped++;}};host.onclick(event);assert.equal(opened,true);assert.equal(focused,true);assert.equal(concept.open,true);assert.equal(prevented,1);assert.equal(stopped,1);assert.equal(d.dirty,undefined);assert.equal(d.pendingApprovals,undefined);
 event.key='Enter';host.onkeydown(event);assert.equal(prevented,2);assert.equal(stopped,2);
});
test('a staged citation missing from refreshed context stays explicitly unavailable and cannot bind identical text elsewhere',async()=>{
 const {e,d}=fixture();d.citationDrafts={scope:{id:'original-source',quote:'identical text'}};d.context.citations=[{id:'different-source',text:'identical text'}];
 const html=e.fieldMarkup(d,'scope','Scope');assert.match(html,/<option value="original-source" selected disabled>Unavailable source/);assert.match(html,/>identical text<\/textarea>/);
 const el={dataset:{ipField:'scope'},querySelector:s=>s==='[data-ip-citation]'?{value:'original-source'}:{value:'identical text'}};await assert.rejects(e.action('add-ref',{closest:()=>el}),/exact nonempty/);assert.deepEqual(d.fields.scope.references,[]);assert.equal(d.citationDrafts.scope.id,'original-source');
});
test('source-only citation preference survives same-unit refresh without becoming unsaved work',async()=>{
 const {e,m,d}=fixture();d.citationDrafts={scope:{id:'source-B',quote:''}};m.api=async()=>({...d,revision:2,citationDrafts:undefined});assert.equal(e.hasUnsaved(),false);await e.open('u');assert.equal(e.draft.revision,2);assert.deepEqual(e.draft.citationDrafts.scope,{id:'source-B',quote:''});assert.equal(e.hasUnsaved(),false);assert.deepEqual(e.draft.fields.scope.references,[]);
});
test('reload guards quotation-only work and a changed source expires removal Undo on read',async()=>{
 const {e,m,d}=fixture();d.citationDrafts={scope:{id:'source',quote:'Unsaved exact wording'}};let dialog='';m.dialog=html=>dialog=html;m.q=()=>({});await e.action('reload',{closest:()=>null});assert.match(dialog,/Reload saved interpretation/);assert.equal(e.draft,d);
 d.dirty=true;d.designUI={undo:{root:'scope'}};m.api=async()=>({...d,context:{...d.context,fingerprint:'changed'}});await e.open('u');assert.equal(d.designUI.undo,null);assert.equal(d.citationDrafts.scope.quote,'Unsaved exact wording');
});

function conflictDialog(m){const buttons=['saved','local'].map(value=>({dataset:{conflictUse:value},disabled:false})),status={textContent:''},dialog={querySelectorAll:()=>buttons,querySelector:()=>status,close(){this.closed=true;}};m.dialog=(html,bind)=>{dialog.html=html;bind(dialog);};return {buttons,status,dialog};}
test('save conflict compares authoritative versions and explicitly rebases a reviewed local draft without saving',async()=>{
 const {e,m,d}=fixture();d.dirty=true;d.check_design=setDesign();let saved={...structuredClone(d),revision:2,fields:{...structuredClone(d.fields),scope:field('Remote wording')}};const calls=[];
 m.api=async(path,body)=>{calls.push({path,body});if(path.endsWith('/save'))throw Object.assign(Error('A newer interpretation is saved.'),{status:409,definitive:true});if(path.endsWith('/context'))return structuredClone(d.context);return structuredClone(saved);};
 await e.save('save',{});assert.equal(d.conflict,true);assert.equal(d.retry,null);const {buttons,dialog}=conflictDialog(m);await e.compareConflict();assert.match(dialog.html,/Remote wording/);assert.match(dialog.html,/manual scope/);assert.equal(d.revision,1);assert.equal(d.fields.scope.value,'manual scope');const count=calls.filter(x=>x.path.endsWith('/save')).length;
 await buttons[1].onclick();assert.equal(d.revision,2);assert.equal(d.fields.scope.value,'manual scope');assert.deepEqual(d.approvalSnapshots,{});assert.equal(d.dirty,true);assert.equal(d.conflict,false);assert.equal(calls.filter(x=>x.path.endsWith('/save')).length,count);
 m.api=async(path,body)=>{assert.equal(body.expected_revision,2);return {document:{...d,revision:3}};};await e.save('save',{});assert.equal(e.draft.revision,3);
});
test('conflict comparison cancellation or another saved version protects local wording and revision',async()=>{
 const {e,m,d}=fixture();d.conflict=true;const latest={...structuredClone(d),revision:2},ctx=structuredClone(d.context);let revision=2;
 m.api=async path=>path.endsWith('/context')?ctx:{...latest,revision};const {buttons,status,dialog}=conflictDialog(m);await e.compareConflict();assert.equal(d.revision,1);assert.equal(dialog.closed,undefined);revision=3;await buttons[1].onclick();assert.equal(d.revision,1);assert.match(status.textContent,/changed again/);assert.equal(dialog.closed,undefined);
 revision=2;await e.compareConflict();d.fields.scope.value='Changed during comparison';await buttons[0].onclick();assert.equal(d.fields.scope.value,'Changed during comparison');assert.match(status.textContent,/local draft changed/);
});
test('context refresh cannot clear a newer-save conflict and explicit reload selects exact saved definitions',async()=>{
 const {e,m,d}=fixture();d.conflict=true;d.sourceChanged=true;const ctx=structuredClone(d.context);m.api=async()=>ctx;await e.action('context',{closest:()=>null});assert.equal(d.sourceChanged,true);assert.equal(d.revision,1);await assert.rejects(e.save('save',{}),/Compare/);
 const remote={...structuredClone(d),revision:4,conflict:undefined,sourceChanged:false,fields:{...structuredClone(d.fields),scope:field('Chosen saved value')},check_design:setDesign()};m.api=async path=>path.endsWith('/context')?ctx:structuredClone(remote);const {buttons}=conflictDialog(m);await e.compareConflict();await buttons[0].onclick();assert.equal(e.draft.revision,4);assert.equal(e.draft.fields.scope.value,'Chosen saved value');assert.equal(e.draft.dirty,false);
});
test('changed context and catalog in conflict recovery invalidate local approval and concept confirmation',async()=>{
 const {e,m,d}=fixture();d.catalog={revision:1};d.check_design=setDesign();d.check_design.concepts=[{id:'c',label:'Facility',status:'confirmed'}];d.approvalSnapshots={scope:'old'};d.pendingApprovals={scope:null};const latest={...structuredClone(d),revision:2,catalog:{revision:2}},ctx={...d.context,fingerprint:'new-context',citations:[]};m.api=async path=>path.endsWith('/context')?ctx:latest;
 const {buttons,dialog}=conflictDialog(m);await e.compareConflict();assert.match(dialog.html,/Source context changed/);assert.match(dialog.html,/Site Model catalog changed/);await buttons[1].onclick();assert.equal(d.context.fingerprint,'new-context');assert.equal(d.catalog.revision,2);assert.equal(d.check_design.concepts[0].status,'proposed');assert.deepEqual(d.pendingApprovals,{});
});
test('uncertain generation start retains the exact confirmed request across edits and retries one run',async()=>{
 const {e,m,d}=fixture();const confirm={disabled:false},dialog={close(){}},requests=[];m.dialog=()=>{};m.q=s=>s==='[data-ip-confirm]'?confirm:s==='#mw-dialog'?dialog:null;e.watch=async(id,key)=>{assert.equal(id,'run-one');assert.equal(key,e.active);};
 m.api=async(path,body)=>{requests.push(JSON.stringify(body));if(requests.length===1)throw Error('Response lost');return {id:'run-one',status:'running',unit_id:'u',context_fingerprint:'fp'};};
 await e.action('generate',{closest:()=>null});await confirm.onclick();assert.ok(d.generationRequest);assert.equal(e.hasUnsaved(),true);d.fields.scope.value='Human edit after lost response';d.context.fingerprint='changed';await assert.rejects(e.action('generate',{closest:()=>null}),/Wait/);await e.action('generation-retry',{closest:()=>null});assert.equal(requests.length,2);assert.equal(requests[0],requests[1]);assert.equal(d.generation.id,'run-one');assert.equal(d.generationRequest,null);assert.equal(d.fields.scope.value,'Human edit after lost response');
});
test('definitive generation rejection clears only the pending start and keeps human fields',async()=>{
 const {e,m,d}=fixture();d.generationRequest={request_id:'same',unit_id:'u'};m.api=async()=>{throw Object.assign(Error('Not connected'),{definitive:true});};await e.startGeneration(e.active);assert.equal(d.generationRequest,null);assert.equal(d.fields.scope.value,'manual scope');
});
test('failed known generation status can retry the same run without replacing unsaved human fields',async()=>{
 const {e,m,d}=fixture();d.generation={id:'run',unit_id:'u'};d.fields.scope.value='Human pending edit';d.dirty=true;const paths=[];m.api=async path=>{paths.push(path);if(paths.length===1)throw Error('Offline');return {id:'run',unit_id:'u',status:'ready',context_fingerprint:'fp',suggestions:{scope:field('AI candidate')}};};await e.watch('run',e.active);assert.equal(d.generationStatusError,true);assert.match(e.editorMarkup(d),/Retry status/);await e.action('generation-status',{closest:()=>null});assert.equal(paths.length,2);assert.equal(paths[0],paths[1]);assert.equal(d.generation,null);assert.equal(d.generationStatusError,false);assert.equal(d.fields.scope.value,'Human pending edit');assert.equal(d.candidate.suggestions.scope.value,'AI candidate');assert.equal(d.dirty,true);
});
test('generation replies bound to another unit or context do not become the active candidate',async()=>{
 const {e,m,d}=fixture();d.generation={id:'run',unit_id:'u'};m.api=async()=>({id:'run',unit_id:'other',status:'ready',context_fingerprint:'fp'});await e.watch('run',e.active);assert.equal(d.candidate,undefined);assert.equal(d.generation.id,'run');m.api=async()=>({id:'run',unit_id:'u',status:'ready',context_fingerprint:'old'});await e.watch('run',e.active);assert.equal(d.candidate,undefined);assert.equal(d.generation,null);
});

test('closing or replacing conflict comparison cancels delayed local application without touching the next dialog',async()=>{
 for(const replace of [false,true]){
  const {e,m,d}=fixture(),remote={...structuredClone(d),revision:2,fields:{...structuredClone(d.fields),scope:field('Remote')}};let finish;const ctx=structuredClone(d.context);m.api=async path=>path.endsWith('/context')?ctx:remote;const {buttons,dialog,status}=conflictDialog(m);dialog.open=true;await e.compareConflict();m.api=async()=>new Promise(r=>finish=r);const pending=buttons[0].onclick();if(replace){const next={textContent:'Next dialog feedback'};dialog.querySelector=()=>next;}else dialog.open=false;finish(remote);await pending;assert.equal(e.draft,d);assert.equal(d.revision,1);assert.equal(d.fields.scope.value,'manual scope');assert.equal(dialog.closed,undefined);assert.equal(status.textContent,'');if(replace)assert.equal(dialog.querySelector().textContent,'Next dialog feedback');
 }
});

test('explicit approvals and candidate dismissal retain focus in the same ABC card without saving',async()=>{const {e,m,d}=fixture(),focused=[],host={querySelector:s=>{const match=/^\[data-card-status="(.*?)"\]$/.exec(s);return match?{focus(){focused.push(match[1]);},scrollIntoView(){}}:null;}};m.q=s=>s==='#mw-interpretation-content'?host:null;m.api=()=>{throw Error('Decision should not save');};e.approveCard('scope');assert.equal(cardApproved(d,'scope'),true);d.candidate={context_fingerprint:'fp',suggestions:{condition:field('Candidate condition'),demand:field('Candidate demand')}};await e.action('accept-card',{dataset:{field:'condition'},closest:()=>null});await e.action('dismiss-card',{dataset:{field:'demand'},closest:()=>null});assert.deepEqual(focused,['scope','condition','demand']);assert.equal(cardApproved(d,'condition'),true);assert.equal(cardApproved(d,'demand'),false);assert.match(e.notice,/Demand candidate dismissed/);assert.equal(d.fields.demand.value,'manual demand');});

test('editing an approved card updates its visible status through valid attribute selectors',()=>{const {e,m,d}=fixture(),labels=Object.fromEntries(['scope','condition','demand'].map(key=>[key,{textContent:'Approved'}]));const host={querySelector(selector){if(selector.includes('data-card-status')){const match=/^\[data-card-status="(scope|condition|demand)"\]$/.exec(selector);if(!match)throw new SyntaxError('Invalid attribute selector');return labels[match[1]];}return null;}};m.q=selector=>selector==='#mw-interpretation-content'?host:null;e.approveCard('scope');assert.match(labels.scope.textContent,/Approved/);d.fields.scope.value='Human changed the scope';e.changed();assert.equal(labels.scope.textContent,'Not approved');assert.equal(d.dirty,true);});
