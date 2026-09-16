import {semanticClass} from './markdown-content.js';
import {quantityPreset,quantityMode,quantityPreview,quantityRange} from './quantity.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const roles=['Subject','Modal Verb','Main Verb','Object','conditions','exceptions','subrequirement'];
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
export const plainField=n=>n.kind==='group'&&!n.span&&(!n.negated||n.role==='conditions')&&n.role!=='requirements'&&n.quantity===1&&n.children.length===1&&['fragment','reference'].includes(n.children[0].kind);
export function structureLabels(doc,unitLabels={}){let g=Object.keys(doc.units||{}).length,f=0;const labels={};for(const t of Object.values({...doc.structure_views,...doc.structures}))for(const n of treeNodes(t))labels[n.id]=n.kind==='fragment'?`F${++f}`:n.kind==='reference'?(unitLabels[n.target_id]||n.target_id):plainField(n)?n.role:`G${++g}`;return labels;}
const control=(action,text,attrs='')=>`<button type="button" data-straction="${action}" ${attrs}>${text}</button>`;
export class StructureEditor{
 constructor(editor){this.e=editor;this.closed=new Set();this.qcOpen=new Set();this.rangeModes=new Map();this.selection=null;}
 tree(uid){return this.e.doc.structures?.[uid]||this.e.doc.structure_views?.[uid];}
 labels(tree){const unitLabels=Object.fromEntries(Object.keys(this.e.doc.units||{}).map(id=>[id,this.e.internalLabel?.(id)||this.e.label(id)]));return structureLabels({...this.e.doc,structure_views:{...this.e.doc.structure_views,...(!Object.values({...this.e.doc.structure_views,...this.e.doc.structures}).some(t=>t.id===tree.id)?{fallback:tree}:{})}},unitLabels);}

 unitMarkup(u,complete,inline){
  const e=this.e,done=e.doc.done.includes(u.id),tree=this.tree(u.id),disabled=e.locked||complete||done;
  const root= !inline && e.rootIds?.(e.doc)?.length===1 && e.rootIds(e.doc)[0]===u.id;
  const body=`<div class="rq-unit-body rq-structure-editor">${done&&!complete?'<button type="button" data-rq="reopen">Continue decomposing</button>':''}${this.nodeMarkup(tree,u,tree,this.labels(tree),disabled,true)}${!complete?`<div class="rq-unit-finish"><button type="button" data-rq="done" ${disabled?'disabled':''}>Finish &amp; collapse</button></div>`:''}</div>`;
  if(root)return `<section class="rq-unit rq-entry-root" data-unit="${esc(u.id)}" aria-current="${u.id===e.selected}">${body}</section>`;
  return `<details class="rq-unit${inline?' rq-inline-condition':''}" data-unit="${esc(u.id)}" aria-current="${u.id===e.selected}" ${!e.closedUnits.has(u.id)?'open':''}><summary data-rq="select-unit" data-id="${esc(u.id)}" data-toggle="true"><strong>${esc(e.internalLabel?.(u.id)||e.label(u.id))}</strong><span class="rq-unit-preview">${esc(u.text.slice(0,100))}</span><span class="rq-badge">${done?'Finished':'Editing'}</span></summary>${body}</details>`;
 }
 toolsMarkup(allowed=roles){return `<div class="rq-selection-tools" data-selection-tools hidden role="toolbar" aria-label="Assign selected source text"><span class="rq-tool-section">${control('add-group','Group')}${control('degroup-range','Degroup')}</span><span class="rq-tool-divider" aria-hidden="true"></span><span class="rq-tool-section">${allowed.filter(role=>!['exceptions','subrequirement','requirements'].includes(role)).map(role=>control('add',esc(role),`data-field="${role}" class="semantic ${semanticClass(role)}"`)).join('')}${control('clear-range','❌','aria-label="Remove selected field marks" title="Remove field marks; keep Groups"')}</span></div>`;}
 sourceMarkup(node,u,tree,disabled){
  const span=node.span||[0,Array.from(u.text).length],allowed=node.kind==='clause'?(this.e.doc.roles?.[u.id]==='condition'?['conditions']:roles):[node.role];
  const offset=this.e.doc.spans?.[u.id]?.[0]||0,referenceSpans=Object.fromEntries(Object.entries(this.e.doc.spans||{}).map(([id,span])=>[id,span.map(n=>n-offset)]));
  return `<div class="rq-group-source" data-source-node="${esc(node.id)}" data-source-owner="${esc(u.id)}" data-source-start="${span[0]}"><div class="rq-selectable-source" data-structure-source tabindex="0" contenteditable="true" spellcheck="false" role="textbox" aria-readonly="true" aria-label="Original text for ${esc(node.id)}">${treeSource(tree,u.text,span,referenceSpans)}</div>${!disabled?this.toolsMarkup(allowed):''}</div>`;
 }
 nodeMarkup(node,u,tree,labels,disabled,root=false){
  const id=esc(node.id),label=labels[node.id],text=node.span?Array.from(u.text).slice(...node.span).join(''):'';
  if(node.kind==='fragment')return `<div class="rq-tree-leaf semantic ${semanticClass(node.role)}" data-structure-node="${id}" data-owner="${u.id}"><span class="rq-tree-id">${label}</span><span>${esc(node.text)}</span>${!disabled?control('decompose','Decompose',` ${node.span?'':'disabled title="Source position is unresolved"'}`)+control('remove','Remove'):''}</div>`;
  if(node.kind==='reference'&&['exceptions','subrequirement'].includes(node.role)){
   const local=this.e.doc.units[node.target_id],linked=this.e.completeRequirements(u.id).find(v=>v.id===node.target_id);
   return `<div class="rq-tree-leaf rq-linked-requirement semantic ${semanticClass(node.role)}" data-structure-node="${id}" data-owner="${u.id}">${local?`<span class="rq-hint">Earlier inline item · ${esc(this.e.internalLabel?.(node.target_id)||node.target_id)}</span><span>${esc(local.text)}</span><details><summary>Saved decomposition</summary>${this.unitMarkup(local,true,true)}</details>`:`<button type="button" data-rq="select-unit" data-id="${esc(node.target_id)}">${esc(this.e.label(node.target_id))}</button><span>${esc(linked?.text||this.e.unitText(node.target_id))}</span>`}${!disabled?control('remove','Unlink','title="Remove this relationship only; keep the referenced Requirement"'):''}</div>`;
  }
  if(node.kind==='reference'&&this.e.doc.units[node.target_id])return `<div class="rq-tree-reference" data-structure-node="${id}" data-owner="${u.id}">${this.unitMarkup(this.e.doc.units[node.target_id],disabled,true)}${!disabled?control('remove','Remove reference'):''}</div>`;
  if(node.kind==='reference')return `<div class="rq-tree-leaf rq-tree-reference" data-structure-node="${id}" data-owner="${u.id}"><button type="button" data-rq="decompose" data-id="${esc(node.target_id)}">${esc(this.e.label(node.target_id))}</button><span>${esc(this.e.unitText(node.target_id))}</span>${!disabled?control('remove','Remove'):''}</div>`;
  if(node.kind==='group'&&['exceptions','subrequirement'].includes(node.role))return `<section class="rq-reference-picker semantic ${semanticClass(node.role)}" data-structure-node="${id}" data-owner="${u.id}"><strong>${node.role==='exceptions'?'Exception':'Subrequirement'}</strong>${node.children.length>1?this.qcMarkup(node,disabled):''}${node.children.map(child=>this.nodeMarkup(child,u,tree,labels,disabled||child.kind==='clause')).join('')}${this.linkMarkup(u,node,disabled)}</section>`;
  if(plainField(node))return `<div class="rq-plain-field semantic ${semanticClass(node.role)}" data-structure-node="${id}" data-owner="${u.id}"><div class="rq-plain-field-title"><strong>${esc(node.role)}</strong>${node.negated?'<small>Saved NOT annotation · read-only</small>':''}</div>${node.children.map(child=>this.nodeMarkup(child,u,tree,labels,disabled)).join('')}</div>`;
  const group=node.kind==='group',kind=group?'Group · '+node.role:'Group',summary=`<strong>${label}</strong><span>${esc(kind)}</span>${node.negated?'<small class="rq-not-label">Saved NOT annotation · read-only</small>':''}${group?control('show-qc',`${node.quantity===null?'?':quantityPreview(node.quantity)}`,'class="rq-tree-count" title="Show quantity controls"'):''}${!root&&text?`<span class="rq-tree-summary">${esc(text)}</span>`:''}`;
  const children=node.children.map(child=>`<li>${group&&!disabled?`<input type="checkbox" data-structure-pick="${esc(child.id)}" aria-label="Select ${labels[child.id]} in ${label}">`:''}${this.nodeMarkup(child,u,tree,labels,disabled)}</li>`).join('');
  return `<${root?'section':'details'} class="rq-tree-node ${group?'rq-tree-group semantic '+semanticClass(node.origin_role||node.role):'rq-tree-clause'}" data-structure-node="${id}" data-owner="${u.id}" ${!root&&!this.closed.has(node.id)?'open':''}>${root?'':`<summary>${summary}</summary>`}<div class="rq-tree-body">${node.span&&!(root&&this.e.rootIds?.(this.e.doc)?.length===1&&this.e.rootIds(this.e.doc)[0]===u.id)?this.sourceMarkup(node,u,tree,disabled):''}${root&&!disabled?'<p class="rq-hint">Select original wording to add a field or Group. Shared conditions stay in the enclosing Group.</p>':''}${group&&(node.children.length>1||node.quantity!==1||this.qcOpen.has(node.id))?this.qcMarkup(node,disabled):''}${group?`<div class="rq-tree-actions">${!disabled&&!['exceptions','subrequirement'].includes(node.role)?control('group','Group selected')+control('ungroup','Degroup',`title="Expand an All group within another All group"`):''}</div>`:''}<ol class="rq-tree-children">${children}</ol>${!node.children.length?'<p class="rq-blank">Select wording above to add items.</p>':''}${this.e.doc.roles?.[u.id]!=='condition'&&(node.kind==='clause'||['subrequirement','exceptions'].includes(node.role))?this.linkMarkup(u,node,disabled):''}</div></${root?'section':'details'}>`;
 }
 linkMarkup(u,node={},disabled=false){
  const fields=node.kind==='group'?[node.role]:['subrequirement','exceptions'].filter(role=>!node.children?.some(n=>n.role===role));
  return fields.map(role=>{const linked=new Set(treeNodes(node).filter(n=>n.kind==='reference'&&n.role===role).map(n=>n.target_id)),choices=this.e.completeRequirements(u.id).filter(v=>!linked.has(v.id));
   const title=role==='exceptions'?'Exception':'Subrequirement';
   return `<section class="rq-reference-picker semantic ${semanticClass(role)}"><strong>${title}</strong><div class="rq-tree-link" data-reference-role="${role}"><label>Link another Requirement<select data-structure-reference aria-label="${title} Requirement" ${disabled||!choices.length?'disabled':''}><option value="">Choose a Requirement…</option>${choices.map(v=>`<option value="${esc(v.id)}">${esc(this.e.label(v.id))} · ${esc(v.text.slice(0,90))}</option>`).join('')}</select></label>${control('link','Link',disabled||!choices.length?'disabled':'')}</div>${!choices.length?'<small>No other available Requirement.</small>':''}</section>`;
  }).join('');
 }
 qcMarkup(node,disabled){
  const count=node.children.length,q=node.quantity,mode=quantityMode(q,count),custom=this.rangeModes.get(node.id)??(q!==null&&mode==='custom'),values=Array.isArray(q)?q:[q??'',q??''];
  return `<div class="rq-qc-row" data-rq-qc data-structure-qc data-count="${count}"><output data-rq-preview class="rq-qc-preview" aria-live="polite">${q===null?'Set QC':quantityPreview(q)}</output><div class="rq-quantity-presets">${[['all','All'],['any','Any'],['one','Only'],['not-all','Not All']].map(([preset,label])=>control('preset',label,`data-preset="${preset}" title="${preset==='not-all'?'At least one, fewer than all':preset==='all'?`K = ${count}`:preset==='any'?`[1, ${count}]`:'K = 1'}" aria-pressed="${!custom&&mode===preset}" ${disabled||!count||(preset==='not-all'&&count<2)?'disabled':''}`)).join('')}${control('range-mode','MIN–MAX',`aria-pressed="${custom}" ${disabled||!count?'disabled':''}`)}</div><input data-rq-min aria-label="Minimum" inputmode="numeric" pattern="[0-9]*" value="${values[0]}" ${disabled||!count||!custom?'disabled':''}><span>-</span><input data-rq-max aria-label="Maximum" inputmode="numeric" pattern="[0-9]*" value="${values[1]}" ${disabled||!count||!custom?'disabled':''}></div><small class="rq-qc-error" data-qc-error hidden role="status"></small>`;
 }
 bind(host){
  host.querySelectorAll?.('[data-entry-source] > .rq-source-preview').forEach(source=>{source.setAttribute('data-structure-source','');source.setAttribute('contenteditable','true');source.setAttribute('role','textbox');source.setAttribute('aria-readonly','true');source.setAttribute('aria-label','Requirement original text');source.setAttribute('spellcheck','false');});
  host.querySelectorAll?.('[data-structure-source]').forEach(source=>{
   source.onbeforeinput=event=>event.preventDefault();source.onpaste=event=>event.preventDefault();source.oncut=event=>event.preventDefault();source.ondrop=event=>event.preventDefault();
   const capture=event=>{
    const selection=window.getSelection();if(!selection?.rangeCount||selection.isCollapsed){host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=true);return;}
    const range=selection.getRangeAt(0);if(!source.contains(range.startContainer)||!source.contains(range.endContainer))return;
    const prefix=range.cloneRange();prefix.selectNodeContents(source);prefix.setEnd(range.startContainer,range.startOffset);
    const entry=source.closest('[data-entry-source]'),container=entry||source.closest('[data-source-node]');
    let start=Number(container.dataset.sourceStart||0)+Array.from(prefix.toString()).length,end=start+Array.from(range.toString()).length,uid=container.dataset.sourceOwner,id=container.dataset.sourceNode;
    if(entry){const candidates=Object.entries(this.e.doc.spans).filter(([,s])=>s[0]<=start&&s[1]>=end).sort((a,b)=>(b[1][1]-b[1][0])-(a[1][1]-a[1][0]));if(!candidates.length)return;uid=candidates[0][0];start-=candidates[0][1][0];end-=candidates[0][1][0];id=this.tree(uid).id;}
    const tree=this.tree(uid),containers=treeNodes(tree).filter(n=>['clause','group'].includes(n.kind)&&n.span&&n.span[0]<=start&&n.span[1]>=end).sort((a,b)=>(a.span[1]-a.span[0])-(b.span[1]-b.span[0]));
    if(containers.length)id=containers[0].id;
    this.selection={unit_id:uid,node_id:id,start,end};
    host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=n.parentElement!==container);
    const bar=container.querySelector('[data-selection-tools]');if(bar){const rect=range.getBoundingClientRect();bar.style.left=Math.max(8,Math.min(event?.clientX??rect.left,window.innerWidth-bar.offsetWidth-8))+'px';bar.style.top=Math.max(8,Math.min((event?.clientY??rect.bottom)+10,window.innerHeight-bar.offsetHeight-8))+'px';}

   };source.onmouseup=capture;source.onkeyup=capture;
  });
  host.onmousedown=event=>{if(!event.target.closest('[data-selection-tools],[data-structure-source]'))host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=true);};
  host.onkeydown=event=>{if(event.key==='Escape')host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=true);};
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
  if(button.dataset.straction==='not')throw Error('Explicit NOT editing is unavailable. Keep negation in the original wording.');
  const element=button.closest('[data-structure-node]'),action=button.dataset.straction,fromSelection=['add','add-group','degroup-range','clear-range'].includes(action),uid=fromSelection?this.selection?.unit_id:element?.dataset.owner,id=fromSelection?this.selection?.node_id:element?.dataset.structureNode;
  if(!uid||!id)throw Error('Select original wording first.');
  if(action==='show-link'){const picker=element.querySelector(':scope > .rq-tree-body > .rq-reference-picker');if(picker){picker.open=true;picker.querySelector('select')?.focus();}return;}
  if(action==='show-qc'){if(this.qcOpen.has(id))this.qcOpen.delete(id);else this.qcOpen.add(id);e.render(true);return;}
  if(e.locked)return;
  if(action==='range-mode'){this.rangeModes.set(id,true);e.render(true);e.host.querySelector(`[data-structure-node="${id}"] [data-rq-min]`)?.focus();return;}
  for(const row of e.host.querySelectorAll('[data-rq-qc]')){if(action==='preset'&&row.contains(button))continue;if(row.commitQuantity&&!(await row.commitQuantity()))return;}
  const model=treeNodes(this.tree(uid)).find(n=>n.id===id);if(!model)return;
  let request={unit_id:uid,node_id:id,operation:action};
  if(fromSelection){
   if(!this.selection||this.selection.unit_id!==uid||this.selection.node_id!==id)throw Error('Select the original wording in this group first.');
   request={...request,...this.selection,field:button.dataset.field};
  }
  if(action==='preset'){this.rangeModes.set(id,false);request.operation='quantity';request.quantity=quantityPreset(button.dataset.preset,model.children.length);e.quantityDrafts.delete('tree:'+uid+':'+id);}
  if(action==='group')request.selected=[...element.querySelectorAll(':scope > .rq-tree-body > .rq-tree-children > li > [data-structure-pick]:checked')].map(n=>n.dataset.structurePick);
  if(action==='link'){const link=button.closest('.rq-tree-link');request.target_id=link.querySelector('[data-structure-reference]').value;request.field=link.dataset.referenceRole;if(!request.target_id)throw Error('Choose another Requirement to link.');}
  if(e.doc.phase==='complete'){if(!(await e.step('phase',{phase:'fields'})))return;}else if(e.doc.done.includes(uid)){if(!(await e.step('reopen',{unit_id:uid})))return;}
  e.selected=uid;await e.step('structure',request);this.selection=null;
 }
}
