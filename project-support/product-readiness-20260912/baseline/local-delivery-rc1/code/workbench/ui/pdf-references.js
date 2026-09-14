const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const copy=v=>JSON.parse(JSON.stringify(v));
const referenceMessage=e=>({stage_or_clear_reference_form_before_confirmation:'Add or clear the unfinished region or relationship before confirming.',complete_reference_table_cells_or_keep_pending:'The table still has unrecorded cells. Complete them or keep this reference as a draft.',complete_original_survey_or_keep_reference_pending:'Finish the whole-page checks and resolve the listed questions, or keep this reference as a draft.',reference_changed_reload_and_compare:'The saved reference changed. Reopen it and compare your retained draft.',reference_draft_belongs_to_another_operator:'This reference belongs to another reviewer.',reference_region_outside_original:'A region lies outside its bound original page. Check its coordinates.'}[e.message]||e.message);
export const referenceStatus=s=>s==='reference_saved'?'Reference saved · assessment pending':'Draft · reference not confirmed';
export function archiveDraft(storage,key,stored,guard){
 if(stored&&stored.guard!==guard){const archive=key+':previous:'+stored.guard;if(storage.getItem(archive)===null)storage.setItem(archive,JSON.stringify(stored));return archive;}
 return null;
}
export function drawnBox(start,end,size){
 const clamp=(v,max)=>Math.max(0,Math.min(max,v));
 const b=[Math.min(start[0],end[0]),Math.min(start[1],end[1]),Math.max(start[0],end[0]),Math.max(start[1],end[1])];
 return b.map((v,i)=>Math.round(clamp(v,i%2?size.height:size.width)*100)/100);
}

export async function showReferences(ex){
 const doc=ex.doc(),token=ex.token,ticket=ex.queueTicket;
 const valid=()=>ex.token===token&&ex.queueTicket===ticket&&ex.discovery==='references'&&ex.docId===doc.id;
 const list=ex.container.querySelector('#ex-list'),panel=ex.container.querySelector('#ex-detail');
 list.innerHTML='<p>Loading reference samples…</p>';panel.textContent='Reference collection starts from the complete original. Saved references still need assessment and independent qualification.';
 const data=await ex.api('/api/system2/references?'+new URLSearchParams({document_id:doc.id}));if(!valid())return;
 list.innerHTML=`<h3>PDF reference samples</h3><p>Development samples; no held-out qualification is inferred.</p><label>Original PDF page<input id="ref-new-page" type="number" min="1" max="${doc.total_pages}" value="${(ex.pdfPage||0)+1}"></label><label>Supporting PDF pages (optional, up to two)<input id="ref-new-support" placeholder="For example: 20, 21"></label><button id="ref-create">Start blank source reference</button><p role="status" id="ref-list-status"></p>${data.items.map((r,i)=>`<button class="task" data-reference="${i}"><strong>PDF page ${r.page_index+1}</strong><span>${referenceStatus(r.status)}</span><small>${esc(r.actor)} · revision ${r.revision}</small></button>`).join('')}`;
 list.querySelectorAll('[data-reference]').forEach(b=>b.onclick=()=>open(data.items[Number(b.dataset.reference)].id).catch(e=>panel.textContent=e.message));
 const createKey='pdf-reference-create:'+location.port+':'+doc.id;
 list.querySelector('#ref-create').onclick=async()=>{
  const button=list.querySelector('#ref-create'),status=list.querySelector('#ref-list-status');button.disabled=true;
  try{
   const p=Number(list.querySelector('#ref-new-page').value)-1,support=list.querySelector('#ref-new-support').value.trim();
   const body={document_id:doc.id,source_sha256:doc.source.content_hash,action:'create',page_index:p,supporting_pages:support?support.split(',').map(v=>Number(v.trim())-1):[]};
   const request=JSON.parse(localStorage.getItem(createKey)||'null')||{...body,request_id:crypto.randomUUID()};
   localStorage.setItem(createKey,JSON.stringify(request));
   const result=await ex.api('/api/system2/references',request);localStorage.removeItem(createKey);
   if(valid()){await open(result.reference_id);status.textContent='Blank reference task created. No source answer was generated.';}
  }catch(e){if(e.definitive)localStorage.removeItem(createKey);if(valid())status.textContent='Creation was not confirmed: '+referenceMessage(e)+' Retry to reconcile the same request.';}
  finally{if(valid())button.disabled=false;}
 };

 async function open(id){
  const detailTicket=ex.detailTicket={};const current=()=>valid()&&ex.detailTicket===detailTicket;
  const task=await ex.api('/api/system2/references?'+new URLSearchParams({reference_id:id}));if(!current())return;
  let index=data.items.findIndex(r=>r.id===id);if(index<0){index=data.items.length;data.items.push(task);}else data.items[index]=task;
  let card=list.querySelector('[data-reference="'+index+'"]');if(!card){card=document.createElement('button');card.className='task';card.dataset.reference=String(index);list.append(card);}
  card.innerHTML=`<strong>PDF page ${task.page_index+1}</strong><span>${referenceStatus(task.status)}</span><small>${esc(task.actor)} · revision ${task.revision}</small>`;card.onclick=()=>open(id).catch(e=>panel.textContent=e.message);
  const key='pdf-reference:'+location.port+':'+id,stored=JSON.parse(localStorage.getItem(key)||'null');
  const archivedKey=archiveDraft(localStorage,key,stored,task.guard);
  let body=copy(stored?.guard===task.guard?stored.body:task.body),pending=stored?.pending||null;
  let regionDirty=!!body.form_draft?.region_dirty,relationDirty=!!body.form_draft?.relation_dirty;
  const pages=[task.page_index,...task.supporting_pages],readonly=task.status!=='draft'||!task.source_current;
  panel.innerHTML=`<h2>Source reference · PDF page ${task.page_index+1}</h2><p>${referenceStatus(task.status)} · ${esc(task.actor)} · revision ${task.revision}</p>${task.study_origin==='engineering_fixture'?'<p role="alert">Engineering fixture. These actions are not independent human reference confirmations.</p>':''}<p>Inspect the full original, including areas without extracted content. No extractor answers are shown here. Qualification and assessment remain pending.</p>${!task.source_current?'<p role="alert">The source version or eligibility changed. This reference cannot be confirmed.</p>':''}<div class="reference-layout"><section><label>Original page<select id="ref-page">${pages.map(p=>`<option value="${p}">${p+1}${p!==task.page_index?' · supporting context':''}</option>`).join('')}</select></label><p>Drag on the original to locate a region, or enter its four PDF-point coordinates. Only your reference regions are highlighted.</p><label>Original magnification<select id="ref-zoom"><option value="100">Fit width</option><option value="150">150%</option><option value="200">200%</option></select></label><div class="reference-image-scroll"><div id="ref-image" class="reference-image"></div></div></section><form id="reference-form"><fieldset ${readonly?'disabled':''}>
  <fieldset id="reference-region-editor"><legend>Original region</legend><label>Existing region<select id="ref-region"><option value="">New region</option></select></label><label>Content role<select id="ref-role">${['text','heading','header','footer','table','table_cell','caption','footnote','figure','unknown'].map(v=>`<option value="${v}">${v.replaceAll('_',' ')}</option>`).join('')}</select></label><label>Printed label / caption (optional)<input id="ref-label"></label><div class="row">${['x0','y0','x1','y1'].map(k=>`<label>${k}<input id="ref-${k}" type="number" step="0.01" min="0"></label>`).join('')}</div><label>Exact original text<textarea id="ref-text" rows="5"></textarea></label><p>For photos and diagrams, keep the whole image region and caption; do not transcribe image-internal text. Scanned body text must be transcribed.</p><div id="ref-table-fields" hidden><label>Table rows<input id="ref-rows" type="number" value="1" min="1"></label><label>Table columns<input id="ref-cols" type="number" value="1" min="1"></label></div><div id="ref-cell-fields" hidden><label>Reference table<select id="ref-table"></select></label>${[['row','Row'],['column','Column'],['rowspan','Rows spanned'],['colspan','Columns spanned']].map(([k,v])=>`<label>${v}<input id="ref-${k}" type="number" min="1" value="1"></label>`).join('')}</div><button type="button" id="ref-stage">Add / update region</button><button type="button" id="ref-clear">Clear region form</button><button type="button" id="ref-remove">Remove selected region</button></fieldset>
  <div id="ref-region-list"></div><fieldset id="reference-link-editor"><legend>Original relationship</legend><label>Relation<select id="ref-link-kind">${['footnote','caption','continuation','reading_order','context'].map(v=>`<option value="${v}">${v.replaceAll('_',' ')}</option>`).join('')}</select></label><label>From region<select id="ref-link-from"></select></label><label>To region<select id="ref-link-to"></select></label><label>Printed marker (optional)<input id="ref-marker"></label><label>Evidence for this relationship<textarea id="ref-link-note"></textarea></label><button type="button" id="ref-link-add">Add relationship</button><button type="button" id="ref-link-clear">Clear relationship form</button></fieldset><div id="ref-links"></div>
  <label>Prior exposure<select id="ref-exposure"><option value="unknown">Not recorded</option><option value="source_only">Original only; no output seen</option><option value="seen_outputs">Extraction or verifier output already seen</option></select></label><label>Assistance / exposure details<textarea id="ref-assistance"></textarea></label><fieldset><legend>Whole primary page survey</legend>${['content','structure','relationships'].map(k=>`<label><input type="checkbox" id="ref-survey-${k}"> I checked ${k}, including areas with no extracted item.</label>`).join('')}<label><input type="checkbox" id="ref-blank"> The primary original page is blank.</label></fieldset><label>Unresolved areas or questions<textarea id="ref-unresolved"></textarea></label><label>Confirmation evidence / revision reason<textarea id="ref-note"></textarea></label><button type="button" id="ref-save">Save reference draft</button><button type="submit">Confirm source reference</button></fieldset><p role="status" id="ref-status"></p>${pending?'<button type="button" id="ref-retry">Retry unconfirmed request</button>':''}</form></div>${task.status==='reference_saved'&&task.source_current?'<label>Reason for a new reference revision<textarea id="ref-revision-reason"></textarea></label><button id="ref-revise">Start a new reference revision</button><button id="ref-assessments">Assess extraction and verifier findings</button>':''}<details><summary>Reference history (${task.history.length})</summary>${task.history.map(h=>`<details><summary>${esc(h.action)} · ${esc(h.actor)} · ${esc(h.at)}</summary><p>${esc(h.after.body.note)}</p>${h.after.body.regions.map(r=>`<p>Page ${r.page_index+1} · ${esc(r.role)} · ${r.bbox.map(v=>v.toFixed(1)).join(', ')}<br>${esc(r.text||r.label)}</p>`).join('')}</details>`).join('')}</details>`;
  const q=s=>panel.querySelector(s),status=q('#ref-status'),form=q('#reference-form');
  const fields=['page','region','role','label','x0','y0','x1','y1','text','rows','cols','table','row','column','rowspan','colspan','link-kind','link-from','link-to','marker','link-note'];
  function collect(){
   body.prior_exposure=q('#ref-exposure').value;body.assistance=q('#ref-assistance').value;body.unresolved=q('#ref-unresolved').value;body.note=q('#ref-note').value;
   body.survey=Object.fromEntries(['content','structure','relationships'].map(k=>[k,q('#ref-survey-'+k).checked]));body.survey.blank_page=q('#ref-blank').checked;
   body.form_draft={region_dirty:regionDirty,relation_dirty:relationDirty,fields:Object.fromEntries(fields.map(k=>[k,q('#ref-'+k).value]))};
   return copy(body);
  }
  const persist=()=>localStorage.setItem(key,JSON.stringify({guard:task.guard,body:collect(),pending}));
  function roleFields(){q('#ref-table-fields').hidden=q('#ref-role').value!=='table';q('#ref-cell-fields').hidden=q('#ref-role').value!=='table_cell';}
  function refreshRegions(){
   const options=body.regions.map((r,i)=>`<option value="${esc(r.id)}">${i+1}. ${esc(r.label||r.role)} · page ${r.page_index+1}</option>`).join('');
   for(const k of ['region','link-from','link-to']){const el=q('#ref-'+k),value=el.value;el.innerHTML='<option value="">Choose region</option>'+options;el.value=value;}
   const table=q('#ref-table'),value=table.value;table.innerHTML='<option value="">Choose a table region</option>'+body.regions.filter(r=>r.role==='table'&&r.page_index===Number(q('#ref-page').value)).map(r=>`<option value="${esc(r.id)}">${esc(r.label||'Reference table')}</option>`).join('');table.value=value;
   q('#ref-region-list').innerHTML=`<p>${body.regions.length} reference regions in this form.</p>`;
   q('#ref-links').innerHTML=body.relations.map((l,i)=>`<p>${esc(l.kind)} · ${esc(l.marker)} · ${esc(l.explanation)} <button type="button" data-remove-link="${i}" ${readonly?'disabled':''}>Remove relationship</button></p>`).join('');
   q('#ref-links').querySelectorAll('[data-remove-link]').forEach(b=>b.onclick=()=>{body.relations.splice(Number(b.dataset.removeLink),1);refreshRegions();persist();});draw();
  }
  function draw(){const svg=q('#ref-image svg');if(!svg)return;svg.innerHTML=body.regions.filter(r=>r.page_index===Number(q('#ref-page').value)).map(r=>`<rect x="${r.bbox[0]}" y="${r.bbox[1]}" width="${r.bbox[2]-r.bbox[0]}" height="${r.bbox[3]-r.bbox[1]}" fill="#2a7a4420" stroke="#24734d" stroke-width="1.5"/>`).join('');}
  async function showPage(){
   const p=Number(q('#ref-page').value),imageTicket={};ex.referenceImageTicket=imageTicket;q('#ref-image').textContent='Loading the bound original…';
   try{const image=await ex.api('/api/system2/preview?'+new URLSearchParams({document_id:doc.id,page_index:p,full:true,expected_hash:task.source.content_hash}));
    if(!current()||ex.referenceImageTicket!==imageTicket)return;
    const size=task.dimensions[String(p)];if(image.width!==size.width||image.height!==size.height)throw Error('Original dimensions changed; reload the reference.');
    q('#ref-image').innerHTML=`<img src="${esc(image.image)}" alt="Original PDF page ${p+1}"><svg aria-label="Your original reference regions" viewBox="0 0 ${size.width} ${size.height}"></svg>`;draw();
    const svg=q('#ref-image svg');let start;
    const point=e=>{const r=svg.getBoundingClientRect();return [(e.clientX-r.left)/r.width*size.width,(e.clientY-r.top)/r.height*size.height];};
    svg.onpointerdown=e=>{if(readonly)return;start=point(e);svg.setPointerCapture(e.pointerId);};
    svg.onpointerup=e=>{if(!start)return;const b=drawnBox(start,point(e),size);start=null;if(b[2]<=b[0]||b[3]<=b[1])return;['x0','y0','x1','y1'].forEach((k,i)=>q('#ref-'+k).value=b[i]);regionDirty=true;persist();status.textContent='Region located in the form. Add/update it, then save or confirm.';};
   }catch(e){if(current())q('#ref-image').textContent='Original unavailable: '+e.message;}
  }
  q('#ref-zoom').onchange=()=>q('#ref-image').style.width=q('#ref-zoom').value+'%';
  q('#ref-page').onchange=()=>{q('#ref-region').value='';refreshRegions();showPage();};
  q('#ref-region').onchange=()=>{const r=body.regions.find(r=>r.id===q('#ref-region').value);if(!r)return;q('#ref-page').value=r.page_index;
   q('#ref-role').value=r.role;q('#ref-label').value=r.label||'';q('#ref-text').value=r.text||'';['x0','y0','x1','y1'].forEach((k,i)=>q('#ref-'+k).value=r.bbox[i]);
   for(const [k,v] of Object.entries({rows:r.row_count||1,cols:r.column_count||1,row:(r.row??0)+1,column:(r.column??0)+1,rowspan:r.row_span||1,colspan:r.column_span||1}))q('#ref-'+k).value=v;
   refreshRegions();q('#ref-table').value=r.table_id||'';regionDirty=false;roleFields();persist();showPage();};
  q('#ref-role').onchange=roleFields;
  q('#ref-stage').onclick=()=>{try{
   const r={id:q('#ref-region').value||crypto.randomUUID(),page_index:Number(q('#ref-page').value),role:q('#ref-role').value,label:q('#ref-label').value,text:q('#ref-text').value,bbox:['x0','y0','x1','y1'].map(k=>Number(q('#ref-'+k).value))};
   if(r.bbox[2]<=r.bbox[0]||r.bbox[3]<=r.bbox[1])throw Error('Locate a nonempty original region.');
   if(r.role==='table')Object.assign(r,{row_count:Number(q('#ref-rows').value),column_count:Number(q('#ref-cols').value)});
   if(r.role==='table_cell')Object.assign(r,{table_id:q('#ref-table').value,row:Number(q('#ref-row').value)-1,column:Number(q('#ref-column').value)-1,row_span:Number(q('#ref-rowspan').value),column_span:Number(q('#ref-colspan').value)});
   const index=body.regions.findIndex(x=>x.id===r.id);if(index<0)body.regions.push(r);else body.regions[index]=r;
   regionDirty=false;refreshRegions();q('#ref-region').value=r.id;persist();status.textContent='Region staged; save the draft to persist it.';
  }catch(e){status.textContent=e.message;}};
  q('#ref-clear').onclick=()=>{q('#ref-region').value='';for(const k of ['label','text','x0','y0','x1','y1'])q('#ref-'+k).value='';regionDirty=false;persist();};
  q('#ref-remove').onclick=()=>{const id=q('#ref-region').value;if(body.relations.some(l=>[...l.from_ids,...l.to_ids].includes(id))||body.regions.some(r=>r.table_id===id)){status.textContent='Remove its relationships and child cells first.';return;}body.regions=body.regions.filter(r=>r.id!==id);q('#ref-clear').click();refreshRegions();persist();};
  q('#ref-link-add').onclick=()=>{const from=q('#ref-link-from').value,to=q('#ref-link-to').value;if(!from||!to||from===to){status.textContent='Choose two distinct original regions.';return;}body.relations.push({id:crypto.randomUUID(),kind:q('#ref-link-kind').value,from_ids:[from],to_ids:[to],marker:q('#ref-marker').value,explanation:q('#ref-link-note').value});relationDirty=false;refreshRegions();persist();};
  q('#ref-link-clear').onclick=()=>{for(const k of ['link-from','link-to','marker','link-note'])q('#ref-'+k).value='';relationDirty=false;persist();};
  form.oninput=e=>{if(e.target.closest('#reference-region-editor'))regionDirty=true;if(e.target.closest('#reference-link-editor'))relationDirty=true;persist();status.textContent='Unsaved reference changes retained locally.';};
  q('#ref-exposure').value=body.prior_exposure;for(const k of ['assistance','unresolved','note'])q('#ref-'+k).value=body[k]||'';
  for(const k of ['content','structure','relationships'])q('#ref-survey-'+k).checked=!!body.survey[k];q('#ref-blank').checked=!!body.survey.blank_page;
  const recovered=body.form_draft?.fields||{};if(recovered.page!==undefined)q('#ref-page').value=recovered.page;
  refreshRegions();for(const [k,v] of Object.entries(recovered))if(fields.includes(k))q('#ref-'+k).value=v;roleFields();showPage();
  status.textContent=stored?.guard===task.guard?'Local changes recovered; save the draft to persist them.':task.status==='draft'?'Saved draft loaded. Reference remains unconfirmed.':'Saved reference loaded. Assessment remains pending.';
  if(archivedKey){status.textContent='A previous local draft has a different saved version. A separate copy is retained below for comparison; it is not applied to the current reference.';const old=document.createElement('details'),title=document.createElement('summary'),contents=document.createElement('pre');title.textContent='Previous local draft';contents.textContent=JSON.stringify(stored.body,null,2);old.append(title,contents);form.append(old);}
  async function submit(action,extra={}){
   if(pending&&action!=='retry'){status.textContent='Retry the unconfirmed request before submitting another change.';return;}
   if(action!=='retry')pending={request_id:crypto.randomUUID(),document_id:doc.id,reference_id:id,source_sha256:task.source.content_hash,guard:task.guard,action,...(action==='revise'?extra:{body:collect()})};
   persist();const fieldset=form.querySelector('fieldset');fieldset.disabled=true;status.textContent='Saving reference…';
   try{await ex.api('/api/system2/references',pending);pending=null;localStorage.removeItem(key);if(current())await open(id);}
   catch(e){if(e.definitive)pending=null;if(current()){persist();fieldset.disabled=readonly;status.textContent='Reference save was not confirmed: '+referenceMessage(e);
     if(pending&&!q('#ref-retry')){const retry=document.createElement('button');retry.type='button';retry.id='ref-retry';retry.textContent='Retry unconfirmed request';retry.onclick=()=>submit('retry');form.append(retry);}}}
  }
  q('#ref-save').onclick=()=>submit('save');form.onsubmit=e=>{e.preventDefault();submit('confirm');};if(q('#ref-retry'))q('#ref-retry').onclick=()=>submit('retry');
  if(q('#ref-assessments'))q('#ref-assessments').onclick=async()=>{const {showAssessments}=await import('./pdf-assessments.js');if(current())showAssessments(ex,task);};
  if(q('#ref-revise'))q('#ref-revise').onclick=()=>submit('revise',{note:q('#ref-revision-reason').value});
 }
}
