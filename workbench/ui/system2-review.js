import {demoCases, pdfSource} from './system2-demo-data.js';
import {DEMO_VERSION, newSession, restoreSession, reviewCounts, nextPending, recordReview} from './system2-review-state.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const statusLabel = status => ({pending:'To review',reviewed:'Reviewed',followup:'Needs follow-up'}[status || 'pending']);
const pdfUrl = '/api/pdf/CS005/' + pdfSource.sourceHash + '/' + encodeURIComponent(pdfSource.filename);
const sourceImage = page => '/demo-assets/cs005-page-' + (page + 1) + '.webp';

function picture(page, boxes, full = false, footnote = false) {
  const {width, height} = pdfSource.pages[page];
  const left = Math.min(...boxes.map(b => b[0])) - 3, top = Math.min(...boxes.map(b => b[1])) - 3;
  const right = Math.max(...boxes.map(b => b[2])) + 3, bottom = Math.max(...boxes.map(b => b[3])) + 3;
  const x = Math.max(0, left - 28), y = Math.max(0, top - (footnote ? 10 : 38));
  const crop = full ? `0 0 ${width} ${height}` : `${x} ${y} ${Math.min(width - x, right - x + 28)} ${Math.min(height - y, bottom - y + (footnote ? 10 : 38))}`;
  return `<svg class="s2-page ${full?'s2-full-page':''}" viewBox="${crop}" role="img" aria-label="Original PDF page ${page + 1}, ${footnote?'footnote':'review region'} outlined in red"><image href="${sourceImage(page)}" width="${width}" height="${height}"/><rect x="${left}" y="${top}" width="${right-left}" height="${bottom-top}" fill="none" stroke="#bf3c38" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
}

export class System2Review {
  constructor() {
    this.session = newSession(); this.actor = {}; this.key = ''; this.raw = null;
    this.root = null; this.reader = null; this.blobUrl = null; this.storageError = ''; this.message = '';
    window.addEventListener('storage', event => {
      if (this.root?.isConnected && event.key === this.key && event.newValue !== this.raw) {
        this.storageError = 'This demo changed in another tab. Reload the demo before continuing.';
        this.showError(this.storageError); this.lockControls();
      }
    });
  }
  leave() {
    this.reader?.abort(); this.reader = null;
    if (this.blobUrl) URL.revokeObjectURL(this.blobUrl);
    this.blobUrl = null; this.root = null;
  }
  mount(root, {actor, history, navigate}) {
    if(this.actor.id!==actor.id){this.message='';this.historySelection=null;}
    this.root = root; this.actor = {...actor}; this.history = history; this.navigate = navigate;
    if(!history)this.historySelection=null;
    this.key = actor.id ? `workbench.system2-demo.${DEMO_VERSION}.${actor.id}` : '';
    this.storageError = ''; this.raw = null;
    try { this.raw = this.key ? localStorage.getItem(this.key) : null; this.session = restoreSession(this.raw); }
    catch (error) { this.session = newSession(); this.storageError = 'Unable to load saved demo records. ' + error.message; }
    this.render();
  }
  persist(next) {
    if (!this.key) throw Error('Select a reviewer at the top first.');
    if (this.storageError) throw Error(this.storageError);
    if (localStorage.getItem(this.key) !== this.raw) throw Error('This demo changed in another tab. Reload the demo before continuing.');
    const raw = JSON.stringify(next);
    localStorage.setItem(this.key, raw);
    this.raw = raw; this.session = next;
  }
  query(selector) { return this.root?.querySelector(selector); }
  on(selector, event, handler) {
    const element = this.query(selector);
    if (element) element.addEventListener(event, handler);
  }
  showError(message) {
    const target = this.query('#s2-error');
    if (target) { target.textContent = message; target.hidden = !message; }
  }
  lockControls() { this.root.querySelectorAll('[data-s2-write], #s2-note, #s2-editor, #s2-record, #s2-fields, [name="s2-list"]').forEach(el => el.disabled = true); }
  saveDraft(patch) {
    const item = this.item();
    try {
      const next = structuredClone(this.session);
      next.items[item.id] ??= {status:'pending'};
      next.items[item.id].draft = {...next.items[item.id].draft, ...patch};
      this.persist(next);
      this.query('#s2-draft-status').textContent = 'Draft saved in this browser. No decision recorded.';
      this.showError('');
    } catch (error) {
      this.showError('Draft was not saved. Copy your text before leaving. ' + error.message);
      this.storageError = error.message; this.root.querySelectorAll('[data-s2-write]').forEach(el => el.disabled = true);
    }
  }
  item() { return demoCases.find(item => item.id === this.session.selected); }
  select(id) {
    this.session.selected = id; this.message = ''; this.full = false;
    if (this.key && !this.storageError) { try { this.persist(this.session); } catch (error) { this.storageError = error.message; } }
    this.render(); this.query('#s2-question')?.focus();
  }
  render() {
    this.reader?.abort(); if (this.blobUrl) URL.revokeObjectURL(this.blobUrl); this.blobUrl = null;
    const counts = reviewCounts(this.session, demoCases);
    const banner = `<div class="s2-demo-bar"><div><span class="s2-badge">Review demo</span> <span>Sample data · Live System2 is not connected</span></div><small>Practice records stay in this browser, under your reviewer name.</small></div>`;
    this.root.innerHTML = `<div class="s2-workspace">${banner}<div id="s2-error" class="issue" role="alert" hidden></div><div id="s2-feedback" class="s2-feedback" role="status">${esc(this.message)}</div><div id="s2-body"></div></div>`;
    if (this.storageError) {
      this.showError(this.storageError);
      const button = document.createElement('button'); button.textContent = 'Reload demo';
      button.onclick = () => this.mount(this.root, {actor:this.actor,history:this.history,navigate:this.navigate});
      this.query('#s2-error').append(document.createElement('br'), button);
    }
    if (this.history) {
      if(this.historySelection){
        this.session.selected=this.historySelection;
        this.query('#s2-body').innerHTML='<button id="s2-back-history">Back to review history</button><section class="s2-detail" id="s2-detail"></section>';
        this.on('#s2-back-history','click',()=>{this.historySelection=null;this.render();});
        this.renderItem(this.item());if(!this.actor.id||this.storageError)this.lockControls();
      }else this.renderHistory();
      return;
    }
    if(this.session.items[this.session.selected]?.status==='reviewed')this.session.selected=null;
    if (!this.session.selected && counts.pending) this.session.selected = demoCases.find(item => !this.session.items[item.id] || this.session.items[item.id].status === 'pending')?.id;
    const item = this.item();
    this.query('#s2-body').innerHTML = `<div class="s2-progress"><span><strong>${counts.pending+counts.followup} pending</strong> · ${counts.followup} need follow-up</span><button id="s2-history" type="button">Demo history</button></div><div class="review-layout s2-layout"><aside class="queue s2-queue" aria-label="Sample review queue"><div class="queue-head"><strong>Queue · ${counts.pending+counts.followup}</strong><input id="s2-search" aria-label="Find a sample" placeholder="Search ID or title" value="${esc(this.search||'')}"></div><div class="queue-list" id="s2-queue-list"></div></aside><section class="s2-detail" id="s2-detail"></section></div>`;
    this.on('#s2-history','click',() => this.navigate('system2History'));
    this.renderQueue();
    this.on('#s2-search','input',e=>{this.search=e.target.value;this.renderQueue();});
    if (!item) {
      this.query('#s2-detail').innerHTML = `<div class="panel empty"><h2>${counts.followup?'New reviews are complete':'No pending reviews'}</h2><p>${counts.followup?`${counts.followup} sample still needs follow-up. Select it from the queue to continue.`:'All reviewed samples are in Review history.'}</p><button id="s2-finished-history">View review history</button></div>`;this.on('#s2-finished-history','click',()=>this.navigate('system2History')); return;
    }
    this.renderItem(item);
    if (!this.actor.id || this.storageError) this.lockControls();
  }
  renderQueue() {
    const matches=demoCases.filter(item=>this.session.items[item.id]?.status!=='reviewed').filter(item=>(item.source+' '+item.title+' '+item.format).toLowerCase().includes((this.search||'').toLowerCase()));
    this.query('#s2-queue-list').innerHTML=matches.map(item=>`<button class="task ${item.id===this.session.selected?'active':''}" data-s2-item="${item.id}" aria-current="${item.id===this.session.selected?'true':'false'}"><span>${esc(item.source)} · ${item.format}</span><strong>${esc(item.title)}</strong><small class="s2-state-${this.session.items[item.id]?.status||'pending'}">${statusLabel(this.session.items[item.id]?.status)}</small></button>`).join('') || (this.search?'<p class="muted">No samples match this search.</p><button id="s2-clear-search">Clear search</button>':'<p class="muted">No pending reviews.</p>');
    this.root.querySelectorAll('[data-s2-item]').forEach(button=>button.onclick=()=>this.select(button.dataset.s2Item));
    this.on('#s2-clear-search','click',()=>{this.search='';this.query('#s2-search').value='';this.renderQueue();});
  }
  renderItem(item) {
    const saved = this.session.items[item.id] || {}, draft = saved.draft || {};
    const reviewed = saved.status === 'reviewed';
    this.query('#s2-detail').innerHTML = `<div class="s2-task-heading"><span class="eyebrow">${esc(item.source)} · ${esc(item.anchor)}</span><h2 id="s2-question" tabindex="-1">${esc(item.question)}</h2><p>${esc(item.hint)}</p></div>${!this.actor.id?'<div class="issue">Select a reviewer at the top to try a decision. You can browse the examples now.</div>':''}${saved.status==='followup'?'<div class="s2-followup">Needs follow-up. This sample has not passed review.</div>':''}<div class="s2-mobile-tabs" role="group" aria-label="Comparison view"><button id="s2-tab-source" aria-pressed="true">Original source</button><button id="s2-tab-text" aria-pressed="false">Extracted result</button></div><div class="s2-comparison" data-mobile-pane="source"><section class="s2-source"><div class="s2-pane-heading"><h3>Original source</h3><span>${item.format === 'PDF'?'Historical PDF':'Synthetic example'}</span></div><div id="s2-source-body"></div></section><section class="s2-result"><div class="s2-pane-heading"><h3>Extracted result</h3><span>${reviewed?'Demo reviewed':'To verify'}</span></div><div id="s2-result-body"></div>${reviewed?`<div class="s2-followup">${esc(this.session.events.filter(e => e.itemId===item.id).at(-1)?.label)} · Demo only</div><button id="s2-reopen" data-s2-write>Reopen sample</button>`:`<details class="s2-notes" ${draft.note?'open':''}><summary>Notes <span class="muted">(optional for approval)</span></summary><label class="s2-sr-only" for="s2-note">Review notes</label><textarea id="s2-note" placeholder="What should the next reviewer know?">${esc(draft.note || '')}</textarea></details><small id="s2-draft-status">Edits and notes are drafts until you save a decision.</small><div class="s2-actions" id="s2-actions"></div><details class="s2-other"><summary>Other issue</summary><p class="muted">Add a short note first. These actions keep the sample unresolved.</p><div class="s2-other-actions"><button data-s2-write data-s2-action="unreadable">Cannot read source</button><button data-s2-write data-s2-action="missing">Report missing content</button><button data-s2-write data-s2-action="reparse">Request reprocessing</button><button data-s2-write data-s2-action="pending">Keep pending</button></div></details>`}</section></div>`;
    this.renderSource(item);
    if(saved.status==='followup'){
      const previous=this.session.events.filter(event=>event.itemId===item.id).at(-1);
      const reason=document.createElement('p');reason.className='s2-followup-note';reason.textContent=previous?.note||'';
      this.query('.s2-followup')?.append(reason);
    }
    this.renderResult(item, draft, saved);
    this.on('#s2-note','input',e => this.saveDraft({note:e.target.value}));
    this.on('#s2-reopen','click',() => this.decide('reopen'));
    this.root.querySelectorAll('[data-s2-action]').forEach(button => button.onclick = () => this.decide(button.dataset.s2Action));
    for (const pane of ['source','text']) this.on('#s2-tab-'+pane,'click',() => {
      this.query('.s2-comparison').dataset.mobilePane = pane;
      for (const name of ['source','text']) this.query('#s2-tab-'+name).setAttribute('aria-pressed',String(pane===name));
    });
  }
  renderSource(item) {
    const source = this.query('#s2-source-body');
    if (item.format === 'PDF') {
      source.innerHTML = `<div class="s2-evidence-links"><a href="${pdfSource.officialUrl}" target="_blank" rel="noopener noreferrer">Official source ↗</a><a href="/api/original/CS005">Download PDF ↓</a></div><div class="s2-view-controls"><button id="s2-region" aria-pressed="${!this.full}">Highlighted region</button><button id="s2-page" aria-pressed="${!!this.full}">Full page</button><select id="s2-zoom" aria-label="Source zoom">${[['fit','Fit width'],['150','150%'],['200','200%']].map(([value,label])=>`<option value="${value}" ${(this.zoom||'fit')===value?'selected':''}>${label}</option>`).join('')}</select></div><div class="s2-image-scroll" id="s2-image" data-zoom="${this.zoom||'fit'}" tabindex="0" aria-label="Source image; zoom to enlarge, scroll to move across the page">${picture(item.page,item.boxes,!!this.full)}</div><p class="s2-source-caption">Page ${item.page+1} of 89 · Red outline marks the review area. Zoom to enlarge.${item.kind==='table'?' Region located manually for this demo.':''}</p>${item.footnote?`<details><summary>Footnote 6 · View source</summary><div class="s2-image-scroll">${picture(item.page,item.footnote.boxes,false,true)}</div><p class="muted">${esc(item.footnote.text)}</p></details>`:''}<button id="s2-open-pdf" class="s2-reader-toggle">Screenshot does not match? Open full PDF</button><div id="s2-reader-area" hidden></div><details class="s2-provenance"><summary>Source details</summary><p>${esc(pdfSource.title)}<br>Version 1.0 · May 2025 · English</p><p>Historical extraction: ${pdfSource.historicalRun}. This document is demonstration evidence, not a live System2 task.</p><small>Source SHA-256: ${pdfSource.sourceHash}</small></details>`;
      this.on('#s2-region','click',() => { this.full=false;this.renderSource(item); });
      this.on('#s2-page','click',() => { this.full=true;this.renderSource(item); });
      this.on('#s2-zoom','change',e=>{this.zoom=e.target.value;this.query('#s2-image').dataset.zoom=this.zoom;});
      this.on('#s2-open-pdf','click',() => this.openPDF(item));
      // Failure to load an evidence image never completes a review.
      const probe = new Image(); probe.onerror = () => {if (this.item()?.id===item.id && this.query('#s2-image')) this.query('#s2-image').textContent = 'Screenshot unavailable. Open the full PDF below.';};probe.src=sourceImage(item.page);
    } else if (item.kind === 'html') {
      source.innerHTML = `<div class="s2-html-source"><small>Sample document / Records</small><h3>3.2 Records</h3><div class="s2-highlight"><p>Keep the following records:</p><ol type="a"><li>Inspection date.</li><li>Operator name.</li></ol></div><h3>3.3 Retention</h3><p class="muted">This adjacent heading is included to show the section boundary.</p></div><p class="s2-source-caption">Synthetic HTML example. Source layout is shown as inert content.</p>`;
    } else {
      source.innerHTML = `<div class="s2-sheet-scroll"><table class="s2-sheet" aria-label="Synthetic Checklist worksheet"><thead><tr><th></th><th>A</th><th>B</th><th>C</th></tr></thead><tbody><tr><th>1</th><td colspan="3">Inspection checklist · Example</td></tr><tr><th>2</th><td></td><td colspan="2">Record details</td></tr><tr><th>3</th><td>Item</td><td>Record</td><td>Required fields</td></tr><tr><th>4</th><td>1</td><td class="s2-cell-focus">Inspection record</td><td class="s2-cell-focus">Date and operator name</td></tr><tr><th>5</th><td>2</td><td>Equipment record</td><td>Equipment ID</td></tr></tbody></table></div><p class="s2-source-caption">Checklist · B4:C4 highlighted, with neighboring headers and rows. Synthetic workbook example.</p>`;
    }
  }
  renderResult(item, draft, saved) {
    const body=this.query('#s2-result-body'), actions=this.query('#s2-actions');
    const reviewed=saved.status==='reviewed';
    const editor=draft.editing && !reviewed;
    if (editor) {
      body.innerHTML=`<label for="s2-editor">Corrected text</label><textarea id="s2-editor" class="s2-editor" spellcheck="true">${esc(draft.text??item.text)}</textarea><p class="muted">Keep the original meaning and any footnote reference.</p>`;
      this.on('#s2-editor','input',e=>this.saveDraft({text:e.target.value}));
    } else if (item.kind==='table') {
      body.innerHTML=`<p class="s2-result-label">Historical table output · 2 rows</p><div class="s2-sheet-scroll"><table class="s2-extracted-table"><tbody>${item.cells.map(row=>'<tr>'+row.map(cell=>'<td>'+esc(cell)+'</td>').join('')+'</tr>').join('')}</tbody></table></div><div class="s2-followup">The table body is missing from this output. Some text was extracted separately as paragraphs.</div><p>Record the missing area once. You do not need to retype the entire table.</p><label for="s2-table-note">What needs reprocessing?</label><textarea id="s2-table-note">${esc(draft.note??'Table 1: restore the body rows and their column relationships. Check all seven requirements on page 21.')}</textarea><p class="muted">A reprocessing request keeps this item open. In this demo, no parser is started.</p>`;
      this.on('#s2-table-note','input',e=>{this.saveDraft({note:e.target.value});const note=this.query('#s2-note');if(note)note.value=e.target.value;});
    } else if (item.kind==='join' && !reviewed) {
      body.innerHTML=item.pieces.map((text,i)=>`<div class="s2-fragment"><small>Fragment ${i+1}</small><p>${esc(text)}</p></div>`).join('')+'<p class="muted">[^6] is the footnote reference. The footnote source is available on the left.</p>';
    } else {
      body.innerHTML=`<div class="s2-extracted-text">${esc(saved.result?.text??item.text)}</div>`;
    }
    if (item.kind==='html') {
      body.insertAdjacentHTML('beforeend',`<fieldset class="s2-choices" ${reviewed?'disabled':''}><legend>Relationship in the source</legend>${[['siblings','a and b are parallel items'],['nested','b belongs inside a']].map(([value,label])=>`<label><input type="radio" name="s2-list" value="${value}" ${(draft.choice??saved.result?.relationship)===value?'checked':''}>${label}</label>`).join('')}</fieldset>`);
      this.root.querySelectorAll('[name="s2-list"]').forEach(radio=>radio.onchange=()=>this.saveDraft({choice:radio.value}));
    }
    if (item.kind==='excel') {
      const selected=(value, expected)=>value===expected?'selected':'';
      body.insertAdjacentHTML('beforeend',`<div class="s2-mapping"><label for="s2-record">Record comes from</label><select id="s2-record" ${reviewed?'disabled':''}><option value="">Choose column</option><option value="B" ${selected(draft.recordColumn??saved.result?.columns?.record,'B')}>B · Record</option><option value="C" ${selected(draft.recordColumn??saved.result?.columns?.record,'C')}>C · Required fields</option></select><label for="s2-fields">Required fields come from</label><select id="s2-fields" ${reviewed?'disabled':''}><option value="">Choose column</option><option value="B" ${selected(draft.fieldsColumn??saved.result?.columns?.requiredFields,'B')}>B · Record</option><option value="C" ${selected(draft.fieldsColumn??saved.result?.columns?.requiredFields,'C')}>C · Required fields</option></select></div>`);
      this.on('#s2-record','change',e=>this.saveDraft({recordColumn:e.target.value}));this.on('#s2-fields','change',e=>this.saveDraft({fieldsColumn:e.target.value}));
    }
    if (!actions) return;
    if(item.kind==='table') this.query('.s2-notes').hidden=true;
    const primary=editor?['correct','Save correction & next']:({text:['accept','Accept & next'],join:['merge','Merge & next'],table:['reparse','Request reprocessing & next'],html:['list','Save relationship & next'],excel:['columns','Save mapping & next']}[item.kind]);
    actions.innerHTML=`<button class="primary" id="s2-primary" data-s2-write>${primary[1]}</button>${['text','join'].includes(item.kind)?`<button id="s2-edit" data-s2-write>${editor?'Cancel editing':'Correct text'}</button>`:''}<button id="s2-skip">Skip for now</button>${item.kind==='join'&&!editor?'<button id="s2-separate" data-s2-write>Keep as separate paragraphs</button>':''}`;
    this.on('#s2-primary','click',()=>this.decide(primary[0]));
    this.on('#s2-separate','click',()=>this.decide('separate'));
    this.on('#s2-edit','click',()=>{this.saveDraft({editing:!editor,text:draft.text??item.text});if(!this.storageError){this.renderResult(item,this.session.items[item.id].draft,saved);this.query('#s2-editor')?.focus();}});
    this.on('#s2-skip','click',()=>{this.session.selected=nextPending(this.session,demoCases,item.id);this.message='Skipped. No decision was recorded.';this.render();});
  }
  decide(action) {
    const item=this.item(),draft={...this.session.items[item.id]?.draft};
    if (this.query('#s2-note')) draft.note=this.query('#s2-note').value;
    if (item.kind==='table' && action==='reparse') draft.note=this.query('#s2-table-note').value;
    if (this.query('#s2-editor')) draft.text=this.query('#s2-editor').value;
    try {
      const next=recordReview(this.session,item,this.actor,action,draft);
      next.selected=action==='reopen'?item.id:nextPending(next,demoCases,item.id);
      this.persist(next);this.message=next.events.at(-1).label+'. Saved to demo history.';this.full=false;if(this.history&&action==='reopen'){this.historySelection=null;this.navigate('system2');return;}this.render();
      this.query('#s2-question')?.focus();
    } catch(error) {
      this.showError(error.message);
      if (!draft.note && ['unreadable','missing','pending','reparse'].includes(action)) { const note=this.query('#s2-note'); if(note){note.closest('details').open=true;note.focus();} }
    }
  }
  async openPDF(item) {
    this.reader?.abort();this.reader=new AbortController();const signal=this.reader.signal;
    const area=this.query('#s2-reader-area');area.hidden=false;
    area.innerHTML=`<div id="s2-pdf-status" role="status">Checking that the full PDF matches this sample…</div><div id="s2-pdf-frame"></div><details><summary>Choose a local copy of this PDF</summary><p class="muted">Select the downloaded original. Its file content must match this sample. It stays in your browser.</p><label for="s2-local-pdf">Local PDF</label><input id="s2-local-pdf" type="file" accept=".pdf,application/pdf" hidden><div class="file-picker"><button type="button" id="s2-choose-pdf">Choose PDF</button><span id="s2-file-name">No file selected</span></div><p id="s2-file-status" role="status"></p></details><button id="s2-close-pdf">Back to screenshot</button>`;
    this.query('#s2-image').hidden=true;this.query('.s2-view-controls').hidden=true;
    const display=(url,label)=>{
      if(signal.aborted||!area.isConnected)return;
      const frame=document.createElement('iframe');frame.className='s2-pdf-reader';frame.title='Full PDF original, page '+(item.page+1);frame.src=url+`#page=${item.page+1}&view=FitH`;
      const box=this.query('#s2-pdf-frame');box.replaceChildren(frame);
      const link=document.createElement('a');link.href=frame.src;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Open full PDF in a new tab ↗';box.prepend(link);
      this.query('#s2-pdf-status').textContent=label+' Use the PDF controls to zoom, search and change pages. If the viewer is blank, open it in a new tab.';
    };
    this.on('#s2-close-pdf','click',()=>{this.reader.abort();if(this.blobUrl)URL.revokeObjectURL(this.blobUrl);this.blobUrl=null;this.renderSource(item);});
    this.on('#s2-choose-pdf','click',()=>this.query('#s2-local-pdf').click());
    this.on('#s2-local-pdf','change',async e=>{
      const file=e.target.files[0], message=this.query('#s2-file-status');if(!file)return;
      this.query('#s2-file-name').textContent=file.name;
      try {
        if(!/\.pdf$/i.test(file.name)||!file.size||file.size>50*1024*1024)throw Error('Choose a non-empty PDF smaller than 50 MB.');
        message.textContent='Checking PDF identity…';const buffer=await file.arrayBuffer();
        if(new TextDecoder().decode(buffer.slice(0,5))!=='%PDF-')throw Error('The file content is not a PDF.');
        const digest=await crypto.subtle.digest('SHA-256',buffer);const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
        if(hash!==pdfSource.sourceHash)throw Error('This is a different PDF or version. Select the original used for this sample.');
        if(signal.aborted||!area.isConnected)return;
        if(this.blobUrl)URL.revokeObjectURL(this.blobUrl);this.blobUrl=URL.createObjectURL(new Blob([buffer],{type:'application/pdf'}));
        message.textContent='File verified: it exactly matches the sample source. Nothing was uploaded.';display(this.blobUrl,'Verified local copy.');
      } catch(error){message.textContent=error.message;}
    });
    try {
      const response=await fetch('/api/preview/CS005',{signal});const info=await response.json();
      if(!response.ok)throw Error(info.error||'Original unavailable.');
      if(info.kind!=='pdf'||info.url!==pdfUrl)throw Error('The registered original has changed. Choose the matching local PDF below.');
      display(info.url,'Original file identity verified.');
    }catch(error){if(!signal.aborted&&area.isConnected)this.query('#s2-pdf-status').textContent='Cannot open the registered original. '+error.message+' You can choose a matching local copy below.';}
  }
  renderHistory() {
    const events=this.session.events.slice().reverse();
    this.query('#s2-body').innerHTML=`<section class="panel"><div class="s2-progress"><div><h2>Demo review history</h2><p class="muted">${esc(this.actor.name||'Select a reviewer to see their practice records')}. These records are excluded from live history and quality metrics.</p></div><button id="s2-back">Back to sample queue</button></div>${events.length?`<div class="s2-history">${events.map(event=>{const item=demoCases.find(i=>i.id===event.itemId);return `<article><div class="s2-history-title"><div><strong>${esc(event.label)}</strong><small>${esc(item?.title)} · ${esc(event.actor.name)} · ${esc(new Date(event.at).toLocaleString('en-GB'))}</small></div><button data-s2-history-item="${esc(event.itemId)}">View sample</button></div><p>${esc(event.note||'No note added.')}</p><details><summary>Decision details</summary><dl><dt>Before</dt><dd>${esc(this.resultText(event.before))}</dd><dt>After</dt><dd>${esc(this.resultText(event.after))}</dd><dt>Outcome</dt><dd>${statusLabel(event.status)} · Demo only</dd></dl></details></article>`;}).join('')}</div>`:'<div class="empty"><h3>No demo decisions yet</h3><p class="muted">Try a sample review. Your name, decision, notes and corrections will appear here.</p></div>'}</section>`;
    this.on('#s2-back','click',()=>this.navigate('system2'));
    this.root.querySelectorAll('[data-s2-history-item]').forEach(button=>button.onclick=()=>{
      this.session.selected=button.dataset.s2HistoryItem;
      try{this.persist(this.session);if(this.session.items[this.session.selected]?.status==='reviewed'){this.historySelection=this.session.selected;this.render();}else this.navigate('system2');}catch(error){this.showError(error.message);}
    });
  }
  resultText(result) {
    return [result.text,result.relationship?'Relationship: '+result.relationship:'',result.columns?`Record: column ${result.columns.record}; required fields: column ${result.columns.requiredFields}`:''].filter(Boolean).join('\n') || 'No text recorded';
  }
}
