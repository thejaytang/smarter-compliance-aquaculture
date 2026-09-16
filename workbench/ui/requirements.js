import {sourcePreview} from './requirement-source.js';
import {annotationLegend} from './markdown-content.js';
// Manual outside-in extraction. All content mutations are source-bound server steps.
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const fields = ['Subject','Modal Verb','Main Verb','Object'];
export const relations = ['conditions','exceptions','subrequirement'];
export const codepointOffset = (text, utf16Offset) => Array.from(text.slice(0, utf16Offset)).length;
export {quantityLabel,quantityPreset,quantityMode,quantityPreview,quantityRange} from './quantity.js';
import {quantityLabel,quantityPreset,quantityMode,quantityPreview,quantityRange} from './quantity.js';
import {StructureEditor,treeNodes} from './requirement-structure.js';
export function groupIds(group) { return group ? group.slice(1).flatMap(x => Array.isArray(x) ? groupIds(x) : [x]) : []; }
const button = (action,label,attrs='') => `<button type="button" data-rq="${action}" ${attrs}>${label}</button>`;
export class RequirementsEditor {
  constructor(materials) { this.m=materials; this.sessions=[]; this.results=[]; this.closedUnits=new Set(); this.quantityDrafts=new Map();this.rangeModes=new Map();this.groupEditor=new StructureEditor(this); this.sessionCollapsed=false; }
  get dirty() { return !!this._dirty || this.quantityDrafts.size>0; }
  set dirty(value) { this._dirty=value;if(!value)this.quantityDrafts.clear(); }
  quantityKey(group) { return [this.doc.id,group.dataset.owner||null,group.dataset.field,group.dataset.path||''].join(':'); }
  get host() { return this.m.q('#mw-requirement-content'); }
  get locked() { return this.loading || this.pending || this.m.busy || this.m.opening || this.m.dirty || this.doc?.stale || !!this.retryRequest || this.m.collaboration.readonly; }
  key() { return `${this.m.state?.actor?.id || ''}:${this.m.id}:${this.m.material?.revision}:${this.m.material?.collaboration?.view || ''}`; }
  render(force=false) {
    const host=this.host;if(!host||!this.m.material)return;
    const key=this.key();
    if(key!==this.context) {
      this.context=key;this.closedUnits.clear();this.quantityDrafts.clear();this.sessionCollapsed=false;this.doc=null;this.sessions=[];this.selected=null;this.results=[];this.notice='Loading saved splitting work…';this.lastRender=null;this.loading=true;this.dirty=false;this.edits=[];
      this.loadList(key);
    }
    const signature=[key,this.doc?.revision,this.selected,this.pending,this.m.busy,this.m.opening,this.m.dirty,this.notice,this.loading,this.results.length,this.m.collaboration.readonly].join('|');
    if(!force&&signature===this.lastRender)return;this.lastRender=signature;
    host.classList?.add('rq-editor');
    host.innerHTML=`${this.m.dirty?'<p class="rq-notice">Save the source content before splitting requirements.</p>':''}
      ${this.notice?`<p class="rq-status" role="status" aria-live="polite">${esc(this.notice)}</p>`:''}
      ${this.dirty?button('save-draft','Save splitting',this.pending?'disabled':''):''}${this.retryRequest?button('retry','Retry saving this step'):''}
      ${annotationLegend()}<div class="rq-list">${this.orderedSessions().map(s=>{const opened=s.id===this.doc?.id&&!this.sessionCollapsed;return `<section class="rq-session" data-session="${esc(s.id)}"><div class="rq-session-header"><div class="rq-entry-bar" data-rq="open-session" data-id="${esc(s.id)}"><button type="button" data-rq="open-session" data-id="${esc(s.id)}" class="rq-entry-toggle" aria-expanded="${opened}" aria-label="${opened?'Collapse':'Expand'} ${esc(this.entryLabel(s))}"><span aria-hidden="true">${opened?'▾':'▸'}</span><span class="rq-session-number">${esc(this.entryLabel(s))}</span></button><span class="rq-entry-actions">${button('locate-session','Locate',`data-id="${esc(s.id)}"`)}${button('auto-extract','Auto-extract',`data-id="${esc(s.id)}" disabled title="Automatic requirement extraction: Not connected"`)}${button('delete','Remove',`data-id="${esc(s.id)}" ${this.locked?'disabled':''}`)}</span></div><div class="rq-session-title" ${opened?'data-entry-source':''}>${sourcePreview({...s,...(s.id===this.doc?.id?this.doc:{}),labels:this.displayLabels()})}${opened&&!this.locked?this.groupEditor.toolsMarkup():''}</div></div>${opened?this.documentMarkup():''}</section>`;}).join('')}</div>
      ${this.deleted?.length?`<details><summary>Removed entries · ${this.deleted.length}</summary>${this.deleted.map(s=>`<p>${esc(s.text.slice(0,100))} ${button('undelete','Restore entry',`data-id="${s.id}"`)}</p>`).join('')}</details>`:''}${!this.sessions.length?'<div class="rq-empty"><h4>Build a requirement from its original text</h4><p>Select a source block in the content pane and choose <strong>To requirements</strong>. Split and assign its wording here; each requirement stays in the list.</p><p>Automatic extraction: Not connected.</p></div>':''}`;
    host.onclick=e=>{const structureAction=e.target.closest('[data-straction]');if(structureAction){e.stopPropagation();e.preventDefault();void this.groupEditor.action(structureAction).catch(error=>this.showError(error));return;}const b=e.target.closest('[data-rq]');if(b&&!b.disabled){e.stopPropagation();if(['open-session','select-unit','locate-session','decompose'].includes(b.dataset.rq))e.preventDefault();(async()=>{for(const row of host.querySelectorAll?.('[data-rq-qc]')||[]){if(['quantity-preset','quantity-range'].includes(b.dataset.rq)&&row.contains(b))continue;if(row.commitQuantity&&!(await row.commitQuantity()))return;}await this.action(b.dataset.rq,b);})().catch(error=>this.showError(error));}};
    host.querySelectorAll?.('[data-rq-qc]:not([data-structure-qc])').forEach(row=>this.bindQuantity(row));
    this.groupEditor.bind(host);
    // Native disclosure is presentation only; retain it across each saved-step render.
    host.querySelectorAll?.('[data-unit]').forEach(card=>card.ontoggle=()=>{if(!card.isConnected)return;if(card.open)this.closedUnits.delete(card.dataset.unit);else this.closedUnits.add(card.dataset.unit);});
    if(this.pending)host.setAttribute('aria-busy','true');else host.removeAttribute('aria-busy');
  }
  orderedSessions() {
    const order=new Map((this.m.draft?.blocks||[]).map((b,i)=>[b.id,i]));
    return [...this.sessions].sort((a,b)=>(order.get(a.block_id)??Infinity)-(order.get(b.block_id)??Infinity));
  }
  async loadList(context=this.context) {
    try {
      const result=await this.m.api('/api/requirements?'+new URLSearchParams({material_id:this.m.id}));
      if(context!==this.context)return;
      this.sessions=result.sessions||[];this.deleted=result.deleted||[];this.notice='';this.loading=false;
      let remembered;try{remembered=sessionStorage.getItem('requirement-session:'+context);}catch{}
      const id=this.sessions.find(s=>s.id===remembered)?.id||this.sessions.at(-1)?.id;
      if(id)await this.open(id,null);else this.render(true);
    }catch(e){if(context===this.context){this.loading=false;this.notice=`Saved splitting work could not be loaded. ${e.message}`;this.render(true);}}
  }
  async open(id,selectedId=undefined) {
    if(this.pending||this.retryRequest)return;
    if(this.dirty){this.m.unsavedDialog?.();return;}
    const context=this.context,ticket=this.readTicket={};this.loading=true;this.notice='Opening saved splitting work…';this.render(true);
    try{const doc=await this.m.api('/api/requirements/session?'+new URLSearchParams({id}));if(context!==this.context||ticket!==this.readTicket)return;this.doc=doc;this.sessionCollapsed=false;this.results=[];this.searchPerformed=false;this.selected=selectedId===null?null:selectedId||this.unitIds()[0];for(const id of doc.done)this.closedUnits.add(id);this.notice=doc.stale?'Source content changed. This saved session is read-only. Bring the current passage to start a new session.':'';try{sessionStorage.setItem('requirement-session:'+context,id);}catch{}}
    catch(e){this.showError(e);}finally{if(context===this.context&&ticket===this.readTicket){this.loading=false;this.render(true);void this.syncInterpretation();}}
  }
  showError(error) {this.notice=error.message||String(error);this.render(true);}
  async start(blockId,combine=false) {
    if(this.pending||this.m.busy||this.m.opening||this.m.dirty||this.retryRequest||this.m.collaboration.readonly||this.loading)return;
    if(this.dirty){this.m.unsavedDialog?.();return;}
    const block=this.m.draft.blocks.find(b=>b.id===blockId);if(!block||block.role==='document_information')return;
    const existing=this.sessions.find(s=>s.block_id===blockId&&s.text===block.text);
    if(!combine&&existing&&!this.doc?.stale)return this.open(existing.id);
    if(!combine)return this.step('start',{material_id:this.m.id,material_revision:this.m.material.revision,block_id:blockId});
    const choices=this.m.draft.blocks.filter(b=>b.role!=='document_information'&&['text','heading'].includes(b.type)&&b.text?.trim());
    this.m.dialog(`<h2>Source passages for this Requirement</h2><p>Select one or more passages. Their original order and individual source links are retained.</p>${choices.map(b=>`<label class="mw-check"><input type="checkbox" data-source-block="${esc(b.id)}" ${b.id===blockId?'checked':''}><span>${esc(b.text)}</span></label>`).join('')}<button data-create-requirement>Create Requirement entry</button>`,dialog=>{
      dialog.querySelector('[data-create-requirement]').onclick=async()=>{const ids=[...dialog.querySelectorAll('[data-source-block]:checked')].map(n=>n.dataset.sourceBlock);if(!ids.length)return;dialog.close();await this.step('start',{material_id:this.m.id,material_revision:this.m.material.revision,block_ids:ids});};
    });
  }

  async step(action,body={},retry=null) {
    if(this.pending)return;
    if(!retry&&this.locked&&!['start','save-draft'].includes(action))return;
    const request=retry||{request_id:crypto.randomUUID(),action,...(this.doc?{session_id:this.doc.id,expected_revision:this.doc.revision}:{}),...body};
    const previousDone=new Set(this.doc?.done||[]);
    const context=this.context;this.pending=true;this.notice=['save-draft','delete','undelete'].includes(request.action)?'Saving…':'Updating unsaved splitting…';this.render(true);this.m.updateNavigationLock?.();
    try {
      if(!(this.edits||[]).length){this.baseSession=request.action==='start'?null:this.doc?.id;this.baseRevision=this.doc?.revision;}
      const isDirect=['delete','undelete','save-draft'].includes(request.action);
      const edits=isDirect?null:[...(this.edits||[]),request];
      const payload=isDirect?request:{request_id:crypto.randomUUID(),action:'preview',...(this.baseSession?{session_id:this.baseSession,expected_revision:this.baseRevision}:{}),steps:edits};
      const result=await this.m.api('/api/requirements/step',payload);
      if(context!==this.context)return;
      if(result.status!=='conflict'&&!isDirect){if(!(this.edits||[]).length&&request.action!=='start'){this.baseSession=request.session_id;this.baseRevision=request.expected_revision;}this.edits=edits;this.dirty=true;}
      if(result.status!=='conflict'&&request.action==='save-draft'){this.edits=[];this.dirty=false;this.baseSession=result.document.id;this.baseRevision=result.document.revision;}

      if(context!==this.context)return;
      if(result.status==='conflict')throw Object.assign(Error(result.error),{status:409,definitive:true});
      this.retryRequest=null;this.doc=result.document;this.sessionCollapsed=false;
      if(this.doc.deleted){this.doc=null;this.selected=null;await this.loadList(context);return;}
      for(const id of this.doc.done)if(!previousDone.has(id))this.closedUnits.add(id);
      if(this.doc.phase==='complete')this.sessionCollapsed=true;
      if(!this.doc.units[this.selected])this.selected=this.unitIds().find(id=>!this.doc.done.includes(id))||this.unitIds()[0];
      const index=this.sessions.findIndex(s=>s.id===this.doc.id);if(index<0)this.sessions.push(this.doc);else this.sessions[index]=this.doc;
      try{sessionStorage.setItem('requirement-session:'+context,this.doc.id);}catch{}
      if(!this.dirty)this.m.interpretations?.sourceChanged();
      this.notice=this.dirty?'Unsaved changes · save before leaving. Changes remain only in this page.':'';
      return true;
    } catch(e) {
      // Keep the exact request for retry when transport failed after a possible save.
      if(!e.definitive)this.retryRequest=request;
      this.notice=e.status===409?'Another tab saved a newer step. Your attempted step was not applied. Reopen this saved passage to continue.':`${e.message}${this.retryRequest?' Retry this same step before leaving.':''}`;
      return false;
    } finally {this.pending=false;this.render(true);this.m.updateNavigationLock?.();}
  }
  async saveDraft(){if(!this.dirty||this.pending)return;for(const row of this.host.querySelectorAll?.('[data-rq-qc]')||[])if(row.commitQuantity&&!(await row.commitQuantity()))return;return this.step('save-draft',{session_id:this.baseSession,expected_revision:this.baseRevision,steps:this.edits});}
  discard(){this.edits=[];this.dirty=false;this.retryRequest=null;this.doc=null;this.baseSession=null;void this.loadList();}
  async navigateAnnotation(refs){
    const jump=async s=>{await this.open(s.session_id);this.selected=s.unit_id;this.closedUnits.delete(s.unit_id);this.render(true);this.m.revealPane?.('requirements');const card=this.host.querySelector(`[data-unit="${s.unit_id}"]`);const field=card?.querySelector(`[data-field="${s.field}"]`)||card;field?.scrollIntoView({block:'nearest'});field?.focus();};
    if(refs.length===1)return jump(refs[0]);
    this.m.dialog(`<h2>Referenced fields</h2><p>Select the field to locate. All relationships covering this text are retained.</p>${refs.map((s,i)=>`<button type="button" data-ann-choice="${i}">${esc(s.field)} · ${esc(s.label)} · ${esc(s.unit_id)}</button>`).join('')}`);
    this.m.q('#mw-dialog').querySelectorAll('[data-ann-choice]').forEach(b=>b.onclick=()=>{this.m.q('#mw-dialog').close();void jump(refs[Number(b.dataset.annChoice)]);});
  }
  unitIds() {return Object.keys(this.doc.units).sort((a,b)=>(this.doc.spans?.[a]?.[0]||0)-(this.doc.spans?.[b]?.[0]||0)||(this.doc.spans?.[b]?.[1]||0)-(this.doc.spans?.[a]?.[1]||0));}
  rootIds(doc) {
    if(doc.roots)return groupIds(doc.roots).filter(id=>doc.units?.[id]);
    const children=new Set(Object.values(doc.units||{}).flatMap(u=>relations.flatMap(f=>groupIds(u[f]))));
    return Object.keys(doc.units||{}).filter(id=>!children.has(id));
  }
  displayLabels() {
    const docs=this.orderedSessions().map(s=>s.id===this.doc?.id?this.doc:s);
    if(this.doc&&!docs.some(s=>s.id===this.doc.id))docs.push(this.doc);
    const labels={};let r=0;
    for(const d of docs){labels[d.id]=`R${++r}`;const first=this.rootIds(d)[0];if(first)labels[first]=labels[d.id];let g=1;
      for(const id of Object.keys(d.units||{}).sort((a,b)=>(d.spans?.[a]?.[0]||0)-(d.spans?.[b]?.[0]||0)))if(id!==first)labels[id]=`G${++g}`;
    }
    return labels;
  }
  entryLabel(doc) {return this.displayLabels()[doc.id]||'R';}
  label(id) {return this.displayLabels()[id] || this.doc?.labels?.[id] || `Linked ${id.slice(0,8)}`;}
  internalLabel(id) {const d=this.doc;if(!d?.units?.[id])return this.label(id);return /^G/.test(this.label(id))?this.label(id):'G1';}
  completeRequirements(owner) {
    return this.orderedSessions().flatMap(s=>{const d=s.id===this.doc?.id?this.doc:s;if(d.units?.[owner])return [];const id=this.rootIds(d)[0];return id?[{...d.units[id],text:d.text}]:[];});
  }
  visibleUnitIds() {
    const hidden=new Set();for(const id of this.unitIds()){const tree=this.groupEditor.tree(id);if(tree)for(const n of treeNodes(tree))if(n.kind==='reference'&&this.doc.units[n.target_id])hidden.add(n.target_id);}
    return this.unitIds().filter(id=>!hidden.has(id));
  }
  relationMarkup(u,field,disabled,complete) {
    const linked=new Set(groupIds(u[field])),choices=this.completeRequirements(u.id).filter(x=>!linked.has(x.id));
    return `<div class="rq-field rq-relation-field semantic semantic-${relations.indexOf(field)+4}" data-field="${field}" tabindex="-1"><dt>${!complete?button('extract',field,`data-field="${field}" title="Extract selected text as ${field}" ${disabled}`):field}</dt><dd>${u[field]?this.groupMarkup(u[field],field,u.id,[],complete):'<span class="rq-blank">Select wording above</span>'}
      ${!complete&&field!=='conditions'?`<div class="rq-existing"><label>Use a complete Requirement<select data-rq-existing data-field="${field}" aria-label="Complete Requirement for ${field}" ${disabled||!choices.length?'disabled':''}>${choices.map(x=>`<option value="${x.id}" title="${esc(x.text)}">${esc(this.label(x.id))} · ${esc(x.text.slice(0,90))}</option>`).join('')||'<option>No other complete Requirement</option>'}</select></label>${button('link-existing','Link Requirement',`data-field="${field}" ${disabled||!choices.length?'disabled':''}`)}</div>`:''}</dd></div>`;
  }
  unitText(id) {return this.doc.units[id]?.text||this.doc.reference_evidence[id]?.text||id;}
  documentMarkup() {
    const d=this.doc,disabled=this.locked?'disabled':'',complete=d.phase==='complete';
    return `<div class="rq-session-body"><div class="rq-source-context"><span>${esc(d.chapter||'Original passage')}</span></div>
      ${complete?`${button('phase','Resume editing',`data-phase="fields" ${disabled}`)}`:''}
      <div class="rq-units">${(d.structure_views?this.visibleUnitIds():this.unitIds().filter(id=>!this.inlineConditionIds().has(id))).map(id=>this.unitMarkup(d.units[id],disabled,complete)).join('')}</div>
      ${this.rootIds(d).length>1?`<details class="rq-outer"><summary>Group of source clauses</summary>${this.groupMarkup(d.roots,'roots',null,[],complete)}</details>`:''}
      <div class="rq-footer">${!complete?button('phase','Save &amp; collapse',`data-phase="complete" ${disabled||d.done.length!==Object.keys(d.units).length?'disabled':''}`):''}${button('reload','Reload saved work',this.pending||this.retryRequest?'disabled':'')}</div>
      </div>`;
  }
  showHelp() {
    const d=this.doc;
    this.m.dialog(`<h2>Requirements help</h2><p>Select original wording to assign fields or create a Group. Use × on a card to remove it; removing a Group also removes its contents. Degroup keeps its contents.</p><p>Only manual saves enter history. Finishing a Requirement does not complete material review.</p><p>Earlier inline relationships remain in saved history.</p>${d?`<details class="rq-history"><summary>Saved history · ${esc(this.entryLabel(d))}</summary><p>Restoring creates a new saved revision.</p>${(d.steps||[]).map(s=>`<p>Revision ${s.revision} · ${esc(s.action)} ${button('restore','Restore',`data-revision="${s.revision}" ${this.locked||this.dirty?'disabled':''}`)}</p>`).join('')}<details><summary>Structured result</summary><pre>${esc(JSON.stringify({requirements:d.roots,units:Object.values(d.units),structures:d.structure_views},null,2))}</pre></details></details>`:''}`,dialog=>{
      dialog.querySelectorAll('[data-rq="restore"]').forEach(b=>b.onclick=()=>{dialog.close();void this.action('restore',b).catch(error=>this.showError(error));});
    });
  }
  inlineConditionIds() {
    return new Set(Object.values(this.doc.units).flatMap(u=>groupIds(u.conditions)).filter(id=>this.doc.roles[id]==='condition'));
  }
  unitMarkup(u,disabled,complete,inline=false) {
    if(this.doc.structure_views?.[u.id]||this.doc.structures?.[u.id])return this.groupEditor.unitMarkup(u,complete,inline);
    const done=this.doc.done.includes(u.id),conditionOnly=this.doc.roles[u.id]==='condition';
    return `<details class="rq-unit${inline?' rq-inline-condition':''}" data-unit="${esc(u.id)}" aria-current="${u.id===this.selected?'true':'false'}" ${!this.closedUnits.has(u.id)?'open':''}>
      <summary data-rq="select-unit" data-id="${esc(u.id)}" data-toggle="true"><strong>${esc(this.label(u.id))}</strong><span class="rq-unit-preview">${esc(u.text.slice(0,100))}</span><span class="rq-badge">${done?'Finished':'Editing'}</span>${inline?button('decompose','Decompose',`data-id="${u.id}" aria-label="Decompose ${esc(this.label(u.id))}" ${disabled}`):''}</summary>
      <div class="rq-unit-body"><div class="rq-unit-tools">${done&&!inline?button('reopen','Continue decomposing',disabled):''}</div><label>Original text<textarea data-rq-text aria-label="${esc(this.label(u.id))} original text" readonly rows="4">${esc(u.text)}</textarea></label>
      ${!complete?`<p class="rq-hint">${conditionOnly?'Select wording to extract a child condition. Each child can be decomposed into further conditions.':'Select wording, then choose a coloured field. Use Decompose to work inside a child.'}</p>`:''}
      <dl class="rq-fields">${!conditionOnly?fields.map((f,i)=>`<div class="rq-field rq-field-${i}" data-field="${f}" tabindex="-1"><dt>${!complete?button('assign',esc(f),`data-field="${f}" title="Assign selected original text to ${f}" ${disabled}`):esc(f)}</dt><dd><span>${u[f]?esc(u[f]):'<span class="rq-blank">Select wording above</span>'}</span>${u[f]&&!complete?button('clear','Clear',`data-field="${f}" aria-label="Clear ${f}" ${disabled}`):''}</dd></div>`).join(''):''}
      ${(conditionOnly?['conditions']:relations).map(f=>this.relationMarkup(u,f,disabled,complete)).join('')}</dl>
      ${!complete&&!conditionOnly?this.linkMarkup(u,disabled):''}
      ${!complete?`<div class="rq-unit-finish">${button('done',done?'Finished':'Finish &amp; collapse',`${disabled||done?'disabled':''}`)}</div>`:''}</div></details>`;
  }
  groupMarkup(group,field,owner,path=[],readonly=false) {
    if(!group)return '<p class="rq-blank">Not stated</p>';
    const disabled=this.locked||readonly?'disabled':'',q=group[0],range=Array.isArray(q),identity=path.join('.'),count=group.length-1,mode=quantityMode(q,count),custom=this.rangeModes.get([this.doc.id,owner||null,field,identity].join(':'))??(mode==='custom');
    return `<div class="rq-group" tabindex="-1" data-rq-group data-field="${field}" data-owner="${owner||''}" data-path="${identity}"><div class="rq-group-options">
      <div class="rq-qc-row rq-quantity" data-rq-qc data-count="${count}" data-current="${esc(JSON.stringify(q))}" role="group" aria-label="Quantity for ${field}"><output data-rq-preview class="rq-qc-preview" aria-live="polite" title="K = exact count; [min, max] = inclusive range">${quantityPreview(q)}</output><div class="rq-quantity-presets">${[['all','All',`K = ${count}`],['any','Any',`[1, ${count}] · at least one`],['one','Only','K = 1 · exactly one'],['not-all','Not All',count>=2?`[1, ${count-1}] · at least one, fewer than all`:'Needs at least 2 items']].map(([preset,label,title])=>button('quantity-preset',label,`data-preset="${preset}" title="${title}" aria-pressed="${!custom&&mode===preset}" ${disabled||(preset==='not-all'?count<2:preset!=='all'&&count<1)?'disabled':''}`)).join('')}${button('quantity-range','MIN–MAX',`aria-pressed="${custom}" ${disabled||!count?'disabled':''}`)}</div><input data-rq-min type="text" inputmode="numeric" pattern="[0-9]*" aria-label="Minimum" title="0–${count}" value="${range?q[0]:q}" ${disabled||!custom?'disabled':''}><span aria-hidden="true">-</span><input data-rq-max type="text" inputmode="numeric" pattern="[0-9]*" aria-label="Maximum" title="0–${count}" value="${range?q[1]:q}" ${disabled||!custom?'disabled':''}></div><small data-rq-qc-error class="rq-qc-error" role="status" hidden></small>
      ${!readonly?`<div class="rq-group-actions">${button('group','Group selected',disabled)}${button('ungroup','Expand selected group',disabled)}${field!=='roots'?button('unlink','Detach selected',disabled):''}</div>`:''}</div>
      <ol class="rq-children">${group.slice(1).map((child,i)=>`<li>${!readonly?`<input type="checkbox" data-rq-pick="${i+1}" aria-label="Select item ${i+1} in ${field} ${identity||'outer group'}" ${disabled}>`:''}${Array.isArray(child)?this.groupMarkup(child,field,owner,[...path,i+1],readonly):this.doc.roles[child]==='condition'&&field==='conditions'?`<div class="rq-condition-slot" data-condition-instance="${esc([owner,field,identity,child].join(':'))}">${this.unitMarkup(this.doc.units[child],this.locked?'disabled':'',readonly,true)}</div>`:`<div class="rq-reference">${button('select-unit',this.label(child),`data-id="${child}" title="${esc(child)}" ${this.doc.units[child]||this.sessions.some(s=>s.units?.[child])?'':'disabled'}`)}<span>${esc(this.unitText(child))}</span>${this.doc.units[child]?button('decompose','Decompose',`data-id="${child}" aria-label="Decompose ${esc(this.label(child))}" ${this.locked?'disabled':''}`):''}${!this.doc.units[child]?button('reference-source','View linked original',`data-id="${child}"`):''}</div>`}</li>`).join('')}</ol>
      </div>`;
  }
  bindQuantity(row){
    const inputs=[...row.querySelectorAll('input')],count=Number(row.dataset.count),output=row.querySelector('[data-rq-preview]'),error=row.parentElement.querySelector('[data-rq-qc-error]');
    const key=this.quantityKey(row.closest('[data-rq-group]'));
    let changed=this.quantityDrafts.has(key);
    if(changed)inputs.forEach((input,i)=>input.value=this.quantityDrafts.get(key)[i]);
    const preview=()=>{
      output.textContent=`[${inputs[0].value||'…'}, ${inputs[1].value||'…'}]`;
      try{quantityRange(inputs[0].value,inputs[1].value,count);error.hidden=true;inputs.forEach(i=>i.removeAttribute('aria-invalid'));return true;}
      catch(e){error.textContent=e.message;error.hidden=false;inputs.forEach(i=>i.setAttribute('aria-invalid','true'));return false;}
    };
    const commit=async()=>{if(!changed)return true;if(this.locked||!preview())return false;const ok=await this.action('quantity',inputs[0]);if(ok===false||this.retryRequest)return false;changed=false;this.quantityDrafts.delete(key);this.render(true);return true;};
    row.commitQuantity=commit;
    for(const input of inputs){
      input.dataset.previous=input.value;
      input.onbeforeinput=e=>{if(e.data&&!/^\d+$/.test(e.data))e.preventDefault();};
      input.oninput=()=>{
        if(!/^\d*$/.test(input.value)){input.value=input.dataset.previous;return;}
        if(input.value!=='')input.value=String(Math.min(count,Number(input.value)));
        input.dataset.previous=input.value;changed=true;this.quantityDrafts.set(key,inputs.map(i=>i.value));this.m.updateNavigationLock?.();preview();
        row.querySelectorAll('[data-preset]').forEach(b=>b.setAttribute('aria-pressed','false'));
      };
      input.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();void commit().catch(e=>this.showError(e));}if(e.key==='Escape'){e.preventDefault();const q=JSON.parse(row.dataset.current),values=Array.isArray(q)?q:[q,q];inputs.forEach((i,n)=>{i.value=String(values[n]);i.dataset.previous=i.value;});output.textContent=quantityPreview(q);error.hidden=true;inputs.forEach(i=>i.removeAttribute('aria-invalid'));changed=false;this.quantityDrafts.delete(key);this.m.updateNavigationLock?.();}};
    }
    if(changed)preview();
    row.onfocusout=e=>{if(row.contains(e.relatedTarget)||e.relatedTarget?.closest('[data-rq]'))return;void commit().catch(e=>this.showError(e));};
  }
  linkMarkup(u,disabled) {
    const local=Object.values(this.doc.units).filter(x=>x.id!==u.id),choices=[...local,...this.results.filter(x=>!this.doc.units[x.id])];
    return `<details class="rq-links"><summary>Link an existing requirement</summary><p>Select the requirement ID belonging to the referenced passage or chapter.</p><label>Find by original text, extracted chapter or ID<input data-rq-search type="search" aria-label="Find requirement by text chapter or ID"></label>${button('search','Find requirements',disabled)}<label>Requirement<select data-rq-target aria-label="Requirement to link">${choices.map(x=>`<option value="${x.id}">${esc(x.chapter?x.chapter+' · ':'')}${esc(x.text.slice(0,110))} · ${x.id.slice(0,8)}</option>`).join('')}</select></label><label>Relationship<select data-rq-relation>${(this.doc.roles[u.id]==='condition'?['conditions']:relations).map(f=>`<option>${f}</option>`).join('')}</select></label>${button('link','Link selected requirement',`${disabled||!choices.length?'disabled':''}`)}<p>${this.searchPerformed?`${this.results.length} saved units found for this reviewer.`:''}</p></details>`;
  }
  async selectFromInterpretation(id){
    if(this.selected===id){this.closedUnits.add(id);this.selected=null;this.render(true);return this.syncInterpretation();}
    const s=this.orderedSessions().find(s=>s.units?.[id]);if(!s)return;
    const changedSession=this.doc?.id!==s.id;
    if(changedSession){await this.open(s.id,id);if(this.doc?.id!==s.id)return;}
    this.selected=id;this.sessionCollapsed=false;this.closedUnits.delete(id);this.render(true);
    this.host.querySelector?.(`[data-unit="${id}"]`)?.scrollIntoView({block:'nearest'});
    if(!changedSession)await this.syncInterpretation();
  }
  async syncInterpretation() {
    if(!this.selected){if(this.m.interpretations){this.m.interpretations.active=null;this.m.interpretations.loading=false;this.m.interpretations.render();}return;}
    if(!this.m.interpretations||this.dirty||this.pending||this.loading||this.m.dirty||this.m.opening||!this.doc?.units?.[this.selected]||this.doc.roles[this.selected]==='condition')return;
    if(this.m.interpretations.pending)return;
    await this.m.interpretations.open(this.selected);
  }
  async action(action,node) {
    if(action==='open-session'){
      if(this.pending||this.retryRequest||this.loading)return;
      if(node.dataset.id!==this.doc?.id)return this.open(node.dataset.id);
      this.sessionCollapsed=!this.sessionCollapsed;this.selected=this.sessionCollapsed?null:this.rootIds(this.doc)[0];this.render(true);return this.syncInterpretation();
    }
    const card=node.closest?.('[data-unit]'),scope=card||this.host;
    if(card){if(this.selected!==card.dataset.unit){this.results=[];this.searchPerformed=false;}this.selected=card.dataset.unit;}
    if(action==='save-draft')return this.saveDraft();
    if(action==='locate-session'||action==='locate-content'||action==='locate'){
      this.m.revealPane?.('original');this.m.revealPane?.('content');this.m.revealPane?.('requirements');
      const doc=action==='locate-session'?(this.sessions.find(s=>s.id===node.dataset.id)||this.doc):this.doc;
      if(!doc)return;
      const span=action==='locate-session'?[0,doc.text.length]:doc.spans?.[this.selected]||[0,doc.text.length];
      const parts=(doc.source_segments||[{block_id:doc.block_id,start:0,end:doc.text.length}]).filter(p=>p.start<span[1]&&p.end>span[0]);
      const locate=async part=>{const i=this.m.draft.blocks.findIndex(b=>b.id===part.block_id);if(i>=0){this.m.jumpToBlock(i);await this.m.locateBlock(this.m.draft.blocks[i]);}};
      if(parts.length===1)return locate(parts[0]);
      this.m.dialog(`<h2>Linked source passages</h2><p>This Requirement spans multiple passages. Choose one to locate in both source panes.</p>${parts.map((p,i)=>`<button data-locate-part="${i}">${esc(p.text||p.block_id)}</button>`).join('')}`,d=>d.querySelectorAll('[data-locate-part]').forEach(b=>b.onclick=()=>{d.close();void locate(parts[Number(b.dataset.locatePart)]);}));return;
    }
    if(action==='delete'){
      if(this.dirty){this.m.unsavedDialog?.();return;}
      if(this.locked)return;
      if(this.m.interpretations?.canLeave?.()===false)return;
      const target=node.dataset?.id?this.sessions.find(s=>s.id===node.dataset.id):this.doc;if(!target)return;
      const request={session_id:target.id,expected_revision:target.revision};
      this.m.dialog(`<h2>Remove ${esc(this.entryLabel(target))}?</h2><p>This removes the Requirement from the working list. Its splitting and interpretation history remain available in Removed entries.</p><button data-cancel-remove>Cancel</button><button data-remove-entry>Remove</button>`,d=>{d.querySelector('[data-cancel-remove]').onclick=()=>d.close();d.querySelector('[data-remove-entry]').onclick=async()=>{d.close();await this.step('delete',request);};});return;
    }
    if(action==='undelete'){if(this.locked)return;await this.open(node.dataset.id);await this.step('undelete');await this.loadList();return;}
    if(action==='reopen'){await this.step('reopen',{unit_id:this.selected});this.closedUnits.delete(this.selected);return this.render(true);}
    if(action==='retry')return this.step('',{},this.retryRequest);
    if(action==='start')return this.start(this.host.querySelector('[data-rq-block]')?.value);
    if(action==='reload'||action==='history'){if(this.dirty){this.m.unsavedDialog?.();return;}return this.open(this.doc.id);}
    if(action==='select-unit'||action==='decompose'){
      const instance=node.closest?.('[data-condition-instance]')?.dataset?.conditionInstance;
      const id=node.dataset.id;if(!this.doc.units[id])return this.selectFromInterpretation(id);this.selected=id;
      if(action==='decompose'){
        if(this.locked)return;
        if(this.doc.done.includes(id)||this.doc.phase==='complete')await this.step('reopen',{unit_id:id});
        if(this.retryRequest)return;
        this.closedUnits.delete(id);
      }else if(node.dataset.toggle&& !this.closedUnits.has(id)){this.closedUnits.add(id);this.selected=null;}else this.closedUnits.delete(id);
      this.render(true);const target=this.host.querySelector?.(instance?`[data-condition-instance="${instance}"] > [data-unit="${id}"]`:`[data-unit="${id}"]`);target?.scrollIntoView({block:'nearest'});
      if(action==='decompose')target?.querySelector('[data-rq-text]')?.focus();
      else await this.syncInterpretation();return;
    }
    if(action==='next'){this.selected=this.unitIds().find(id=>!this.doc.done.includes(id))||this.selected;return this.render(true);}
    if(action==='reference-source'){const id=node.dataset.id,ref=this.doc.reference_evidence[id];if(!ref)return;const linked=await this.m.api('/api/requirements/session?'+new URLSearchParams({id:ref.session_id}));const location=ref.source.source_refs?.[0];this.m.dialog(`<h2>Linked requirement original</h2><p class="rq-original">${esc(ref.text)}</p><p>${esc(linked.title)} · ${esc(linked.chapter||'Original passage')}${location?.page?' · Page '+esc(location.page):''}</p><p>${linked.stale?'The source content has changed; this link retains the previously saved wording.':'Source wording retained with the saved reference.'}</p><a href="/api/material/original?${new URLSearchParams({id:linked.material_id})}" target="_blank" rel="noopener">Open original document</a><details><summary>Reference identity</summary><p>${esc(id)} · saved revision ${ref.revision}</p></details>`);return;}
    if(action==='search'){
      const context=this.context,session=this.doc.id,selected=this.selected,q=scope.querySelector('[data-rq-search]').value;const result=await this.m.api('/api/requirements/search?'+new URLSearchParams({q}));
      if(context!==this.context||session!==this.doc.id||selected!==this.selected)return;this.results=result.units;this.searchPerformed=true;this.render(true);this.host.querySelector(`[data-unit="${selected}"] .rq-links`).open=true;return;
    }
    if(this.locked)return;
    const body={unit_id:this.selected};
    if(action==='phase'){await this.step('phase',{phase:node.dataset.phase});if(node.dataset.phase==='complete'&&this.dirty&&!this.retryRequest)await this.saveDraft();return;}
    if(action==='restore')return this.step('restore',{history_revision:Number(node.dataset.revision)});
    if(action==='done')return this.step('done',body);
    if(action==='link-existing'){body.field=node.dataset.field;body.target_id=scope.querySelector(`[data-rq-existing][data-field="${body.field}"]`).value;return this.step('link',body);}
    if(action==='link'){body.field=scope.querySelector('[data-rq-relation]').value;body.target_id=scope.querySelector('[data-rq-target]').value;return this.step(action,body);}
    if(action==='clear')return this.step('clear',{...body,field:node.dataset.field});
    if(['assign','extract'].includes(action)){
      const area=scope.querySelector('[data-rq-text]');body.start=codepointOffset(area.value,area.selectionStart);body.end=codepointOffset(area.value,area.selectionEnd);
      body.field=node.dataset.field;
      return this.step(action,body);
    }
    if(action==='quantity-range'){const group=node.closest('[data-rq-group]');this.rangeModes.set(this.quantityKey(group),true);this.render(true);return;}
    if(['quantity','quantity-preset','group','ungroup','unlink'].includes(action)){
      const group=node.closest('[data-rq-group]');body.unit_id=group.dataset.owner;body.field=group.dataset.field;body.path=group.dataset.path?group.dataset.path.split('.').map(Number):[];
      if(action==='quantity-preset'){
        let combination=body.field==='roots'?this.doc.roots:this.doc.units[body.unit_id][body.field];for(const index of body.path)combination=combination[index];
        this.rangeModes.set(this.quantityKey(group),false);body.quantity=quantityPreset(node.dataset.preset,combination.length-1);this.quantityDrafts.delete(this.quantityKey(group));return this.step('quantity',body);
      }
      if(action==='quantity'){
        const controls=group.querySelector('.rq-quantity');
        let combination=body.field==='roots'?this.doc.roots:this.doc.units[body.unit_id][body.field];for(const index of body.path)combination=combination[index];
        body.quantity=quantityRange(controls.querySelector('[data-rq-min]').value,controls.querySelector('[data-rq-max]').value,combination.length-1);
        if(JSON.stringify(body.quantity)===JSON.stringify(combination[0]))return;
      }else body.indices=[...group.querySelectorAll(':scope > .rq-children > li > [data-rq-pick]:checked')].map(x=>Number(x.dataset.rqPick));
      return this.step(action,body);
    }
  }
}
