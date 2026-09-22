import {diffWordsWithSpace} from '../assets/vendor/markdown/tools.mjs';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stable=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x,2);
export function versionTextDiff(saved='',local=''){
 const parts=diffWordsWithSpace(saved,local,{timeout:80})||[{value:saved,removed:true},{value:local,added:true}];
 return parts.map(p=>p.added?`<ins class="md-added">${esc(p.value)}</ins>`:p.removed?`<del class="md-removed">${esc(p.value)}</del>`:p.value.length>420?`<span>${esc(p.value.slice(0,140))}</span><details class="version-unchanged"><summary>${p.value.length-280} unchanged characters</summary>${esc(p.value.slice(140,-140))}</details><span>${esc(p.value.slice(-140))}</span>`:esc(p.value)).join('');
}
const wording=b=>!b?'':b.markdown?.source??b.markdown_source??b.text??'';
export function versionComparison(saved,local,scope=[]){
 const before=new Map((saved.blocks||[]).map(b=>[b.id,b])),after=new Map((local.blocks||[]).map(b=>[b.id,b]));
 const ids=[...new Set([...before.keys(),...after.keys()])],changed=ids.filter(id=>stable(before.get(id))!==stable(after.get(id)));
 const order=(saved.blocks||[]).map(b=>b.id),next=(local.blocks||[]).map(b=>b.id);
 const survivors=order.filter(id=>after.has(id)),nextSurvivors=next.filter(id=>before.has(id)),moved=survivors.some((id,i)=>id!==nextSurvivors[i]);
 const orderMarkup=(ids,blocks)=>ids.map(id=>`<li>${esc((wording(blocks.get(id))||blocks.get(id)?.type||'Passage').slice(0,160))} <small>(${esc(id)})</small></li>`).join('');
 const declarations=stable([saved.checked_scope,saved.association_reviewed])!==stable([local.checked_scope,local.association_reviewed]);
 const scopes=new Map([...scope,...(saved.scope||[])].map(s=>[s.id,s.label||s.id]));
 const reviewMarkup=doc=>`<p>Checked original ranges: ${doc.checked_scope?doc.checked_scope.length?doc.checked_scope.map(id=>esc(scopes.get(id)||id)+(scopes.get(id)&&scopes.get(id)!==id?' ('+esc(id)+')':'')).join('; '):'None recorded':'Not recorded'}</p><p>Association review declaration: ${doc.association_reviewed===true?'Recorded':doc.association_reviewed===false?'Not recorded as complete':'Not supplied'}</p>`;
 return `<p><strong>${changed.length} changed passages</strong> · ${ids.length-changed.length} unchanged. <del class="md-removed">Saved version only</del> <ins class="md-added">Local version only</ins></p>${moved?`<details><summary>Passage order changed</summary><p>Relative order of surviving passages changed.</p><h4>Saved order</h4><ol>${orderMarkup(order,before)}</ol><h4>Local order</h4><ol>${orderMarkup(next,after)}</ol></details>`:''}${changed.map(id=>{
  const a=before.get(id),b=after.get(id),meta=x=>Object.fromEntries(Object.entries(x||{}).filter(([k])=>!['text','markdown','markdown_source','id'].includes(k)));
  return `<article class="version-passage"><h3>${esc(b?.numbering||a?.numbering||id)}${!a?' · Added passage':!b?' · Removed passage':''}</h3><div class="version-diff">${versionTextDiff(wording(a),wording(b))}</div>${stable(meta(a))!==stable(meta(b))?`<details><summary>Structure, table or source links changed</summary><div class="version-diff">${versionTextDiff(stable(meta(a)),stable(meta(b)))}</div></details>`:''}</article>`;
 }).join('')}${stable(saved.issues||[])!==stable(local.issues||[])?`<details><summary>Review notes differ · unresolved saved findings remain open</summary><div class="version-diff">${versionTextDiff(stable(saved.issues||[]),stable(local.issues||[]))}</div></details>`:''}${declarations?`<details><summary>Human review declarations differ</summary><p>These recorded declarations are separate from content. Choosing a version still follows the saved review checks.</p><div class="collab-comparison"><section><h4>Saved declarations</h4>${reviewMarkup(saved)}</section><section><h4>Local declarations</h4>${reviewMarkup(local)}</section></div></details>`:''}${!changed.length&&!moved?'<p>The passage contents and order are identical.</p>':''}`;
}
