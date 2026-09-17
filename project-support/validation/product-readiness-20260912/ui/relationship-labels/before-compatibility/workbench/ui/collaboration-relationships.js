const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const parts=path=>String(path||'').split('/').slice(1).map(p=>p.replaceAll('~1','/').replaceAll('~0','~'));
export function relationshipKind(diff){const p=parts(diff.path);return p.length===3&&p[0]==='blocks'&&['parent_id','dependencies'].includes(p[2])?p[2]:null;}
export const relationshipTitle=kind=>kind==='parent_id'?'Under heading':'Related content';
const blockLabel=b=>[b.numbering,b.text?.trim()||`${b.type||'Content'} (text not recorded)`].filter(Boolean).join(' · ').replace(/\s+/g,' ').slice(0,180);
const details=value=>`<details><summary>Reference details</summary><pre class="collab-value">${esc(JSON.stringify(value,null,2))}</pre></details>`;

export function relationshipValueMarkup(value,{kind,present=true,context={}}){
 if(!present)return '<em>Not present</em>';
 if(kind==='parent_id'&&(value===null||value===''))return '<span>Top level</span>'+details(value);
 if(kind==='dependencies'&&Array.isArray(value)&&!value.length)return '<span>No related content</span>'+details(value);
 const references=kind==='parent_id'?[value]:Array.isArray(value)?value:[value];
 return references.map(id=>{
  const b=typeof id==='string'&&Object.hasOwn(context,id)?context[id]:null;
  const valid=b&&(kind!=='parent_id'||b.type==='heading');
  return `<p>${valid?esc(blockLabel(b)):kind==='parent_id'?'Referenced heading not found in this version':'Referenced content not found in this version'}</p>`;
 }).join('')+details(value);
}

export function relationshipOptions(diff,blocks){
 const owner=parts(diff.path)[1],position=blocks.findIndex(b=>b.id===owner),block=blocks[position],kind=relationshipKind(diff);
 if(!block)throw Error('The content being edited is no longer in the combined version. Reopen the comparison.');
 return blocks.map((b,i)=>({block:b,position:i})).filter(({block:b,position:i})=>b.id!==owner&&(kind!=='parent_id'||b.type==='heading'&&i<position&&(block.type!=='heading'||b.level<block.level)));
}

export function relationshipEditor(diff,value,blocks){
 const kind=relationshipKind(diff),options=relationshipOptions(diff,blocks),selected=kind==='parent_id'?(value?[value]:[]):Array.isArray(value)?value:[],available=new Set(options.map(o=>o.block.id)),missing=selected.filter(id=>!available.has(id));
 return `<p>Choose from the combined content. This changes a reference only; it does not create or restore content.</p>${missing.length?'<p role="alert">Some referenced content is unavailable in the combined version. Choose an available replacement or remove that link.</p>':''}<label>${relationshipTitle(kind)}<select id="collab-relationship-value" ${kind==='dependencies'?`multiple size="${Math.min(8,Math.max(3,options.length+missing.length))}"`:''}>${kind==='parent_id'?`<option value="" ${!selected.length?'selected':''}>Top level</option>`:''}${missing.map(id=>`<option value="${esc(id)}" selected>Referenced ${kind==='parent_id'?'heading':'content'} unavailable</option>`).join('')}${options.map(({block:b,position})=>`<option value="${esc(b.id)}" ${selected.includes(b.id)?'selected':''}>${position+1} · ${esc(blockLabel(b))}</option>`).join('')}</select></label>${kind==='dependencies'?'<p>Select one or more related blocks.</p><button type="button" id="collab-relationship-clear">Clear related content</button>':''}${details(value)}<p id="collab-relationship-error" role="status" aria-live="polite"></p>`;
}

export function collectRelationshipValue(root,diff,blocks){
 const kind=relationshipKind(diff),input=root.querySelector('#collab-relationship-value'),allowed=new Set(relationshipOptions(diff,blocks).map(o=>o.block.id));
 const value=kind==='parent_id'?input.value||null:Array.from(input.selectedOptions,o=>o.value),selected=kind==='parent_id'?(value?[value]:[]):value;
 if(selected.some(id=>!allowed.has(id)))throw Error('A selected heading or related block is no longer available in the combined content. Choose an available item or remove the link before saving.');
 return value;
}
