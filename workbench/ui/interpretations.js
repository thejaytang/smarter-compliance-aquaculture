import {treeNodes,treeText} from './requirement-structure.js';
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
// Mechanical projection of recorded wording and group counts; no inferred predicates.
export function sourceSections(context){
 const u=context?.requirement||{},units=Object.assign({},...(context?.sessions||[]).map(s=>s.units),u.id?{[u.id]:u}:{});
 if(context.structure){
  const tree=context.structure,trees=Object.assign({},...(context.sessions||[]).map(s=>s.structures||{})),clauses=[];const visit=n=>{if(n.role==='exceptions')return;if(n.kind==='clause')clauses.push(n);for(const child of n.children||[])visit(child);};visit(tree);
  const grouped=tree.children.find(n=>n.role==='requirements');let g=0;const labels=Object.fromEntries(treeNodes(tree).filter(n=>['clause','group'].includes(n.kind)).map(n=>[n.id,'G'+(++g)]));
  const pick=(clause,fields)=>clause.children.filter(n=>fields.includes(n.role)).map(n=>`${n.role}: ${treeText(n,units,trees)}`).join('\n');
  const at=(fields)=>clauses.map(c=>{const text=pick(c,fields);return text?`${clauses.length>1?labels[c.id]+': ':''}${text}`:'';}).filter(Boolean).join('\n');
  const values={scope:at(['Subject']),condition:[at(['conditions']),at(['exceptions'])?'Exception structure (separate scope): '+at(['exceptions']):''].filter(Boolean).join('\n'),demand:[at(['Modal Verb','Main Verb','Object','subrequirement']),grouped?'Requirement branches (QC applies to complete branches): '+treeText(grouped,units,trees):''].filter(Boolean).join('\n')};
  const pending=treeNodes(tree).some(n=>(n.kind==='clause'&&!n.children.length)||(n.kind==='group'&&(n.quantity===null||!n.children.length)));
  return Object.fromEntries(Object.entries(values).map(([key,value])=>[key,{value,basis:value?'interpretation':'unresolved',state:value&&!pending?'specified':'unresolved',references:[],gaps:[...(!value?['No '+key+' wording has been assigned in the Requirement.']:[]),...(pending?['Complete empty groups and unresolved QC in the third pane.']:[])]}]));
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
  const host=this.host;if(!host)return;
  const r=this.m.requirements,entries=(r?.orderedSessions?.()||[]).map(s=>s.id===r.doc?.id?r.doc:s);
  const d=this.draft,valid=d&&this.active?.startsWith(this.owner()+':')&&r?.selected===d.unit_id;
  const list=entries.map(s=>{const ids=r.rootIds?r.rootIds(s):Object.keys(s.units||{}).filter(id=>s.roles?.[id]!=='condition'),id=ids[0];if(!id)return '';const active=valid&&s.units?.[d.unit_id];
   return `<details class="ip-requirement" ${active?'open':''}><summary data-ip-select="${active?d.unit_id:id}"><strong>${esc(r.entryLabel?r.entryLabel(s):r.label(id))}</strong> ${esc((s.text||s.units[id].text).slice(0,100))}</summary>${active&&ids.length>1?`<div class="ip-clause-choices">${ids.map((uid,i)=>`<button data-ip-select="${uid}" aria-pressed="${d.unit_id===uid}">${esc(r.internalLabel?.(uid)||`G${i+1}`)} · ${esc(s.units[uid].text.slice(0,65))}</button>`).join('')}</div>`:''}${active?this.editorMarkup(d):''}</details>`;}).join('');
  host.innerHTML=(this.loading?'<p role="status">Loading Requirement…</p>':'')+(list||'<p>Select or create a Requirement in the third pane.</p>');
  host.querySelectorAll?.('[data-ip-select]')?.forEach(n=>n.onclick=async e=>{e.preventDefault();await r.selectFromInterpretation(n.dataset.ipSelect);});
  host.onclick=e=>{const b=e.target.closest('[data-ip]');if(b&&!b.disabled)void this.action(b.dataset.ip,b).catch(error=>{this.notice=error.message;this.render();});};
  host.querySelectorAll?.('[data-logic-value]')?.forEach(el=>el.oninput=()=>{
   const key=el.dataset.logicValue,c=d.logicCandidates?.[key];
   if(c){c.value=el.value;c.edited=true;}else{d.fields[key]={...d.fields[key],value:el.value,basis:'interpretation',state:el.value.trim()?'specified':'unresolved'};}
   this.changed();const state=host.querySelector('.ip-state');if(state)state.textContent='Unsaved changes';
  });
  host.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='s'){e.preventDefault();e.stopPropagation();void this.save('save',{}).catch(error=>{this.notice=error.message;this.render();});}};
  if(valid&&d.check_design)bindDesign(host,d.check_design,()=>this.changed(),()=>this.render(),d.catalog);
 }
 editorMarkup(d){
  const derived=sourceSections(d.context),blocked=this.pending||this.loading||d.retry||this.m.collaboration.readonly,disabled=blocked?'disabled':'',r=this.m.requirements;
  return `<div class="ip-heading"><p class="ip-state">${d.dirty?'Unsaved changes':d.revision?'Saved':'Not saved'} · ${esc(r.label(d.unit_id))}</p></div><p class="ip-notice" role="status">${esc(this.notice)}</p>
   ${d.stale||d.sourceChanged?'<p class="ip-warning">Source changed. Refresh before saving or generating.</p><button data-ip="context">Refresh source</button>':''}
   ${['scope','condition','demand'].map((key,i)=>{const k=logicKeys[i],c=d.logicCandidates?.[k];return `<section class="ip-group"><h4>${['Scope','Conditions','Demands'][i]}</h4><blockquote class="ip-source-wording">${esc(derived[key].value||'No wording assigned in the third pane.')}</blockquote><div class="ip-field" data-ip-field="${k}"><label>Logic<textarea data-logic-value="${k}" rows="4">${esc(c?c.value:d.fields[k].value)}</textarea></label><div class="ip-ai-actions">${c?.status==='generating'?'<button disabled>Generating…</button>':c?.status==='ready'?`<button data-ip="accept-logic">Accept</button><button data-ip="suggest-logic" ${!d.provider?.available?'disabled':''}>Regenerate</button><span>Editable AI candidate · not accepted</span>`:`<button data-ip="suggest-logic" ${!d.provider?.available?'disabled':''}>AI suggestion</button>${!d.provider?.available?'<span>Not connected</span>':''}`}</div>${c?.edited&&c.suggestion?`<details><summary>Generated suggestion · your edits are retained above</summary><p>${esc(c.suggestion.value)}</p></details>`:''}</div></section>`;}).join('')}
   <details class="ip-context"><summary>Sources &amp; details</summary><button data-ip="review" ${disabled||d.dirty||!d.revision||d.stale||d.sourceChanged||interpretationKeys.some(k=>!reviewReady(d.fields[k]))?'disabled':''}>Mark interpretation reviewed</button><p>${esc(d.provider?.destination||'AI service: Not connected')} ${esc(d.provider?.model||'')}</p><p>AI uses the full saved text of these materials:</p><ul>${(d.context?.materials||[]).map(x=>`<li>${esc(x.title||x.id)} · revision ${x.revision}</li>`).join('')}</ul><button data-ip="source">Locate source</button><button data-ip="trace" ${d.revision?'':'disabled'}>Source trail</button><button data-ip="context">Refresh source</button><p>Source wording follows the recorded decomposition. Counts, branches and exceptions are retained; no Site Model assessment is performed.</p>${Object.entries(d.fields).filter(([k,f])=>f.references?.length||f.gaps?.length).map(([k,f])=>`<h5>${esc(k)}</h5>${(f.references||[]).map(ref=>`<blockquote>${esc(ref.quote)}</blockquote>`).join('')}${(f.gaps||[]).map(g=>`<p>${esc(g)}</p>`).join('')}`).join('')}</details>
   <details><summary>Checking chain</summary><div class="ip-logic">${logicMarkup(checkingLogic({...d.fields,...derived},d.context?.exceptions))}</div></details>
   ${designMarkup(d.check_design||emptyDesign(),disabled,d.catalog)}
   <div class="ip-save"><button data-ip="save" ${disabled}>Save interpretation</button>${d.retry?'<button data-ip="retry">Retry save</button>':''}</div>
   <details><summary>History</summary><button data-ip="reload" ${disabled}>Reload saved interpretation</button>${(d.history||[]).map(h=>`<p>Revision ${h.revision} <button data-ip="restore" data-revision="${h.revision}" ${disabled}>Restore</button></p>`).join('')}</details>`;
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
  const d=this.draft,key=this.active;if(this.pending)return;
  if(this.m.requirements?.dirty)throw Error('Save Requirement splitting before saving its interpretation.');if(d.savingWorking)throw Error('Working copy is still saving. Retry in a moment.');clearTimeout(d.autosaveTimer);
  const invalid=this.host?.querySelector(':invalid');if(invalid&&action!=='retry')throw Error(invalid.validationMessage||'Correct the rule value before saving.');
  if((d.stale||d.sourceChanged)&&action!=='retry')throw Error('Refresh the context, then review your fields before saving.');
  if(Object.keys(d.logicCandidates||{}).length)throw Error('Accept the AI candidates before saving. Your edits remain in the text boxes.');
  if(action==='save')Object.assign(d.fields,sourceSections(d.context));
  const changeAtStart=action==='retry'?(d.retryChangeNumber??0):(d.changeNumber||0);
  if(action!=='retry')d.retryChangeNumber=changeAtStart;
  const request=action==='retry'?d.retry:{request_id:crypto.randomUUID(),unit_id:d.unit_id,expected_revision:d.revision,context_fingerprint:d.context?.fingerprint,linked_material_ids:d.linked_material_ids,fields:copy(d.fields),check_design:copy(d.check_design||emptyDesign()),...(d.catalog?.revision?{catalog_revision:d.catalog.revision}:{}),action:action==='save'?'save':action,history_revision:Number(node?.dataset?.revision)};
  if(!request)return;this.pending=true;d.retry=request;this.journal();this.notice='Saving interpretation…';this.render();
  try{const result=await this.m.api('/api/interpretations/save',request);d.retry=null;d.dirty=false;d.draftRevision=result.draft_revision??d.draftRevision;this.journal();const saved=await this.m.api('/api/interpretations?'+new URLSearchParams({unit_id:d.unit_id}));if((d.changeNumber||0)!==changeAtStart){d.revision=saved.revision;d.context=saved.context;d.dirty=true;this.notice='Saved. Newer edits remain unsaved.';}else{this.drafts.set(key,{...saved,draftRevision:d.draftRevision,dirty:false,candidate:d.candidate});this.notice='Interpretation saved.';}}
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
