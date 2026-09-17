from pathlib import Path
p=Path('workbench/ui/requirements.js')
s=p.read_text().replace('this.results=[]; }','this.results=[]; this.closedUnits=new Set(); this.sessionCollapsed=false; }',1)
s=s.replace("this.context=key;this.doc=null;", "this.context=key;this.closedUnits.clear();this.sessionCollapsed=false;this.doc=null;")
a=s.index('    const blocks=',s.index('  render('));b=s.index('    if(this.pending)host.setAttribute',a)
s=s[:a]+'''    host.innerHTML=`${this.m.dirty?'<p class="rq-notice">Save the source content before splitting requirements.</p>':''}
      <p class="rq-status" role="status" aria-live="polite">${esc(this.notice||'Select a source block in the content pane, then choose To requirements.')}</p>
      ${this.retryRequest?button('retry','Retry saving this step'):''}
      <div class="rq-list">${this.orderedSessions().map((s,i)=>`<details class="rq-session" data-session="${esc(s.id)}" ${s.id===this.doc?.id&&!this.sessionCollapsed?'open':''}>
        <summary data-rq="open-session" data-id="${esc(s.id)}"><span class="rq-session-number">${i+1}</span><span class="rq-session-title">${esc(s.text.slice(0,110))}</span><span class="rq-badge">${s.phase==='complete'?'Complete':'In progress'}</span></summary>
        ${s.id===this.doc?.id?this.documentMarkup():''}</details>`).join('')}</div>
      ${!this.sessions.length?'<div class="rq-empty"><h4>Build a requirement from its original text</h4><p>Select a source block in the content pane and choose <strong>To requirements</strong>. Split and assign its wording here; each requirement stays in the list.</p><p>Automatic extraction: Not connected.</p></div>':''}`;
    host.onclick=e=>{const b=e.target.closest('[data-rq]');if(b&&!b.disabled){e.stopPropagation();if(b.dataset.rq==='open-session')e.preventDefault();this.action(b.dataset.rq,b).catch(error=>this.showError(error));}};
    // Native disclosure is presentation only; retain it across each saved-step render.
    host.querySelectorAll?.('[data-unit]').forEach(card=>card.ontoggle=()=>{if(!card.isConnected)return;if(card.open)this.closedUnits.delete(card.dataset.unit);else this.closedUnits.add(card.dataset.unit);});
''' +s[b:]
s=s.replace('  async loadList(','''  orderedSessions() {
    const order=new Map((this.m.draft?.blocks||[]).map((b,i)=>[b.id,i]));
    return [...this.sessions].sort((a,b)=>(order.get(a.block_id)??Infinity)-(order.get(b.block_id)??Infinity));
  }
  async loadList(''',1)
s=s.replace('this.doc=doc;this.selected=this.unitIds()[0];','this.doc=doc;this.sessionCollapsed=false;this.results=[];this.searchPerformed=false;this.selected=this.unitIds()[0];for(const id of doc.done)this.closedUnits.add(id);')
s=s.replace('this.retryRequest=null;this.doc=result.document;','''this.retryRequest=null;this.doc=result.document;this.sessionCollapsed=false;
      for(const id of this.doc.done)this.closedUnits.add(id);
      if(action==='phase'&&body.phase==='complete')this.sessionCollapsed=true;''')
s=s.replace('this.sessions=this.sessions.filter(s=>s.id!==this.doc.id).concat(this.doc);','const index=this.sessions.findIndex(s=>s.id===this.doc.id);if(index<0)this.sessions.push(this.doc);else this.sessions[index]=this.doc;')
a=s.index('  documentMarkup()');b=s.index('  groupMarkup(',a)
s=s[:a]+'''  documentMarkup() {
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
    return `<details class="rq-unit" data-unit="${esc(u.id)}" ${!complete&&!this.closedUnits.has(u.id)?'open':''}>
      <summary><strong>${esc(this.label(u.id))}</strong><span class="rq-unit-preview">${esc(u.text.slice(0,100))}</span><span class="rq-badge">${done?'Finished':'Editing'}</span></summary>
      <div class="rq-unit-body"><label>Original text<textarea data-rq-text aria-label="${esc(this.label(u.id))} original text" readonly rows="4">${esc(u.text)}</textarea></label>
      ${!complete?`<p class="rq-hint">Select wording, then click its field below. To separate requirements, place the cursor at their boundary.</p>${button('split','Split at cursor',disabled)}`:''}
      ${!terminal?`<dl class="rq-fields">${fields.map((f,i)=>`<div class="rq-field rq-field-${i}"><dt>${!complete?button('assign',esc(f),`data-field="${f}" title="Assign selected original text to ${f}" ${disabled}`):esc(f)}</dt><dd><span>${u[f]?esc(u[f]):'<span class="rq-blank">Select wording above</span>'}</span>${u[f]&&!complete?button('clear','Clear',`data-field="${f}" aria-label="Clear ${f}" ${disabled}`):''}</dd></div>`).join('')}</dl>`:''}
      ${relations.filter(f=>u[f]).map(f=>`<details class="rq-relation" open><summary>${f}</summary>${this.groupMarkup(u[f],f,u.id,[],complete)}</details>`).join('')}
      ${!complete&&!terminal?`<details class="rq-add-relations"><summary>Add a condition, exception or subrequirement</summary><p class="rq-hint">Select wording in the original text above, then choose its relationship.</p><div class="rq-assign">${relations.map(f=>button('extract',esc(f),`data-field="${f}" ${disabled}`)).join('')}</div>${this.linkMarkup(u,disabled)}</details>`:''}
      ${!complete?`<div class="rq-unit-finish">${button('done',done?'Finished':'Finish &amp; collapse',`${disabled||done?'disabled':''}`)}</div>`:''}</div></details>`;
  }
''' +s[b:]
s=s.replace("    if(action==='retry')",'''    if(action==='open-session'){
      if(this.pending||this.retryRequest||this.loading)return;
      if(node.dataset.id!==this.doc?.id)return this.open(node.dataset.id);
      this.sessionCollapsed=!this.sessionCollapsed;return this.render(true);
    }
    const card=node.closest?.('[data-unit]'),scope=card||this.host;
    if(card){if(this.selected!==card.dataset.unit){this.results=[];this.searchPerformed=false;}this.selected=card.dataset.unit;}
    if(action==='retry')''',1)
s=s.replace("if(action==='select-unit'){this.selected=node.dataset.id;return this.render(true);}","if(action==='select-unit'){this.selected=node.dataset.id;this.closedUnits.delete(this.selected);this.render(true);this.host.querySelector(`[data-unit=\"${this.selected}\"]`)?.scrollIntoView({block:'nearest'});return;}")
s=s.replace("this.host.querySelector('[data-rq-search]')","scope.querySelector('[data-rq-search]')")
s=s.replace("this.host.querySelector('.rq-links').open=true", "this.host.querySelector(`[data-unit=\"${selected}\"] .rq-add-relations`).open=true;this.host.querySelector(`[data-unit=\"${selected}\"] .rq-links`).open=true")
s=s.replace("this.host.querySelector('[data-rq-relation]')","scope.querySelector('[data-rq-relation]')").replace("this.host.querySelector('[data-rq-target]')","scope.querySelector('[data-rq-target]')").replace("this.host.querySelector('[data-rq-text]')","scope.querySelector('[data-rq-text]')")
p.write_text(s)
p=Path('workbench/src/local_workbench/requirements.py');s=p.read_text().replace("(doc['phase'] != 'fields' or set(doc['done']) != set(doc['units']))", "set(doc['done']) != set(doc['units'])")
s=s.replace("if not u or doc['phase'] != 'fields':\n                raise ValueError('Choose a unit in the fields step.')","if not u:\n                raise ValueError('Choose a requirement unit.')")
s=s.replace("if doc['phase'] != 'fields' or not u:\n                raise ValueError('First establish the outer relationships, then open a unit.')","if not u:\n                raise ValueError('Choose a requirement unit.')")
p.write_text(s)
