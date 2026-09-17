// Manual outside-in extraction. All content mutations are source-bound server steps.
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const fields = ['Subject','Modal Verb','Main Verb','Object'];
export const relations = ['conditions','exceptions','subrequirement'];
export const codepointOffset = (text, utf16Offset) => Array.from(text.slice(0, utf16Offset)).length;
export function quantityLabel(q) { return Array.isArray(q) ? `${q[0]} to ${q[1]}` : `Exactly ${q}`; }
export function groupIds(group) { return group ? group.slice(1).flatMap(x => Array.isArray(x) ? groupIds(x) : [x]) : []; }
const button = (action,label,attrs='') => `<button type="button" data-rq="${action}" ${attrs}>${label}</button>`;
export class RequirementsEditor {
  constructor(materials) { this.m=materials; this.sessions=[]; this.results=[]; this.closedUnits=new Set(); this.sessionCollapsed=false; }
  get host() { return this.m.q('#mw-requirement-content'); }
  get locked() { return this.loading || this.pending || this.m.busy || this.m.opening || this.m.dirty || this.doc?.stale || !!this.retryRequest || this.m.collaboration.readonly; }
  key() { return `${this.m.state?.actor?.id || ''}:${this.m.id}:${this.m.material?.collaboration?.view || ''}`; }
  render(force=false) {
    const host=this.host;if(!host||!this.m.material)return;
    const key=this.key();
    if(key!==this.context) {
      this.context=key;this.closedUnits.clear();this.sessionCollapsed=false;this.doc=null;this.sessions=[];this.selected=null;this.results=[];this.notice='Loading saved splitting work…';this.lastRender=null;this.loading=true;
      this.loadList(key);
    }
    const auto=this.m.q('[data-action="reprocess"]');if(auto){auto.disabled=true;auto.title='Automatic requirement extraction is not connected.';}
    const signature=[key,this.doc?.revision,this.selected,this.pending,this.m.busy,this.m.opening,this.m.dirty,this.notice,this.loading,this.results.length,this.m.collaboration.readonly].join('|');
    if(!force&&signature===this.lastRender)return;this.lastRender=signature;
    host.classList?.add('rq-editor');
    host.innerHTML=`${this.m.dirty?'<p class="rq-notice">Save the source content before splitting requirements.</p>':''}
      <p class="rq-status" role="status" aria-live="polite">${esc(this.notice||'Select a source block in the content pane, then choose To requirements.')}</p>
      ${this.retryRequest?button('retry','Retry saving this step'):''}
      <div class="rq-list">${this.orderedSessions().map((s,i)=>`<details class="rq-session" data-session="${esc(s.id)}" ${s.id===this.doc?.id&&!this.sessionCollapsed?'open':''}>
        <summary data-rq="open-session" data-id="${esc(s.id)}"><span class="rq-session-number">${i+1}</span><span class="rq-session-title">${esc(s.text.slice(0,110))}</span><span class="rq-badge">${s.phase==='complete'?'Complete':'In progress'}</span></summary>
        ${s.id===this.doc?.id?this.documentMarkup():''}</details>`).join('')}</div>
      ${!this.sessions.length?'<div class="rq-empty"><h4>Build a requirement from its original text</h4><p>Select a source block in the content pane and choose <strong>To requirements</strong>. Split and assign its wording here; each requirement stays in the list.</p><p>Automatic extraction: Not connected.</p></div>':''}`;
    host.onclick=e=>{const b=e.target.closest('[data-rq]');if(b&&!b.disabled){e.stopPropagation();if(b.dataset.rq==='open-session')e.preventDefault();this.action(b.dataset.rq,b).catch(error=>this.showError(error));}};
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
      this.sessions=result.sessions||[];this.notice='';this.loading=false;
      let remembered;try{remembered=sessionStorage.getItem('requirement-session:'+context);}catch{}
      const id=this.sessions.find(s=>s.id===remembered)?.id||this.sessions.at(-1)?.id;
      if(id)await this.open(id);else this.render(true);
    }catch(e){if(context===this.context){this.loading=false;this.notice=`Saved splitting work could not be loaded. ${e.message}`;this.render(true);}}
  }
  async open(id) {
    if(this.pending||this.retryRequest)return;
    const context=this.context,ticket=this.readTicket={};this.loading=true;this.notice='Opening saved splitting work…';this.render(true);
    try{const doc=await this.m.api('/api/requirements/session?'+new URLSearchParams({id}));if(context!==this.context||ticket!==this.readTicket)return;this.doc=doc;this.sessionCollapsed=false;this.results=[];this.searchPerformed=false;this.selected=this.unitIds()[0];for(const id of doc.done)this.closedUnits.add(id);this.notice=doc.stale?'Source content changed. This saved session is read-only. Bring the current passage to start a new session.':`Saved step ${doc.revision} · ${doc.phase==='complete'?'Splitting complete; material review is separate.':'Ready to continue.'}`;try{sessionStorage.setItem('requirement-session:'+context,id);}catch{}}
    catch(e){this.showError(e);}finally{if(context===this.context&&ticket===this.readTicket){this.loading=false;this.render(true);}}
  }
  showError(error) {this.notice=error.message||String(error);this.render(true);}
  async start(blockId) {
    if(this.pending||this.m.busy||this.m.opening||this.m.dirty||this.retryRequest||this.m.collaboration.readonly||this.loading)return;
    const block=this.m.draft.blocks.find(b=>b.id===blockId);if(!block||block.role==='document_information')return;
    const existing=this.sessions.find(s=>s.block_id===blockId&&s.text===block.text);
    if(existing&&!this.doc?.stale)return this.open(existing.id);
    await this.step('start',{material_id:this.m.id,material_revision:this.m.material.revision,block_id:blockId});
  }
  async step(action,body={},retry=null) {
    if(this.pending)return;
    if(!retry&&this.locked&&action!=='start')return;
    const request=retry||{request_id:crypto.randomUUID(),action,...(this.doc?{session_id:this.doc.id,expected_revision:this.doc.revision}:{}),...body};
    const context=this.context;this.pending=true;this.notice='Saving step…';this.render(true);this.m.updateNavigationLock?.();
    try {
      const result=await this.m.api('/api/requirements/step',request);
      if(context!==this.context)return;
      this.retryRequest=null;this.doc=result.document;this.sessionCollapsed=false;
      for(const id of this.doc.done)this.closedUnits.add(id);
      if(action==='phase'&&body.phase==='complete')this.sessionCollapsed=true;
      if(!this.doc.units[this.selected])this.selected=this.unitIds().find(id=>!this.doc.done.includes(id))||this.unitIds()[0];
      const index=this.sessions.findIndex(s=>s.id===this.doc.id);if(index<0)this.sessions.push(this.doc);else this.sessions[index]=this.doc;
      try{sessionStorage.setItem('requirement-session:'+context,this.doc.id);}catch{}
      this.notice=`Saved step ${this.doc.revision} · ${this.doc.phase==='complete'?'Splitting complete. This does not confirm material review.':'You can leave and resume this passage.'}`;
    } catch(e) {
      // Keep the exact request for retry when transport failed after a possible save.
      if(!e.definitive)this.retryRequest=request;
      this.notice=e.status===409?'Another tab saved a newer step. Your attempted step was not applied. Reopen this saved passage to continue.':`${e.message}${this.retryRequest?' Retry this same step before leaving.':''}`;
    } finally {this.pending=false;this.render(true);this.m.updateNavigationLock?.();}
  }
  unitIds() {return Object.keys(this.doc.units).sort((a,b)=>(this.doc.spans?.[a]?.[0]||0)-(this.doc.spans?.[b]?.[0]||0)||(this.doc.spans?.[b]?.[1]||0)-(this.doc.spans?.[a]?.[1]||0));}
  label(id) { const local=this.unitIds(),n=local.indexOf(id);return this.doc.labels?.[id] || (n<0?`Linked ${id.slice(0,8)}`:`${this.doc.roles[id]==='condition'?'C':'R'}${n+1}`); }
  unitText(id) {return this.doc.units[id]?.text||this.doc.reference_evidence[id]?.text||id;}
  documentMarkup() {
    const d=this.doc,disabled=this.locked?'disabled':'',complete=d.phase==='complete';
    return `<div class="rq-session-body"><div class="rq-source-context"><span>${esc(d.chapter||'Original passage')}</span>${button('locate','Locate original')}</div>
      ${complete?`<p class="rq-hint">Splitting complete. Material review is separate.</p>${button('phase','Resume editing',`data-phase="fields" ${disabled}`)}`:''}
      <div class="rq-units">${this.unitIds().map(id=>this.unitMarkup(d.units[id],disabled,complete)).join('')}</div>
      ${this.unitIds().length>1?`<details class="rq-outer"><summary>Relationships between requirements</summary>${this.groupMarkup(d.roots,'roots',null,[],complete)}</details>`:''}
      <div class="rq-footer">${!complete?button('phase','Complete &amp; collapse',`data-phase="complete" ${disabled||d.done.length!==Object.keys(d.units).length?'disabled':''}`):''}${button('reload','Reload saved work',this.pending||this.retryRequest?'disabled':'')}</div>
      <details class="rq-history"><summary>History &amp; structured result</summary><p>Restoring creates a new saved revision. Original history remains available. These personal sessions are stored locally; collaboration ZIPs currently contain source and material review work only.</p>${button('history','Load step history',this.pending?'disabled':'')}<div class="rq-history-list">${(d.steps||[]).map(s=>`<div>Step ${s.revision} · ${esc(s.action)} ${button('restore','Restore',`data-revision="${s.revision}" ${disabled}`)}</div>`).join('')}</div><pre>${esc(JSON.stringify({requirements:d.roots,units:Object.values(d.units)},null,2))}</pre></details></div>`;
  }
  unitMarkup(u,disabled,complete) {
    const done=this.doc.done.includes(u.id),terminal=this.doc.roles[u.id]==='condition';
    return `<details class="rq-unit" data-unit="${esc(u.id)}" ${!this.closedUnits.has(u.id)?'open':''}>
      <summary><strong>${esc(this.label(u.id))}</strong><span class="rq-unit-preview">${esc(u.text.slice(0,100))}</span><span class="rq-badge">${done?'Finished':'Editing'}</span></summary>
      <div class="rq-unit-body"><label>Original text<textarea data-rq-text aria-label="${esc(this.label(u.id))} original text" readonly rows="4">${esc(u.text)}</textarea></label>
      ${!complete?`<p class="rq-hint">${terminal?'This condition retains its original wording. Split only when it contains separate components.':'Select wording, then click its field below. To separate requirements, place the cursor at their boundary.'}</p>${button('split','Split at cursor',disabled)}`:''}
      ${!terminal?`<dl class="rq-fields">${fields.map((f,i)=>`<div class="rq-field rq-field-${i}"><dt>${!complete?button('assign',esc(f),`data-field="${f}" title="Assign selected original text to ${f}" ${disabled}`):esc(f)}</dt><dd><span>${u[f]?esc(u[f]):'<span class="rq-blank">Select wording above</span>'}</span>${u[f]&&!complete?button('clear','Clear',`data-field="${f}" aria-label="Clear ${f}" ${disabled}`):''}</dd></div>`).join('')}</dl>`:''}
      ${relations.filter(f=>u[f]).map(f=>`<details class="rq-relation" open><summary>${f}</summary>${this.groupMarkup(u[f],f,u.id,[],complete)}</details>`).join('')}
      ${!complete&&!terminal?`<details class="rq-add-relations"><summary>Add a condition, exception or subrequirement</summary><p class="rq-hint">Select wording in the original text above, then choose its relationship.</p><div class="rq-assign">${relations.map(f=>button('extract',esc(f),`data-field="${f}" ${disabled}`)).join('')}</div>${this.linkMarkup(u,disabled)}</details>`:''}
      ${!complete?`<div class="rq-unit-finish">${button('done',done?'Finished':'Finish &amp; collapse',`${disabled||done?'disabled':''}`)}</div>`:''}</div></details>`;
  }
  groupMarkup(group,field,owner,path=[],readonly=false) {
    if(!group)return '<p class="rq-blank">Not stated</p>';
    const disabled=this.locked||readonly?'disabled':'',q=group[0],range=Array.isArray(q),identity=path.join('.');
    return `<div class="rq-group" data-rq-group data-field="${field}" data-owner="${owner||''}" data-path="${identity}"><details class="rq-group-options"><summary>${quantityLabel(q)} of ${group.length-1} · count &amp; grouping</summary><div class="rq-quantity">${!readonly?`<label>Count<select data-rq-count ${disabled}><option value="exact" ${!range?'selected':''}>Exactly k</option><option value="range" ${range?'selected':''}>Range min–max</option></select></label><label>k / min<input data-rq-min type="number" min="0" max="${group.length-1}" value="${range?q[0]:q}" ${disabled}></label><label>max<input data-rq-max type="number" min="0" max="${group.length-1}" value="${range?q[1]:q}" ${disabled}></label>${button('quantity','Set count',disabled)}`:''}</div>${!readonly?`<div class="rq-group-actions">${button('group','Group selected',disabled)}${button('ungroup','Expand selected group',disabled)}${field!=='roots'?button('unlink','Detach selected',disabled):''}</div>`:''}</details>
      <ol class="rq-children">${group.slice(1).map((child,i)=>`<li>${!readonly?`<input type="checkbox" data-rq-pick="${i+1}" aria-label="Select item ${i+1} in ${field} ${identity||'outer group'}" ${disabled}>`:''}${Array.isArray(child)?this.groupMarkup(child,field,owner,[...path,i+1],readonly):`<div class="rq-reference">${button('select-unit',this.label(child),`data-id="${child}" title="${esc(child)}" ${this.doc.units[child]?'':'disabled'}`)}<span>${esc(this.unitText(child))}</span>${!this.doc.units[child]?button('reference-source','View linked original',`data-id="${child}"`):''}</div>`}</li>`).join('')}</ol>
      </div>`;
  }
  linkMarkup(u,disabled) {
    const local=Object.values(this.doc.units).filter(x=>x.id!==u.id),choices=[...local,...this.results.filter(x=>!this.doc.units[x.id])];
    return `<details class="rq-links"><summary>Link an existing requirement</summary><p>Select the requirement ID belonging to the referenced passage or chapter.</p><label>Find by original text, extracted chapter or ID<input data-rq-search type="search" aria-label="Find requirement by text chapter or ID"></label>${button('search','Find requirements',disabled)}<label>Requirement<select data-rq-target aria-label="Requirement to link">${choices.map(x=>`<option value="${x.id}">${esc(x.chapter?x.chapter+' · ':'')}${esc(x.text.slice(0,110))} · ${x.id.slice(0,8)}</option>`).join('')}</select></label><label>Relationship<select data-rq-relation>${relations.map(f=>`<option>${f}</option>`).join('')}</select></label>${button('link','Link selected requirement',`${disabled||!choices.length?'disabled':''}`)}<p>${this.searchPerformed?`${this.results.length} saved units found for this reviewer.`:''}</p></details>`;
  }
  async action(action,node) {
    if(action==='open-session'){
      if(this.pending||this.retryRequest||this.loading)return;
      if(node.dataset.id!==this.doc?.id)return this.open(node.dataset.id);
      this.sessionCollapsed=!this.sessionCollapsed;return this.render(true);
    }
    const card=node.closest?.('[data-unit]'),scope=card||this.host;
    if(card){if(this.selected!==card.dataset.unit){this.results=[];this.searchPerformed=false;}this.selected=card.dataset.unit;}
    if(action==='retry')return this.step('',{},this.retryRequest);
    if(action==='start')return this.start(this.host.querySelector('[data-rq-block]')?.value);
    if(action==='reload'||action==='history')return this.open(this.doc.id);
    if(action==='select-unit'){this.selected=node.dataset.id;this.closedUnits.delete(this.selected);this.render(true);this.host.querySelector(`[data-unit="${this.selected}"]`)?.scrollIntoView({block:'nearest'});return;}
    if(action==='next'){this.selected=this.unitIds().find(id=>!this.doc.done.includes(id))||this.selected;return this.render(true);}
    if(action==='locate'){const ref=this.doc.source_refs[0];if(ref)this.m.locate(ref);return;}
    if(action==='reference-source'){const id=node.dataset.id,ref=this.doc.reference_evidence[id];if(!ref)return;const linked=await this.m.api('/api/requirements/session?'+new URLSearchParams({id:ref.session_id}));const location=ref.source.source_refs?.[0];this.m.dialog(`<h2>Linked requirement original</h2><p class="rq-original">${esc(ref.text)}</p><p>${esc(linked.title)} · ${esc(linked.chapter||'Original passage')}${location?.page?' · Page '+esc(location.page):''}</p><p>${linked.stale?'The source content has changed; this link retains the previously saved wording.':'Source wording retained with the saved reference.'}</p><a href="/api/material/original?${new URLSearchParams({id:linked.material_id})}" target="_blank" rel="noopener">Open original document</a><details><summary>Reference identity</summary><p>${esc(id)} · saved revision ${ref.revision}</p></details>`);return;}
    if(action==='search'){
      const context=this.context,session=this.doc.id,selected=this.selected,q=scope.querySelector('[data-rq-search]').value;const result=await this.m.api('/api/requirements/search?'+new URLSearchParams({q}));
      if(context!==this.context||session!==this.doc.id||selected!==this.selected)return;this.results=result.units;this.searchPerformed=true;this.render(true);this.host.querySelector(`[data-unit="${selected}"] .rq-add-relations`).open=true;this.host.querySelector(`[data-unit="${selected}"] .rq-links`).open=true;return;
    }
    if(this.locked)return;
    const body={unit_id:this.selected};
    if(action==='phase')return this.step('phase',{phase:node.dataset.phase});
    if(action==='restore')return this.step('restore',{history_revision:Number(node.dataset.revision)});
    if(action==='done')return this.step('done',body);
    if(action==='link'){body.field=scope.querySelector('[data-rq-relation]').value;body.target_id=scope.querySelector('[data-rq-target]').value;return this.step(action,body);}
    if(action==='clear')return this.step('clear',{...body,field:node.dataset.field});
    if(['split','assign','extract'].includes(action)){
      const area=scope.querySelector('[data-rq-text]');body.start=codepointOffset(area.value,area.selectionStart);body.end=codepointOffset(area.value,area.selectionEnd);
      if(action==='split'){body.at=body.start;delete body.start;delete body.end;}else body.field=node.dataset.field;
      return this.step(action,body);
    }
    if(['quantity','group','ungroup','unlink'].includes(action)){
      const group=node.closest('[data-rq-group]');body.unit_id=group.dataset.owner;body.field=group.dataset.field;body.path=group.dataset.path?group.dataset.path.split('.').map(Number):[];
      if(action==='quantity'){
        const controls=group.querySelector('.rq-quantity'),low=Number(controls.querySelector('[data-rq-min]').value),high=Number(controls.querySelector('[data-rq-max]').value);
        body.quantity=controls.querySelector('[data-rq-count]').value==='exact'?low:[low,high];
      }else body.indices=[...group.querySelectorAll(':scope > .rq-children > li > [data-rq-pick]:checked')].map(x=>Number(x.dataset.rqPick));
      return this.step(action,body);
    }
  }
}
