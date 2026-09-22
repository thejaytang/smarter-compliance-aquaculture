import {showPackageDownload} from './export-status.js';
import {valueMarkup} from './collaboration.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const words=v=>String(v??'').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
export function receiptMarkup(entry,items=[]){
 const r=entry.receipt||entry,material=r.material||{},inspection=r.result?.inspection||{},item=items.find(i=>i.id===r.item_id)||{};
 const source=material.source?.source_id||r.source_receipt?.source_id||item.base?.source_id||'Not recorded';
 const title=material.title||inspection.title||item.proposal?.title||item.base?.source_title||item.base?.title||'Adoption receipt';
 const review=material.content_status?words(material.content_status):'Not recorded in this receipt';
 const status=r.choice==='current'?'Kept current':words(r.status)||'Not recorded';
 const fields=[['Material / task',title],['Source',source],['Contributor',r.contributor||item.actor||'Not recorded'],['Adopted by',r.actor||'Not recorded'],['Master revision',material.revision??'Not recorded'],['Recorded at',r.at||'Not recorded'],['Adoption decision',status],['Content review at receipt',review]];
 if(inspection.archive_revision!=null)fields.push(['Checked archive revision',inspection.archive_revision]);
 if(inspection.status)fields.push(['Spot-check status',words(inspection.status)]);
 return `<article class="collab-submission"><h3>${esc(title)}</h3><dl class="collab-values">${fields.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${valueMarkup(value)}</dd></div>`).join('')}</dl><p>Adoption and content review are separate. This receipt records a past decision; it does not update personal work.</p><details><summary>Original receipt details</summary><pre class="collab-value">${esc(JSON.stringify(entry,null,2))}</pre></details></article>`;
}
export function receiptsMarkup(receipts=[],items=[]){return receipts.map(r=>receiptMarkup(r,items)).join('')||'<p>No adoption receipts recorded.</p>';}
export class SubmissionDrawer {
 constructor(w){this.w=w;this.pending=w.collectionPending||=(new Map());}
 owner(){return this.w.state?.actor?.id||'';}
 async open(kind='submission'){
  const actor=this.owner(),data=await this.w.api('/api/collaboration/collection-catalogue?kind='+kind);if(this.owner()!==actor)return;const view=Symbol();this.w.collectionView=view;
  this.w.dialog(`<h2>${kind==='work'?'Distribute selected work':kind==='receipt'?'Return adoption receipts':'My submissions'}</h2><p>${kind==='receipt'?'Select the recorded decisions to return to contributors. Receipts do not alter their saved work.':kind==='work'?'Select sources, source tasks and archived material checks. Originals and common versions are included.':'Select saved source reviews, material drafts and inspection results. Download freezes each selected result; later editing cannot change the package.'}</p>${(data.assignment_changes||[]).map(i=>`<p role="status">${esc(i.task?.title||i.task?.id)}: ${esc(i.message)}</p>`).join('')}<div class="submission-choices">${data.items.map((i,n)=>`<label class="mw-check"><input type="checkbox" data-item-index="${n}"><span>${esc(i.title)}${i.revision!=null?' · saved revision '+i.revision:''}${i.status?' · '+esc(i.status):''}</span></label>`).join('')||'<p>No saved results available. Save progress in the source or material workspace first.</p>'}</div><label>Completed scope and remaining work<textarea id="bundle-summary" rows="3"></textarea></label><button id="bundle-download">Download selected ${kind==='work'?'work':'results'} as one package</button><p id="bundle-status" role="status"></p>${kind==='submission'?`<details><summary>Received adoption receipts</summary>${receiptsMarkup(data.received_receipts||[],data.inbox||[])}</details><details><summary>Frozen package history</summary>${(data.sent||[]).map(p=>`<article><p>${esc(p.at)} · ${p.items.length} items · ${esc(p.summary)}</p><button data-bundle-download="${esc(p.id)}">Download this saved package</button></article>`).join('')||'<p>No frozen packages yet.</p>'}</details>`:''}`,d=>{
   const owner=this.owner(),formKey=owner+':freeze-form:'+kind,controls=[...d.querySelectorAll('[data-item-index]'),d.querySelector('#bundle-summary')],b=d.querySelector('#bundle-download'),status=d.querySelector('#bundle-status');
   const remembered=this.pending.get(formKey);if(remembered){controls.forEach(n=>{if(n.dataset.itemIndex!==undefined){const item=data.items[Number(n.dataset.itemIndex)];n.checked=remembered.payload.items.some(x=>x.type===item.type&&x.key===item.key);}else n.value=remembered.payload.summary;});}
   const lock=value=>{controls.forEach(n=>n.disabled=value);b.disabled=value;};
   let initializing=true;const bindEntry=entry=>{entry.refresh=()=>{if(this.owner()!==owner||this.w.collectionView!==view||d.open===false&&!initializing||d.querySelector('#bundle-status')!==status)return;lock(entry.busy);if(entry.result){showPackageDownload(status,entry.result,{frozen:true});const scope=status.ownerDocument.createElement('span');scope.textContent=' Captured selection: '+entry.payload.items.map(i=>data.items.find(x=>x.type===i.type&&x.key===i.key)?.title||i.key).join('; ')+(entry.payload.summary?' · '+entry.payload.summary:'');status.appendChild(scope);}else if(entry.message)status.textContent=entry.message;};};lock(!!remembered?.busy);if(remembered){bindEntry(remembered);remembered.refresh();}initializing=false;
   b.onclick=async()=>{if(b.disabled)return;const items=[...d.querySelectorAll('[data-item-index]:checked')].map(n=>data.items[Number(n.dataset.itemIndex)]);if(!items.length){status.textContent='Select at least one saved item.';return;}
    const payload={kind,items:items.map(i=>({type:i.type,key:i.key})),summary:d.querySelector('#bundle-summary').value},key=owner+':freeze:'+JSON.stringify(payload);
    const entry=this.pending.get(key)||{payload,request:{...payload,request_id:crypto.randomUUID()}};this.pending.set(key,entry);this.pending.set(formKey,entry);if(entry.busy)return;bindEntry(entry);entry.busy=true;lock(true);status.textContent='Freezing the selected saved items…';
    try{const result=await this.w.api.download('/api/collaboration/collection-export',entry.request);entry.result=result;this.pending.delete(formKey);this.pending.delete(key);
    }catch(e){entry.message=e.message+' Retry this selection to recover the same frozen package.';}finally{entry.busy=false;if(this.owner()===owner)entry.refresh?.();}
   };
   d.querySelectorAll('[data-bundle-download]').forEach(b=>b.onclick=()=>this.w.api.download('/api/collaboration/collection-download',{id:b.dataset.bundleDownload}).then(result=>showPackageDownload(d.querySelector('#bundle-status'),result)).catch(e=>d.querySelector('#bundle-status').textContent=e.message));
  });
 }
 async inbox(){const data=await this.w.api('/api/collaboration/collection-catalogue');this.w.dialog(`<h2>Submitted tasks and inspections</h2><p>Each item has its own receipt. Apply related source decisions before material results. Incomplete or outdated items remain pending.</p>${(data.inbox||[]).map(i=>`<article><h3>${esc(i.proposal?.title||i.base?.source_title||i.base?.operation_id||i.id)}</h3><p>${esc(i.actor)} · ${esc(i.status)}</p><button data-bundle-item="${esc(i.id)}" ${i.status==='adopted'?'disabled':''}>Compare task result</button></article>`).join('')||'<p>No imported task results.</p>'}<button id="bundle-receipts">Download selected adoption receipts</button><details><summary>Per-item adoption receipts</summary>${receiptsMarkup(data.receipts||[],data.inbox||[])}</details>`,d=>{d.querySelector('#bundle-receipts').onclick=()=>this.open('receipt');d.querySelectorAll('[data-bundle-item]').forEach(b=>b.onclick=async()=>{try{await this.compare(b.dataset.bundleItem);}catch(e){this.w.message(e.message);}});});}
 async compare(id){
  const owner=this.owner(),key=owner+':adopt:'+id,old=this.pending.get(key),preview=old?.preview||await this.w.api('/api/collaboration/collection-preview',{item_id:id});
  if(this.owner()!==owner)return;
  const view=Symbol();this.w.collectionView=view;
  this.w.dialog('<div id="bundle-comparison"></div>',d=>{
   let initializing=true;const comparisonRoot=d.querySelector('#bundle-comparison'),current=()=>this.w.collectionView===view&&this.owner()===owner&&(initializing||d.open!==false)&&d.querySelector('#bundle-comparison')===comparisonRoot;let p=preview,refreshing=false,outdated=false;
   const draw=()=>{
    if(!current())return;const pending=this.pending.get(key);if(pending)pending.refresh=()=>{if(!current())return;outdated=!!pending.expired;draw();d.querySelector('#bundle-adopt-status').textContent=pending.message;if(pending.expired)d.querySelector('#bundle-refresh').hidden=false;};const locked=!!pending||outdated,terminal=pending?.result?.status==='adopted';
    d.querySelector('#bundle-comparison').innerHTML=`<h2>Review task result</h2><p>${esc(p.item.actor)} · ${p.conflict?'Task changed since the shared starting version. Keep current or record a new task using this evidence.':'Current task matches the assigned starting version.'}</p><div class="collab-comparison"><section><h3>Current task</h3>${valueMarkup(p.current)}</section><section><h3>Submitted result</h3>${valueMarkup(p.proposed)}</section></div><details><summary>Shared starting version</summary>${valueMarkup(p.base)}</details><label class="mw-check"><input id="bundle-confirm" type="checkbox" ${locked?'disabled':''}>I reviewed the scope, evidence and current task. Apply only this selected decision.</label><button data-bundle-choice="current" ${locked?'disabled':''}>Keep current</button><button data-bundle-choice="incoming" ${locked||p.conflict?'disabled':''}>Adopt submitted result</button><p id="bundle-adopt-status" role="status">${esc(pending?.message||'')}</p>${pending&&!terminal?`<button id="bundle-adopt-retry" ${pending.busy?'disabled':''}>Retry ${pending.request.choice==='current'?'Keep current':'Adopt submitted result'}</button>`:''}<button id="bundle-refresh" hidden>Refresh comparison</button>`;
    d.querySelectorAll('[data-bundle-choice]').forEach(b=>b.onclick=()=>{
     if(b.disabled||this.pending.has(key)||!d.querySelector('#bundle-confirm').checked||!current())return;
     const entry={preview:p,request:{item_id:id,expected_current_digest:p.current_digest,choice:b.dataset.bundleChoice,explicit_confirmation:true,request_id:crypto.randomUUID()}};this.pending.set(key,entry);return decide(entry);
    });
    const retry=d.querySelector('#bundle-adopt-retry');if(retry)retry.onclick=()=>decide(pending);
    d.querySelector('#bundle-refresh').onclick=async()=>{
     if(refreshing||this.pending.has(key)||!current())return;refreshing=true;d.querySelector('#bundle-refresh').disabled=true;
     try{const fresh=await this.w.api('/api/collaboration/collection-preview',{item_id:id});if(!current())return;p=fresh;outdated=false;draw();}
     catch(e){if(current()){d.querySelector('#bundle-adopt-status').textContent=e.message+' The previous comparison is retained.';d.querySelector('#bundle-refresh').disabled=false;}}
     finally{refreshing=false;}
    };
   };
   const decide=async entry=>{
    if(entry.busy||entry.result?.status==='adopted'||!current())return;entry.busy=true;entry.message='Recording the selected decision…';draw();
    try{const result=await this.w.api('/api/collaboration/collection-adopt',entry.request);entry.result=result;entry.message=result.status==='adopted'?'Selected decision recorded; the receipt preserves contributor and adopter.':'This item remains pending: '+(result.result?.message||result.status)+'. Retry the same decision to recover its receipt.';}
    catch(e){entry.message=e.message;if(e.definitive){this.pending.delete(key);entry.expired=/Task changed after comparison/i.test(e.message);outdated=entry.expired;}}
    finally{entry.busy=false;entry.refresh?.();}
   };
   draw();initializing=false;
  });
 }
}
