import {semanticClass} from './markdown-content.js';
import {quantityPreset,quantityMode,quantityPreview,quantityRange} from './quantity.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const roles=['Subject','Modal Verb','Main Verb','Object','conditions','subrequirement'];
export function treeNodes(tree){return [tree,...(tree.children||[]).flatMap(treeNodes)];}
export function treeText(node,units={},trees={},seen=new Set()){
 if(node.kind==='fragment')return node.text;
 if(node.kind==='reference'){
  const u=units[node.target_id];if(!u)return `Unresolved reference ${node.target_id}`;
  if(seen.has(node.target_id))return u.text;
  return trees[node.target_id]?.children?.length?u.text+' [ '+treeText(trees[node.target_id],units,trees,new Set([...seen,node.target_id]))+' ]':u.text;
 }
 const parts=node.children.map(n=>treeText(n,units,trees,seen));
 if(node.kind==='clause')return '{ '+node.children.map((n,i)=>`${n.role}: ${parts[i]}`).join('; ')+' }';
 const q=node.quantity===null?'QC unresolved':quantityPreview(node.quantity);
 return `${node.negated?'NOT ':''}(${q} of ${node.children.length}: ${parts.join(' | ')})`;
}
export function treeSource(tree,text,bounds,referenceSpans={}){
 const chars=Array.from(text),[a,b]=bounds||[0,chars.length];
 const spans=treeNodes(tree).map(n=>n.kind==='reference'&&referenceSpans[n.target_id]?{...n,span:referenceSpans[n.target_id]}:n).filter(n=>n.role&&n.role!=='requirements'&&n.span&&n.span[0]>=a&&n.span[1]<=b);
 const stops=[...new Set([a,b,...spans.flatMap(n=>n.span)])].sort((x,y)=>x-y);
 return stops.slice(0,-1).map((start,i)=>{
  const end=stops[i+1],active=spans.filter(n=>n.span[0]<=start&&n.span[1]>=end),word=esc(chars.slice(start,end).join(''));
  if(!active.length)return word;
  const nested=active.slice().sort((x,y)=>(y.span[1]-y.span[0])-(x.span[1]-x.span[0]));
  const overlap=nested.some((n,j)=>j&&!(n.span[0]>=nested[j-1].span[0]&&n.span[1]<=nested[j-1].span[1]));
  return `<span class="semantic ${overlap?'semantic-overlap':semanticClass(nested.at(-1).role)}" title="${esc(active.map(n=>n.role+' · '+n.id).join('; '))}">${word}</span>`;
 }).join('');
}
const control=(action,text,attrs='')=>`<button type="button" data-straction="${action}" ${attrs}>${text}</button>`;
export class StructureEditor{
 constructor(editor){this.e=editor;this.closed=new Set();this.qcOpen=new Set();this.selection=null;}
 tree(uid){return this.e.doc.structures?.[uid]||this.e.doc.structure_views?.[uid];}
 labels(tree){let g=0,f=0;return Object.fromEntries(treeNodes(tree).map(n=>[n.id,n.kind==='fragment'?`F${++f}`:n.kind==='reference'?this.e.label(n.target_id):`G${++g}`]));}
 unitMarkup(u,complete,inline){
  const e=this.e,done=e.doc.done.includes(u.id),tree=this.tree(u.id),disabled=e.locked||complete||done;
  return `<details class="rq-unit${inline?' rq-inline-condition':''}" data-unit="${esc(u.id)}" aria-current="${u.id===e.selected}" ${!e.closedUnits.has(u.id)?'open':''}><summary data-rq="select-unit" data-id="${esc(u.id)}" data-toggle="true"><strong>${esc(e.label(u.id))}</strong><span class="rq-unit-preview">${esc(u.text.slice(0,100))}</span><span class="rq-badge">${done?'Finished':'Editing'}</span></summary><div class="rq-unit-body rq-structure-editor">${done&&!complete?'<button type="button" data-rq="reopen">Continue decomposing</button>':''}${this.nodeMarkup(tree,u,tree,this.labels(tree),disabled,true)}${!complete?`<div class="rq-unit-finish"><button type="button" data-rq="done" ${disabled?'disabled':''}>Finish &amp; collapse</button></div>`:''}</div></details>`;
 }
 sourceMarkup(node,u,tree,disabled){
  const span=node.span||[0,Array.from(u.text).length],allowed=node.kind==='clause'?(this.e.doc.roles?.[u.id]==='condition'?['conditions']:roles):[node.role];
  const offset=this.e.doc.spans?.[u.id]?.[0]||0,referenceSpans=Object.fromEntries(Object.entries(this.e.doc.spans||{}).map(([id,span])=>[id,span.map(n=>n-offset)]));
  return `<div class="rq-group-source" data-source-node="${esc(node.id)}" data-source-owner="${esc(u.id)}" data-source-start="${span[0]}"><div class="rq-selectable-source" data-structure-source tabindex="0" contenteditable="true" spellcheck="false" role="textbox" aria-readonly="true" aria-label="Original text for ${esc(node.id)}">${treeSource(tree,u.text,span,referenceSpans)}</div>${!disabled?`<div class="rq-selection-tools" data-selection-tools hidden role="toolbar" aria-label="Assign selected source text">${allowed.map(role=>control(role==='subrequirement'?'show-link':'add',esc(role),`data-field="${role}" class="semantic ${semanticClass(role)}"`)).join('')}${control('add-group','Group')}</div>`:''}</div>`;
 }
 nodeMarkup(node,u,tree,labels,disabled,root=false){
  const id=esc(node.id),label=labels[node.id],readonly=disabled?'disabled':'',text=node.span?Array.from(u.text).slice(...node.span).join(''):'';
  if(node.kind==='fragment')return `<div class="rq-tree-leaf semantic ${semanticClass(node.role)}" data-structure-node="${id}" data-owner="${u.id}"><span class="rq-tree-id">${label}</span><span>${esc(node.text)}</span>${!disabled?control('decompose','Decompose',` ${node.span?'':'disabled title="Source position is unresolved"'}`)+control('remove','Remove'):''}</div>`;
  if(node.kind==='reference'&&this.e.doc.roles?.[node.target_id]==='condition'&&this.e.doc.units[node.target_id])return `<div class="rq-tree-reference" data-structure-node="${id}" data-owner="${u.id}">${this.unitMarkup(this.e.doc.units[node.target_id],disabled,true)}${!disabled?control('remove','Remove reference'):''}</div>`;
  if(node.kind==='reference')return `<div class="rq-tree-leaf rq-tree-reference" data-structure-node="${id}" data-owner="${u.id}"><button type="button" data-rq="decompose" data-id="${esc(node.target_id)}">${esc(this.e.label(node.target_id))}</button><span>${esc(this.e.unitText(node.target_id))}</span>${!disabled?control('remove','Remove'):''}</div>`;
  const group=node.kind==='group',kind=group?node.role:'Group',summary=`<strong>${label}</strong><span>${esc(kind)}</span>${node.negated?'<b class="rq-not-label">NOT</b>':''}${group?control('show-qc',`QC ${node.quantity===null?'?':quantityPreview(node.quantity)}`,'class="rq-tree-count" title="Show quantity controls"'):''}${!root&&text?`<span class="rq-tree-summary">${esc(text)}</span>`:''}`;
  const children=node.children.map(child=>`<li>${group&&!disabled?`<input type="checkbox" data-structure-pick="${esc(child.id)}" aria-label="Select ${labels[child.id]} in ${label}">`:''}${this.nodeMarkup(child,u,tree,labels,disabled)}</li>`).join('');
  return `<${root?'section':'details'} class="rq-tree-node ${group?'rq-tree-group semantic '+semanticClass(node.origin_role||node.role):'rq-tree-clause'}" data-structure-node="${id}" data-owner="${u.id}" ${!root&&!this.closed.has(node.id)?'open':''}>${root?'':`<summary>${summary}</summary>`}<div class="rq-tree-body">${node.span?this.sourceMarkup(node,u,tree,disabled):''}${root&&!disabled?'<p class="rq-hint">Select original wording to add a field or Group. Shared conditions stay in the enclosing Group.</p>':''}${group&&(node.children.length>1||node.quantity!==1||this.qcOpen.has(node.id))?this.qcMarkup(node,disabled):''}${group?`<div class="rq-tree-actions">${control('not',node.negated?'NOT on':'NOT',`aria-pressed="${node.negated}" title="Negate this entire group" ${readonly}`)}${!disabled?control('group','Group selected')+control('ungroup','Ungroup',`title="Expand an All group within another All group"`):''}</div>`:''}${!root&&!disabled?control('remove','Remove group','class="rq-remove-group"'):''}<ol class="rq-tree-children">${children}</ol>${!node.children.length?'<p class="rq-blank">Select wording above to add items.</p>':''}${!disabled&&this.e.doc.roles?.[u.id]!=='condition'&&(node.kind==='clause'||['requirements','subrequirement'].includes(node.role))?this.linkMarkup(u):''}</div></${root?'section':'details'}>`;
 }
 linkMarkup(u){const choices=this.e.completeRequirements(u.id);return `<details class="rq-reference-picker"><summary>Reference a Requirement</summary><div class="rq-tree-link"><label>Subrequirement<select data-structure-reference aria-label="Requirement to reference">${choices.map(v=>`<option value="${v.id}">${esc(this.e.label(v.id))} · ${esc(v.text.slice(0,70))}</option>`).join('')||'<option value="">No other Requirement</option>'}</select></label>${control('link','Link Requirement',choices.length?'':'disabled')}</div></details>`;}
 qcMarkup(node,disabled){
  const count=node.children.length,q=node.quantity,mode=quantityMode(q,count),values=Array.isArray(q)?q:[q??'',q??''];
  return `<strong class="rq-qc-title" title="Quantitative constraints">QC</strong><div class="rq-qc-row" data-rq-qc data-structure-qc data-count="${count}"><output data-rq-preview class="rq-qc-preview" aria-live="polite">${q===null?'Set QC':quantityPreview(q)}</output><div class="rq-quantity-presets">${[['all','All'],['any','Any'],['one','Only'],['not-all','Not All']].map(([preset,label])=>control('preset',label,`data-preset="${preset}" title="${preset==='not-all'?'At least one, fewer than all':preset==='all'?`K = ${count}`:preset==='any'?`[1, ${count}]`:'K = 1'}" aria-pressed="${mode===preset}" ${disabled||!count||(preset==='not-all'&&count<2)?'disabled':''}`)).join('')}</div><span class="rq-qc-range-label">MIN-MAX:</span><input data-rq-min aria-label="Minimum" inputmode="numeric" pattern="[0-9]*" value="${values[0]}" ${disabled||!count?'disabled':''}><span>-</span><input data-rq-max aria-label="Maximum" inputmode="numeric" pattern="[0-9]*" value="${values[1]}" ${disabled||!count?'disabled':''}></div><small class="rq-qc-error" data-qc-error hidden role="status"></small>`;
 }
 bind(host){
  host.querySelectorAll?.('[data-structure-source]').forEach(source=>{
   source.onbeforeinput=event=>event.preventDefault();source.onpaste=event=>event.preventDefault();source.oncut=event=>event.preventDefault();source.ondrop=event=>event.preventDefault();
   const capture=()=>{
    const selection=window.getSelection();if(!selection?.rangeCount||selection.isCollapsed)return;
    const range=selection.getRangeAt(0);if(!source.contains(range.startContainer)||!source.contains(range.endContainer))return;
    const prefix=range.cloneRange();prefix.selectNodeContents(source);prefix.setEnd(range.startContainer,range.startOffset);
    const container=source.closest('[data-source-node]'),start=Number(container.dataset.sourceStart)+Array.from(prefix.toString()).length,end=start+Array.from(range.toString()).length;
    this.selection={unit_id:container.dataset.sourceOwner,node_id:container.dataset.sourceNode,start,end};
    host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=n.parentElement!==container);
   };source.onmouseup=capture;source.onkeyup=capture;
  });
  host.querySelectorAll?.('[data-selection-tools]').forEach(toolbar=>toolbar.onmousedown=e=>{if(e.target.closest('button'))e.preventDefault();});
  host.querySelectorAll?.('details[data-structure-node]').forEach(node=>node.ontoggle=()=>{if(!node.isConnected)return;if(node.open)this.closed.delete(node.dataset.structureNode);else this.closed.add(node.dataset.structureNode);});
  host.querySelectorAll?.('[data-structure-qc]').forEach(row=>this.bindQC(row));
 }
 bindQC(row){
  const e=this.e,node=row.closest('[data-structure-node]'),uid=node.dataset.owner,id=node.dataset.structureNode,key='tree:'+uid+':'+id;
  const model=treeNodes(this.tree(uid)).find(n=>n.id===id),inputs=[row.querySelector('[data-rq-min]'),row.querySelector('[data-rq-max]')],output=row.querySelector('[data-rq-preview]'),error=row.parentElement.querySelector('[data-qc-error]'),count=model.children.length;
  const validate=()=>{try{quantityRange(...inputs.map(i=>i.value),count);error.hidden=true;inputs.forEach(i=>i.removeAttribute('aria-invalid'));return true;}catch(err){error.textContent=err.message;error.hidden=false;inputs.forEach(i=>i.setAttribute('aria-invalid','true'));return false;}};
  const preview=()=>{output.textContent=`[${inputs[0].value||'…'}, ${inputs[1].value||'…'}]`;validate();};
  if(e.quantityDrafts.has(key)){inputs.forEach((n,i)=>n.value=e.quantityDrafts.get(key)[i]);preview();}
  row.commitQuantity=async()=>{
   if(!e.quantityDrafts.has(key))return true;
   if(e.locked||!validate())return false;
   const value=quantityRange(...inputs.map(i=>i.value),count);
   if(JSON.stringify(value)!==JSON.stringify(model.quantity)){
    const ok=await e.step('structure',{unit_id:uid,node_id:id,operation:'quantity',quantity:value});if(!ok)return false;
   }
   e.quantityDrafts.delete(key);e.render(true);return true;
  };
  inputs.forEach(input=>{input.dataset.previous=input.value;input.onbeforeinput=event=>{if(event.data&&!/^\d+$/.test(event.data))event.preventDefault();};input.oninput=()=>{if(!/^\d*$/.test(input.value)){input.value=input.dataset.previous;return;}if(input.value!=='')input.value=String(Math.min(count,Number(input.value)));input.dataset.previous=input.value;e.quantityDrafts.set(key,inputs.map(i=>i.value));preview();e.m.updateNavigationLock?.();};input.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();void row.commitQuantity();}if(event.key==='Escape'){event.preventDefault();e.quantityDrafts.delete(key);e.render(true);}};});
  row.onfocusout=event=>{if(row.contains(event.relatedTarget)||event.relatedTarget?.closest('[data-rq],[data-straction]'))return;void row.commitQuantity();};
 }
 async action(button){
  const e=this.e;if(button.disabled)return;
  const element=button.closest('[data-structure-node]'),uid=element.dataset.owner,id=element.dataset.structureNode,action=button.dataset.straction;
  if(action==='show-link'){const picker=element.querySelector(':scope > .rq-tree-body > .rq-reference-picker');if(picker){picker.open=true;picker.querySelector('select')?.focus();}return;}
  if(action==='show-qc'){if(this.qcOpen.has(id))this.qcOpen.delete(id);else this.qcOpen.add(id);e.render(true);return;}
  if(e.locked)return;
  for(const row of e.host.querySelectorAll('[data-rq-qc]')){if(action==='preset'&&row.contains(button))continue;if(row.commitQuantity&&!(await row.commitQuantity()))return;}
  const model=treeNodes(this.tree(uid)).find(n=>n.id===id);if(!model)return;
  let request={unit_id:uid,node_id:id,operation:action};
  if(['add','add-group'].includes(action)){
   if(!this.selection||this.selection.unit_id!==uid||this.selection.node_id!==id)throw Error('Select the original wording in this group first.');
   request={...request,...this.selection,field:button.dataset.field};
  }
  if(action==='not')request.negated=!model.negated;
  if(action==='preset'){request.operation='quantity';request.quantity=quantityPreset(button.dataset.preset,model.children.length);e.quantityDrafts.delete('tree:'+uid+':'+id);}
  if(action==='group')request.selected=[...element.querySelectorAll(':scope > .rq-tree-body > .rq-tree-children > li > [data-structure-pick]:checked')].map(n=>n.dataset.structurePick);
  if(action==='link')request.target_id=button.closest('.rq-tree-link').querySelector('select').value;
  e.selected=uid;await e.step('structure',request);this.selection=null;
 }
}
