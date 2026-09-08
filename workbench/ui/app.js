'use strict';
import {showEvidence} from './evidence-viewer.js';
import {restoreDraft, sameRevision, scoresComplete, pendingReceipt, historyRows, importedReview, previousImportedReview} from './review-state.js';
import {renderDashboard} from './dashboard.js';
import {System2Review} from './system2-review.js';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fields={authority_quality:['Authority','Publisher and document type'],scope_relevance:['Scope relevance','Scope, subject and jurisdiction'],version_currency:['Version currency','Version, date and supersession'],traceability:['Traceability','Exact origin and source record'],access_permission:['Access permission','Permission to obtain and use']};
let state,view='overview',selected=null,draft={},busy=false,search='',saveTimer,requestStatus='',activeTask=null;
let queueFilter=null,queueFilterLabel='';
const main=$('#main');
const system2Review=new System2Review();
const notice=message=>{$('#notice').textContent=message||''};
async function api(path,body){const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-CSRF-Token':state.csrf}:{},body:body?JSON.stringify(body):undefined});const result=await response.json();if(!response.ok)throw Error(result.error||'Unable to load data');return result}
function safeLink(url,label){try{const u=new URL(url);if(!['http:','https:'].includes(u.protocol))return '';return '<a href="'+esc(u.href)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' ↗</a>'}catch{return ''}}
function noteWithLinks(note){const text=String(note||'');const matches=[...text.matchAll(/https?:\/\/[^\s<>"']+/gi)];let html='',from=0;for(const match of matches){html+=esc(text.slice(from,match.index))+safeLink(match[0],match[0]);from=match.index+match[0].length}return html+esc(text.slice(from))}
function linkReviewProgress(record,review){if(review?.verdict!=='INCORRECT')return '';const open=state.tasks.find(t=>t.source_id===record.source_id&&t.human_issue);if(!open)return '';const url=open.source?.retrieval_url;if(!url||!String(review.note).includes(url))return '';return '<p class="link-review-progress">Suggested link is registered. Original document still needs verification.</p><button class="history-followup" data-followup-source="'+esc(record.source_id)+'">Continue review</button>'}
function task(){return activeTask?.operation_id===selected?activeTask:state.tasks.find(t=>t.operation_id===selected)}
function currentNote(){return $('#note')?.value??draft.note??''}
async function refresh(render=true){
  const previousActor=state?.actor.id;
  state=await api('/api/state');
  const picker=$('#actor'), focused=document.activeElement===picker, selectedName=focused?picker.value:state.actor.name||'';
  const names=state.actors.map(a=>a.name), signature=JSON.stringify(names);
  if(picker.dataset.roster!==signature){picker.innerHTML='<option value="">Select a reviewer</option>'+names.map(n=>'<option value="'+esc(n)+'">'+esc(n)+'</option>').join('');picker.dataset.roster=signature;}
  picker.value=selectedName;
  $('#actor-save').textContent=state.actor.name?'Switch reviewer':'Use this name';
  renderRequests();if(render||(previousActor!==state.actor.id&&view.startsWith('system2')))renderView();
}
function renderRequests(){const labels={queued:'Submitted',running:'Applying',waiting:'Waiting',applied:'Applied',blocked:'Needs attention',stale:'Out of date'};$('#requests').innerHTML=state.requests.slice(0,4).map(r=>'<div class="request"><strong>'+esc(labels[r.status]||r.status)+'</strong><span>'+esc(r.actor)+' · '+esc(r.message)+'</span></div>').join('')}
function renderView(){system2Review.leave();document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===view);if(b.dataset.view===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});$('#heading').textContent={overview:'Requirement overview',system1:'System1 · Pending review',history:'System1 · Review history',system2:'System2 · Pending review',system2History:'System2 · Review history',system3:'System3 · Pending review',system3History:'System3 · Review history'}[view];
if(view==='overview'){renderDashboard(main,{...state.dashboard,qa_schedule:state.qa_schedule},openFilteredTasks,switchView);return}
if(view==='history'){const rows=historyRows(state);main.innerHTML='<section class="panel"><h2>Review records · '+rows.length+'</h2><p class="muted">Review history preserves each reviewer, decision and original note. A blank reviewer on a pending task means this round is not yet complete.</p><div class="history-wrap"><table class="history"><thead><tr><th>Source</th><th>Reviewer</th><th>Recorded at</th><th>Decision / result</th><th>Notes</th></tr></thead><tbody>'+rows.map(historyRowHTML).join('')+'</tbody></table></div></section>';main.querySelectorAll('[data-followup-source]').forEach(button=>button.onclick=()=>openFilteredTasks([button.dataset.followupSource],'Link verification'));return}
if(view.startsWith('system2')){system2Review.mount(main,{actor:state.actor,history:view==='system2History',navigate:switchView});return}
if(view.startsWith('system3')){main.innerHTML='<section class="panel"><span class="eyebrow">System3</span><h2 class="spacer">Semantic enrichment is in design</h2><p class="muted">Live tasks will be connected after the semantic interface is validated with the Site Model team.</p></section>';return}
const filtered=state.tasks.filter(t=>(!queueFilter||queueFilter.has(t.source_id))&&(t.source_id+' '+t.source_title).toLowerCase().includes(search.toLowerCase()));if(!selected||!task()){selected=filtered[0]?.operation_id;activeTask=state.tasks.find(t=>t.operation_id===selected);draft=restoreDraft(draft,activeTask);}
main.innerHTML='<div class="review-layout"><section class="queue"><div class="queue-head"><strong>Queue · '+state.tasks.length+'</strong><input id="search" aria-label="Find a source" placeholder="Search ID or title" value="'+esc(search)+'"></div><div class="queue-list">'+filtered.map(t=>'<button class="task '+(t.operation_id===selected?'active':'')+'" data-task="'+esc(t.operation_id)+'"><span>'+esc(t.source_id)+'</span><strong>'+esc(t.source_title)+'</strong><small class="queue-context">'+esc([String(t.source?.file_format||'').toUpperCase(),t.source?.issuer].filter(Boolean).join(' · '))+'</small><small class="queue-reason">'+esc(issueLabel(t))+'</small></button>').join('')+'</div></section><section id="detail" class="panel detail"></section></div>';
if(queueFilter){const filter=document.createElement('div');filter.className='queue-filter';filter.append(document.createTextNode(queueFilterLabel+' · '+filtered.length+' tasks'));const clear=document.createElement('button');clear.textContent='Show all';clear.onclick=()=>{queueFilter=null;queueFilterLabel='';search='';renderView()};filter.append(clear);$('.queue-head').append(filter)}
$('#search').oninput=e=>{search=e.target.value;renderView();$('#search').focus();$('#search').setSelectionRange(search.length,search.length)};
document.querySelectorAll('[data-task]').forEach(b=>b.onclick=async()=>{await saveDraft();selected=b.dataset.task;await loadDraft();renderView()});renderDetail()}
function historyRowHTML(record){
  const review=importedReview(record);
  const when=review?.review_date||record.checked_at||record.program_operated_at||'Not provided';
  const timing=review&&!review.review_date?'<br><small>Imported at; review date not provided in the original workbook</small>':'';
  const verdict=review?.verdict||record.decision;
  const status=review?'Excel review synced':record.program_status;
  return '<tr data-history-source="'+esc(record.source_id)+'"><td>'+esc(record.source_id)+'</td><td>'+esc(review?.reviewer||record.operator)+'</td><td>'+esc(when)+timing+'</td><td>'+esc(verdict)+'<br><small>'+esc(status)+'</small></td><td class="review-note">'+noteWithLinks(review?review.note:record.operator_note)+linkReviewProgress(record,review)+'</td></tr>';
}
function previousReviewHTML(t){
  const review=previousImportedReview(state,t.source_id);
  if(!review)return '';
  let remaining='The previous decision and original notes are preserved in review history.';
  if(t.human_issue)remaining='The reported issue still needs verification. See the reviewer feedback below.';
  else if(review.verdict==='ACCEPT'&&t.source?.operator_selection_decision==='INCLUDE'&&t.source?.effective_selection==='PENDING'){
    const unresolved=Object.entries(fields).filter(([key])=>t.source[key]!=='HIGH').map(([key,[label]])=>label+' '+({HIGH:'H',MEDIUM:'M',LOW:'L'}[t.source[key]]||'Not rated'));
    remaining='Previously approved for inclusion. Still to verify'+(unresolved.length?': '+unresolved.join(', '):'source ratings')+'. Existing ratings were preserved.';
  }
  return '<section class="prior-review" aria-label="Previous colleague review"><strong>Previous Excel review · '+esc(review.reviewer)+' · '+esc(review.verdict)+'</strong>'+(review.note&&!t.human_issue?'<p class="review-note">'+esc(review.note)+'</p>':'')+'<p>'+esc(remaining)+'</p><button type="button" id="previous-review">View review history</button></section>';
}
function taskInstruction(t){if(t.operation_type==='RANDOM_QA_CHECK')return 'Check the source record against the original, including its identity, links, version and ratings. Record the result below.';const codes=t.trigger||'';if(codes.includes('PAYWALL'))return 'Obtain and upload an authorised original. You may complete source ratings when you have enough evidence.';if(t.human_issue)return 'Check the feedback below, correct source details and record how you verified the original.';return 'Review the source and original document. Your decision is applied automatically.'}
function issueLabel(t){const s=t.trigger||'';if(s.includes('HUMAN_REPORTED_ISSUE'))return 'Reported issue needs verification';if(s.includes('PAYWALL'))return 'Authorised original needed';if(s.includes('SELECTION'))return 'Source ratings needed';if(t.operation_type==='RANDOM_QA_CHECK')return 'Weekly random check';return 'Check source details'}
async function loadDraft(){const id=selected,actor=state.actor.id;const saved=actor&&id?await api('/api/draft?task='+encodeURIComponent(id)):{};if(selected!==id||state.actor.id!==actor)return;activeTask=state.tasks.find(t=>t.operation_id===id);draft=restoreDraft(saved,activeTask);$('#reload-task').hidden=true;notice(draft.stale?'The source or task has changed. Your written draft is preserved; please rate and verify each item again.':'')}
async function saveDraft(){clearTimeout(saveTimer);if(!state?.actor.id||!selected||activeTask?.operation_id!==selected)return;draft.note=currentNote();const id=selected,body=structuredClone(draft);await api('/api/draft',{task_id:id,draft:body})}
function renderDetail(){const t=task();if(!t){$('#detail').innerHTML='<div class="empty">No pending reviews.</div>';return}const s=t.source||{};const actor=!state.actor.id;const oldScore=k=>({HIGH:'H',MEDIUM:'M',LOW:'L'}[s[k]]||'Unknown');
$('#detail').innerHTML='<span class="source-id">'+esc(t.source_id)+'</span><h2 class="spacer">'+esc(t.source_title)+'</h2><div class="meta"><span>'+esc(s.issuer||'Issuer unconfirmed')+'</span><span>'+esc(s.authoritative_language||'Language unconfirmed')+'</span><span>Version '+esc(s.version||'Not recorded')+'</span></div><div class="links">'+safeLink(s.official_url,'Official page')+(s.retrieval_url!==s.official_url?safeLink(s.retrieval_url,'Retrieval link'):'')+(s.snapshot_status==='STORED'?'<a href="/api/original/'+encodeURIComponent(t.source_id)+'">Download original ↓</a><button id="preview" type="button">'+(/\.pdf$/i.test(s.stored_filename||'')?'View full PDF':'View original')+'</button>':'<span class="muted">No local original available</span>')+'</div>'+previousReviewHTML(t)+'<div id="preview-box"></div><p class="muted">'+esc(taskInstruction(t))+'</p>'+(t.human_issue?'<div class="issue"><strong>Reviewer feedback</strong><br>'+esc(t.human_issue.reason)+'</div>':'')+(actor?'<div class="issue">Select a reviewer at the top first.</div>':'')+'<section id="assessment"><h3>Source assessment</h3><p class="muted">Light fill shows the previous rating; dark fill shows your current selection. The fifth rating submits your decision automatically.</p><div id="ratings">'+Object.entries(fields).map(([k,[label,hint]])=>'<div class="score-row"><span>'+label+'<small>'+hint+'</small></span><div class="rating" role="group" aria-label="'+label+'">'+[['HIGH','H'],['MEDIUM','M'],['LOW','L']].map(([v,text])=>'<button data-score="'+k+'" data-value="'+v+'" class="'+[s[k]===v?'previous':'',draft.scores?.[k]===v?'selected':''].filter(Boolean).join(' ')+'" aria-pressed="'+(draft.scores?.[k]===v)+'" aria-label="'+text+(s[k]===v?', previous rating':'')+(draft.scores?.[k]===v?', current selection':'')+'" '+(actor||busy?'disabled':'')+' title="'+esc({H:'Verified with sufficient evidence',M:'Needs confirmation',L:'Does not meet criteria or insufficient evidence'}[text])+'">'+text+'</button>').join('')+'</div></div>').join('')+'</div></section><details class="note" '+(draft.note?'open':'')+'><summary>Notes / reason</summary><textarea id="note" placeholder="Questions, unresolved items or evidence for this decision">'+esc(draft.note||'')+'</textarea><small id="draft-status">Notes are saved as a draft and do not complete the task.</small></details><div class="row"><button id="defer" '+(actor||busy?'disabled':'')+'>Keep pending</button><button id="exclude" class="danger" '+(actor||busy?'disabled':'')+'>Remove from scope</button></div><details '+(t.human_issue?'open':'')+'><summary>Correct links and source details</summary><label for="retrieval">Original download URL</label><input class="field" id="retrieval" value="'+esc(draft.urls?.retrieval_url??s.retrieval_url??'')+'"><label for="official">Official source page</label><input class="field" id="official" value="'+esc(draft.urls?.official_url??s.official_url??'')+'"><button id="correct" '+(actor||busy?'disabled':'')+'>Save corrected links</button><p class="muted spacer">This saves source details and keeps the existing snapshot. The new link is not yet a verified original.</p>'+ (t.human_issue?'<div class="checks"><label><input type="checkbox" id="issue-verified">I checked the original and confirmed the reported issue is resolved</label></div><button id="verify" '+(actor||busy?'disabled':'')+'>Record verification</button>':'')+'</details><details '+((t.trigger||'').includes('PAYWALL')?'open':'')+'><summary>Upload authorised original</summary><p class="muted">Choose a local PDF, HTML or XLSX. After the format check, verify the content and permissions below.</p><div class="file-picker"><button type="button" id="choose-upload" '+(actor||busy?'disabled':'')+'>Choose file</button><span id="upload-name">No file selected</span></div><input id="upload" type="file" accept=".pdf,.html,.htm,.xlsx" hidden '+(actor||busy?'disabled':'')+'><p id="upload-status" class="muted"></p><div class="checks"><label><input id="identity-check" type="checkbox">The file matches this source, version and language, and is complete</label><label><input id="permission-check" type="checkbox">I have permission to obtain and use this original</label></div><button id="manual" disabled>Submit original</button></details>';
if($('#previous-review'))$('#previous-review').onclick=async()=>{await switchView('history');document.querySelector('[data-history-source="'+CSS.escape(t.source_id)+'"]').scrollIntoView({block:'center'})};
$('#note').oninput=()=>{clearTimeout(saveTimer);saveTimer=setTimeout(()=>saveDraft().then(()=>{if($('#draft-status'))$('#draft-status').textContent='Draft saved.'}).catch(e=>notice(e.message)),350)};
document.querySelectorAll('[data-score]').forEach(b=>b.onclick=async()=>{
  if(draft.pending)return;
  draft.scores??={};draft.scores[b.dataset.score]=b.dataset.value;draft.note=currentNote();
  document.querySelectorAll('[data-score]').forEach(option=>{const checked=draft.scores[option.dataset.score]===option.dataset.value;option.classList.toggle('selected',checked);option.setAttribute('aria-pressed',String(checked))});
  try{await saveDraft();if(scoresComplete(draft.scores))await submit('assess',{scores:draft.scores})}catch(error){notice('The ratings draft was not saved. Please retry. '+error.message)}
});
for(const [id,key] of [['retrieval','retrieval_url'],['official','official_url']]){
  $('#'+id).oninput=e=>{draft.urls??={};draft.urls[key]=e.target.value;clearTimeout(saveTimer);saveTimer=setTimeout(()=>saveDraft().catch(error=>notice(error.message)),350)};
}
$('#defer').onclick=()=>submit('defer');$('#exclude').onclick=()=>submit('exclude');
$('#correct').onclick=()=>{const updates={};if($('#retrieval').value!==s.retrieval_url)updates.retrieval_url=$('#retrieval').value;if($('#official').value!==s.official_url)updates.official_url=$('#official').value;submit('correct',{updates})};
if($('#verify'))$('#verify').onclick=()=>submit('verify',{issue_verified:$('#issue-verified').checked});
if($('#preview'))$('#preview').onclick=()=>showEvidence($('#preview-box'),t.source_id,api);
let uploadResult=null;const checkUpload=()=>{$('#manual').disabled=!uploadResult||!$('#identity-check').checked||!$('#permission-check').checked||busy};
$('#identity-check').onchange=checkUpload;$('#permission-check').onchange=checkUpload;
$('#choose-upload').onclick=()=>$('#upload').click();
$('#upload').onchange=async e=>{uploadResult=null;$('#identity-check').checked=false;$('#permission-check').checked=false;checkUpload();const file=e.target.files[0];if(!file)return;$('#upload-name').textContent=file.name;try{if(file.size===0||file.size>50*1024*1024)throw Error('The file is empty or exceeds 50 MB.');$('#upload-status').textContent='Staging file…';const response=await fetch('/api/upload',{method:'POST',headers:{'X-CSRF-Token':state.csrf,'X-File-Extension':'.'+file.name.split('.').pop().toLowerCase()},body:file});const r=await response.json();if(!response.ok)throw Error(r.error);uploadResult=r;$('#upload-status').textContent=r.message;checkUpload()}catch(e){$('#upload-status').textContent=e.message}};
$('#manual').onclick=()=>submit('manual',{upload_id:uploadResult.upload_id,identity_verified:true,permission_verified:true});
if(!(t.trigger||'').includes('SELECTION_PENDING')&&$('#assessment'))$('#assessment').hidden=true;
if((t.trigger||'').includes('PAYWALL')&&$('#assessment'))$('#assessment').before($('#upload').closest('details'));
if(t.operation_type==='RANDOM_QA_CHECK'){
  $('#assessment').hidden=true;$('#defer').hidden=true;$('#exclude').hidden=true;
  const qa=document.createElement('section');qa.innerHTML='<h3>Random source check</h3><dl class="qa-facts">'+[['Jurisdiction',s.jurisdiction],['Document type',s.document_type],['Source status',s.source_status],...Object.entries(fields).map(([key,[label]])=>[label,oldScore(key)])].map(([label,value])=>'<div><dt>'+esc(label)+'</dt><dd>'+esc(value||'Not recorded')+'</dd></div>').join('')+'</dl><p class="muted">Check the original before selecting Correct. Describe any errors in Notes; a correction task will be created.</p><div class="row"><button id="qa-correct" class="primary">Correct</button><button id="qa-incorrect">Report an error</button></div>';
  $('#note').closest('details').before(qa);
  $('#retrieval').closest('details').hidden=true;$('#upload').closest('details').hidden=true;$('#qa-correct').disabled=actor;$('#qa-incorrect').disabled=actor;
  $('#qa-correct').onclick=()=>submit('qa',{verdict:'CORRECT'});$('#qa-incorrect').onclick=()=>submit('qa',{verdict:'INCORRECT'});
}
if(draft.pending){
  const receipt=pendingReceipt(draft,state.requests);
  $('#detail').querySelectorAll('input,textarea,button').forEach(control=>{if(!['preview','previous-review'].includes(control.id))control.disabled=true});
  const pending=document.createElement('div');pending.className='issue';pending.textContent=receipt?receipt.message:'Submission is unconfirmed. Your decision and draft are preserved.';
  if(!receipt){const retry=document.createElement('button');retry.textContent='Retry submission';retry.disabled=busy;retry.onclick=()=>transmitPending();pending.append(document.createElement('br'),retry)}
  $('#detail').prepend(pending);
}
}
async function transmitPending(){
  if(busy||!draft.pending)return;
  busy=true;renderDetail();
  try{await api('/api/decisions',draft.pending);notice('Decision submitted. Waiting for it to be applied.');await refresh(false)}
  catch(error){notice('Submission is unconfirmed. Your draft and request ID are preserved; retry the same decision. '+error.message)}
  finally{busy=false;renderDetail()}
}
async function submit(action,extra={}){
  if(busy||draft.pending)return;
  const t=task(),latest=state.tasks.find(x=>x.operation_id===selected),note=currentNote();
  if(!state.actor.id){notice('Please select a reviewer first.');return}
  if(!sameRevision(draft,latest)){notice('The source or task has changed. Reload and review it again.');$('#reload-task').hidden=false;return}
  if((['defer','exclude','verify'].includes(action)||(action==='qa'&&extra.verdict==='INCORRECT'))&&!note.trim()){notice('Enter the reason or evidence for this decision in Notes.');$('#note').closest('details').open=true;$('#note').focus();return}
  if(action==='correct'&&!Object.keys(extra.updates).length){notice('Enter a corrected URL first.');return}
  draft.note=note;draft.pending={request_id:crypto.randomUUID(),task_id:t.operation_id,revision:t.revision,source_revision:t.source_revision,action,note,...extra};
  try{await saveDraft()}catch(error){draft.pending=null;notice('The draft was not saved; the decision has not been sent. '+error.message);return}
  await transmitPending();
}
async function openFilteredTasks(ids,label){await saveDraft();queueFilter=ids?new Set(ids):null;queueFilterLabel=label;search='';selected=state.tasks.find(t=>!queueFilter||queueFilter.has(t.source_id))?.operation_id;activeTask=null;await switchView('system1')}
async function switchView(next){await saveDraft();view=next;const group=next==='history'?'system1':next.replace('History','');if(group.startsWith('system')){const control=document.querySelector('[data-system="'+group+'"]');if(control){control.setAttribute('aria-expanded','true');document.getElementById(control.getAttribute('aria-controls')).hidden=false;}}if(next==='system1'){selected=selected||state.tasks[0]?.operation_id;await loadDraft()}renderView()}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{if(b.dataset.view==='system1'){queueFilter=null;queueFilterLabel='';search=''}switchView(b.dataset.view).catch(e=>notice(e.message))});
document.querySelectorAll('[data-system]').forEach(button=>button.onclick=()=>{const expanded=button.getAttribute('aria-expanded')==='true';button.setAttribute('aria-expanded',String(!expanded));document.getElementById(button.getAttribute('aria-controls')).hidden=expanded});
$('#actor-form').onsubmit=async e=>{e.preventDefault();const name=$('#actor').value;try{await saveDraft();await api('/api/actor',{name});await refresh(false);await loadDraft();notice('');renderView()}catch(e){notice(e.message)}};
$('#stop').onclick=async()=>{try{await api('/api/stop',{});notice('Workbench stopped. Double-click the launcher to continue.');clearInterval(poll)}catch(e){notice(e.message)}};
$('#reload-task').onclick=async()=>{
  const receipt=pendingReceipt(draft,state.requests);
  if(draft.pending&&!receipt){notice('Retry the original request first to avoid duplicate submissions.');return}
  if(receipt&&['queued','running','waiting'].includes(receipt.status)){notice('The original decision is still processing. Please wait for the receipt.');return}
  draft.pending=null;draft.revision=null;await saveDraft();activeTask=null;
  if(!state.tasks.some(t=>t.operation_id===selected)){selected=state.tasks[0]?.operation_id;search='';}
  await loadDraft();$('#reload-task').hidden=true;renderView();
};
const poll=setInterval(async()=>{
  if(!state||busy)return;
  try{
    await refresh(false);
    const receipt=pendingReceipt(draft,state.requests);
    if(receipt?.status==='applied'){
      draft={note:draft.note||'',scores:{}};await saveDraft();activeTask=null;
      if(!state.tasks.some(t=>t.operation_id===selected)){selected=state.tasks[0]?.operation_id;search='';}
      await loadDraft();renderView();notice('Decision applied. The queue and Dashboard have been updated.');return;
    }
    if(receipt&&['blocked','stale'].includes(receipt.status)){
      notice(receipt.message);$('#reload-task').hidden=false;
    }else if(view==='system1'&&activeTask&&!sameRevision(draft,state.tasks.find(t=>t.operation_id===selected))&&!draft.pending){
      notice('The source or task has changed. Your draft is preserved; reload and review it again.');$('#reload-task').hidden=false;
    }
    const status=receipt?.status||'';
    if(view==='system1'&&draft.pending&&status!==requestStatus)renderDetail();
    requestStatus=status;
    if(view==='overview')renderView();
  }catch(error){notice('Unable to read the workbench state. Your draft is preserved. '+error.message)}
},2500);
refresh().catch(e=>notice(e.message));
