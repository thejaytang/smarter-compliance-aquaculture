import {diffWordsWithSpace} from '../assets/vendor/markdown/tools.mjs';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stable=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x,2);
export function versionTextDiff(saved='',local=''){
 const parts=diffWordsWithSpace(saved,local,{timeout:80})||[{value:saved,removed:true},{value:local,added:true}];
 return parts.map(p=>p.added?`<ins class="md-added">${esc(p.value)}</ins>`:p.removed?`<del class="md-removed">${esc(p.value)}</del>`:p.value.length>420?`<span>${esc(p.value.slice(0,140))}</span><details class="version-unchanged"><summary>${p.value.length-280} unchanged characters</summary>${esc(p.value.slice(140,-140))}</details><span>${esc(p.value.slice(-140))}</span>`:esc(p.value)).join('');
}
const wording=b=>!b?'':b.markdown?.source??b.markdown_source??b.text??'';
export function versionComparison(saved,local){
 const before=new Map((saved.blocks||[]).map(b=>[b.id,b])),after=new Map((local.blocks||[]).map(b=>[b.id,b]));
 const ids=[...new Set([...before.keys(),...after.keys()])],changed=ids.filter(id=>stable(before.get(id))!==stable(after.get(id)));
 const order=(saved.blocks||[]).map(b=>b.id),next=(local.blocks||[]).map(b=>b.id);
 const sameIds=order.length===next.length&&order.every(id=>after.has(id));
 const moved=sameIds&&order.some((id,i)=>id!==next[i]);
 return `<p><strong>${changed.length} changed passages</strong> · ${ids.length-changed.length} unchanged. <del class="md-removed">Saved version only</del> <ins class="md-added">Local version only</ins></p>${moved?`<details><summary>Passage order changed</summary><p>Saved: ${esc(order.join(' → '))}</p><p>Local: ${esc(next.join(' → '))}</p></details>`:''}${changed.map(id=>{
  const a=before.get(id),b=after.get(id),meta=x=>Object.fromEntries(Object.entries(x||{}).filter(([k])=>!['text','markdown','markdown_source','id'].includes(k)));
  return `<article class="version-passage"><h3>${esc(b?.numbering||a?.numbering||id)}${!a?' · Added passage':!b?' · Removed passage':''}</h3><div class="version-diff">${versionTextDiff(wording(a),wording(b))}</div>${stable(meta(a))!==stable(meta(b))?`<details><summary>Structure, table or source links changed</summary><div class="version-diff">${versionTextDiff(stable(meta(a)),stable(meta(b)))}</div></details>`:''}</article>`;
 }).join('')}${stable(saved.issues||[])!==stable(local.issues||[])?`<details><summary>Review notes differ · unresolved saved findings remain open</summary><div class="version-diff">${versionTextDiff(stable(saved.issues||[]),stable(local.issues||[]))}</div></details>`:''}${!changed.length&&!moved?'<p>The passage contents and order are identical.</p>':''}`;
}
