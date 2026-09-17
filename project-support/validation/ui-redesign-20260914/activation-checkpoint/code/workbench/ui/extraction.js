import {showEvidence} from './evidence-viewer.js';
import {exportStatusText} from './export-status.js';
import {repairControls,showSourceContext} from './pdf-repairs.js';
import {showPages,showOutline} from './pdf-pages.js';
import {sourceCheckMarkup,wireSourceFindings} from './source-check.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const classificationLabel=value=>({requirement:'Requirement',context:'Related context',non_requirement:'Not a Requirement',undetermined:'Undetermined'})[value]||'Not recorded in this historical entry';
const passed = status => ['human_accepted','machine_accepted'].includes(status);
const percent = value => value == null ? 'Not calibrated' : `${(value * 100).toFixed(1)}%`;
const label = unit => unit.kind === 'coverage' ? 'Full-text coverage' : unit.edits?.identifier || unit.original.fields.identifier || unit.original.fields.title || unit.id;

export function dependencyMarkup(checks=[]){
  if(!checks.length)return '';
  return `<details class="ex-dependencies"><summary>Before B can proceed: ${checks.length} pending content checks</summary><p>These source ranges or shared passages also need content review. Confirming this item alone does not complete them. Each prerequisite is listed once; this is not an independent reviewer task count.</p>${checks.map(c=>`<article><strong>${esc(c.title)}</strong><p>${esc((c.scope||[]).join(' · '))}</p><p>${esc(c.reason)}</p>${c.available?`<button type="button" data-content-dependency="${esc(c.unit_id)}">Open prerequisite: ${esc(c.title)}</button>`:'<p>Source dependency unavailable. Repair is required before proceeding.</p>'}</article>`).join('')}</details>`;
}

const taskNames={content:'Text fidelity',structure:'Structure & location',requirement:'Requirement judgment',coverage:'Completeness check'};
const weeklyMessage=error=>({
  repair_and_recheck_before_closing_weekly_finding:'Complete the repair and content checks before closing this finding.',
  weekly_result_changed_refresh_required:'The result changed. Reopen this sample and compare the current result before submitting.',
  stale_weekly_sample:'This sample has a newer decision. Reopen it before submitting.',
  sample_source_changed_requires_followup:'The sampled source is no longer current. Keep the inspection unverified and follow up on the source change.',
  sample_original_changed_or_unavailable:'The original file changed or is unavailable. The inspection cannot be confirmed.',
  weekly_inspection_evidence_note_required:'Add the original evidence and your finding before submitting.'
}[error.message]||error.message);
export class Extraction {
  leave(){this.token=null;this.detailTicket=null;}
  async mount(container,{api,state,history=false,onReviewUnit}){
    const token=this.token={};this.container=container;this.api=api;this.state=state;this.history=history;this.onReviewUnit=onReviewUnit;this.cache??=new Map();
    container.innerHTML='<p role="status">Opening review tasks…</p>';
    try{
      this.data=await api('/api/system2/state?view=summary');if(this.token!==token)return;
      this.data.documents.sort((a,b)=>a.source.source_id.localeCompare(b.source.source_id));
      if(!this.data.documents.some(d=>d.id===this.docId))this.docId=this.data.documents[0]?.id;
      this.shell();await this.queue();
    }catch(e){if(this.token===token)container.textContent=e.message;}
  }
  shell(){
    const docs=this.data.documents, eligible=this.state.sources.filter(s=>s.effective_selection==='INCLUDE');
    this.stage??='content';
    this.container.innerHTML=`<section class="panel"><div class="row"><label>Source<select id="ex-document">${docs.map(d=>`<option value="${d.id}" ${d.id===this.docId?'selected':''}>${esc(d.source.source_id)}${d.processing_failure?" · Source follow-up":""}</option>`).join('')}</select></label><button id="ex-refresh">Refresh progress</button><a href="/api/system2/workbook?cached=true" download>Download full-text Excel</a><span id="ex-export-status"></span><button id="ex-qa">Weekly checks</button><button id="ex-source-issue">Report an original problem to Source Management System</button></div><div id="ex-progress"></div><details><summary>Source processing</summary><label>Included source<select id="ex-source">${eligible.map(s=>`<option value="${esc(s.source_id)}">${esc(s.source_id)} · ${esc(s.source_title)}</option>`).join('')}</select></label><button id="ex-start" ${!eligible.length?'disabled':''}>Start processing</button><button id="ex-control">Pause / resume</button><button id="ex-reprocess">Request reprocessing</button><p>Parsing starts explicitly. Accepted items are delivered incrementally.</p></details><p role="status" id="ex-message"></p></section><div class="ex-stages" role="group" aria-label="Review stage" ${this.history?'hidden':''}><button id="ex-stage-content" aria-pressed="${this.stage==='content'}">1 · Content proofreading <span id="ex-content-count"></span></button><button id="ex-stage-requirement" aria-pressed="${this.stage==='requirement'}">2 · Requirement judgment <span id="ex-requirement-count"></span></button><span id="ex-stage-waiting"></span></div>${this.history?'':`<p class="muted">${this.stage==='content'?'Check the original text, structure and completeness first. Accepted units move to Requirement judgment when their related content is ready.':'Only content that passed proofreading and dependency checks appears here. Review the machine suggestion, evidence and uncertainty before classifying.'}</p>`}<div class="review-layout extraction-review"><section class="queue"><div class="queue-head"><label>Chapter<select id="ex-chapter"><option value="">All chapters</option></select></label><label>Task type<select id="ex-type"><option value="">All tasks</option>${Object.entries(taskNames).filter(([k])=>this.stage==='requirement'?['requirement','coverage'].includes(k):k!=='requirement').map(([k,v])=>`<option value="${k}" ${this.type===k?'selected':''}>${v}</option>`).join('')}</select></label><input id="ex-search" type="search" aria-label="Search review items" placeholder="Find a number or text…" value="${esc(this.query||'')}"><label class="ex-review-toggle"><input id="ex-all" type="checkbox" ${this.showAll?'checked':''}> Browse all original content</label><div class="ex-pagination"><button id="ex-prev">Previous</button><span id="ex-count"></span><button id="ex-next">Next</button></div></div><div id="ex-list" class="queue-list"></div></section><section id="ex-detail" class="panel detail"></section></div>`;
    const q=s=>this.container.querySelector(s);
    const statusNode=q('#ex-export-status');
    const updateExport=()=>this.api('/api/system2/export-status').then(status=>{if(statusNode.isConnected)statusNode.textContent=exportStatusText(status);}).catch(()=>{if(statusNode.isConnected)statusNode.textContent='Excel synchronization status unavailable. Review decisions remain in the database.';}).finally(()=>setTimeout(()=>{if(statusNode.isConnected)updateExport();},5000));
    updateExport();
    for(const stage of ['content','requirement'])q('#ex-stage-'+stage).onclick=()=>{this.stage=stage;this.type='';this.offset=0;this.unitId=null;this.shell();this.queue();};
    q('#ex-document').onchange=e=>{this.docId=e.target.value;this.offset=0;this.chapter='';this.unitId=null;this.outlineParent=null;this.outlineOffset=0;this.queue();};
    q('#ex-refresh').onclick=()=>this.reload();
    q('#ex-start').onclick=()=>this.send('/api/system2/start',{source_ids:[q('#ex-source').value]});
    q('#ex-control').onclick=()=>{const d=this.doc();this.send('/api/system2/control',{document_id:d.id,revision:d.revision,action:d.state==='paused'?'resume':d.state==='failed'?'retry':'pause'});};
    q('#ex-reprocess').onclick=()=>{const d=this.doc();this.send('/api/system2/control',{document_id:d.id,revision:d.revision,action:'reprocess'});};
    q('#ex-source-issue').onclick=()=>{const d=this.doc();q('#ex-detail').innerHTML='<h2>Original problem</h2><p>Describe missing, incorrect or unreadable original content. Source Management System will receive a linked source review task.</p><textarea id="original-problem"></textarea><button id="original-report">Submit source issue</button>';q('#original-report').onclick=()=>this.send('/api/system2/source-issue',{document_id:d.id,source_sha256:d.source.content_hash,note:q('#original-problem').value});};
    q('#ex-qa').onclick=()=>qualityChecks(q('#ex-detail'),this.api,async item=>{this.docId=item.document_id;this.stage=item.stage==='A'?'content':'requirement';this.history=false;await this.queue();await this.select({id:item.repair_unit_id||item.unit_id});});
    q('#ex-chapter').onchange=e=>{this.chapter=e.target.value;this.offset=0;this.queue();};
    q('#ex-type').onchange=e=>{this.type=e.target.value;this.offset=0;this.queue();};
    q('#ex-search').oninput=e=>{this.query=e.target.value;clearTimeout(this.searchTimer);this.searchTimer=setTimeout(()=>{this.offset=0;this.queue();},200);};
    q('#ex-all').onchange=e=>{this.showAll=e.target.checked;this.offset=0;this.queue();};
    q('#ex-prev').onclick=()=>{this.offset=Math.max(0,(this.offset||0)-50);this.queue();};
    q('#ex-next').onclick=()=>{this.offset=(this.offset||0)+50;this.queue();};
  }
  doc(){return this.data.documents.find(d=>d.id===this.docId);}
  async queue(){
    const token=this.token, ticket=this.queueTicket={};const d=this.doc(),q=s=>this.container.querySelector(s);
    if(!d){q('#ex-detail').innerHTML='<h2>No source processing started</h2><p>Choose an included source under Source processing.</p>';return;}
    q('#ex-progress').innerHTML=`<div class="ex-metrics"><span><strong>${d.pending_count}</strong> Pending review items</span><span><strong>${d.waiting_count||0}</strong> Waiting for dependencies</span><span><strong>${d.published_count||0}</strong> Accepted Requirements</span><span><strong>${d.error||d.issues?.length?'Blocked':'Available'}</strong> Source evidence</span><span><strong>${d.complete?'Complete':'Incomplete'}</strong> Source coverage</span></div>${d.upstream_issues?.length?'<p class="issue">Original verification is pending in Source Management System. Downstream delivery is suspended.</p>':''}${d.error?'<p role="alert">'+(String(d.error).includes('empty_body')?'The registered file has no usable document body. Report the original problem to Source Management System.':'Processing needs attention. Open processing details for the recorded error.')+'</p>':''}<details><summary>Processing and evidence details</summary><p>${esc(d.state)} · ${d.unit_count} source units · policy ${this.data.policy.revision}</p><p>Items include content, table structure and coverage checks. Related items can overlap the same original passage; this count is not independent reviewer workload.</p><p>${esc([d.error,...(d.issues||[])].filter(Boolean).join(', '))}</p></details>`;
    const pageMode=d.source.file_format==='pdf'&&this.stage==='content'&&!this.history;
    if(pageMode){q('#ex-progress').insertAdjacentHTML('beforeend',`<button id="ex-discovery">${this.discovery==='pages'?'Return to review tasks':'Inspect original PDF pages'}</button>`);q('#ex-discovery').onclick=()=>{this.discovery=this.discovery==='pages'?'tasks':'pages';this.queue();};}
    if(pageMode&&d.hierarchy_version){q('#ex-progress').insertAdjacentHTML('beforeend','<button id="ex-outline">Inspect source outline</button>');q('#ex-outline').onclick=()=>{this.discovery='outline';this.outlineParent=null;this.queue();};}
    if(pageMode){q('#ex-progress').insertAdjacentHTML('beforeend','<button id="ex-references">PDF reference samples</button>');q('#ex-references').onclick=()=>{this.discovery='references';this.queue();};}
    q('.extraction-review').classList.toggle('reference-mode',pageMode&&this.discovery==='references');
    q('.queue-head').hidden=pageMode&&['pages','outline','references'].includes(this.discovery);
    if(d.state==='conversion_required'){this.conversion(q('#ex-detail'),d);return;}
    try{
      if(this.history){
        const data=await this.api('/api/system2/state?view=history_page&document_id='+encodeURIComponent(d.id)+'&offset='+(this.offset||0));if(token!==this.token)return;
        const history=data.items||[];q('#ex-count').textContent=`${data.offset+1}–${Math.min(data.offset+50,data.total)} / ${data.total}`;q('#ex-prev').disabled=!data.offset;q('#ex-next').disabled=data.offset+50>=data.total;
        q('#ex-list').textContent='Applied decisions';q('#ex-detail').innerHTML=history.map(h=>`<details><summary>${esc(h.actor)} · ${esc(h.action)}${h.classification_after?' · '+esc(classificationLabel(h.classification_after)):''}</summary><p>${esc(h.at||'Time not recorded in this older entry')} · Saved revision ${esc(h.revision)}</p>${['classify','clear_subdivision','subdivide_requirement'].includes(h.action)?'<p>Classification: '+esc(classificationLabel(h.classification_before))+' → '+esc(classificationLabel(h.classification_after))+'</p>':''}<p>${esc(h.note)}</p><button type="button" data-history-open="${esc(h.unit_id)}">Open current result to review</button>${h.subdivision_before||h.subdivision_after?'<p>Provisional B subdivision before / after</p><div class="ex-compare"><pre>'+esc(JSON.stringify(h.subdivision_before,null,2))+'</pre><pre>'+esc(JSON.stringify(h.subdivision_after,null,2))+'</pre></div>':''}${(h.created_units||[]).map(u=>`<p>Inserted original content</p><pre>${esc(u.fields.body)}</pre>`).join('')}<div class="ex-compare"><pre>${esc(JSON.stringify(h.before.fields,null,2))}</pre><pre>${esc(JSON.stringify(h.after.fields,null,2))}</pre></div></details>`).join('')||'<p>No applied decisions for this source.</p>';
        q('#ex-detail').querySelectorAll('[data-history-open]').forEach(b=>b.onclick=async()=>{
          try{const current=await this.api('/api/system2/state?'+new URLSearchParams({view:'unit',document_id:d.id,unit_id:b.dataset.historyOpen}));
            if(token===this.token)this.onReviewUnit(b.dataset.historyOpen,current.task?.stage||'content');
          }catch(e){b.insertAdjacentHTML('afterend','<p role="status">'+esc(e.message)+'</p>');}
        });return;
      }
      if(pageMode&&this.discovery==='references'){
        let module;
        try{module=await import('./pdf-references.js');}
        catch{throw Error('PDF reference review is not loaded by this running service. Existing review tasks remain available. Reopen this feature after the workbench service has been updated.');}
        if(token===this.token&&ticket===this.queueTicket)await module.showReferences(this);
        return;
      }
      const params=new URLSearchParams({view:'tasks',stage:this.stage,document_id:d.id,offset:this.offset||0,query:this.query||'',chapter:this.chapter||'',task_type:this.type||'',include_reviewed:!!this.showAll});
      const page=await this.api('/api/system2/state?'+params);if(token!==this.token||ticket!==this.queueTicket)return;
      this.page=page;for(const stage of ['content','requirement'])q('#ex-'+stage+'-count').textContent='('+page.stage_counts[stage]+')';q('#ex-stage-waiting').textContent=page.stage_counts.waiting+' waiting for dependencies';q('#ex-chapter').innerHTML='<option value="">All chapters</option>'+page.chapters.map(c=>`<option ${this.chapter===c?'selected':''}>${esc(c)}</option>`).join('');
      if(pageMode&&this.discovery==='pages'){await showPages(this);return;}
      if(pageMode&&this.discovery==='outline'&&d.hierarchy_version){await showOutline(this);return;}
      q('#ex-count').textContent=`${page.total?page.offset+1:0}–${Math.min(page.total,page.offset+50)} / ${page.total}`;q('#ex-prev').disabled=!page.offset;q('#ex-next').disabled=page.offset+50>=page.total;
      q('#ex-list').innerHTML=page.items.map(u=>`<button class="task" data-unit="${esc(u.id)}"><small>${esc(taskNames[u.task_type])}</small><strong>${esc(u.title)}</strong><small>${esc(u.chapter)}</small><span class="task-reason">${esc(u.reason)}</span>${u.waiting?'<small>Waiting for related content</small>':''}</button>`).join('');
      if(d.processing_failure&&this.stage==='content'){
        q('#ex-count').textContent+=' · 1 source follow-up';
        q('#ex-list').insertAdjacentHTML('afterbegin',`<button class="task" id="ex-processing-failure"><small>Source follow-up</small><strong>${esc(d.processing_failure.title)}</strong><span class="task-reason">${esc(d.processing_failure.reason)}</span></button>`);
        q('#ex-processing-failure').onclick=()=>{this.unitId='processing-failure';this.processingFailure(d);};
      }
      q('#ex-list').querySelectorAll('[data-unit]').forEach(b=>b.onclick=()=>this.select(page.items.find(u=>u.id===b.dataset.unit)));
      if(d.processing_failure&&this.stage==='content'&&(this.unitId==='processing-failure'||!page.items.length)){await this.processingFailure(d);return;}
      const next=this.requestedUnitId?{id:this.requestedUnitId}:page.items.find(u=>u.id===this.unitId)||page.items[0];this.requestedUnitId=null;if(next)await this.select(next);else q('#ex-detail').innerHTML='<h2>No matching actionable tasks</h2><p>Unfinished coverage and blocked dependencies remain recorded above. Browse all original content to inspect them.</p>';
    }catch(e){if(token===this.token)q('#ex-detail').textContent=e.message;}
  }
  async processingFailure(doc){
    const panel=this.container.querySelector('#ex-detail'),failure=doc.processing_failure,ticket=this.detailTicket={};
    const draftKey=`source-followup-draft:${this.state.actor.id}:${doc.id}`;
    const initial=`${failure.title}. ${failure.reason} Source ${doc.source.source_id}, snapshot ${doc.source.snapshot_id}, SHA256 ${doc.source.content_hash}. Please verify the complete original through source governance.`;
    panel.innerHTML=`<header><small>Source follow-up · Pending</small><h2>${esc(failure.title)}</h2><p class="issue">${esc(failure.reason)}</p><p>Machine confidence: No supported content score. No Requirement was inferred from this failed processing attempt.</p></header><div class="ex-compare"><section><h3>Saved original</h3><a href="/api/original/${encodeURIComponent(doc.source.source_id)}?expected_hash=${doc.source.content_hash}" target="_blank" rel="noopener">Open full saved file</a><div id="ex-failure-evidence"></div></section><section><h3>Follow-up needed</h3><p>${failure.missing_body?'Compare the contents list with the actual body. If the body is absent, report the incomplete original to Source Management System.':'Check whether the original is complete and readable. Report an original problem to Source Management System, or retry processing after its cause has been corrected.'}</p><p>The stored original, source decision and earlier history are retained. Reporting a problem does not retrieve another file or complete this task.</p><div id="ex-failure-observations"></div><details><summary>Recorded processing failure</summary><pre>${esc(failure.codes.join('\n'))}</pre></details><label>Original evidence and requested follow-up<textarea id="ex-failure-note">${esc(localStorage.getItem(draftKey)??initial)}</textarea></label><p class="muted">Draft text is retained in this browser. Submit to save the follow-up in Source Management System.</p><button id="ex-failure-report">Send source follow-up to Source Management System</button><p role="status" id="ex-decision-message"></p></section></div>`;
    const note=panel.querySelector('#ex-failure-note');note.oninput=()=>localStorage.setItem(draftKey,note.value);
    panel.querySelector('#ex-failure-report').onclick=()=>this.send('/api/system2/source-issue',{document_id:doc.id,source_sha256:doc.source.content_hash,note:note.value},draftKey);
    const evidence=await showEvidence(panel.querySelector('#ex-failure-evidence'),doc.source.source_id,this.api,{documentId:doc.id,unitId:'processing-failure',full:false,references:[{source_sha256:doc.source.content_hash}]});
    if(this.detailTicket!==ticket)return;
    const observed=evidence?.processing_observations;
    if(observed){panel.querySelector('#ex-failure-observations').innerHTML=`<h4>Observed in the saved HTML</h4>${observed.content_regions.map(r=>`<p>${esc(r.id||r.xpath)}: ${r.text_characters} text characters${r.empty?' · Empty':''}.</p>`).join('')}${observed.full_document_links.map(l=>`<p>Original full-document link, not opened: ${esc(l.label)}<br><code>${esc(l.href)}</code></p>`).join('')}`;}
  }
  async select(item){
    this.unitId=item.id;const token=this.token,ticket=this.detailTicket={};const d=this.doc(),panel=this.container.querySelector('#ex-detail');
    this.container.querySelectorAll('[data-unit]').forEach(b=>b.classList.toggle('active',b.dataset.unit===item.id));
    const key=d.id+':'+item.id+':'+item.fingerprint+':'+this.data.policy.revision;
    if(this.cache.has(key)){const start=performance.now();this.detail(d,this.cache.get(key));panel.dataset.cachedRenderMs=(performance.now()-start).toFixed(2);}else panel.innerHTML='<p role="status">Opening this original unit…</p>';
    try{const result=await this.api('/api/system2/state?view=unit&document_id='+encodeURIComponent(d.id)+'&unit_id='+encodeURIComponent(item.id));
      if(this.token!==token||this.detailTicket!==ticket)return;
      this.cache.set(key,result);while(this.cache.size>32)this.cache.delete(this.cache.keys().next().value);this.prefetch(d,item);if(!panel.querySelector('form')||this.currentGuard!==result.guard)this.detail(d,result);
    }catch(e){if(this.token===token&&this.detailTicket===ticket)panel.textContent=e.message;}
  }
  prefetch(doc,item){
    const next=this.page?.items[this.page.items.findIndex(u=>u.id===item.id)+1];if(!next)return;
    const token=this.token,key=doc.id+':'+next.id+':'+next.fingerprint+':'+this.data.policy.revision;
    if(this.cache.has(key))return;
    this.api('/api/system2/state?'+new URLSearchParams({view:'unit',document_id:doc.id,unit_id:next.id})).then(result=>{
      if(this.token!==token)return;this.cache.set(key,result);while(this.cache.size>32)this.cache.delete(this.cache.keys().next().value);
      return this.api('/api/system2/preview?'+new URLSearchParams({document_id:doc.id,unit_id:next.id,expected_hash:doc.source.content_hash}));
    }).catch(()=>{});
  }
  detail(doc,result){
    const u=result.unit,t=result.task||{},panel=this.container.querySelector('#ex-detail');this.currentGuard=result.guard;
    const fields=result.display_fields||{...u.original.fields,...u.edits}, key=`extraction-draft:${this.state.actor.id}:${doc.id}:${u.id}`;
    let draft;try{draft=JSON.parse(localStorage.getItem(key)||'null');}catch{}
    draft??=u.drafts?.[this.state.actor.name];
    const stale=!!draft&&draft.guard!==result.guard;
    const actions=t.stage==='requirement'?['classify','reopen']:t.type==='coverage'?['accept_content','resolve_content','supplement','reopen','unreadable']:['accept_content','correct','structure','location','relocate','resolve_content','unreadable','split','merge'];
    const names={accept_content:'Confirm this exact content range',resolve_content:'Resolve the listed issues',correct:'Correct extracted text',structure:'Assign a field to an original region',location:'Original region is incorrect',relocate:'Correct the original region',classify:'Record Requirement judgment',unreadable:'Cannot read the original',reopen:'Unable to decide / keep pending',supplement:'Add missing content',split:'Correct a split boundary',merge:'Merge incorrect fragments'};
    if(result.effective?.table){const index=actions.indexOf('correct');if(index>=0)actions.splice(index,1);}
    if(doc.hierarchy_version){for(const action of ['merge','split']){const index=actions.indexOf(action);if(index>=0)actions.splice(index,1);}}
    if(u.table_assembly){actions.splice(0,actions.length,...(t.stage==='requirement'?['classify','reopen']:['accept_content','resolve_content','reopen','unreadable']));}
    if(t.stage==='requirement'&&!u.table_assembly&&u.kind!=='coverage'&&!u.evidence_only&&!u.superseded_by){actions.push('subdivide_requirement');if(u.requirement_subdivision){actions.splice(actions.indexOf('classify'),1,'clear_subdivision');}}
    names.subdivide_requirement='Create / replace requirement subitems';names.clear_subdivision='Remove subitems and classify the complete parent';
    const proposal=t.proposal||{};
    panel.innerHTML=`<header><small>${esc(t.chapter)} · ${esc(taskNames[t.type])}</small><h2>${esc(t.question||'Review this source unit')}</h2><h3>${esc(t.title)}</h3><p class="issue">${esc(t.reason)}</p><p><strong>Machine confidence:</strong> ${t.confidence==null?'No reliable score available':percent(t.confidence)} · Threshold ${percent(this.data.policy[t.stage]||this.data.policy.content)}. Human confirmation is recorded separately.</p></header><details ${t.type==='requirement'?'open':''}><summary>Machine suggestion and evidence</summary><p><strong>Suggested classification:</strong> ${esc(proposal.classification)}</p><p>${esc(proposal.rule)}</p><p>${esc(proposal.uncertainty)}</p><p>Matched original wording: ${esc([...(proposal.matches||[]),...(proposal.scope_evidence||[]),...(proposal.context_evidence||[])].map(m=>m.text).join(', ')||'No decisive wording')}</p><p>Method: ${esc(proposal.method)}. ${esc((t.reasons||[]).join(' '))}</p></details>${result.coverage?`<section><h3>Coverage of this range</h3><table><thead><tr><th>Chapter</th><th>Units</th><th>Content accepted</th><th>Classified</th></tr></thead><tbody>${result.coverage.map(r=>`<tr><td>${esc(r.chapter)}</td><td>${r.units}</td><td>${r.content_accepted}</td><td>${r.classified}</td></tr>`).join('')}</tbody></table><p>These counts describe recorded content. Compare the original to find omissions; report any missing or duplicate content before confirming.</p></section>`:''}<div class="ex-compare"><section><h3>Bound original</h3><button id="ex-original">Expand original context</button><a href="/api/original/${encodeURIComponent(doc.source.source_id)}?expected_hash=${doc.source.content_hash}" target="_blank" rel="noopener">Open full file</a><div id="ex-evidence"></div></section><section><h3>Extracted content</h3>${result.effective?.table?.html?'<p class="table-scroll-hint">Scroll horizontally for all columns. Select the table and use the left/right arrow keys.</p>':''}<div class="ex-text" ${result.effective?.table?.html?'tabindex="0" role="region" aria-label="Extracted table; scroll horizontally to inspect all columns"':''}>${result.effective?.table?.html ? result.effective.table.html+['title','notes','context','applicability'].filter(k=>fields[k]).map(k=>'<p>'+esc(k+': '+fields[k])+'</p>').join('') : esc(['identifier','title','body','criteria','level','applicability','notes','context'].map(k=>fields[k]).filter(Boolean).join('\n\n'))}</div>${u.members?`<p>${u.members.length} original fragments in this range. All are included in the comparison.</p>`:''}</section></div><details><summary>Optional assistance</summary><p>Local review works without an API. A configured provider can only offer evidence-bound suggestions.</p><button id="ex-suggest">Get optional assistance</button><p id="ex-suggestion-status"></p></details><details><summary>Technical evidence and original structure</summary><pre>${esc(JSON.stringify({references:u.original.references,structure:u.original.structure,blockers:u.blockers},null,2))}</pre></details>${subitemSummary(u)}<form id="ex-form">${stale?'<p class="issue">This saved draft refers to an earlier unit or dependency version.</p><label><input type="checkbox" id="ex-draft-reviewed">I compared this draft with the current original.</label>':''}<label>Decision<select id="ex-action">${actions.map(a=>`<option value="${a}">${names[a]}</option>`).join('')}</select></label><div id="ex-fields" hidden>${Object.entries({identifier:'Original number',title:'Title',body:'Text',criteria:'Criteria',notes:'Footnotes',context:'Context',applicability:'Applicability'}).map(([k,title])=>`<label>${title}<textarea name="${k}" rows="${k==='body'?8:2}">${esc(draft?.fields?.[k]??fields[k]??'')}</textarea></label>`).join('')}<details><summary>Text before this correction</summary><pre>${esc(fields.body||'')}</pre></details></div>${subitemMarkup(fields)}<label id="ex-class-wrap" hidden>Classification<select id="ex-class"><option value="requirement" ${(u.kind==='coverage'||u.table_assembly)?'disabled':''}>Requirement</option><option value="context" ${(u.kind==='coverage'||u.table_assembly)?'selected':''}>Related context</option><option value="non_requirement">Not a Requirement</option></select></label><div id="ex-relationship" hidden><label>Correct source position<input id="ex-locator" placeholder="Original page / DOM region / worksheet range"></label><label>Relationship<select id="ex-role"><option value="body">Body</option><option value="notes">Footnote</option><option value="identifier">Number</option><option value="context">Context</option></select></label></div><label id="ex-split-wrap" hidden>Correct boundaries, one per line<textarea id="ex-split"></textarea></label><label id="ex-merge-wrap" hidden>IDs of verified fragments to merge, one per line<textarea id="ex-merge"></textarea></label><div id="ex-issues" hidden>${(u.blockers||[]).map((b,i)=>`<label><input type="checkbox" data-issue="${i}"> ${esc((t.reasons||[])[i]||b)}</label>`).join('')}</div><label>Evidence or reason<textarea id="ex-note">${esc(draft?.note||'')}</textarea></label><label><input type="checkbox" id="ex-range">I checked the complete displayed range, including associated subitems, tables and footnotes.</label><button type="submit" class="primary">Submit decision</button><button type="button" id="ex-draft">Save draft</button><p role="status" id="ex-decision-message"></p></form>`;
    const q=s=>panel.querySelector(s), refs=(result.coverage_pages?.length?result.effective.references:u.reviewed_references||u.original.references)||[], ref=refs.find(r=>r.page_index!=null)||refs[0]||{};
    q('header').insertAdjacentHTML('beforeend',dependencyMarkup(result.pending_content_dependencies));
    for(const button of panel.querySelectorAll('[data-content-dependency]'))button.onclick=()=>this.select({id:button.dataset.contentDependency});
    if(result.coverage_pages?.length){
      q('header').insertAdjacentHTML('beforeend',`<section class="ex-coverage-pages"><p>This content check covers original PDF pages ${result.coverage_pages.map(p=>p+1).join(', ')}. Inspect every page, including regions without extracted items.</p>${result.coverage_pages.map(p=>`<button type="button" data-coverage-page="${p}">Open original page ${p+1}</button>`).join('')}</section>`);
      for(const button of panel.querySelectorAll('[data-coverage-page]'))button.onclick=()=>{this.pdfPage=Number(button.dataset.coveragePage);this.discovery='pages';this.queue();};
    }
    if(u.requirement_human){
      q('header').insertAdjacentHTML('beforeend',`<p><strong>Saved human judgment:</strong> ${esc(classificationLabel(u.classification))}. Any replacement requires a new submitted decision.</p>`);
      q('#ex-class').value=u.classification;
    }
    q('.ex-text').insertAdjacentHTML('afterend',sourceCheckMarkup(u.source_verification));
    showSourceContext(q('.ex-compare').lastElementChild,result.effective?.related_content,id=>this.select({id}));
    if(result.confidence_dimensions){
      const labels={text:'Text accuracy',coverage:'Original coverage',structure:'Structure and relationships',order:'Reading order',classification:'Requirement classification',association:'Original association',subdivision:'Parent and subitem correctness'};
      const statuses={missing:'No supported score',duplicate:'Conflicting score entries',validated:'Meets the current threshold',not_validated:'Requires verification'};
      const why={confidence_missing:'No score recorded',confidence_invalid:'Invalid score',confidence_uncalibrated:'No applicable calibration recorded',evidence_missing:'Original evidence is missing',evidence_conflict:'Evidence disagrees',confidence_below_threshold:'Below the current threshold'};
      panel.querySelector('header').insertAdjacentHTML('beforeend',`<details><summary>Scores and evidence by dimension</summary><p>All required dimensions must be supported. A high score in one dimension does not establish the others. Human confirmation is recorded separately. These routing scores do not establish whole-document accuracy.</p>${Object.entries(result.confidence_dimensions).map(([stage,rows])=>`<h4>${stage==='content'?'A · Content':'B · Requirement judgment'}</h4><table><thead><tr><th>Dimension</th><th>Score</th><th>Status and evidence</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${labels[r.aspect]||esc(r.aspect)}</td><td>${percent(r.confidence)}</td><td>${statuses[r.status]||'Requires verification'}${r.reasons?.length?'<p>'+r.reasons.map(code=>esc(why[code]||'Score entries need checking')).join('; ')+'</p>':''}<details><summary>Recorded evidence</summary><p>Method: ${esc(r.method||'Not recorded')}. Calibration: ${esc(r.calibration_version||'Not recorded')}.</p><pre>${esc(JSON.stringify(r.evidence||[],null,2))}</pre></details></td></tr>`).join('')}</tbody></table>`).join('')}</details>`);
    }
    if(t.stage==='requirement'&&u.requirement_blockers?.some(code=>code.startsWith('weekly_qa:'))){
      q('#ex-note').parentElement.insertAdjacentHTML('beforebegin',`<fieldset><legend>Weekly findings rechecked against the original</legend>${u.requirement_blockers.filter(code=>code.startsWith('weekly_qa:')).map(code=>`<label><input type="checkbox" data-weekly-issue="${esc(code)}">I rechecked this reported classification problem: ${esc(code.slice(10))}</label>`).join('')}<p>Submit the corrected B judgment with an evidence note, then return to Weekly checks to record the follow-up.</p></fieldset>`);
    }
    const evidenceApi=(path,body)=>this.api(path+(path.includes('?')?'&':'?')+'expected_hash='+doc.source.content_hash,body);
    const preview=full=>{
      if(u.table_assembly&&!full&&result.effective?.table_assembly?.fragments?.length){
        const container=q('#ex-evidence');container.replaceChildren();
        for(const [index,fragment]of result.effective.table_assembly.fragments.entries()){
          const section=document.createElement('section'),title=document.createElement('h4'),body=document.createElement('div');
          title.textContent='Original table fragment '+(index+1);section.append(title,body);container.append(section);
          showEvidence(body,doc.source.source_id,evidenceApi,{references:fragment.references||[],documentId:doc.id,unitId:fragment.unit_id});
        }
        return;
      }
      return showEvidence(q('#ex-evidence'),doc.source.source_id,evidenceApi,{page:(ref.page_index??0)+1,locator:ref.locator||'',references:refs,full,documentId:doc.id,unitId:u.id});
    };
    q('#ex-original').onclick=()=>preview(true);preview(false);
    q('#ex-suggest').onclick=async()=>{try{const r=await this.api('/api/system2/suggest',{request_id:crypto.randomUUID(),document_id:doc.id,unit_id:u.id,revision:result.revision});if(r.guard){result.guard=r.guard;this.currentGuard=r.guard;}q('#ex-suggestion-status').textContent=r.suggestions?.length?JSON.stringify(r.suggestions):'No provider suggestion is available. Continue local or human review.';}catch(e){q('#ex-suggestion-status').textContent=e.message;}};
    const toggle=()=>{const a=q('#ex-action').value;q('#ex-fields').hidden=!['correct','supplement'].includes(a);q('#ex-class-wrap').hidden=!['classify','clear_subdivision'].includes(a);q('#ex-subitems').hidden=a!=='subdivide_requirement';q('#ex-relationship').hidden=!['structure','supplement','location','relocate'].includes(a);q('#ex-split-wrap').hidden=a!=='split';q('#ex-merge-wrap').hidden=a!=='merge';q('#ex-issues').hidden=a!=='resolve_content';};toggle();q('#ex-action').onchange=toggle;
    const collectSubitems=wireSubitems(panel,fields,draft?.subdivision||u.requirement_subdivision);
    const collect=()=>({stage:t.stage,subdivision:collectSubitems(),guard:result.guard,fields:Object.fromEntries([...panel.querySelectorAll('textarea[name]')].map(e=>[e.name,e.value])),note:q('#ex-note').value});
    const persist=()=>localStorage.setItem(key,JSON.stringify({...collect(),guard:stale&&!q('#ex-draft-reviewed')?.checked?draft.guard:result.guard}));
    let draftClaim;
    const claimKey=key+':request';
    q('#ex-form').oninput=()=>{persist();if(!draftClaim){
      const request=JSON.parse(localStorage.getItem(claimKey)||'null')||{...base(),request_id:crypto.randomUUID(),action:'draft',draft:collect()};
      localStorage.setItem(claimKey,JSON.stringify(request));
      draftClaim=this.api('/api/system2/decision',request).then(receipt=>{result.guard=receipt.guard;result.revision=receipt.revision;this.currentGuard=receipt.guard;if(result.effective?.table_owner_id===u.id)result.table_owner_fingerprint=receipt.unit_fingerprint;localStorage.removeItem(claimKey);persist();}).catch(e=>{q('#ex-decision-message').textContent=e.message+' Your local draft is retained. Edit again to retry the same request.';draftClaim=null;throw e;});draftClaim.catch(()=>{});
    }};
    const base=()=>({document_id:doc.id,unit_id:u.id,revision:result.revision,guard:result.guard,source_sha256:doc.source.content_hash,policy_revision:result.policy_revision});
    repairControls(panel,{api:this.api,doc,result,base,draftKey:key,openUnit:id=>this.select({id}),onReceipt:r=>{result.guard=r.guard;result.revision=r.revision;this.currentGuard=r.guard;if(result.effective?.table_owner_id===u.id)result.table_owner_fingerprint=r.unit_fingerprint;},send:(...args)=>this.send(...args)});
    q('#ex-draft').onclick=async()=>{try{if(draftClaim)await draftClaim;}catch{return;}persist();this.send('/api/system2/decision',{...base(),action:'draft',draft:collect()},key);};
    q('#ex-form').onsubmit=async e=>{e.preventDefault();try{if(draftClaim)await draftClaim;}catch{return;}persist();const action=q('#ex-action').value;
      if(stale&&!q('#ex-draft-reviewed').checked){q('#ex-decision-message').textContent='Compare this saved draft before submitting.';return;}
      if(['accept_content','resolve_content','classify','subdivide_requirement','clear_subdivision'].includes(action)&&!q('#ex-range').checked){q('#ex-decision-message').textContent='Confirm the exact reviewed range first.';return;}
      const body={...base(),action,note:q('#ex-note').value};
      if(['correct','supplement'].includes(action))body.fields=Object.fromEntries(Object.entries(collect().fields).filter(([k,v])=>action==='supplement'?v:v!==(fields[k]||'')));
      if(['classify','clear_subdivision'].includes(action))body.classification=q('#ex-class').value;
      if(['classify','clear_subdivision','subdivide_requirement'].includes(action)){
        const resolved=[...panel.querySelectorAll('[data-weekly-issue]:checked')].map(el=>el.dataset.weeklyIssue);
        if(resolved.length)body.resolved_requirement_issues=resolved;
      }
      if(action==='subdivide_requirement')Object.assign(body,collectSubitems(),{complete_range_reviewed:q('#ex-range').checked});
      if(action==='relocate'){body.action='structure';body.structure=[{locator:q('#ex-locator').value,role:'source_region'}];}
      if(action==='structure')body.structure=[{locator:q('#ex-locator').value,role:q('#ex-role').value}];
      if(action==='location'){body.action='location';body.locator=q('#ex-locator').value;}
      if(action==='supplement')body.locator=q('#ex-locator').value;
      if(action==='resolve_content')body.resolved_issues=[...panel.querySelectorAll('[data-issue]:checked')].map(el=>u.blockers[Number(el.dataset.issue)]);
      if(action==='split')body.split_parts=q('#ex-split').value.split('\n').filter(Boolean);
      if(action==='merge')body.merge_ids=[u.id,...q('#ex-merge').value.split('\n').filter(Boolean)];
      this.send('/api/system2/decision',body,key);
    };
    wireSourceFindings(panel,u.source_verification,this);
  }
  conversion(panel,doc){
    panel.innerHTML='<h2>Human format conversion</h2><p>Keep the original. Register a faithful HTML, XLSX or PDF parsing copy with its provenance.</p><label>Parsing copy<input id="conversion-file" type="file" accept=".pdf,.html,.htm,.xlsx"></label><label>Conversion method<input id="conversion-method"></label><label>Completeness evidence<textarea id="conversion-note"></textarea></label><label><input type="checkbox" id="conversion-complete">I compared this copy with the complete original.</label><button id="conversion-submit">Register parsing copy</button><p id="conversion-result" role="status"></p>';
    const q=s=>panel.querySelector(s);
    q('#conversion-submit').onclick=async()=>{try{
      const file=q('#conversion-file').files[0];if(!file)throw Error('Choose the converted copy.');
      const response=await fetch('/api/upload',{method:'POST',headers:{'X-CSRF-Token':this.state.csrf,'X-File-Extension':'.'+file.name.split('.').pop().toLowerCase()},body:file});
      const upload=await response.json();if(!response.ok)throw Error(upload.error);
      await this.api('/api/system2/conversion',{request_id:crypto.randomUUID(),document_id:doc.id,revision:doc.revision,upload_id:upload.upload_id,method:q('#conversion-method').value,note:q('#conversion-note').value,complete:q('#conversion-complete').checked});await this.reload();
    }catch(e){q('#conversion-result').textContent=e.message;}};
  }
  async send(path,body,draftKey){
    const message=this.container.querySelector('#ex-decision-message')||this.container.querySelector('#ex-message');const storageKey=`extraction-request:${this.state.actor.id}:${path}`;
    try{if(!this.state.actor.id)throw Error('Select a named reviewer first.');
      if(path==='/api/system2/source-issue'&&!String(body.note??'').trim())throw Error('Describe the original problem before submitting.');
      const old=JSON.parse(localStorage.getItem(storageKey)||'null'),signature=JSON.stringify(body);
      if(old&&old.signature!==signature)throw Error('A previous request has an uncertain receipt. Retry the same action first.');
      const request=old?.request||{...body,request_id:crypto.randomUUID()};localStorage.setItem(storageKey,JSON.stringify({signature,request}));
      message.textContent='Submitted; waiting for the application receipt…';const receipt=await this.api(path,request);
      localStorage.removeItem(storageKey);if(draftKey){if(body.action==='draft')localStorage.setItem(draftKey,JSON.stringify({...body.draft,guard:receipt.guard}));else localStorage.removeItem(draftKey);}this.cache.clear();await this.reload();
      this.container.querySelector('#ex-message').textContent=path==='/api/system2/source-issue'?'Source follow-up saved in Source Management System. The reported problem remains pending.':['accept_content','resolve_content'].includes(body.action)?'Content decision applied. Ready items are now listed under Requirement judgment.':body.action==='draft'?'Draft saved. No decision has been applied.':`Applied · ${this.state.actor.name||'Named reviewer'} · revision ${receipt.revision??''}`;
      return receipt;
    }catch(e){if(e.definitive)localStorage.removeItem(storageKey);if(e.current){this.detail(this.doc(),e.current);this.container.querySelector('#ex-decision-message').textContent=e.message;}else if(message)message.textContent=e.message;}
  }
  async reload(){return this.mount(this.container,{api:this.api,state:this.state,history:this.history});}
}
export async function settings(container,api) {
  const data=await api('/api/settings');
  const labels={system1:'Source Management System · Source assessments',content:'Requirement Extraction System · Content and structure',requirement:'Requirement Extraction System · Requirements and coverage'};
  container.innerHTML=`<section class="panel"><h2>Confidence thresholds</h2><p>Scores guide review routing; they are not document accuracy. Missing or uncalibrated scores and evidence conflicts always require review.</p><form id="policy-form">${Object.entries(labels).map(([key,label])=>`<label>${label}<input type="number" name="${key}" min="0.01" max="100" step="0.01" required value="${(data.policy[key]*100).toFixed(2)}"></label>`).join('')}<p>Raising thresholds reopens affected machine decisions. Lowering thresholds rechecks untouched, low-score-only tasks. Human decisions and drafts remain protected.</p><button>Save and re-evaluate</button><p role="status" id="policy-status"></p></form><details><summary>Policy history</summary><table><thead><tr><th>Revision</th><th>Operator</th><th>Changed</th><th>Source Management System</th><th>Content</th><th>Requirements</th></tr></thead><tbody>${data.history.map(h=>`<tr><td>${h.policy.revision}</td><td>${esc(h.actor)}</td><td>${esc(new Date(h.created*1000).toLocaleString())}</td><td>${percent(h.policy.system1)}</td><td>${percent(h.policy.content)}</td><td>${percent(h.policy.requirement)}</td></tr>`).join('')}</tbody></table></details></section>`;
  container.querySelector('#policy-form').onsubmit=async event=>{event.preventDefault();try{const values=Object.fromEntries([...container.querySelectorAll('input[name]')].map(e=>[e.name,Number(e.value)/100]));await api('/api/settings',{revision:data.policy.revision,values:{...values,system3:data.policy.system3}});await settings(container,api);}catch(e){container.querySelector('#policy-status').textContent=e.message;}};
}

export async function sourceAssessments(container,api,state) {
  container.innerHTML=`<section class="panel"><h2>Source assessment suggestions</h2><p>Without an API, verified local rules supply supported ratings. Unknown dimensions require human review. Existing H/M/L scores are not confidence percentages.</p><select id="assessment-source">${state.sources.map(s=>`<option value="${esc(s.source_id)}">${esc(s.source_id)} · ${esc(s.source_title)}</option>`).join('')}</select><button id="assessment-run">Assess selected source</button><div id="assessment-result"></div></section>`;
  const render=result=>{container.querySelector('#assessment-result').innerHTML=result.assessments.map(a=>`<h3>${esc(a.source_id)} · ${esc(a.mode)}</h3><table><thead><tr><th>Dimension</th><th>Suggested rating</th><th>Confidence</th><th>Evidence</th></tr></thead><tbody>${Object.entries(a.dimensions).map(([k,v])=>`<tr><td>${esc(k.replaceAll('_',' '))}</td><td>${esc(v.rating)}</td><td>${percent(v.confidence)}</td><td>${esc(v.evidence.join(', '))}</td></tr>`).join('')}</tbody></table><p>These machine suggestions do not overwrite named human decisions.</p>${a.proposals?.length?`<details><summary>Additional model suggestions, awaiting verification</summary><pre>${esc(JSON.stringify(a.proposals,null,2))}</pre></details>`:''}`).join('');};
  const show=()=>{const source=state.sources.find(s=>s.source_id===container.querySelector('#assessment-source').value);if(source?.machine_assessment)render({assessments:[source.machine_assessment]});else container.querySelector('#assessment-result').textContent='No version-bound machine assessment yet.';};
  container.querySelector('#assessment-source').onchange=show;show();
  container.querySelector('#assessment-run').onclick=async()=>{try{render(await api('/api/system1/assess',{source_ids:[container.querySelector('#assessment-source').value]}));}catch(e){container.querySelector('#assessment-result').textContent=e.message;}};
}

async function legacyQualityChecks(container,api) {
  const data=await api('/api/system2/qa');
  container.innerHTML=`<section class="panel"><h2>Weekly checks of machine-accepted requirements</h2><p>Up to five items per week. Incomplete samples have no reported accuracy.</p>${data.batches.map(b=>`<h3>${esc(b.week)} · ${b.accuracy==null?'Awaiting completed sample':b.accuracy.toFixed(1)+'% correct'}</h3>${b.items.map(i=>`<details><summary>${esc(i.item.source.source_id)} · ${esc(i.item.fields.identifier||i.unit_id)} · ${esc(i.verdict||'Pending')}</summary><pre>${esc(JSON.stringify(i.item.fields,null,2))}</pre><p>${esc(JSON.stringify(i.item.references))}</p>${i.verdict?`<p>${esc(i.actor)} · ${esc(i.note)}</p>`:`<label>Evidence and findings<textarea data-note="${i.id}"></textarea></label><button data-check="${i.id}" data-week="${b.week}" data-verdict="CORRECT">Correct</button><button data-check="${i.id}" data-week="${b.week}" data-verdict="INCORRECT">Incorrect, send to review</button>`}</details>`).join('')||'<p>No eligible machine-accepted items in this weekly sample.</p>'}`).join('')}<p role="status" id="qa-result"></p></section>`;
  container.querySelectorAll('[data-check]').forEach(button=>button.onclick=async()=>{try{await api('/api/system2/qa',{request_id:crypto.randomUUID(),week:button.dataset.week,item_id:button.dataset.check,verdict:button.dataset.verdict,note:container.querySelector(`[data-note="${button.dataset.check}"]`).value});await qualityChecks(container,api);}catch(e){container.querySelector('#qa-result').textContent=e.message;}});
}

export async function qualityChecks(container,api,openRepair) {
  let data;
  try{data=await api('/api/system2/weekly');}catch{return legacyQualityChecks(container,api);}
  container.innerHTML=`<section class="panel"><h2>Weekly original and classification checks</h2><p>Monday targets: Source Management System 5 governance records · A 20 original scopes · B 5 classification judgments.</p><p>${data.schedule.enabled?'A/B sampling is enabled for this runtime.':'A/B schedule activation is pending. Existing records remain available.'} These checks monitor ongoing work; they do not establish independent acceptance accuracy.</p><label>Show<select id="weekly-filter"><option value="pending">Pending</option><option value="history">Review history</option></select></label><div id="weekly-list"></div><div id="weekly-detail"></div><details><summary>Earlier machine-only checks</summary><div id="weekly-legacy"></div><button id="weekly-load-legacy">Open retained earlier checks</button></details></section>`;
  const list=container.querySelector('#weekly-list'),panel=container.querySelector('#weekly-detail');
  const render=()=>{
    const history=container.querySelector('#weekly-filter').value==='history';
    list.innerHTML=data.batches.map(b=>`<section><h3>${esc(b.week)} · ${b.stage==='A'?'A · original content':'B · classification'}</h3><p>${b.sampled}/${b.requested} sampled · ${b.pending} unfinished${b.shortfall?' · Shortfall: '+b.shortfall:''}${b.missing_strata.length?' · Missing classifications: '+esc(b.missing_strata.join(', ')):''}. ${b.complete?'Batch checks completed.':'Batch remains incomplete.'}</p>${b.source_catalog_errors.map(e=>`<p class="issue">${esc(e.source_id)}: original sampling unavailable · ${esc(e.reason)}</p>`).join('')}${b.items.filter(i=>(i.status==='complete')===history).map(i=>`<button class="task" data-weekly="${i.id}"><strong>${esc(i.source_id)} · ${esc(i.title)}</strong><span>${esc(i.status.replaceAll('_',' '))}${i.classification?' · '+esc(i.classification):''}</span></button>`).join('')}</section>`).join('')||'<p>No A/B batches have been created in this runtime.</p>';
    list.querySelectorAll('[data-weekly]').forEach(button=>button.onclick=()=>detail(button.dataset.weekly));
  };
  const detail=async id=>{
    panel.textContent='Opening the frozen sample and current result…';
    try{
      const d=await api('/api/system2/weekly?item_id='+id),key='weekly-draft:'+location.origin+':'+id;
      const saved=JSON.parse(localStorage.getItem(key)||'null');
      const items=d.stage==='A'?(d.status==='finding_open'?d.current.units:d.extracted):[{view:d.status==='finding_open'?null:d.effective}];
      if(d.stage==='B'&&d.status==='finding_open'){
        const current=await api('/api/system2/state?'+new URLSearchParams({view:'unit',document_id:d.document_id,unit_id:d.unit_id}));
        items[0].view=current.effective;items[0].classification=current.unit.classification;
      }
      panel.innerHTML=`<h3>${esc(d.source.source_id)} · ${esc(d.title)}</h3><p>${d.stage==='A'?'Compare the complete original scope, including regions with no extracted text.':'Check whether the original supports this classification, including advisory requirements.'}</p><p>Sampled classification: ${esc(d.classification||'Not applicable to A')} · ${esc(d.status.replaceAll('_',' '))}</p>${d.stage==='A'&&!d.processed?'<p class="issue">This original scope was not marked as processed when sampled. Confirming an omission here must not be reported as a measured parser error rate.</p>':''}${d.current.source_sha256!==d.source.content_hash||!d.current.eligible?'<p class="issue">The sampled source is no longer current. Preserve it as unverified and follow up on the source change.</p>':''}<div class="ex-compare"><section><h3>Bound original</h3><div id="weekly-original"></div>${(d.scope?.unverified||[]).map(v=>`<p class="issue">${esc(v)}</p>`).join('')}</section><section><h3>${d.status==='finding_open'?'Current result after the finding':'Frozen result at sampling'}</h3>${items.length?items.map(u=>`<article>${u.unit_id?'<p>'+esc(u.unit_id)+'</p>':''}${u.classification?'<p>Current classification: '+esc(u.classification)+'</p>':''}<div class="ex-text">${esc(Object.values(u.view?.fields||{}).filter(Boolean).join('\n\n'))}</div><p>${esc([u.content_status,u.requirement_status].filter(Boolean).join(' · '))}</p></article>`).join(''):'<p class="issue">No extracted content was mapped to this original scope.</p>'}</section></div><details><summary>Retained inspection history and sample evidence</summary><pre>${esc(JSON.stringify({snapshot:d.snapshot_sha256,position:d.scope?.references||d.effective?.references,history:d.history},null,2))}</pre></details>${d.status==='complete'?'<p>This inspection is saved in Review history.</p>':`<form id="weekly-form"><label>Evidence and exact finding<textarea id="weekly-note" required>${esc(saved?.note||'')}</textarea></label>${saved&&saved.guard!==d.guard?'<p class="issue">The saved draft predates this item version. Compare it with the current view before submitting.</p>':''}<label><input type="checkbox" id="weekly-confirm" required>I checked the complete displayed scope and relevant context.</label>${d.status==='finding_open'?'<button type="button" id="weekly-repair">Open the repair task</button><button type="submit" data-verdict="" data-action="resolve">Confirm repair follow-up</button>':'<button type="submit" data-verdict="CORRECT" data-action="inspect">Original and result agree</button><button type="submit" data-verdict="INCORRECT" data-action="inspect">Report a problem</button><button type="submit" data-verdict="UNVERIFIED" data-action="inspect">Keep unverified</button>'}<p role="status" id="weekly-status"></p></form>`}`;
      if(d.stage==='B'){
        const judged=d.status==='finding_open'?d.current.units[0]:d.judgment;
        panel.querySelector('.ex-compare section:last-child').insertAdjacentHTML('beforeend',subitemSummary(judged)+`<p>Machine classification confidence: ${percent(judged.requirement_confidence)}. Named review decisions remain separate.</p>`);
      }
      panel.querySelector('#weekly-original').insertAdjacentHTML('beforebegin',`<a href="/api/original/${encodeURIComponent(d.source.source_id)}?expected_hash=${d.source.content_hash}" target="_blank" rel="noopener">Open complete original file</a>`);
      const refs=d.scope?.references||d.effective.references;
      await showEvidence(panel.querySelector('#weekly-original'),d.source.source_id,()=>api('/api/system2/weekly-preview?item_id='+id),{documentId:d.document_id,unitId:'weekly:'+id,references:refs});
      const form=panel.querySelector('#weekly-form');if(!form)return;
      const note=panel.querySelector('#weekly-note');note.oninput=()=>localStorage.setItem(key,JSON.stringify({note:note.value,guard:d.guard}));
      panel.querySelector('#weekly-repair')?.addEventListener('click',()=>openRepair?.(d));
      form.onsubmit=async event=>{
        event.preventDefault();const button=event.submitter,status=panel.querySelector('#weekly-status');
        const body={request_id:crypto.randomUUID(),item_id:id,guard:d.guard,result_guard:d.result_guard,action:button.dataset.action,note:note.value};
        if(button.dataset.verdict)body.verdict=button.dataset.verdict;
        const pendingKey=key+':request',pending=JSON.parse(localStorage.getItem(pendingKey)||'null');
        const payload=pending||body;localStorage.setItem(pendingKey,JSON.stringify(payload));
        [...form.querySelectorAll('button')].forEach(b=>b.disabled=true);
        try{await api('/api/system2/weekly',payload);localStorage.removeItem(key);localStorage.removeItem(pendingKey);await qualityChecks(container,api,openRepair);}
        catch(e){status.textContent=weeklyMessage(e)+' The draft is retained; this item has not been completed.';[...form.querySelectorAll('button')].forEach(b=>b.disabled=false);if(/stale_|changed_refresh|required|invalid_/.test(e.message))localStorage.removeItem(pendingKey);}
      };
    }catch(e){panel.textContent=e.message;}
  };
  container.querySelector('#weekly-filter').onchange=()=>{panel.replaceChildren();render();};
  container.querySelector('#weekly-load-legacy').onclick=()=>legacyQualityChecks(container.querySelector('#weekly-legacy'),api);
  render();
}

export async function handoff(container,api) {
  const data=await api('/api/system3/input');
  let page=data;while(page.has_more){page=await api('/api/system3/input?after='+page.cursor);data.events.push(...page.events);data.documents=page.documents;data.current_requirements=page.current_requirements;}
  container.innerHTML=`<section class="panel"><h2>System3 input feed</h2><p>Versioned delivery is available. The System3 enrichment service is not connected.</p>${data.documents.map(d=>`<p>${esc(d.source_id)} · ${esc(d.state)} · ${d.complete?'Source complete':'Source incomplete'} · ${d.remaining} units remaining${d.parser_complete?'':' · Parsing incomplete'}</p>${d.unparsed_pages?.length?`<p>Unparsed pages: ${esc(d.unparsed_pages.join(', '))}</p>`:''}`).join('')}<h3>Currently available · ${(data.current_requirements||[]).length}</h3>${(data.current_requirements||[]).map(r=>`<details><summary>${esc(r.source.source_id)} · ${esc(r.fields.identifier||r.requirement_id)}</summary><pre>${esc(JSON.stringify(r.fields,null,2))}</pre></details>`).join('')}<h3>Delivery and suspension history</h3>${data.events.filter(e=>['add','replace','suspend','withdraw'].includes(e.kind)).map(e=>`<details><summary>${e.sequence} · ${esc(e.kind)} · ${esc(e.requirement_id||e.requirement?.requirement_id)}</summary><pre>${esc(JSON.stringify(e.requirement||e,null,2))}</pre></details>`).join('')||'<p>No requirements have passed both gates yet.</p>'}</section>`;
}

// B subitem controls share the existing served extraction module.
const bFieldLabels = {body:'Text',criteria:'Criteria',title:'Title',notes:'Footnotes',context:'Context',applicability:'Applicability',level:'Level'};
function subitemSummary(unit) {
  const item=unit.requirement_subdivision;
  if(!item)return '';
  return `<section><h3>Requirement subitems · provisional</h3><p>Original parent number: ${esc(item.parent_original_number||'No original number')}. Counting rule: ${item.policy.count_basis==='parent'?'one complete parent':'subitems only'}. Peer confirmation is pending.</p><p>${unit.requirement_status?.endsWith('_accepted')?'The saved B decision passed its current checks.':'This subdivision is awaiting review. Its previous spans remain in history.'}</p><ol>${item.subitems.map(c=>`<li><strong>${esc(c.generated_label)} · generated label</strong><pre>${esc(c.text)}</pre></li>`).join('')}</ol><p>Unassigned text decision: ${esc(item.remainder_reason||'All displayed text assigned.')}</p></section>`;
}
function subitemMarkup(fields) {
  return `<section id="ex-subitems" hidden><h3>Keep the full parent and select requirement subitems</h3><p>This is a provisional B judgment. The complete accepted text, original number, source position and shared context are retained. Generated labels do not claim original numbering. Include advisory requirements where applicable.</p><label>Original field<select id="ex-subitem-field">${Object.keys(bFieldLabels).filter(k=>fields[k]).map(k=>`<option value="${k}">${bFieldLabels[k]}</option>`).join('')}</select></label><label>Select the exact original wording<textarea id="ex-subitem-original" readonly rows="8"></textarea></label><button type="button" id="ex-subitem-add">Add selected text as a subitem</button><label>Or paste the exact wording<textarea id="ex-subitem-quote" rows="2"></textarea></label><button type="button" id="ex-subitem-quote-add">Add exact wording as a subitem</button><p role="status" id="ex-subitem-message"></p><div id="ex-subitem-list"></div><details open><summary>Text not assigned to a subitem</summary><div id="ex-subitem-remainder"></div></details><label>Why does the unassigned text contain no additional requirement?<textarea id="ex-subitem-reason" rows="3"></textarea></label><label>Provisional counting rule<select id="ex-subitem-count"><option value="subitems">Count subitems; parent provides full context</option><option value="parent">Count one complete parent; subitems provide detail</option></select></label><p>Both options keep the complete parent and all linked subitems. Changing the rule creates a new B decision and preserves the previous decision.</p></section>`;
}
function wireSubitems(panel, fields, initial) {
  const q=s=>panel.querySelector(s), source=q('#ex-subitem-original');
  let parts=structuredClone(initial?.subitems||[]).map(({field,start,end,text,original_number})=>({field,start,end,text,original_number:original_number||''}));
  q('#ex-subitem-count').value=initial?.count_basis||initial?.policy?.count_basis||'subitems';
  q('#ex-subitem-reason').value=initial?.remainder_reason||'';
  const changed=()=>q('#ex-subitems').dispatchEvent(new Event('input',{bubbles:true}));
  const render=()=>{
    q('#ex-subitem-list').innerHTML=parts.map((p,i)=>`<div><strong>Subitem ${i+1} · generated label</strong><pre>${esc(p.text)}</pre><label>Original number at the start of Subitem ${i+1}, if present<input data-subitem-number="${i}" value="${esc(p.original_number||'')}" placeholder="Leave blank when the original has no subitem number"></label><button type="button" data-remove-subitem="${i}">Remove Subitem ${i+1}</button></div>`).join('');
    for(const input of panel.querySelectorAll('[data-subitem-number]'))input.oninput=()=>{parts[Number(input.dataset.subitemNumber)].original_number=input.value;};
    for(const button of panel.querySelectorAll('[data-remove-subitem]'))button.onclick=()=>{parts.splice(Number(button.dataset.removeSubitem),1);render();changed();};
    const unassigned=[];
    for(const field of Object.keys(bFieldLabels)){
      const text=Array.from(fields[field]||'');let cursor=0;
      const spans=parts.filter(p=>p.field===field).sort((a,b)=>a.start-b.start);
      for(const span of [...spans,{start:text.length,end:text.length}]){
        const remaining=text.slice(cursor,span.start).join('');if(remaining.trim())unassigned.push(`<p>${bFieldLabels[field]}</p><pre>${esc(remaining)}</pre>`);
        cursor=span.end;
      }
    }
    q('#ex-subitem-remainder').innerHTML=unassigned.join('')||'<p>All displayed text has been assigned.</p>';
  };
  q('#ex-subitem-field').onchange=()=>{source.value=fields[q('#ex-subitem-field').value]||'';};
  q('#ex-subitem-field').onchange();
  q('#ex-subitem-add').onclick=()=>{
    const start=Array.from(source.value.slice(0,source.selectionStart)).length,end=Array.from(source.value.slice(0,source.selectionEnd)).length;
    const text=Array.from(source.value).slice(start,end).join(''),field=q('#ex-subitem-field').value;
    if(!text.trim()){q('#ex-subitem-message').textContent='Select the original wording before adding a subitem.';return;}
    if(parts.some(p=>p.field===field&&start<p.end&&p.start<end)){q('#ex-subitem-message').textContent='This selection overlaps an existing subitem. Remove or change that selection first.';return;}
    parts.push({field,start,end,text});q('#ex-subitem-message').textContent='Selection added. Check the remaining text and shared context.';render();changed();
  };
  q('#ex-subitem-quote-add').onclick=()=>{
    const text=q('#ex-subitem-quote').value,field=q('#ex-subitem-field').value,original=fields[field]||'';
    const index=original.indexOf(text);
    if(!text.trim()||index<0){q('#ex-subitem-message').textContent='Paste wording that exactly matches the selected original field.';return;}
    if(original.indexOf(text,index+1)>=0){q('#ex-subitem-message').textContent='This wording occurs more than once. Select its exact original occurrence above.';return;}
    const start=Array.from(original.slice(0,index)).length,end=start+Array.from(text).length;
    if(parts.some(p=>p.field===field&&start<p.end&&p.start<end)){q('#ex-subitem-message').textContent='This wording overlaps an existing subitem.';return;}
    parts.push({field,start,end,text});q('#ex-subitem-quote').value='';q('#ex-subitem-message').textContent='Exact original wording linked.';render();changed();
  };
  render();
  return ()=>({subdivision_schema:'requirement-subdivision/1',subitems:parts,count_basis:q('#ex-subitem-count').value,remainder_reason:q('#ex-subitem-reason').value});
}
