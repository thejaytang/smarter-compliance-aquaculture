import {treeNodes,treeText,relationshipSides,structureLabels,transparentGroup} from './requirement-structure.js';
import {emptyDesign,setDesign,setHandoff,designMarkup,domainMarkup,ruleMarkup,ruleSummaryMarkup,logicText,logicFields,pruneConcepts,conceptIssues,bindDesign} from './check-design.js';
import {semanticFields,semanticClass} from './markdown-content.js';
// Interpretation is a source-bound design, not an executed compliance check.
export const interpretationKeys=['scope','scope_information','condition','condition_information','demand','verification'];
export const interpretationLabels=['Scope','Information needed to identify scoped objects','Condition','Information needed to determine applicability','Demand','Verification method and criteria'];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const copy=v=>structuredClone(v);
export const fieldState=f=>f?.state||(f?.value?.trim()&&f?.basis!=='unresolved'?'specified':'unresolved');
export const reviewReady=f=>!f.gaps?.length&&((fieldState(f)==='specified'&&!!f.value?.trim()&&f.basis!=='unresolved')||(fieldState(f)==='not_stated'&&!!f.absence_reason?.trim()&&!f.value?.trim()));
export function checkingLogic(fields,exceptions=[],design=null,contextFingerprint='',catalog={fields:[],revision:0}){
 const originalFields=fields;fields=logicFields(fields,design);
 const values=Object.fromEntries(interpretationKeys.map(k=>[k,fieldState(fields[k])==='not_stated'?'Not explicitly stated in the reviewed source. '+(fields[k].absence_reason||''):(fields[k]?.value||'').trim()]));
 const result={version:1,executable:false,steps:[
  {title:'Identify Set A',description:values.scope,information:values.scope_information},
  {title:'Determine Set B within A',description:values.condition,information:values.condition_information},
  {title:'Check Demand for each object in B',description:values.demand,information:values.verification}],exceptions,
  gaps:[...interpretationKeys.filter(k=>fieldState(fields[k])!=='specified'||!values[k]||fields[k]?.basis==='unresolved').map(k=>interpretationLabels[interpretationKeys.indexOf(k)]),...interpretationKeys.flatMap(k=>fields[k]?.gaps||[])],
  source_structure:{},rule:'B is a subset of A. In the same assessment context, check B ⊆ C, where C contains objects with sufficient evidence of meeting Demand.',
  boundary:'Check design only. Distinguish evidence of failure from insufficient information; no site assessment has been performed.'};
 if(design?.schema==='requirement-check-design/2')Object.assign(result,{version:2,handoff:setHandoff(originalFields,design,contextFingerprint,catalog)});
 return result;
}
export function logicMarkup(logic){return `<p class="ip-set-formula">B ⊆ C</p><p>Every applicable object in B must meet Demand in the same assessment period. B is selected within A.</p>${logic.exceptions?.length?`<details><summary>Source exceptions (${logic.exceptions.length})</summary>${logic.exceptions.map(x=>`<p>Owner ${esc(x.owner_id)}: ${esc(x.text.join(' / '))}</p><pre>${esc(JSON.stringify(x.combination))}</pre>`).join('')}<p>Exceptions keep their original ownership.</p></details>`:''}${logic.gaps.length?`<details class="ip-warning"><summary>Review questions (${logic.gaps.length})</summary><ul>${logic.gaps.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details>`:''}<p class="ip-caption">Check design only · no site assessment performed.</p>`;}
// Mechanical projection of recorded wording and group counts; no inferred predicates.
export function sourceSections(context){
 const u=context?.requirement||{},units=Object.assign({},...(context?.sessions||[]).map(s=>s.units),u.id?{[u.id]:u}:{});
 if(context?.structure){
  const tree=context.structure,trees=Object.assign({},...(context.sessions||[]).map(s=>s.structures||{})),clauses=[];const visit=n=>{if(n.role==='exceptions')return;if(n.kind==='clause')clauses.push(n);for(const child of n.children||[])visit(child);};visit(tree);
  const grouped=tree.children.find(n=>n.role==='requirements'),session=context.sessions?.find(s=>s.units?.[u.id])||{units:{[u.id]:u}};
  const labels=structureLabels({...session,structure_views:{...session.structures,[u.id]:tree}}),hasRelationship=treeNodes(tree).some(n=>n.relationship);
  const pick=(clause,fields)=>clause.children.filter(n=>fields.includes(n.role)).map(n=>`${n.role}: ${treeText(n,units,trees)}`).join('\n');
  const at=(fields)=>clauses.map(c=>{const text=pick(c,fields);return text?`${clauses.length>1?labels[c.id]+': ':''}${text}`:'';}).filter(Boolean).join('\n');
  const values={scope:at(['Subject']),condition:[at(['conditions']),at(['exceptions'])?'Exception structure (separate scope): '+at(['exceptions']):''].filter(Boolean).join('\n'),demand:[at(['Modal Verb','Main Verb','Object','subrequirement']),grouped?(hasRelationship?'Source Groups: ':'Requirement branches (QC applies to complete branches): ')+treeText(hasRelationship&&transparentGroup(grouped)?grouped.children[0]:grouped,units,trees):''].filter(Boolean).join('\n')};
  const pending=treeNodes(tree).some(n=>(n.kind==='clause'&&!n.children.length)||(n.kind==='group'&&(n.quantity===null||!n.children.length))||(n.relationship&&(!relationshipSides(n).before.length||!relationshipSides(n).after.length)));
  return Object.fromEntries(Object.entries(values).map(([key,value])=>[key,{value,basis:value?'interpretation':'unresolved',state:value&&!pending?'specified':'unresolved',references:[],gaps:[...(!value?['No '+key+' wording has been assigned in the Requirement.']:[]),...(pending?['Complete empty groups, both sides of relationships and unresolved quantities in the third pane.']:[])]}]));
 }
 const group=(g,seen=new Set())=>!g?'':`${Array.isArray(g[0])?`${g[0][0]}–${g[0][1]}`:`Exactly ${g[0]}`} of ${g.length-1}: [${g.slice(1).map(x=>{
  if(Array.isArray(x))return group(x,seen);
  const child=units[x];if(!child)return `Unresolved reference ${x}`;
  if(seen.has(x))return child.text;const next=new Set([...seen,x]);
  return [child.text,...['conditions','exceptions','subrequirement'].filter(k=>child[k]).map(k=>`${k}: ${group(child[k],next)}`)].join('\n');
 }).join(' | ')}]`;
 const values={scope:u.Subject||'',condition:[group(u.conditions),u.exceptions?'Exceptions: '+group(u.exceptions):''].filter(Boolean).join('\n'),demand:[[u['Modal Verb'],u['Main Verb'],u.Object].filter(Boolean).join(' '),u.subrequirement?'Subrequirements: '+group(u.subrequirement):''].filter(Boolean).join('\n')};
 return Object.fromEntries(Object.entries(values).map(([k,value])=>[k,{value,basis:value?'interpretation':'unresolved',state:value?'specified':'unresolved',references:[],gaps:value?[]:['No '+k+' wording has been assigned in the Requirement.']} ]));
}
export const logicKeys=['scope_information','condition_information','verification'];
const cardKeys=['scope','condition','demand'];
function cardSnapshot(d,key){
 const design=d.check_design||{},group=design.groups?.[key]||null,ids=new Set();
 const visit=n=>{if(!n)return;(n.concept_ids||[]).forEach(id=>ids.add(id));(n.rules||[]).forEach(visit);};visit(group);
 return JSON.stringify({fields:[d.fields[key],d.fields[logicKeys[cardKeys.indexOf(key)]]],group,concepts:(design.concepts||[]).filter(t=>ids.has(t.id)).map(({status,...term})=>term),object_type:design.object_type||'',assessment_context:design.assessment_context||'',context:d.context?.fingerprint});
}
function reviewDraft(doc){
 const d={...doc,approvalSnapshots:{},pendingApprovals:{}};
 for(const key of cardKeys)if(doc.card_review_status?.[key])d.approvalSnapshots[key]=cardSnapshot(d,key);
 return d;
}
export const cardApproved=(d,key)=>!d.stale&&!d.sourceChanged&&!!d.approvalSnapshots?.[key]&&d.approvalSnapshots[key]===cardSnapshot(d,key);
export class InterpretationEditor{
 constructor(m){this.m=m;this.drafts=new Map();this.active=null;this.loading=false;this.pending=false;this.notice='';this.editing=null;}
 async refreshProvider(){
  try{const [p,catalog]=await Promise.all([this.m.api('/api/settings/ai'),this.m.api('/api/settings/site-catalog')]);for(const [key,d] of this.drafts)if(key.startsWith(this.owner()+':')){d.provider=p;d.catalog=catalog;}this.render();}catch(e){this.m.message(e.message,'warning');}
 }
 get host(){return this.m.q('#mw-interpretation-content');}
 owner(){return `${this.m.state?.actor?.id}:${this.m.id}`;}
 key(uid){return `${this.owner()}:${uid}`;}
 get draft(){return this.drafts.get(this.active);}
 hasUnsaved(){return [...this.drafts.entries()].some(([key,d])=>key.startsWith(this.owner()+':')&&(d.dirty||d.retry))||this.pending;}
 needsRecovery(){return this.hasUnsaved();}
 canLeave(){if(this.pending){this.m.message('Wait for the current save result.','warning');return false;}if(this.hasUnsaved()){this.m.unsavedDialog?.();return false;}return true;}
 journal(){return true;} // Unsaved work is held in page memory only.
 restoreJournal(){} // Legacy copies are retained but never restored automatically.
 async open(uid){
  this.restoreJournal();const key=this.key(uid),owner=this.owner();if(this.active!==key)this.editing=null;this.active=key;this.loading=true;this.notice='Loading interpretation…';this.render();
  try{const doc=await this.m.api('/api/interpretations?'+new URLSearchParams({unit_id:uid}));if(this.owner()!==owner||this.active!==key)return;
   const remote=null;
   if(this.owner()!==owner||this.active!==key)return;
   if(remote?.body&&!this.drafts.get(key)?.dirty){const b=remote.body;this.drafts.set(key,{...doc,...b,dirty:true,draftRevision:remote.revision,workingStored:true,context:doc.context,sourceChanged:b.context_fingerprint!==doc.context?.fingerprint||b.revision!==doc.revision});}
   const old=this.drafts.get(key);if(remote&&old?.dirty&&remote.revision!==old.draftRevision)old.workingConflict=true;if(old?.dirty||old?.retry){old.latest=doc;old.provider=doc.provider;old.sourceChanged=old.sourceChanged||old.context?.fingerprint!==doc.context?.fingerprint||old.revision!==doc.revision;old.catalog=doc.catalog;old.impact=doc.impact;}
   else this.drafts.set(key,{...reviewDraft(doc),dirty:false,candidate:(doc.runs||[]).find(r=>r.status==='ready'&&r.context_fingerprint===doc.context?.fingerprint)});
   this.notice=old?.dirty?'Unsaved changes in this page. Save before leaving.':doc.stale?'Source dependencies changed. Review and refresh the context before saving.':'Saved and reviewed are separate states.';
   const running=doc.runs?.find(r=>r.status==='running');if(running)this.watch(running.id,key);
  }catch(e){this.notice=e.message;}finally{if(this.active===key){this.loading=false;this.render();}}
 }
 sourceChanged(){for(const [key,d] of this.drafts)if(key.startsWith(this.owner()+':'))d.sourceChanged=true;this.render();}
 referenceClass(ref,d){
  const source=this.m.requirements?.doc;
  if(!source||source.id!==d.context?.session_id||ref.id!==d.context.material_id+':'+source.block_id)return '';
  const u=source.units[d.unit_id];if(!u)return '';
  const linked=g=>Array.isArray(g)?g.slice(1).flatMap(x=>Array.isArray(x)?linked(x):[x]):[];
  const matches=semanticFields.filter(f=>typeof u[f]==='string'?u[f]===ref.quote&&source.field_spans?.[d.unit_id]?.[f]:linked(u[f]).some(id=>source.units[id]?.text===ref.quote));
  return matches.length===1?'semantic '+semanticClass(matches[0]):matches.length>1?'semantic semantic-overlap':'';
 }
 render(){
  const host=this.host;if(!host)return;const disclosures=[...(host.querySelectorAll?.('details[open][data-disclosure]')||[])].map(el=>el.dataset.disclosure),conceptsOpen=[...(host.querySelectorAll?.('details[open][data-concept]')||[])].map(el=>el.closest('[data-rd-path]').dataset.rdPath+':'+el.dataset.concept);
  const r=this.m.requirements,entries=(r?.orderedSessions?.()||[]).map(s=>s.id===r.doc?.id?r.doc:s);
  const d=this.draft,valid=d&&this.active?.startsWith(this.owner()+':')&&r?.selected===d.unit_id;
  const selected=entries.find(s=>s.units?.[r?.selected]);
  const ids=selected?(r.rootIds?r.rootIds(selected):Object.keys(selected.units||{})):[];
  host.innerHTML=this.loading?'<p role="status">Loading interpretation…</p>':valid?`<section class="ip-requirement ip-current" aria-label="Interpretation for ${esc(r.label(d.unit_id))}">${ids.length>1?`<div class="ip-clause-choices">${ids.map(uid=>`<button data-ip-select="${uid}" aria-pressed="${d.unit_id===uid}">${esc(r.internalLabel?.(uid)||r.label(uid))}</button>`).join('')}</div>`:''}${this.editorMarkup(d)}</section>`:'<p class="ip-empty">Select a Requirement in the third pane to review its interpretation.</p>';
  host.querySelectorAll?.('details[data-disclosure]')?.forEach(el=>{if(disclosures.includes(el.dataset.disclosure))el.open=true;});
  host.querySelectorAll?.('details[data-concept]')?.forEach(el=>{if(conceptsOpen.includes(el.closest('[data-rd-path]').dataset.rdPath+':'+el.dataset.concept))el.open=true;});
  host.querySelectorAll?.('[data-ip-select]')?.forEach(n=>n.onclick=async e=>{e.preventDefault();await r.selectFromInterpretation(n.dataset.ipSelect);});
  host.onclick=e=>{const b=e.target.closest('[data-ip]');if(b&&!b.disabled)void this.action(b.dataset.ip,b).catch(error=>{this.notice=error.message;this.render();});};
  host.querySelectorAll?.('[data-logic-value]')?.forEach(el=>el.oninput=()=>{
   const key=el.dataset.logicValue,c=d.logicCandidates?.[key];
   if(c){c.value=el.value;c.edited=true;}else{d.fields[key]={...d.fields[key],value:el.value,basis:'interpretation',state:el.value.trim()?'specified':'unresolved',absence_reason:''};}
   this.changed();
  });
  host.querySelectorAll?.('[data-field-gaps]')?.forEach(el=>el.oninput=()=>{d.fields[el.dataset.fieldGaps].gaps=el.value.split('\n').map(s=>s.trim()).filter(Boolean);this.changed();});
  host.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='s'){e.preventDefault();e.stopPropagation();void this.save('save',{}).catch(error=>{this.notice=error.message;this.render();});}};
  if(valid&&d.check_design)bindDesign(host,d.check_design,()=>this.changed(),()=>this.render(),d.catalog,d.fields);
 }
 fieldMarkup(d,key,label,readOnly=false){
  const f=d.fields[key],editing=this.editing===this.active,disabled=this.m.collaboration.readonly?'disabled':'';
  return `<div class="ip-field" data-ip-field="${key}">${readOnly?`<details><summary>Earlier explanation</summary><p>${esc(f.value||'No earlier explanation.')}</p></details>`:editing?`<label>${esc(label)}<textarea data-logic-value="${key}" aria-label="${esc(label)}" rows="3" ${disabled}>${esc(f.value)}</textarea></label>`:`<p class="ip-caption">${esc(label)}</p><p>${esc(f.value||f.absence_reason||'Not yet defined.')}</p>`}<details class="ip-evidence" data-disclosure="evidence-${key}"><summary>Quotations &amp; questions (${f.references?.length||0})</summary>${f.state==='not_stated'?`<p>${esc(f.absence_reason)}</p>`:''}${(f.references||[]).map((ref,i)=>`<blockquote>${esc(ref.quote)}</blockquote>${editing?`<button data-ip="remove-ref" data-ref="${i}" ${disabled}>Remove citation</button>`:''}`).join('')}${editing?`<label>Saved context passage<select data-ip-citation ${disabled}>${(d.context?.citations||[]).map(ref=>`<option value="${esc(ref.id)}">${esc(ref.text.slice(0,130))}</option>`).join('')}</select></label><label>Exact supporting quotation<textarea data-ip-quote rows="2" ${disabled}></textarea></label><button data-ip="add-ref" ${disabled}>Add citation</button><label>Open questions · one per line<textarea data-field-gaps="${key}" rows="2" ${disabled}>${esc((f.gaps||[]).join('\n'))}</textarea></label>`:(f.gaps||[]).length?`<ul>${f.gaps.map(g=>`<li>${esc(g)}</li>`).join('')}</ul>`:''}</details></div>`;
 }
 cardCandidate(d,key,index,disabled){
  const c=d.candidate;if(!c?.suggestions?.[key]||c.accepted?.includes(key)||c.dismissed?.includes(key)||c.id&&(d.card_reviews?.[key]?.candidate_run_id===c.id||d.adopted_candidates?.[key]?.includes(c.id)))return '';
  return `<details class="ip-candidate" data-disclosure="candidate-${key}" open><summary>AI candidate · approval required</summary><p>${esc(logicText(c.check_design?.groups[key])||c.suggestions[key].value)}</p><p>${esc(c.suggestions[logicKeys[index]]?.value||'')}</p>${c.check_design?`<p>Concepts: ${esc((c.check_design.concepts||[]).filter(t=>JSON.stringify(c.check_design.groups[key]).includes('"'+t.id+'"')).map(t=>t.label).join(', '))}</p>`:''}<details><summary>Candidate evidence</summary>${[key,logicKeys[index]].flatMap(k=>(c.suggestions[k]?.references||[]).map(ref=>`<blockquote>${esc(ref.quote)}</blockquote>`)).join('')}${[key,logicKeys[index]].flatMap(k=>(c.suggestions[k]?.gaps||[]).map(g=>`<p>${esc(g)}</p>`)).join('')}</details><button data-ip="accept-card" data-field="${key}" ${disabled}>Approve ${key} candidate</button><button data-ip="dismiss-card" data-field="${key}" ${disabled}>Dismiss candidate</button></details>`;
 }
 editorMarkup(d){
  const derived=sourceSections(d.context),blocked=this.pending||this.loading||d.retry||this.m.collaboration.readonly,disabled=blocked?'disabled':'',editDisabled=this.m.collaboration.readonly?'disabled':'',r=this.m.requirements,editing=this.editing===this.active;
  const design=d.check_design=setDesign(d.check_design||emptyDesign()),logic=checkingLogic(d.fields,d.context?.exceptions,design,d.context?.fingerprint,d.catalog),conceptGaps=conceptIssues(design);
  logic.gaps=[...new Set([...logic.gaps,...conceptGaps])];
  const notice=this.notice==='Saved and reviewed are separate states.'?'':this.notice;
  return `<div class="ip-heading"><p class="ip-state">${esc(r.label(d.unit_id))} · ${d.dirty?'Unsaved changes':d.revision?'Saved':'Not saved'} · ${d.reviewed&&!d.stale&&!d.sourceChanged?'Confirmed':'Review pending'}</p><button data-ip="edit" aria-pressed="${editing}" ${editDisabled}>${editing?'Done editing':'Edit'}</button></div><p class="ip-notice" role="status">${esc(notice)}</p>
   ${d.context_error?`<p class="ip-warning" role="status">${esc(d.context_error)} Saved interpretation text is retained; current source wording is unavailable.</p>`:''}
   ${d.stale||d.sourceChanged?'<p class="ip-warning">Source changed. Refresh before saving or generating.</p><button data-ip="context">Refresh source</button>':''}
   <div class="ip-generate"><button data-ip="generate" ${disabled||!d.provider?.available||d.generation?'disabled':''}>${d.generation?'Generating candidates…':'Generate AI candidates'}</button>${!d.provider?.available?'<span class="ip-caption">AI: Not connected · manual editing available</span>':''}</div>
   <p class="ip-caption">Fill in your interpretation. AI candidates enter the draft only after individual approval.</p>
   ${editing?`<details data-disclosure="check-context"><summary>Check context</summary>${domainMarkup(design,editDisabled)}</details>`:''}
   ${cardKeys.map((key,i)=>`<section class="ip-group" data-card="${key}"><h4>${['Scope · A','Condition · B','Demand · C'][i]}</h4><details class="ip-mapped" data-disclosure="mapped-${key}"><summary>From third-column annotations · program-combined</summary><blockquote class="ip-source-wording" tabindex="0" aria-label="${['Scope','Conditions','Demands'][i]} mapped wording">${esc(derived[key].value||'No wording assigned in the third pane.')}</blockquote><p class="ip-caption">Recorded wording and grouping only. You decide its meaning here.</p>${editing&&!design.groups[key]?`<button data-ip="use-mapped" data-field="${key}" ${disabled||!derived[key].value?'disabled':''}>Copy as starting text</button>`:''}</details><p class="ip-caption" data-card-status="${key}">${cardApproved(d,key)?'Approved'+(Object.hasOwn(d.pendingApprovals||{},key)?' · save pending':''):'Draft · not approved'}</p>${editing?(design.groups[key]?ruleMarkup(design,key,editDisabled,d.catalog):`${this.fieldMarkup(d,key,['Scope Logic','Condition Logic','Demand Logic'][i])}${ruleMarkup(design,key,editDisabled,d.catalog)}`):design.groups[key]?ruleSummaryMarkup(design,key):`<p>${esc(d.fields[key].value||d.fields[key].absence_reason||'Not yet defined.')}</p>`}<details data-disclosure="support-${key}"><summary>${esc(interpretationLabels[interpretationKeys.indexOf(logicKeys[i])])}</summary>${this.fieldMarkup(d,logicKeys[i],interpretationLabels[interpretationKeys.indexOf(logicKeys[i])])}</details><button data-ip="approve-card" data-field="${key}" ${disabled||cardApproved(d,key)||(!logicText(design.groups[key])&&!d.fields[key].value?.trim()&&fieldState(d.fields[key])!=='not_stated')?'disabled':''}>Approve ${key}</button>${this.cardCandidate(d,key,i,disabled)}</section>`).join('')}
   <p class="rd-error" role="alert"></p><section class="ip-logic ip-set-output" aria-label="Checking relationship">${logicMarkup(logic)}</section>
   <details class="ip-evidence-panel" data-disclosure="sources"><summary>Evidence</summary><button data-ip="source">Locate source</button>${cardKeys.map((key,i)=>`<section><h5>${['Scope','Condition','Demand'][i]}</h5>${design.groups[key]||!editing?this.fieldMarkup(d,key,'',true):''}</section>`).join('')}</details>
   <details class="ip-more" data-disclosure="more"><summary>More</summary>
    ${!editing?`<details data-disclosure="check-context"><summary>Check context</summary><p><strong>Check object</strong><br>${esc(design.object_type||'Not specified.')}</p><p><strong>Period / event</strong><br>${esc(design.assessment_context||'Not specified.')}</p></details>`:''}
    <details class="ip-context" data-disclosure="context"><summary>Source context</summary><p>${esc(d.provider?.destination||'AI service: Not connected')} ${esc(d.provider?.model||'')}</p><p>Full saved materials used for interpretation:</p><ul>${(d.context?.materials||[]).map(x=>`<li>${esc(x.title||x.id)} · revision ${x.revision}</li>`).join('')}</ul><div class="ip-source-actions"><button data-ip="trace" ${d.revision?'':'disabled'}>Source trail</button><button data-ip="context">Refresh source</button><button data-ip="related" ${disabled}>Add related saved context</button>${(d.linked_material_ids||[]).map(id=>`<button data-ip="remove-related" data-material="${esc(id)}" ${disabled}>Remove: ${esc(d.context?.materials.find(m=>m.id===id)?.title||id)}</button>`).join('')}</div></details>
    <details data-disclosure="history"><summary>History</summary><button data-ip="reload" ${disabled}>Reload saved interpretation</button>${(d.history||[]).map(h=>`<p>Revision ${h.revision} · ${esc(h.edited_by||'Author not recorded')} · ${esc(h.at||'')} <button data-ip="restore" data-revision="${h.revision}" ${disabled}>Restore</button></p>`).join('')}</details>
    ${designMarkup(design,disabled,d.catalog,logic.handoff)}
   </details>
   <div class="ip-save"><button data-ip="save" ${disabled||(!d.dirty&&d.revision)?'disabled':''}>Save draft</button><button class="primary" data-ip="review" ${disabled||d.reviewed||d.dirty||!d.revision||d.stale||d.sourceChanged||cardKeys.some(k=>!cardApproved(d,k))||conceptGaps.length||interpretationKeys.some(k=>!reviewReady(logicFields(d.fields,design)[k]))?'disabled':''}>Confirm interpretation</button>${d.retry?'<button data-ip="retry">Retry save</button>':''}</div>`;
 }
 async suggestLogic(k){
  const d=this.draft,key=this.active;if(!d.provider?.available||d.logicCandidates?.[k]?.status==='generating')return;
  if(this.m.requirements?.dirty)throw Error('Save Requirement splitting before generating its logic.');
  if(d.stale||d.sourceChanged)throw Error('Refresh the changed source before generating.');
  d.logicCandidates||={};const previous=d.logicCandidates[k];
  const c=d.logicCandidates[k]={value:previous?.value??d.fields[k].value,status:'generating',edited:false,previous};
  this.changed();this.render();
  try{const run=await this.m.api('/api/interpretations/generate',{request_id:crypto.randomUUID(),unit_id:d.unit_id,fields:[k],linked_material_ids:d.linked_material_ids,context_fingerprint:d.context.fingerprint,confirm_context:true});c.run=run.id;this.watchLogic(run.id,key,k,c);}
  catch(e){c.status='error';this.notice=e.message;if(c.edited)d.fields[k]={...d.fields[k],value:c.value,basis:'interpretation'};if(previous&&!c.edited)d.logicCandidates[k]=previous;else delete d.logicCandidates[k];this.render();}
 }
 async watchLogic(id,key,k,c){
  try{const run=await this.m.api('/api/interpretations/run?'+new URLSearchParams({id})),d=this.drafts.get(key);if(!d||d.logicCandidates?.[k]!==c)return;
   if(run.status==='running'){setTimeout(()=>this.watchLogic(id,key,k,c),1500);return;}
   if(run.status!=='ready'||run.context_fingerprint!==d.context.fingerprint){c.status='error';this.notice=run.error||'The source changed. Generate again.';if(c.edited)d.fields[k]={...d.fields[k],value:c.value,basis:'interpretation'};if(c.previous&&!c.edited)d.logicCandidates[k]=c.previous;else delete d.logicCandidates[k];}
   else{c.status='ready';c.context_fingerprint=run.context_fingerprint;c.suggestion=run.suggestions[k];if(!c.edited)c.value=c.suggestion.value;this.notice='Candidate ready. Edit it freely, then Accept.';}
   if(this.active===key)this.render();
  }catch(e){c.status='error';const d=this.drafts.get(key);if(d?.logicCandidates?.[k]===c){if(c.edited)d.fields[k]={...d.fields[k],value:c.value,basis:'interpretation'};if(c.previous&&!c.edited)d.logicCandidates[k]=c.previous;else delete d.logicCandidates[k];}this.notice=e.message;if(this.active===key)this.render();}
 }
 refreshOutput(){const d=this.draft,output=this.host?.querySelector?.('.ip-set-output');if(output){const logic=checkingLogic(d.fields,d.context?.exceptions,setDesign(d.check_design||emptyDesign()),d.context?.fingerprint,d.catalog);logic.gaps=[...new Set([...logic.gaps,...conceptIssues(d.check_design)])];output.innerHTML=logicMarkup(logic);const h=logic.handoff,preview=this.host.querySelector('.rd-handoff-preview'),gaps=this.host.querySelector('.rd-mapping-gaps'),summary=this.host.querySelector('.rd-mapping-summary');if(preview)preview.textContent=JSON.stringify(h,null,2);if(gaps)gaps.innerHTML=h.gaps.map(g=>`<li>${esc(g)}</li>`).join('');if(summary)summary.textContent='Set handoff & mapping questions ('+h.gaps.length+')';const integration=this.host.querySelector('.ip-rule-design > summary');if(integration)integration.textContent='Data integration · '+(h.mapping_status==='incomplete'?'mapping incomplete':'ready for consumer validation');}const review=this.host?.querySelector?.('[data-ip="review"]');if(review)review.disabled=true;}
 changed(){const d=this.draft;d.dirty=true;d.reviewed=false;d.workingStored=false;d.check_design=setDesign(d.check_design||emptyDesign());d.check_design.based_on=null;d.changeNumber=(d.changeNumber||0)+1;const state=this.host?.querySelector?.('.ip-state');if(state)state.textContent='Unsaved changes';
  for(const key of cardKeys){if(!cardApproved(d,key)){delete d.approvalSnapshots?.[key];delete d.pendingApprovals?.[key];}const label=this.host?.querySelector?.(`[data-card-status="${key}"]`),button=this.host?.querySelector?.(`[data-ip="approve-card"][data-field="${key}"]`);if(label)label.textContent=cardApproved(d,key)?'Approved'+(Object.hasOwn(d.pendingApprovals||{},key)?' · save pending':''):'Draft · not approved';if(button)button.disabled=!!(this.pending||this.loading||this.m.collaboration?.readonly||cardApproved(d,key)||(!logicText(d.check_design.groups[key])&&!d.fields[key].value?.trim()&&fieldState(d.fields[key])!=='not_stated'));}
  this.refreshOutput();const save=this.host?.querySelector?.('[data-ip="save"]');if(save)save.disabled=!!(this.pending||this.loading||d.retry||this.m.collaboration?.readonly);}
 approveCard(key,runId=null){
  const d=this.draft;if(!cardKeys.includes(key))throw Error('Choose Scope, Condition or Demand.');
  if(this.pending||this.m.collaboration.readonly)throw Error('This interpretation is not editable right now.');
  if(d.stale||d.sourceChanged||this.m.requirements?.dirty)throw Error('Save the Requirement and refresh its context before approving.');
  if(!logicText(d.check_design?.groups[key])&&!d.fields[key].value?.trim()&&fieldState(d.fields[key])!=='not_stated')throw Error('Fill this card before approving.');
  d.approvalSnapshots||={};d.pendingApprovals||={};d.approvalSnapshots[key]=cardSnapshot(d,key);d.pendingApprovals[key]=runId;this.changed();
  this.notice=key[0].toUpperCase()+key.slice(1)+' approved in this draft. Save to record your approval.';this.render();
 }
 async persistWorking(){} // No background writes to browser storage or the server.
 async clearWorking(d){d.dirty=false;d.retry=null;}
 async showDrafts(){
  try{const data=await this.m.api('/api/interpretations/drafts');this.m.dialog(`<h2>Interpretation working copies</h2><p>These are kept separately from formal saves and review decisions.</p>${data.drafts.length?data.drafts.map(x=>`<p>${esc(x.title||x.unit_id)}<br><button data-inspect-draft data-unit="${esc(x.unit_id)}">View working copy</button><button data-resume-draft data-unit="${esc(x.unit_id)}" data-material="${esc(x.material_id)}">Resume working copy</button></p>`).join(''):'<p>No saved working copies.</p>'}`);this.m.q('#mw-dialog').querySelectorAll('[data-inspect-draft]').forEach(b=>b.onclick=async()=>{const x=await this.m.api('/api/interpretations/drafts?'+new URLSearchParams({unit_id:b.dataset.unit}));this.m.dialog(`<h2>Saved working copy</h2><p>${esc(x.body?.title||b.dataset.unit)}</p><pre>${esc(JSON.stringify(x.body,null,2))}</pre>`);});this.m.q('#mw-dialog').querySelectorAll('[data-resume-draft]').forEach(b=>b.onclick=async()=>{this.m.q('#mw-dialog').close();if(b.dataset.material!==this.m.id||!this.m.material)await this.m.open(b.dataset.material);else this.m.showDetail();if(this.m.id!==b.dataset.material)return;this.m.revealPane('interpretation');await this.open(b.dataset.unit);});}catch(e){this.m.message(e.message,'warning');}
 }
 async showImpacts(){
  try{const result=await this.m.api('/api/interpretations/impacts?'+new URLSearchParams({material_id:this.m.id}));this.m.dialog(`<h2>Requirements needing source review</h2>${result.requirements.length?result.requirements.map(x=>`<section><p>${esc(x.title)}</p><p>${x.items.length} dependency changes · ${esc(x.message)}</p><button data-open-impact data-unit="${esc(x.unit_id)}">Review affected fields</button></section>`).join(''):'<p>No changed dependencies found in saved interpretations for this material.</p>'}`);this.m.q('#mw-dialog').querySelectorAll('[data-open-impact]').forEach(b=>b.onclick=()=>{this.m.q('#mw-dialog').close();void this.open(b.dataset.unit);});}catch(e){this.m.message(e.message,'warning');}
 }
 async action(action,node){
  const d=this.draft,k=node.closest('[data-ip-field]')?.dataset.ipField,field=k?d.fields[k]:null;
  if(action==='edit'){this.editing=this.editing===this.active?null:this.active;this.render();this.host?.querySelector?.('[data-ip="edit"]')?.focus();return;}
  if(action==='approve-card')return this.approveCard(node.dataset.field);
  if(action==='dismiss-card'){d.candidate.dismissed=[...(d.candidate.dismissed||[]),node.dataset.field];return this.render();}
  if(action==='accept-card'){
   const key=node.dataset.field,c=d.candidate;if(!c?.suggestions?.[key])return;
   if(this.pending||this.m.collaboration.readonly||this.m.requirements?.dirty)throw Error('Save the Requirement before approving a candidate.');
   if(d.stale||d.sourceChanged||c.context_fingerprint!==d.context?.fingerprint)throw Error('This candidate belongs to an older source. Generate again.');
   if(!logicText(c.check_design?.groups[key])&&!c.suggestions[key].value?.trim()&&fieldState(c.suggestions[key])!=='not_stated')throw Error('This candidate is empty. Fill in your interpretation or generate again.');
   for(const field of [key,logicKeys[['scope','condition','demand'].indexOf(key)]])if(c.suggestions[field])d.fields[field]=copy(c.suggestions[field]);
   if(c.check_design){
    d.check_design=setDesign(d.check_design||emptyDesign());d.check_design.concepts||=[];c.termIds||={};
    const group=copy(c.check_design.groups[key]);const walk=n=>{n.id=crypto.randomUUID();if(n.rules)n.rules.forEach(walk);else n.concept_ids=(n.concept_ids||[]).map(id=>{c.termIds[id]||=crypto.randomUUID();const target=c.termIds[id];if(!d.check_design.concepts.some(t=>t.id===target))d.check_design.concepts.push({...copy(c.check_design.concepts.find(t=>t.id===id)),id:target,status:'proposed'});return target;});};if(group)walk(group);d.check_design.groups[key]=group;
    if(!d.check_design.object_type)d.check_design.object_type=c.check_design.object_type;
    if(!d.check_design.assessment_context)d.check_design.assessment_context=c.check_design.assessment_context;
   }else if(d.check_design){d.check_design.groups[key]=null;}
   pruneConcepts(d.check_design);
   c.accepted=[...(c.accepted||[]),key];return this.approveCard(key,c.id||null);
  }
  if(action==='use-mapped'){
   const key=node.dataset.field,value=sourceSections(d.context)[key]?.value;if(!value)return;
   const apply=()=>{d.fields[key]=copy(sourceSections(d.context)[key]);this.changed();this.render();};
   if(d.fields[key].value.trim()){this.m.dialog('<h2>Replace this Logic with mapped wording?</h2><p>The current draft text will be replaced. Saved history remains available.</p><button data-ip-confirm>Use mapped wording</button>');this.m.q('[data-ip-confirm]').onclick=()=>{this.m.q('#mw-dialog').close();apply();};return;}apply();return;
  }
  if(action==='confirm-mappings'){
   this.changed();d.check_design.based_on={fields:Object.fromEntries(interpretationKeys.map(key=>[key,d.fields[key].value])),context_fingerprint:d.context?.fingerprint||'',catalog_revision:d.catalog?.revision||0,design:copy(Object.fromEntries(Object.entries(d.check_design).filter(([k])=>k!=='based_on')))};this.notice='Mapping confirmation saved in this draft. Unmapped predicates and incomplete definitions remain unresolved.';return this.render();
  }
  if(action==='suggest-logic')return this.suggestLogic(k);
  if(action==='accept-logic'){
   const c=d.logicCandidates?.[k];if(c?.status!=='ready')return;
   if(d.stale||d.sourceChanged||c.context_fingerprint!==d.context.fingerprint)throw Error('This candidate belongs to an older source. Regenerate it.');
   d.fields[k]={...copy(c.suggestion),value:c.value,basis:'interpretation',state:c.value.trim()?'specified':'unresolved'};delete d.logicCandidates[k];this.changed();this.notice='Accepted into your draft. Save when ready.';return this.render();
  }
  if(action==='impacts')return this.showImpacts();
  if(action==='working-retry'){await this.persistWorking(this.active);this.render();return;}
  if(action==='working-conflict'){
   const remote=await this.m.api('/api/interpretations/drafts?'+new URLSearchParams({unit_id:d.unit_id}));
   this.m.dialog(`<h2>Compare working copies</h2><h3>This window</h3><pre>${esc(JSON.stringify(d.fields,null,2))}</pre><h3>Saved working copy</h3><pre>${esc(JSON.stringify(remote.body?.fields||{},null,2))}</pre><p>Choose the working copy to continue. Formal saved interpretations remain unchanged.</p><button data-keep-local>Keep this window’s edits</button><button data-use-remote ${remote.body?'':'disabled'}>Use saved working copy</button>`);
   this.m.q('[data-keep-local]').onclick=async()=>{d.draftRevision=remote.revision;d.workingRequest=null;d.workingConflict=false;this.m.q('#mw-dialog').close();await this.persistWorking(this.active);this.render();};
   this.m.q('[data-use-remote]').onclick=()=>{Object.assign(d,remote.body,{draftRevision:remote.revision,workingRequest:null,workingConflict:false,workingStored:true,dirty:true});this.journal();this.m.q('#mw-dialog').close();this.render();};return;
  }
  if(action==='focus-field'){const el=this.host.querySelector('[data-ip-field="'+node.dataset.field+'"]');el.scrollIntoView({block:'start'});el.querySelector('textarea').focus();return;}
  if(action==='trace'){
   const trail=await this.m.api('/api/interpretations/trace?'+new URLSearchParams({unit_id:d.unit_id,revision:d.revision}));
   this.m.dialog(`<h2>Saved source trail</h2><p>Interpretation revision ${trail.revision} → Requirement ${esc(trail.unit_id)} → splitting revision ${trail.session_revision}</p><p>${esc(trail.source.source_id)} · ${esc(trail.chapter||'Source passage')} · material revision ${trail.material_revision}</p><p>Saved extracted passage:</p><blockquote>${esc(Array.from(trail.original_text).slice(trail.start,trail.end).join(''))}</blockquote><p>Block ${esc(trail.block_id)} · characters ${trail.start}–${trail.end} (Unicode)</p>${trail.fields.sort((a,b)=>interpretationKeys.indexOf(a.key)-interpretationKeys.indexOf(b.key)).map(f=>`<details><summary>${esc(interpretationLabels[interpretationKeys.indexOf(f.key)])} · ${f.references.length} citations</summary><p>${esc(f.value)}</p>${f.references.map(r=>`<blockquote>${esc(r.quote)}</blockquote><p>${esc(r.source.source_id||r.material_id)} · ${esc(r.block_id||'document information')} · ${esc(r.anchor_status)}</p>`).join('')}</details>`).join('')}${trail.concepts?.length?`<details><summary>Concepts (${trail.concepts.length})</summary>${trail.concepts.map(c=>`<p>${esc(c.label)} · ${esc(c.kind)} · ${esc(c.status)} · ${esc(c.id)}</p>${c.references.map(ref=>`<blockquote>${esc(ref.quote)}</blockquote><p>${esc(ref.id)}</p>`).join('')}`).join('')}</details>`:''}${trail.rules?.length?`<details><summary>Rule mappings (${trail.rules.length} nodes)</summary>${trail.rules.filter(r=>r.field_key).map(r=>`<p>${esc(r.rule.expression||r.rule.field)} ${esc(r.rule.operator||'')} → ${esc(interpretationLabels[interpretationKeys.indexOf(r.field_key)])}</p>`).join('')}</details>`:''}<details><summary>Original version and location</summary><pre>${esc(JSON.stringify({source:trail.source,locations:trail.source_refs},null,2))}</pre></details><p>Saved evidence remains tied to this version even when current text changes.</p>`);return;
  }
  if(action==='switch')return this.open(node.dataset.unit);
  if(action==='source'){const r=this.m.requirements;if(r.doc?.id!==d.context?.session_id)await r.open(d.context.session_id);this.m.revealPane('content');const i=this.m.draft.blocks.findIndex(b=>b.id===r.doc?.block_id);if(i>=0)this.m.jumpToBlock(i);return;}
  if(action==='context'){
   const ids=d.linked_material_ids||[];const ctx=await this.m.api('/api/interpretations/context',{unit_id:d.unit_id,linked_material_ids:ids});
   if(d.context?.fingerprint!==ctx.fingerprint)for(const term of d.check_design?.concepts||[])term.status='proposed';d.context=ctx;d.linked_material_ids=ids;d.context_error=null;d.stale=false;d.sourceChanged=false;this.changed();this.notice='Context refreshed. Check each card against these source versions.';return this.render();
  }
  if(action==='related'){
   const catalog=await this.m.api('/api/materials?limit=100');
   const available=(catalog.materials||[]).filter(x=>x.id!==this.m.id&&!(d.linked_material_ids||[]).includes(x.id));
   this.m.dialog(`<h2>Add related saved material</h2><p>Only explicitly selected local materials join the interpretation context.</p><label>Material<select data-ip-related>${available.map(x=>`<option value="${esc(x.id)}">${esc(x.title||x.id)}</option>`).join('')}</select></label><button data-ip-confirm ${available.length?'':'disabled'}>Add to context</button>`);
   this.m.q('[data-ip-confirm]').onclick=async()=>{const id=this.m.q('[data-ip-related]').value;try{const ids=[...(d.linked_material_ids||[]),id];const ctx=await this.m.api('/api/interpretations/context',{unit_id:d.unit_id,linked_material_ids:ids});if(d.context?.fingerprint!==ctx.fingerprint)for(const term of d.check_design?.concepts||[])term.status='proposed';d.context=ctx;d.linked_material_ids=ids;this.changed();this.m.q('#mw-dialog').close();this.notice='Related material added. Review the updated context before generating.';this.render();}catch(e){this.m.message(e.message,'warning');}};return;
  }
  if(action==='remove-related'){d.linked_material_ids=d.linked_material_ids.filter(x=>x!==node.dataset.material);this.changed();return this.action('context',node);}
  if(action==='add-ref'){const el=node.closest('[data-ip-field]'),id=el.querySelector('[data-ip-citation]').value,quote=el.querySelector('[data-ip-quote]').value,c=d.context?.citations.find(c=>c.id===id);if(!quote||!c?.text.includes(quote))throw Error('Use an exact nonempty quotation from the selected saved block.');field.references.push({id,quote});this.changed();return this.render();}
  if(action==='remove-ref'){field.references.splice(Number(node.dataset.ref),1);this.changed();return this.render();}
  if(action==='use'){
   const suggestion=d.candidate.suggestions[k];if(d.candidate.context_fingerprint!==d.context?.fingerprint)throw Error('Candidate source versions changed. Generate a current suggestion.');
   const adopt=()=>{d.fields[k]=copy(suggestion);this.changed();this.notice='Suggestion adopted into the editable draft. Save and review remain separate.';this.render();};
   if(field.value||field.references.length){this.m.dialog(`<h2>Replace this field?</h2><h3>Current edited value</h3><pre>${esc(JSON.stringify(field,null,2))}</pre><h3>Candidate value and references</h3><pre>${esc(JSON.stringify(suggestion,null,2))}</pre><button data-ip-confirm>Replace with suggestion</button><p>Closing this dialog keeps your current value.</p>`);this.m.q('[data-ip-confirm]').onclick=()=>{this.m.q('#mw-dialog').close();adopt();};return;}adopt();return;
  }
  if(action==='generate'||action==='generate-one'){
   if(!d.provider?.available)throw Error('AI: Not connected. Configure the API in Settings, or fill in the draft yourself.');
   if(this.m.collaboration.readonly||this.pending||d.generation)throw Error('Wait for the current operation before generating.');
   if(this.m.requirements?.dirty)throw Error('Save Requirement splitting before generating.');
   if(d.sourceChanged||d.stale)throw Error('Refresh and review the source context before generating.');
   const key=this.active,request={request_id:crypto.randomUUID(),unit_id:d.unit_id,fields:action==='generate-one'?[k]:interpretationKeys,structured:action==='generate',linked_material_ids:d.linked_material_ids,context_fingerprint:d.context.fingerprint,confirm_context:true};
   this.m.dialog(`<h2>Generate all three candidates</h2><p>Generate Scope, Condition and Demand together from the complete saved materials and their third-column annotations:</p><p class="ip-address">${esc(d.provider.destination)} · ${esc(d.provider.model)}</p><ul>${d.context.materials.map(x=>`<li>${esc(x.title||x.id)} · revision ${x.revision}</li>`).join('')}</ul><p>Review and approve each candidate separately before it enters your draft. Existing text is kept until you approve its replacement.</p><button data-ip-confirm class="primary">Generate all three</button>`);
   this.m.q('[data-ip-confirm]').onclick=async()=>{this.m.q('[data-ip-confirm]').disabled=true;try{const run=await this.m.api('/api/interpretations/generate',request);d.generation=run;this.journal();this.m.q('#mw-dialog').close();this.notice='Generation in progress. Your formal fields remain editable.';this.render();this.watch(run.id,key);}catch(e){this.m.q('#mw-dialog').close();this.notice=e.message;this.render();}};return;
  }
  if(action==='reload'){
   if(d.dirty||d.retry){this.m.dialog('<h2>Reload saved interpretation?</h2><p>Your current unsaved draft will be replaced by the server version.</p><button data-ip-confirm>Reload saved version</button>');this.m.q('[data-ip-confirm]').onclick=async()=>{try{await this.clearWorking(d);this.m.q('#mw-dialog').close();this.drafts.delete(this.active);this.journal();void this.open(d.unit_id);}catch(e){this.m.message(e.message,'warning');}};return;}
   return this.open(d.unit_id);
  }
  if(['save','review','restore','retry'].includes(action))return this.save(action,node);
 }
 async save(action,node){
  const d=this.draft,key=this.active;if(this.pending)return;
  if(this.m.requirements?.dirty)throw Error('Save Requirement splitting before saving its interpretation.');if(d.savingWorking)throw Error('Working copy is still saving. Retry in a moment.');clearTimeout(d.autosaveTimer);
  const invalid=this.host?.querySelector(':invalid');if(invalid&&action!=='retry')throw Error(invalid.validationMessage||'Correct the rule value before saving.');
  if((d.stale||d.sourceChanged)&&action!=='retry')throw Error('Refresh the context, then review your fields before saving.');
  if(Object.keys(d.logicCandidates||{}).length)throw Error('Accept the AI candidates before saving. Your edits remain in the text boxes.');
  if(action==='review'&&cardKeys.some(k=>!cardApproved(d,k)))throw Error('Approve Scope, Condition and Demand individually, then save before confirming.');
  if(action==='save')d.check_design=setDesign(d.check_design||emptyDesign());
  const changeAtStart=action==='retry'?(d.retryChangeNumber??0):(d.changeNumber||0);
  if(action!=='retry')d.retryChangeNumber=changeAtStart;
  const request=action==='retry'?d.retry:{request_id:crypto.randomUUID(),unit_id:d.unit_id,expected_revision:d.revision,context_fingerprint:d.context?.fingerprint,linked_material_ids:d.linked_material_ids,fields:copy(d.fields),check_design:copy(d.check_design||emptyDesign()),approve_cards:action==='save'?Object.fromEntries(Object.entries(d.pendingApprovals||{}).filter(([k])=>cardApproved(d,k))):{},...(d.catalog?.revision?{catalog_revision:d.catalog.revision}:{}),action:action==='save'?'save':action,history_revision:Number(node?.dataset?.revision)};
  if(!request)return;this.pending=true;d.retry=request;this.journal();this.notice='Saving interpretation…';this.render();
  try{const result=await this.m.api('/api/interpretations/save',request);d.retry=null;d.dirty=false;d.draftRevision=result.draft_revision??d.draftRevision;this.journal();const saved=result.document||await this.m.api('/api/interpretations?'+new URLSearchParams({unit_id:d.unit_id}));if((d.changeNumber||0)!==changeAtStart){d.revision=saved.revision;d.context=saved.context;d.card_reviews=saved.card_reviews;for(const k of Object.keys(request.approve_cards||{}))if(cardSnapshot(d,k)===cardSnapshot(saved,k))delete d.pendingApprovals?.[k];d.dirty=true;this.notice='Saved. Newer edits remain unsaved.';}else{this.drafts.set(key,{...reviewDraft(saved),draftRevision:d.draftRevision,dirty:false,candidate:d.candidate});this.notice=action==='review'?'Interpretation confirmed.':'Draft and individual approvals saved.';}}
  catch(e){if(e.definitive){d.retry=null;if(e.status===409)d.sourceChanged=true;}this.notice=e.message+(d.retry?' Save outcome uncertain. Retry the same save before leaving.':'');this.journal();}
  finally{this.pending=false;this.render();}
 }
 async watch(id,key){
  try{const run=await this.m.api('/api/interpretations/run?'+new URLSearchParams({id}));const d=this.drafts.get(key);if(!d)return;
   if(run.status==='running'){setTimeout(()=>this.watch(id,key),1500);return;}
   d.generation=null;if(run.status==='ready'){d.candidate=run;this.notice='Three candidates ready. Approve each separately to fill your draft.';}
   else this.notice=run.error||'Candidate is stale. Refresh source context before generating again.';
   if(this.active===key)this.render();
  }catch(e){if(this.active===key){this.notice='Generation status unavailable. Reopen the requirement to recover its saved request.';this.render();}}
 }
}
