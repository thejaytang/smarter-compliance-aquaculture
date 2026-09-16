import {emptyDesign,designMarkup,bindDesign} from './check-design.js';
import {semanticFields,semanticClass} from './markdown-content.js';
// Interpretation is a source-bound design, not an executed compliance check.
export const interpretationKeys=['scope','scope_information','condition','condition_information','demand','verification'];
export const interpretationLabels=['Scope','Information needed to identify scoped objects','Condition','Information needed to determine applicability','Demand','Verification method and criteria'];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const copy=v=>structuredClone(v);
export const fieldState=f=>f?.state||(f?.value?.trim()&&f?.basis!=='unresolved'?'specified':'unresolved');
export const reviewReady=f=>!f.gaps?.length&&((fieldState(f)==='specified'&&!!f.value?.trim()&&f.basis!=='unresolved')||(fieldState(f)==='not_stated'&&!!f.absence_reason?.trim()&&!f.value?.trim()));
export function checkingLogic(fields,exceptions=[]){
 const values=Object.fromEntries(interpretationKeys.map(k=>[k,fieldState(fields[k])==='not_stated'?'Not explicitly stated in the reviewed source. '+(fields[k].absence_reason||''):(fields[k]?.value||'').trim()]));
 return {version:1,executable:false,steps:[
  {title:'Identify Set A',description:values.scope,information:values.scope_information},
  {title:'Determine Set B within A',description:values.condition,information:values.condition_information},
  {title:'Check Demand for each object in B',description:values.demand,information:values.verification}],exceptions,
  gaps:[...interpretationKeys.filter(k=>fieldState(fields[k])!=='specified'||!values[k]||fields[k]?.basis==='unresolved').map(k=>interpretationLabels[interpretationKeys.indexOf(k)]),...interpretationKeys.flatMap(k=>fields[k]?.gaps||[])],
  source_structure:{},rule:'B is a subset of A. In the same assessment context, check B ⊆ C, where C contains objects with sufficient evidence of meeting Demand.',
  boundary:'Check design only. Distinguish evidence of failure from insufficient information; no site assessment has been performed.'};
}
export function logicMarkup(logic){return `<h4>Checking Logic</h4><p class="ip-caption">Generated from the six formal fields · draft preview</p><ol>${logic.steps.map(s=>`<li><strong>${esc(s.title)}</strong><p>${esc(s.description||'Not specified')}</p><p>${esc(s.information||'Information needed is not specified')}</p></li>`).join('')}</ol><p>${esc(logic.rule)}</p>${logic.exceptions?.length?`<details><summary>Source exception relationships · keep their ownership</summary>${logic.exceptions.map(x=>`<p>Owner ${esc(x.owner_id)}: ${esc(x.text.join(' / '))}</p><pre>${esc(JSON.stringify(x.combination))}</pre>`).join('')}<p>Apply exceptions only within their stated scope. Missing scope remains unresolved.</p></details>`:''}${logic.gaps.length?`<p class="ip-warning">Unresolved information</p><ul>${logic.gaps.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}<p class="ip-caption">${esc(logic.boundary)}</p>`;}
export class InterpretationEditor{
 constructor(m){this.m=m;this.drafts=new Map();this.active=null;this.loading=false;this.pending=false;this.notice='';}
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
  this.restoreJournal();const key=this.key(uid),owner=this.owner();this.active=key;this.loading=true;this.notice='Loading interpretation…';this.render();
  try{const doc=await this.m.api('/api/interpretations?'+new URLSearchParams({unit_id:uid}));if(this.owner()!==owner||this.active!==key)return;
   const remote=null;
   if(this.owner()!==owner||this.active!==key)return;
   if(remote?.body&&!this.drafts.get(key)?.dirty){const b=remote.body;this.drafts.set(key,{...doc,...b,dirty:true,draftRevision:remote.revision,workingStored:true,context:doc.context,sourceChanged:b.context_fingerprint!==doc.context?.fingerprint||b.revision!==doc.revision});}
   const old=this.drafts.get(key);if(remote&&old?.dirty&&remote.revision!==old.draftRevision)old.workingConflict=true;if(old?.dirty||old?.retry){old.latest=doc;old.provider=doc.provider;old.sourceChanged=old.sourceChanged||old.context?.fingerprint!==doc.context?.fingerprint||old.revision!==doc.revision;old.catalog=doc.catalog;old.impact=doc.impact;}
   else this.drafts.set(key,{...doc,dirty:false,candidate:(doc.runs||[]).filter(r=>r.status==='ready'&&r.context_fingerprint===doc.context?.fingerprint).reverse().reduce((prev,r)=>({...r,suggestions:{...prev?.suggestions,...r.suggestions}}),null)});
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
  const host=this.host;if(!host)return;this.restoreJournal();
  const d=this.draft,valid=d&&this.active?.startsWith(this.owner()+':')&&!this.m.collaboration.readonly;
  if(!valid){if(this.loading){host.innerHTML='<p role="status">Loading saved source context for this interpretation…</p>';return;}host.innerHTML=`${this.notice?'<p class="ip-warning" role="alert">'+esc(this.notice)+'</p>':''}`+'<div class="ip-empty"><button data-ip-impact>Review changed sources</button><h4>Explain how this requirement can be checked</h4><p>Choose <strong>Interpret requirement</strong> in the third pane. Define Scope, Condition and Demand, then the information and evidence each needs.</p><p>The checking chain is generated from your six fields.</p></div>';const resume=host.querySelector?.('[data-ip-drafts]');if(resume)resume.onclick=()=>this.showDrafts();const impact=host.querySelector?.('[data-ip-impact]');if(impact)impact.onclick=()=>this.showImpacts();return;}
  const expanded=new Set([...host.querySelectorAll('details[open]')].map(x=>x.dataset.preserve||x.querySelector('summary')?.textContent));const position=host.scrollTop;
  d.check_design ||= emptyDesign();
  const locked=this.loading||this.pending||d.retry,disabled=locked?'disabled':'',suggestions=d.candidate?.suggestions||{};
  const other=[...this.drafts.entries()].filter(([k,x])=>k.startsWith(this.owner()+':')&&x.dirty);
  host.innerHTML=`<div class="ip-heading"><p class="ip-caption">Interpretation · revision ${d.revision||0}</p><p class="ip-state">${d.dirty?'Unsaved changes · save before leaving':d.reviewed?'Interpretation reviewed':d.revision?'Saved / not reviewed':'Not saved'}${d.stale||d.sourceChanged?' · needs source review':''}</p></div><p class="ip-notice" role="status">${esc(this.notice)}</p>${other.length?`<details><summary>${other.length} unsaved interpretation(s)</summary>${other.map(([k,x])=>`<button data-ip="switch" data-unit="${esc(x.unit_id)}">${esc(x.context?.requirement?.text?.slice(0,80)||x.unit_id)}</button>`).join('')}</details>`:''}
   <blockquote class="ip-original">${esc(d.context?.requirement?.text||d.latest?.context?.requirement?.text||'Current source unavailable')}</blockquote><div class="ip-source-actions"><button data-ip="impacts">Review changed sources</button><button data-ip="source">Locate source</button><button data-ip="trace" ${d.revision?'':'disabled'}>Source trail</button></div>
   ${d.stale||d.sourceChanged?`<button data-ip="context" ${disabled}>Review updated source context</button>`:''}
   ${d.impact?.status==='changed'||d.impact?.status==='legacy'?`<details class="ip-impact"><summary>What needs review${d.impact.items?.length?' · '+d.impact.items.length+' changes':''}</summary><p>${esc(d.impact.message)}</p>${(d.impact.items||[]).map(x=>`<section><p>${esc(x.reason.replaceAll('_',' '))} · ${esc(x.block_id||x.session_id||'Context')}</p>${x.before!==undefined?`<details><summary>Compare saved and current passage</summary><h5>Previously used</h5><blockquote>${esc(x.before)}</blockquote><h5>Current text</h5><blockquote>${esc(x.after??'Unavailable')}</blockquote></details>`:''}<p>${x.fields.length?'Review: '+x.fields.map(k=>interpretationLabels[interpretationKeys.indexOf(k)]).join(', '):'Context changed; decide whether this affects the interpretation.'}</p>${x.fields.map(k=>`<button data-ip="focus-field" data-field="${k}">${esc(interpretationLabels[interpretationKeys.indexOf(k)])}</button>`).join('')}<p>${x.rules.length?'Affected rules: '+esc(x.rules.join(', ')):''}</p></section>`).join('')}</details>`:''}
   ${d.context_error?`<p class="ip-warning">${esc(d.context_error)}</p>`:''}
   <details class="ip-context"><summary>Material scope &amp; AI service</summary><p>${esc(d.provider?.status||'Not connected')}</p><p class="ip-address">${esc(d.provider?.destination||'Set up the shared API in Settings → AI service')} ${esc(d.provider?.model||'')}</p><ul>${(d.context?.materials||[]).map(x=>`<li>${esc(x.title||x.id)} · saved revision ${x.revision} · ${esc(x.review_status)}</li>`).join('')}</ul><p>Full saved text, the selected requirement and related splitting are included. Missing or unreviewed information stays unresolved.</p><p>Explicitly related local materials</p>${(d.linked_material_ids||[]).map(id=>`<p>${esc(d.context?.materials?.find(m=>m.id===id)?.title||id)} <button data-ip="remove-related" data-material="${esc(id)}" ${disabled}>Remove</button></p>`).join('')}<button data-ip="related" ${disabled}>Add related material</button><button data-ip="context" ${disabled}>Review / refresh context</button>${(d.context?.limitations||[]).map(x=>`<p class="ip-caption">${esc(x)}</p>`).join('')}</details>
   <div class="ip-actions"><p class="ip-caption">AI service: ${esc(d.provider?.status||'Not connected')}</p><button data-ip="generate" ${disabled||!d.provider?.available?'disabled':''}>Generate six suggestions</button>${d.retry?'<button data-ip="retry">Retry the same save</button>':''}${d.workingConflict?'<button data-ip="working-conflict">Compare working copies</button>':d.dirty&&!d.workingStored?'<button data-ip="working-retry">Save working copy now</button>':''}</div>
   ${[0,2,4].map((start,g)=>`<section class="ip-group"><h4>${['Scope','Condition','Demand'][g]}</h4>${interpretationKeys.slice(start,start+2).map((k,i)=>{const f=d.fields[k],s=suggestions[k];return `<div class="ip-field" data-ip-field="${k}"><label>Source status<select data-ip-state ${disabled}>${Object.entries({specified:'Specified',not_stated:'Not explicitly stated',unresolved:'Unresolved'}).map(([v,t])=>`<option value="${v}" ${fieldState(f)===v?'selected':''}>${t}</option>`).join('')}</select></label><label>${start+i+1}. ${interpretationLabels[start+i]}<textarea data-ip-value ${disabled} rows="3">${esc(f.value)}</textarea></label>${fieldState(f)==='not_stated'?`<label>Why this is not explicitly stated<textarea data-ip-absence ${disabled} rows="2">${esc(f.absence_reason||'')}</textarea></label><p class="ip-caption">This records an absence in the reviewed context. It does not mean the requirement applies unconditionally.</p>`:''}<details class="ip-evidence" data-preserve="evidence-${k}"><summary>Evidence &amp; gaps · ${f.references?.length||0} references${f.gaps?.length?' · '+f.gaps.length+' gaps':''}</summary><div class="ip-field-meta"><label>Basis<select data-ip-basis ${disabled}>${['source','interpretation','unresolved'].map(x=>`<option value="${x}" ${f.basis===x?'selected':''}>${{source:'Explicit source wording',interpretation:'Interpretation / proposed design',unresolved:'Unresolved'}[x]}</option>`).join('')}</select></label><label>Unresolved items (one per line)<textarea data-ip-gaps ${disabled} rows="2">${esc((f.gaps||[]).join('\n'))}</textarea></label></div>
    <details><summary>Source references (${f.references?.length||0})</summary>${(f.references||[]).map((r,n)=>`<blockquote class="${this.referenceClass(r,d)}">${esc(r.quote)}<footer>${esc(r.id)}</footer><button data-ip="remove-ref" data-ref="${n}" ${disabled}>Remove reference</button></blockquote>`).join('')}<label>Source block<select data-ip-citation ${disabled}>${(d.context?.citations||[]).map(c=>`<option value="${esc(c.id)}">${esc(c.text.slice(0,100))}</option>`).join('')}</select></label><label>Exact quotation<textarea data-ip-quote ${disabled}></textarea></label><button data-ip="add-ref" ${disabled}>Add quotation</button></details></details>
    <details class="ip-candidate" data-preserve="candidate-${k}" ${s?'open':''}><summary>${s?'Review AI candidate':'AI assistance'}</summary>${s?`<p>${esc(s.value)}</p><p class="ip-caption">${esc(s.basis)} · ${esc(s.gaps.join('; '))}</p>${s.references.map(r=>`<blockquote class="${this.referenceClass(r,d)}">${esc(r.quote)}<footer>${esc(r.id)}</footer></blockquote>`).join('')}<button data-ip="use" ${disabled||d.candidate.context_fingerprint!==d.context?.fingerprint||d.candidate.status!=='ready'?'disabled':''}>Use suggestion</button>`:'<p class="ip-caption">No candidate yet. Manual editing is available.</p>'}<button data-ip="generate-one" ${disabled||!d.provider?.available?'disabled':''}>Generate this field</button></details></div>`;}).join('')}</section>`).join('')}
   ${designMarkup(d.check_design,disabled,d.catalog)}
   <section class="ip-logic" aria-label="Generated checking logic">${logicMarkup(checkingLogic(d.fields,d.context?.exceptions))}</section>
   <details><summary>Preserved source structure</summary><p>Quantities and nested branches retain their original meaning. They are not inferred from free text.</p><pre>${esc(JSON.stringify(d.context?.sessions?.map(x=>({id:x.id,revision:x.revision,roots:x.roots,units:x.units})),null,2))}</pre></details>
   <div class="ip-save"><button data-ip="save" class="primary" ${disabled||d.context_error?'disabled':''}>Save interpretation</button><button data-ip="review" ${disabled||d.dirty||!d.revision||d.stale||d.sourceChanged||interpretationKeys.some(k=>!reviewReady(d.fields[k]))?'disabled':''}>Mark interpretation reviewed</button></div>
   <details><summary>History &amp; recovery</summary><button data-ip="reload" ${disabled}>Reload saved version</button><p>Restore creates a new revision. Full workspace snapshots include saved splitting and interpretations. Working copies remain local until formally saved.</p>${(d.history||[]).map(h=>`<p>Revision ${h.revision} · ${esc(h.action)} · ${esc(h.at)} <button data-ip="restore" data-revision="${h.revision}" ${disabled}>Restore</button></p>`).join('')}</details>`;
  host.querySelectorAll('details').forEach(x=>{if(expanded.has(x.dataset.preserve||x.querySelector('summary')?.textContent))x.open=true;});host.scrollTop=position;
  bindDesign(host,d.check_design,()=>{this.changed();host.querySelector('.ip-state').textContent='Unsaved draft';host.querySelector('[data-ip="review"]').disabled=true;},()=>this.render(),d.catalog);
  host.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='s'){e.preventDefault();e.stopPropagation();if(!locked)void this.save('save',{dataset:{}}).catch(error=>{this.notice=error.message;this.render();});}};
  host.onclick=e=>{const b=e.target.closest('[data-ip]');if(!b||b.disabled)return;void this.action(b.dataset.ip,b).catch(error=>{this.notice=error.message;this.render();});};
  host.querySelectorAll('[data-ip-field]').forEach(el=>{const k=el.dataset.ipField;el.querySelectorAll('[data-ip-value],[data-ip-basis],[data-ip-gaps],[data-ip-state],[data-ip-absence]').forEach(input=>input.oninput=()=>{if(input.matches('[data-ip-value]')&&(d.fields[k].basis==='source'||(input.value.trim()&&d.fields[k].basis==='unresolved'&&!d.fields[k].gaps.length)))el.querySelector('[data-ip-basis]').value='interpretation';d.fields[k].state=el.querySelector('[data-ip-state]').value;if(input.matches('[data-ip-value]')&&input.value.trim())d.fields[k].state='specified';el.querySelector('[data-ip-state]').value=d.fields[k].state;d.fields[k].absence_reason=el.querySelector('[data-ip-absence]')?.value||d.fields[k].absence_reason||'';d.fields[k].value=el.querySelector('[data-ip-value]').value;d.fields[k].basis=el.querySelector('[data-ip-basis]').value;d.fields[k].gaps=el.querySelector('[data-ip-gaps]').value.split('\n').filter(x=>x.trim());this.changed();if(input.matches('[data-ip-state]'))return this.render();host.querySelector('.ip-logic').innerHTML=logicMarkup(checkingLogic(d.fields,d.context?.exceptions));host.querySelector('.ip-state').textContent='Unsaved draft';host.querySelector('[data-ip="review"]').disabled=true;});});
 }
 changed(){const d=this.draft;d.dirty=true;d.reviewed=false;d.workingStored=false;d.changeNumber=(d.changeNumber||0)+1;}
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
   this.m.dialog(`<h2>Saved source trail</h2><p>Interpretation revision ${trail.revision} → Requirement ${esc(trail.unit_id)} → splitting revision ${trail.session_revision}</p><p>${esc(trail.source.source_id)} · ${esc(trail.chapter||'Source passage')} · material revision ${trail.material_revision}</p><p>Saved extracted passage:</p><blockquote>${esc(Array.from(trail.original_text).slice(trail.start,trail.end).join(''))}</blockquote><p>Block ${esc(trail.block_id)} · characters ${trail.start}–${trail.end} (Unicode)</p>${trail.fields.sort((a,b)=>interpretationKeys.indexOf(a.key)-interpretationKeys.indexOf(b.key)).map(f=>`<details><summary>${esc(interpretationLabels[interpretationKeys.indexOf(f.key)])} · ${f.references.length} citations</summary><p>${esc(f.value)}</p>${f.references.map(r=>`<blockquote>${esc(r.quote)}</blockquote><p>${esc(r.source.source_id||r.material_id)} · ${esc(r.block_id||'document information')} · ${esc(r.anchor_status)}</p>`).join('')}</details>`).join('')}${trail.rules?.length?`<details><summary>Rule mappings (${trail.rules.length} nodes)</summary>${trail.rules.filter(r=>r.field_key).map(r=>`<p>${esc(r.rule.field)} ${esc(r.rule.operator)} → ${esc(interpretationLabels[interpretationKeys.indexOf(r.field_key)])}</p>`).join('')}</details>`:''}<details><summary>Original version and location</summary><pre>${esc(JSON.stringify({source:trail.source,locations:trail.source_refs},null,2))}</pre></details><p>Saved evidence remains tied to this version even when current text changes.</p>`);return;
  }
  if(action==='switch')return this.open(node.dataset.unit);
  if(action==='source'){const r=this.m.requirements;if(r.doc?.id!==d.context?.session_id)await r.open(d.context.session_id);this.m.revealPane('content');const i=this.m.draft.blocks.findIndex(b=>b.id===r.doc?.block_id);if(i>=0)this.m.jumpToBlock(i);return;}
  if(action==='context'){
   const ids=d.linked_material_ids||[];const ctx=await this.m.api('/api/interpretations/context',{unit_id:d.unit_id,linked_material_ids:ids});
   d.context=ctx;d.linked_material_ids=ids;d.context_error=null;d.stale=false;d.sourceChanged=false;this.changed();this.notice='Context refreshed. Check the six fields against these source versions.';return this.render();
  }
  if(action==='related'){
   const catalog=await this.m.api('/api/materials?limit=100');
   const available=(catalog.materials||[]).filter(x=>x.id!==this.m.id&&!(d.linked_material_ids||[]).includes(x.id));
   this.m.dialog(`<h2>Add related saved material</h2><p>Only explicitly selected local materials join the interpretation context.</p><label>Material<select data-ip-related>${available.map(x=>`<option value="${esc(x.id)}">${esc(x.title||x.id)}</option>`).join('')}</select></label><button data-ip-confirm ${available.length?'':'disabled'}>Add to context</button>`);
   this.m.q('[data-ip-confirm]').onclick=async()=>{const id=this.m.q('[data-ip-related]').value;try{const ids=[...(d.linked_material_ids||[]),id];const ctx=await this.m.api('/api/interpretations/context',{unit_id:d.unit_id,linked_material_ids:ids});d.context=ctx;d.linked_material_ids=ids;this.changed();this.m.q('#mw-dialog').close();this.notice='Related material added. Review the updated context before generating.';this.render();}catch(e){this.m.message(e.message,'warning');}};return;
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
   if(d.sourceChanged||d.stale)throw Error('Refresh and review the source context before generating.');
   const key=this.active,request={request_id:crypto.randomUUID(),unit_id:d.unit_id,fields:action==='generate-one'?[k]:interpretationKeys,linked_material_ids:d.linked_material_ids,context_fingerprint:d.context.fingerprint,confirm_context:true};
   this.m.dialog(`<h2>Generate candidate suggestions</h2><p>Send the complete saved text of these materials and their related splitting to:</p><p class="ip-address">${esc(d.provider.destination)} · ${esc(d.provider.model)}</p><ul>${d.context.materials.map(x=>`<li>${esc(x.title||x.id)} · revision ${x.revision}</li>`).join('')}</ul><p>Formal edits remain unchanged. This action generates suggestions for human review.</p><button data-ip-confirm class="primary">Send this context and generate</button>`);
   this.m.q('[data-ip-confirm]').onclick=async()=>{this.m.q('[data-ip-confirm]').disabled=true;try{const run=await this.m.api('/api/interpretations/generate',request);d.generation=run;this.journal();this.m.q('#mw-dialog').close();this.notice='Generation in progress. Your formal fields remain editable.';this.render();this.watch(run.id,key);}catch(e){this.m.q('#mw-dialog').close();this.notice=e.message;this.render();}};return;
  }
  if(action==='reload'){
   if(d.dirty||d.retry){this.m.dialog('<h2>Reload saved interpretation?</h2><p>Your current unsaved draft will be replaced by the server version.</p><button data-ip-confirm>Reload saved version</button>');this.m.q('[data-ip-confirm]').onclick=async()=>{try{await this.clearWorking(d);this.m.q('#mw-dialog').close();this.drafts.delete(this.active);this.journal();void this.open(d.unit_id);}catch(e){this.m.message(e.message,'warning');}};return;}
   return this.open(d.unit_id);
  }
  if(['save','review','restore','retry'].includes(action))return this.save(action,node);
 }
 async save(action,node){
  const d=this.draft,key=this.active;if(this.pending)return;if(d.savingWorking)throw Error('Working copy is still saving. Retry in a moment.');clearTimeout(d.autosaveTimer);
  const invalid=this.host?.querySelector(':invalid');if(invalid&&action!=='retry')throw Error(invalid.validationMessage||'Correct the rule value before saving.');
  if((d.stale||d.sourceChanged)&&action!=='retry')throw Error('Refresh the context, then review your fields before saving.');
  const request=action==='retry'?d.retry:{request_id:crypto.randomUUID(),unit_id:d.unit_id,expected_revision:d.revision,context_fingerprint:d.context?.fingerprint,linked_material_ids:d.linked_material_ids,fields:copy(d.fields),check_design:copy(d.check_design||emptyDesign()),...(d.catalog?.revision?{catalog_revision:d.catalog.revision}:{}),action:action==='save'?'save':action,history_revision:Number(node?.dataset?.revision)};
  if(!request)return;this.pending=true;d.retry=request;this.journal();this.notice='Saving interpretation…';this.render();
  try{const result=await this.m.api('/api/interpretations/save',request);d.retry=null;d.dirty=false;d.draftRevision=result.draft_revision??d.draftRevision;this.journal();const saved=await this.m.api('/api/interpretations?'+new URLSearchParams({unit_id:d.unit_id}));this.drafts.set(key,{...saved,draftRevision:d.draftRevision,dirty:false,candidate:d.candidate});this.notice='Interpretation saved. Material review and archive status are unchanged.';}
  catch(e){if(e.definitive){d.retry=null;if(e.status===409)d.sourceChanged=true;}this.notice=e.message+(d.retry?' Save outcome uncertain. Retry the same save before leaving.':'');this.journal();}
  finally{this.pending=false;this.render();}
 }
 async watch(id,key){
  try{const run=await this.m.api('/api/interpretations/run?'+new URLSearchParams({id}));const d=this.drafts.get(key);if(!d)return;
   if(run.status==='running'){setTimeout(()=>this.watch(id,key),1500);return;}
   d.generation=null;if(run.status==='ready'){d.candidate={...run,suggestions:{...(d.candidate?.context_fingerprint===run.context_fingerprint?d.candidate.suggestions:{}),...run.suggestions}};this.notice='Candidates ready. Use suggestion to adopt a field.';}
   else this.notice=run.error||'Candidate is stale. Refresh source context before generating again.';
   if(this.active===key)this.render();
  }catch(e){if(this.active===key){this.notice='Generation status unavailable. Reopen the requirement to recover its saved request.';this.render();}}
 }
}
