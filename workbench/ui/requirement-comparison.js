// Readable, escaped projections of saved Requirement bundles. No editable JSON.
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const quantity=q=>Array.isArray(q)?`[${q[0]}, ${q[1]}]`:q??'Not set';
export function requirementComparison(value){
 if(!/^requirement-delivery\/[1234]$/.test(value?.schema||''))return null;
 const sessions=value.sessions||[],labels=new Map();
 sessions.forEach((s,i)=>{for(const id of Object.keys(s.document.units||{}))labels.set(id,`R${i+1}`);});
 function tree(n,depth=0){
  if(!n||depth>25)return '';
  if(n.kind==='fragment')return `<li><strong>${esc(n.role)}</strong>: ${esc(n.text)}</li>`;
  if(n.kind==='reference')return `<li>${esc(n.role)} → ${esc(labels.get(n.target_id)||n.target_id)}</li>`;
  return `<li><strong>${n.kind==='group'?'Group · '+esc(n.role):'Group'}</strong>${n.kind==='group'?` · Quantity ${esc(quantity(n.quantity))}`:''}${n.negated?' · NOT':''}${n.relationship?` · Relationship: ${esc(n.relationship.text)}`:''}<ul>${(n.children||[]).map(c=>tree(c,depth+1)).join('')}</ul></li>`;
 }
 function legacy(group,field){
  if(!Array.isArray(group))return '';
  return `<li><strong>${esc(field)}</strong> · Quantity ${esc(quantity(group[0]))}<ul>${group.slice(1).map(c=>Array.isArray(c)?legacy(c,field):`<li>Link → ${esc(labels.get(c)||c)}</li>`).join('')}</ul></li>`;
 }
 return `<div class="sync-requirements"><p>${sessions.length} source passages · ${(value.interpretations||[]).length} interpretations</p><details open><summary>Inspect this Requirement version</summary>${sessions.map((s,i)=>{const d=s.document;return `<section><h5>R${i+1} · ${esc(d.chapter||'Source passage')} · revision ${d.revision}${d.deleted?' · Removed':''}</h5><p>${esc(d.edited_by||d.created_by||value.owners?.[d.id]||value.actor)} · ${esc(d.saved_at||'Time not recorded')}</p><blockquote>${esc(d.text)}</blockquote>${Object.entries(d.units||{}).map(([uid,u])=>{const n=d.structures?.[uid];return n?`<ul>${(n.children||[]).map(c=>tree(c)).join('')}</ul>`:`<ul>${['Subject','Modal Verb','Main Verb','Object'].filter(k=>u[k]).map(k=>`<li><strong>${k}</strong>: ${esc(u[k])}</li>`).join('')}${['conditions','exceptions','subrequirement'].map(k=>legacy(u[k],k)).join('')}</ul>`;}).join('')}</section>`;}).join('')}${(value.interpretations||[]).map(x=>{const d=x.history.find(h=>h.document.revision===x.head_revision)?.document;return `<details><summary>${esc(labels.get(x.unit_id)||x.unit_id)} · Interpretation</summary>${Object.entries(d?.fields||{}).map(([k,f])=>`<p><strong>${esc(k.replaceAll('_',' '))}</strong>: ${esc(f.value||f.absence_reason||'Unresolved')}</p>`).join('')}</details>`;}).join('')}</details></div>`;
}
