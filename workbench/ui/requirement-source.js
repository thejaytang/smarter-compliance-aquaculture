import {semanticClass} from './markdown-content.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const leaves=g=>g?g.slice(1).flatMap(x=>Array.isArray(x)?leaves(x):[x]):[];
export function sourcePreview(doc){
 const text=Array.from(doc.text),spans=[];
 for(const [id,u] of Object.entries(doc.units||{})){
  const offset=doc.spans?.[id]?.[0]??0;
  for(const [field,[a,b]] of Object.entries(doc.field_spans?.[id]||{}))spans.push({field,start:offset+a,end:offset+b,id});
  for(const field of ['conditions','exceptions','subrequirement'])for(const child of leaves(u[field]))if(doc.spans?.[child]){const [start,end]=doc.spans[child];spans.push({field,start,end,id:child,owner:id});}
 }
 const stops=[...new Set([0,text.length,...spans.flatMap(s=>[s.start,s.end])])].sort((a,b)=>a-b);
 const content=stops.slice(0,-1).map((start,i)=>{
  const end=stops[i+1],active=spans.filter(s=>s.start<=start&&s.end>=end).sort((a,b)=>(b.end-b.start)-(a.end-a.start));
  let html=esc(text.slice(start,end).join(''));if(!active.length)return html;
  const nested=active.every((s,j)=>!j||(s.start>=active[j-1].start&&s.end<=active[j-1].end&&(s.start>active[j-1].start||s.end<active[j-1].end)));
  const label=active.map(s=>`${s.field} · ${doc.labels?.[s.id]||s.id}${s.owner?' in '+(doc.labels?.[s.owner]||s.owner):''}`).join('; ');
  html=`<span class="semantic ${nested?semanticClass(active.at(-1).field):'semantic-overlap'}" title="${esc(label)}" tabindex="0" aria-label="${esc(label)}">${html}</span>`;
  if(nested)for(const s of active.slice(0,-1).reverse())html=`<span class="annotation-outer ${semanticClass(s.field)}">${html}</span>`;
  return html;
 }).join('');
 const groups=spans.filter(s=>s.owner).map(s=>`<span class="annotation-relation semantic ${semanticClass(s.field)}">${esc(s.field)} · ${esc(doc.labels?.[s.id]||s.id)} in ${esc(doc.labels?.[s.owner]||s.owner)}</span>`).join('');
 return `<span class="rq-source-preview">${content}</span>${groups?`<span class="rq-source-groups">${groups}</span>`:''}`;
}
